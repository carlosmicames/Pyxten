import { createClient } from './supabaseClient'

const DOCUMENTS_BUCKET = 'documents'

export interface UploadResult {
  success: boolean
  url?: string
  fileName?: string
  error?: string
}

/**
 * Upload a document to Supabase Storage
 * @param file - The file to upload
 * @param validationId - The document validation ID (used for organizing files)
 * @param docCode - The document requirement code
 * @returns Upload result with public URL
 */
export async function uploadDocument(
  file: File,
  validationId: string,
  docCode: string
): Promise<UploadResult> {
  const supabase = createClient()

  // Validate file type (PDF only)
  if (file.type !== 'application/pdf') {
    return {
      success: false,
      error: 'Solo se permiten archivos PDF',
    }
  }

  // Validate file size (max 10MB)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    return {
      success: false,
      error: 'El archivo no puede exceder 10MB',
    }
  }

  // Create a unique file path: validations/{validationId}/{docCode}_{timestamp}.pdf
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
        error: error.message || 'Error al subir el archivo',
      }
    }

    // Get the public URL
    const { data: urlData } = supabase.storage
      .from(DOCUMENTS_BUCKET)
      .getPublicUrl(data.path)

    return {
      success: true,
      url: urlData.publicUrl,
      fileName: file.name,
    }
  } catch (err) {
    console.error('Upload error:', err)
    return {
      success: false,
      error: 'Error inesperado al subir el archivo',
    }
  }
}

/**
 * Delete a document from Supabase Storage
 * @param fileUrl - The public URL of the file to delete
 * @returns Success status
 */
export async function deleteDocument(fileUrl: string): Promise<boolean> {
  const supabase = createClient()

  try {
    // Extract the path from the URL
    const url = new URL(fileUrl)
    const pathMatch = url.pathname.match(/\/storage\/v1\/object\/public\/documents\/(.+)/)

    if (!pathMatch) {
      console.error('Could not extract file path from URL')
      return false
    }

    const filePath = pathMatch[1]

    const { error } = await supabase.storage
      .from(DOCUMENTS_BUCKET)
      .remove([filePath])

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
