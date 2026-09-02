'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  AuditEvent,
  CASE_STATUS_LABELS,
  CaseDocument,
  CaseRecord,
  DocumentType,
  ReviewerIdentity,
  formatDate,
  reviewerApi,
} from '@/lib/reviewerApi'
import DocumentUploader from '@/components/reviewer/DocumentUploader'
import SinAcceso from '@/components/reviewer/SinAcceso'

/** Human-readable names for what the audit trail records. */
const EVENT_LABELS: Record<string, string> = {
  case_created: 'Expediente abierto',
  case_updated: 'Expediente actualizado',
  document_uploaded: 'Documento subido',
  document_duplicate_rejected: 'Documento duplicado rechazado',
  document_classified: 'Documento clasificado',
  document_classification_failed: 'Clasificacion no completada',
  document_type_overridden: 'Tipo corregido por el revisor',
  document_viewed: 'Documento consultado',
}

export default function CasoPage() {
  const params = useParams<{ id: string }>()
  const caseId = params?.id

  const [identity, setIdentity] = useState<ReviewerIdentity | null>(null)
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null)
  const [documents, setDocuments] = useState<CaseDocument[]>([])
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [showAudit, setShowAudit] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!caseId) return

    const load = async () => {
      const me = await reviewerApi.me()
      setIdentity(me)

      if (me) {
        try {
          const [detail, types] = await Promise.all([
            reviewerApi.getCase(caseId),
            reviewerApi.taxonomy(),
          ])
          setCaseRecord(detail.case)
          setDocuments(detail.documents)
          setDocumentTypes(types)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error cargando el expediente')
        }
      }
      setLoading(false)
    }
    load()
  }, [caseId])

  const loadAudit = async () => {
    if (!caseId) return
    setShowAudit(true)
    try {
      setAuditEvents(await reviewerApi.auditTrail(caseId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error cargando la bitacora')
    }
  }

  if (loading) return <div className="p-8 text-gray-500">Cargando...</div>
  if (!identity) return <SinAcceso />

  if (!caseRecord) {
    return (
      <div className="p-8 max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-900">Expediente no encontrado</h1>
        <p className="text-gray-600 mt-2">
          {error || 'El expediente no existe o no pertenece a su oficina.'}
        </p>
        <Link href="/revisor/bandeja" className="btn-secondary inline-block mt-6">
          Volver a la bandeja
        </Link>
      </div>
    )
  }

  const sinClasificar = documents.filter((d) => d.doc_type === 'desconocido').length
  const bajaConfianza = documents.filter((d) => d.classification_band === 'baja').length

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <Link href="/revisor/bandeja" className="text-sm text-primary-700 hover:underline">
          ← Bandeja de expedientes
        </Link>
        <div className="flex items-baseline gap-3 mt-2 flex-wrap">
          <h1 className="text-2xl font-bold text-gray-900 font-mono">
            {caseRecord.case_number}
          </h1>
          <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
            {CASE_STATUS_LABELS[caseRecord.status] || caseRecord.status}
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6 text-sm">
          {error}
        </div>
      )}

      {/* ---------- Case facts ---------- */}
      <section className="card mb-6">
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <Campo label="Solicitante" value={caseRecord.applicant_name} />
          <Campo label="Catastro" value={caseRecord.catastro} mono />
          <Campo label="Direccion" value={caseRecord.property_address} />
          <Campo label="Tipo de permiso" value={caseRecord.permit_type} />
          <div className="sm:col-span-2 pt-2 border-t border-gray-100">
            <dt className="text-gray-500 text-xs uppercase tracking-wide">
              Version de reglamento aplicada
            </dt>
            <dd className="font-mono text-xs text-gray-700 mt-0.5">
              {caseRecord.ruleset_version_id}
            </dd>
          </div>
        </dl>
      </section>

      {/* ---------- What needs a person ---------- */}
      {documents.length > 0 && (sinClasificar > 0 || bajaConfianza > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-md px-4 py-3 mb-6 text-sm text-amber-900">
          <p className="font-medium">Requiere criterio del revisor</p>
          <ul className="list-disc list-inside mt-1 space-y-0.5">
            {sinClasificar > 0 && (
              <li>
                {sinClasificar}{' '}
                {sinClasificar === 1
                  ? 'documento quedo sin clasificar'
                  : 'documentos quedaron sin clasificar'}
                .
              </li>
            )}
            {bajaConfianza > 0 && (
              <li>
                {bajaConfianza}{' '}
                {bajaConfianza === 1
                  ? 'documento tiene confianza baja'
                  : 'documentos tienen confianza baja'}{' '}
                y debe confirmarse manualmente.
              </li>
            )}
          </ul>
        </div>
      )}

      {/* ---------- Documents ---------- */}
      <section className="card mb-6">
        <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
          <h2 className="text-lg font-semibold text-gray-900">
            Documentos ({documents.length})
          </h2>
        </div>

        <DocumentUploader
          caseId={caseRecord.id}
          documents={documents}
          documentTypes={documentTypes}
          canWrite={identity.can_write}
          onDocumentsChanged={setDocuments}
        />
      </section>

      {/* ---------- Audit trail ---------- */}
      <section className="card">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Bitacora</h2>
            <p className="text-sm text-gray-600 mt-1">
              Registro completo e inalterable de lo ocurrido en este expediente.
            </p>
          </div>
          {!showAudit && (
            <button type="button" onClick={loadAudit} className="btn-secondary">
              Ver bitacora
            </button>
          )}
        </div>

        {showAudit && (
          <div className="mt-4">
            {auditEvents.length === 0 ? (
              <p className="text-sm text-gray-500">Sin eventos registrados.</p>
            ) : (
              <ol className="space-y-2">
                {auditEvents.map((event) => (
                  <li
                    key={event.id}
                    className="text-sm border-l-2 border-gray-200 pl-3 py-1"
                  >
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <span className="font-medium text-gray-900">
                        {EVENT_LABELS[event.event_type] || event.event_type}
                      </span>
                      <span className="text-xs text-gray-500 font-mono">
                        {formatDate(event.created_at)}
                      </span>
                    </div>
                    {Object.keys(event.payload || {}).length > 0 && (
                      <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap break-words font-mono">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

function Campo({
  label,
  value,
  mono,
}: {
  label: string
  value?: string | null
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-gray-500 text-xs uppercase tracking-wide">{label}</dt>
      <dd className={`text-gray-900 mt-0.5 ${mono ? 'font-mono' : ''}`}>
        {value || <span className="text-gray-400">No indicado</span>}
      </dd>
    </div>
  )
}
