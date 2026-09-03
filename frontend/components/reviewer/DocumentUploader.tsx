'use client'

import { useRef, useState } from 'react'
import {
  CaseDocument,
  DocumentType,
  formatDate,
  reviewerApi,
} from '@/lib/reviewerApi'
import { BandaChip, FuenteChip, OcrChip, ProcesamientoChip } from './Chips'

interface Props {
  caseId: string
  documents: CaseDocument[]
  documentTypes: DocumentType[]
  canWrite: boolean
  onDocumentsChanged: (documents: CaseDocument[]) => void
}

export default function DocumentUploader({
  caseId,
  documents,
  documentTypes,
  canWrite,
  onDocumentsChanged,
}: Props) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejected, setRejected] = useState<{ filename: string; reason: string }[]>([])
  const [openingId, setOpeningId] = useState<string | null>(null)
  const [savingTypeFor, setSavingTypeFor] = useState<string | null>(null)

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return

    const files = Array.from(fileList)
    setUploading(true)
    setError(null)
    setRejected([])

    try {
      const outcome = await reviewerApi.uploadDocuments(caseId, files)
      onDocumentsChanged([...documents, ...outcome.documents])
      setRejected(outcome.rejected)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error subiendo los documentos')
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  const handleOpen = async (documentId: string) => {
    setOpeningId(documentId)
    setError(null)
    try {
      const { url } = await reviewerApi.documentUrl(documentId)
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo abrir el documento')
    } finally {
      setOpeningId(null)
    }
  }

  const handleTypeChange = async (documentId: string, docType: string) => {
    setSavingTypeFor(documentId)
    setError(null)
    try {
      const updated = await reviewerApi.setDocumentType(documentId, docType)
      onDocumentsChanged(documents.map((d) => (d.id === documentId ? updated : d)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el tipo')
    } finally {
      setSavingTypeFor(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* ---------- Drop zone ---------- */}
      {canWrite && (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300 bg-white'
          }`}
        >
          <input
            ref={fileInput}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />

          {uploading ? (
            <div className="text-gray-600">
              <p className="font-medium">Procesando documentos...</p>
              <p className="text-sm mt-1">
                Se esta extrayendo el texto y clasificando cada archivo. Esto puede tomar
                un momento.
              </p>
            </div>
          ) : (
            <>
              <p className="text-gray-700 font-medium">
                Arrastre los PDF del expediente aqui
              </p>
              <p className="text-sm text-gray-500 mt-1">
                Puede subir varios a la vez. Solo PDF, hasta 25 MB por archivo.
              </p>
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                className="btn-primary mt-4"
              >
                Seleccionar archivos
              </button>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {rejected.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md text-sm">
          <p className="font-medium mb-1">
            {rejected.length === 1
              ? 'Un archivo no se pudo agregar:'
              : `${rejected.length} archivos no se pudieron agregar:`}
          </p>
          <ul className="list-disc list-inside space-y-0.5">
            {rejected.map((r) => (
              <li key={r.filename}>
                <span className="font-medium">{r.filename}</span> — {r.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---------- Document list ---------- */}
      {documents.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-6">
          Aun no hay documentos en este expediente.
        </p>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="bg-white border border-gray-200 rounded-lg p-4"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => handleOpen(doc.id)}
                      disabled={openingId === doc.id}
                      className="font-medium text-primary-700 hover:underline text-left truncate max-w-md disabled:opacity-60"
                      title="Abrir documento"
                    >
                      {openingId === doc.id ? 'Abriendo...' : doc.filename}
                    </button>
                    <ProcesamientoChip status={doc.processing_status} />
                  </div>

                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <span className="text-sm text-gray-900 font-medium">
                      {doc.doc_type_label}
                    </span>
                    <BandaChip band={doc.classification_band} />
                    <FuenteChip source={doc.doc_type_source} />
                    <OcrChip status={doc.ocr_status} />
                  </div>

                  {/* Why the system reached this conclusion, in its own words. */}
                  {doc.classification_reason && (
                    <p className="text-xs text-gray-600 mt-2">
                      <span className="font-medium">Motivo:</span>{' '}
                      {doc.classification_reason}
                    </p>
                  )}

                  {/* Evidence pointer. Every conclusion names where it came from. */}
                  <p className="text-xs text-gray-500 mt-1 font-mono">
                    {doc.page_count ?? '—'} pag.
                    {doc.classification_page
                      ? ` · evidencia en p. ${doc.classification_page}`
                      : ' · sin pagina de evidencia'}
                    {' · '}
                    {formatDate(doc.uploaded_at)}
                  </p>
                </div>

                {/* Reviewer override */}
                {canWrite && (
                  <div className="w-full sm:w-64">
                    <label className="label text-xs">Tipo de documento</label>
                    <select
                      value={doc.doc_type}
                      disabled={savingTypeFor === doc.id}
                      onChange={(e) => handleTypeChange(doc.id, e.target.value)}
                      className="input-field text-sm"
                    >
                      {documentTypes.map((t) => (
                        <option key={t.code} value={t.code}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      {savingTypeFor === doc.id
                        ? 'Guardando...'
                        : 'Su seleccion queda registrada en la bitacora.'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
