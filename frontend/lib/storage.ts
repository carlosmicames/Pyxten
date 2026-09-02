import { createClient } from './supabaseClient'

const DOCUMENTS_BUCKET = 'documents'

/**
 * How long a generated download link stays valid, in seconds.
 * Short on purpose: the link is created the moment the user clicks, so it only
 * has to survive the browser opening it.
 */
const SIGNED_URL_TTL_SECONDS = 60

export interface UploadResult {
  success: boolean
  /**
   * Path of the object inside the `documents` bucket, e.g.
   * `validations/<id>/planos_<ts>_file.pdf`.
   *
   * This is what gets saved on the validation record. We deliberately store the
   * path rather than a URL: the bucket is private, so a URL is only valid for a
   * minute and must be generated on demand.
   */
  path?: string
  fileName?: string
  error?: string
}

/**
 * Turn whatever is stored on a document record into a bucket path.
 *
 * Two shapes exist in the database:
 *   1. Rows written before the bucket was made private hold a full public URL
 *      (`https://<ref>.supabase.co/storage/v1/object/public/documents/<path>`).
 *   2. Rows written from now on hold the bare path.
 *
 * Both resolve to the same path, so old records keep working with no backfill.
 */
export function resolveStoragePath(stored: string): string | null {
  if (!stored) return null

  // Shape 2: already a path.
  if (!stored.startsWith('http://') && !stored.startsWith('https://')) {
    return stored.replace(/^\/+/, '')
  }

  // Shape 1: legacy public (or signed) URL - pull the path back out of it.
  try {
    const url = new URL(stored)
    const match = url.pathname.match(
      /\/storage\/v1\/object\/(?:public|sign)\/documents\/(.+)$/
    )
    return match ? decodeURIComponent(match[1]) : null
  } catch {
    return null
  }
}

/**
 * Upload a document to Supabase Storage.
 *
 * @param file - the PDF to upload
 * @param validationId - document validation this file belongs to; it becomes the
 *   second path segment, which is what the storage RLS policy checks ownership against
 * @param docCode - the document requirement code
 */
export async function uploadDocument(
  file: File,
  validationId: string,
  docCode: string
): Promise<UploadResult> {
  const supabase = createClient()

  if (file.type !== 'application/pdf') {
    return { success: false, error: 'Solo se permiten archivos PDF' }
  }

  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    return { success: false, error: 'El archivo no puede exceder 10MB' }
  }

  const timestamp = Date.now()
  const sanitizedFileName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_')
  const filePath = `validations/${validationId}/${docCode}_${timestamp}_${sanitizedFileName}`

  try {
    const { data, error } = await supabase.storage
      .from(DOCUMENTS_BUCKET)
      .upload(filePath, file, {
        cacheControl: '3600',
        upsert: false,
      })

    if (error) {
      console.error('Storage upload error:', error)
      return {
        success: false,
        error:
          'No se pudo subir el archivo. Si el problema persiste, verifique los permisos del almacenamiento.',
      }
    }

    return { success: true, path: data.path, fileName: file.name }
  } catch (err) {
    console.error('Upload error:', err)
    return { success: false, error: 'Error inesperado al subir el archivo' }
  }
}

/**
 * Create a short-lived link for viewing a stored document.
 *
 * The bucket is private, so there is no permanent URL - one is minted per click
 * and expires shortly after. Returns null when the file cannot be signed (moved,
 * deleted, or not owned by the signed-in user).
 */
export async function getDocumentUrl(stored: string): Promise<string | null> {
  const path = resolveStoragePath(stored)
  if (!path) return null

  const supabase = createClient()

  const { data, error } = await supabase.storage
    .from(DOCUMENTS_BUCKET)
    .createSignedUrl(path, SIGNED_URL_TTL_SECONDS)

  if (error) {
    console.error('Storage sign error:', error)
    return null
  }

  return data?.signedUrl ?? null
}

/**
 * Delete a document from Supabase Storage.
 * Accepts either a stored path or a legacy public URL.
 */
export async function deleteDocument(stored: string): Promise<boolean> {
  const path = resolveStoragePath(stored)
  if (!path) {
    console.error('Could not resolve a storage path from:', stored)
    return false
  }

  const supabase = createClient()

  try {
    const { error } = await supabase.storage.from(DOCUMENTS_BUCKET).remove([path])

    if (error) {
      console.error('Storage delete error:', error)
      return false
    }

    return true
  } catch (err) {
    console.error('Delete error:', err)
    return false
  }
}
