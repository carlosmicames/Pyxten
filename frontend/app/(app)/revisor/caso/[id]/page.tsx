'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  AuditEvent,
  CASE_STATUS_LABELS,
  CaseDocument,
  CaseProfile,
  CaseRecord,
  CheckSummary,
  ComplianceCheck,
  DocumentType,
  ExtractionOutcome,
  GIS_SOURCE_LABELS,
  GisOutcome,
  QUALITY_LABELS,
  ReviewerIdentity,
  formatDate,
  reviewerApi,
} from '@/lib/reviewerApi'
import ChecksPanel from '@/components/reviewer/ChecksPanel'
import DocumentUploader from '@/components/reviewer/DocumentUploader'
import PerfilCaso from '@/components/reviewer/PerfilCaso'
import SinAcceso from '@/components/reviewer/SinAcceso'

const EVENT_LABELS: Record<string, string> = {
  case_created: 'Expediente abierto',
  case_updated: 'Expediente actualizado',
  document_uploaded: 'Documento subido',
  document_duplicate_rejected: 'Documento duplicado rechazado',
  document_classified: 'Documento clasificado',
  document_classification_failed: 'Clasificacion no completada',
  document_type_overridden: 'Tipo corregido por el revisor',
  document_viewed: 'Documento consultado',
  extraction_run: 'Lectura de documentos ejecutada',
  gis_lookup_run: 'Consulta de calificacion ejecutada',
  evaluation_run: 'Reglas evaluadas',
}

type Tab = 'verificaciones' | 'documentos' | 'perfil' | 'bitacora'

export default function CasoPage() {
  const params = useParams<{ id: string }>()
  const caseId = params?.id

  const [identity, setIdentity] = useState<ReviewerIdentity | null>(null)
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null)
  const [documents, setDocuments] = useState<CaseDocument[]>([])
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([])
  const [checks, setChecks] = useState<ComplianceCheck[]>([])
  const [summary, setSummary] = useState<CheckSummary | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])

  const [tab, setTab] = useState<Tab>('verificaciones')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<null | 'extract' | 'gis' | 'evaluate'>(null)
  const [extraction, setExtraction] = useState<ExtractionOutcome | null>(null)
  const [gisOutcome, setGisOutcome] = useState<GisOutcome | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadChecks = useCallback(async (id: string) => {
    const result = await reviewerApi.checks(id)
    setChecks(result.verificaciones)
    setSummary(result.resumen.total_evaluadas > 0 ? result.resumen : null)
  }, [])

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
          await loadChecks(caseId)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error cargando el expediente')
        }
      }
      setLoading(false)
    }
    load()
  }, [caseId, loadChecks])

  /**
   * Read the documents, look up the parcel, then run the rules.
   *
   * Order matters: the zoning lookup needs the activity declared on the
   * applicant's own patente, which extraction produces. One button, because
   * facts with no evaluation tell a reviewer nothing and evaluating without
   * re-reading would report a stale answer.
   */
  const handleAnalyze = async () => {
    if (!caseId) return
    setError(null)
    setExtraction(null)
    setGisOutcome(null)

    try {
      setRunning('extract')
      setExtraction(await reviewerApi.extract(caseId))

      // A GIS failure is a recorded escalation, not a reason to abandon the
      // run - the other thirty-two rules still have something to say.
      setRunning('gis')
      try {
        setGisOutcome(await reviewerApi.gis(caseId))
      } catch (gisError) {
        console.error('GIS lookup failed', gisError)
      }

      setRunning('evaluate')
      await reviewerApi.evaluate(caseId)
      await loadChecks(caseId)
      setTab('verificaciones')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo analizar el expediente')
    } finally {
      setRunning(null)
    }
  }

  const loadAudit = async () => {
    if (!caseId) return
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

  const unclassified = documents.filter((d) => d.doc_type === 'desconocido').length
  const lastEvaluated = checks.length ? checks[0].evaluated_at : null

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    {
      id: 'verificaciones',
      label: 'Verificaciones',
      badge: summary?.hallazgo_identificado || undefined,
    },
    { id: 'documentos', label: 'Documentos', badge: documents.length || undefined },
    { id: 'perfil', label: 'Perfil' },
    { id: 'bitacora', label: 'Bitacora' },
  ]

  return (
    <div className="p-8 max-w-5xl">
      {/* ---------- Header ---------- */}
      <div className="mb-6">
        <Link href="/revisor/bandeja" className="text-sm text-primary-700 hover:underline">
          ← Bandeja de expedientes
        </Link>
        <div className="flex items-start justify-between gap-4 flex-wrap mt-2">
          <div>
            <div className="flex items-baseline gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-gray-900 font-mono">
                {caseRecord.case_number}
              </h1>
              <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                {CASE_STATUS_LABELS[caseRecord.status] || caseRecord.status}
              </span>
            </div>
            <p className="text-gray-600 mt-1 text-sm">
              {caseRecord.applicant_name || 'Solicitante no indicado'}
              {caseRecord.property_address ? ` · ${caseRecord.property_address}` : ''}
            </p>
          </div>

          {identity.can_write && (
            <button
              type="button"
              className="btn-primary whitespace-nowrap"
              onClick={handleAnalyze}
              disabled={running !== null || documents.length === 0}
              title={
                documents.length === 0
                  ? 'Suba documentos antes de analizar'
                  : 'Lee los documentos y evalua las reglas'
              }
            >
              {running === 'extract'
                ? 'Leyendo documentos...'
                : running === 'gis'
                  ? 'Consultando calificacion...'
                  : running === 'evaluate'
                    ? 'Evaluando reglas...'
                    : 'Analizar expediente'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6 text-sm">
          {error}
        </div>
      )}

      {unclassified > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-md px-4 py-3 mb-6 text-sm text-amber-900">
          {unclassified === 1
            ? '1 documento quedo sin clasificar. No se leeran sus datos hasta que se le asigne un tipo.'
            : `${unclassified} documentos quedaron sin clasificar. No se leeran sus datos hasta que se les asigne un tipo.`}
        </div>
      )}

      {extraction && (
        <div className="bg-gray-50 border border-gray-200 rounded-md px-4 py-3 mb-6 text-sm text-gray-700">
          Se leyeron {extraction.campos_totales} campos en{' '}
          {extraction.procesados.length}{' '}
          {extraction.procesados.length === 1 ? 'documento' : 'documentos'}.
          {extraction.omitidos.length > 0 && (
            <> {extraction.omitidos.length} documento(s) omitidos por falta de tipo.</>
          )}
        </div>
      )}

      {gisOutcome && gisOutcome.consultas.length > 0 && (
        <div className="border border-gray-200 rounded-md px-4 py-3 mb-6 bg-white">
          <p className="text-sm font-medium text-gray-900 mb-2">Consultas externas</p>
          <ul className="space-y-1.5">
            {gisOutcome.consultas.map((consulta, index) => (
              <li key={`${consulta.source}-${index}`} className="text-sm">
                <span className="text-gray-700">
                  {GIS_SOURCE_LABELS[consulta.source] || consulta.source}
                </span>
                {': '}
                <span
                  className={
                    consulta.quality_flag === 'ok' ? 'text-gray-600' : 'text-amber-800'
                  }
                >
                  {QUALITY_LABELS[consulta.quality_flag] || consulta.quality_flag}
                </span>
                {consulta.valor && (
                  <span className="font-mono text-xs text-gray-500"> · {consulta.valor}</span>
                )}
                {consulta.nota && (
                  <p className="text-xs text-amber-800 mt-0.5">{consulta.nota}</p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---------- Tabs ---------- */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1 -mb-px flex-wrap">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setTab(item.id)
                if (item.id === 'bitacora' && auditEvents.length === 0) loadAudit()
              }}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === item.id
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {item.label}
              {item.badge !== undefined && (
                <span className="ml-1.5 text-xs tabular-nums text-gray-500">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* ---------- Panels ---------- */}
      {tab === 'verificaciones' && (
        <ChecksPanel
          checks={checks}
          summary={summary}
          documents={documents}
          evaluatedAt={lastEvaluated}
        />
      )}

      {tab === 'documentos' && (
        <DocumentUploader
          caseId={caseRecord.id}
          documents={documents}
          documentTypes={documentTypes}
          canWrite={identity.can_write}
          onDocumentsChanged={setDocuments}
        />
      )}

      {tab === 'perfil' && (
        <div className="card">
          <PerfilCaso
            caseId={caseRecord.id}
            profile={caseRecord.profile || {}}
            filingDate={caseRecord.filing_date}
            canWrite={identity.can_write}
            onSaved={(profile: CaseProfile, filingDate: string | null) =>
              setCaseRecord({ ...caseRecord, profile, filing_date: filingDate })
            }
          />
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm mt-6 pt-6 border-t border-gray-100">
            <Campo label="Catastro" value={caseRecord.catastro} mono />
            <Campo label="Tipo de permiso" value={caseRecord.permit_type} />
            <div className="sm:col-span-2">
              <dt className="text-gray-500 text-xs uppercase tracking-wide">
                Version de reglamento aplicada
              </dt>
              <dd className="font-mono text-xs text-gray-700 mt-0.5">
                {caseRecord.ruleset_version_id}
              </dd>
              <p className="text-xs text-gray-500 mt-1">
                Fija para este expediente. Si el reglamento cambia, este caso se
                sigue evaluando bajo las reglas vigentes al abrirlo.
              </p>
            </div>
          </dl>
        </div>
      )}

      {tab === 'bitacora' && (
        <div className="card">
          <p className="text-sm text-gray-600 mb-4">
            Registro completo e inalterable de lo ocurrido en este expediente.
          </p>
          {auditEvents.length === 0 ? (
            <p className="text-sm text-gray-500">Sin eventos registrados.</p>
          ) : (
            <ol className="space-y-2">
              {auditEvents.map((event) => (
                <li key={event.id} className="text-sm border-l-2 border-gray-200 pl-3 py-1">
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
