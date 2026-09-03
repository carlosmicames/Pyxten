'use client'

import { useState } from 'react'
import {
  Citation,
  CaseDocument,
  CheckStatus,
  CheckSummary,
  ComplianceCheck,
  DECISION_STATES,
  FAMILY_LABELS,
  REASON_LABELS,
  formatDate,
  reviewerApi,
} from '@/lib/reviewerApi'
import { BandaChip } from './Chips'

interface Props {
  checks: ComplianceCheck[]
  summary: CheckSummary | null
  documents: CaseDocument[]
  evaluatedAt: string | null
}

/** Findings first, then what needs a person, then what passed. */
const ORDER: CheckStatus[] = [
  'hallazgo_identificado',
  'requiere_criterio',
  'sin_hallazgos',
]

const STATUS_STYLES: Record<CheckStatus, { stripe: string; chip: string }> = {
  hallazgo_identificado: {
    stripe: 'border-l-red-500',
    chip: 'bg-red-100 text-red-800',
  },
  requiere_criterio: {
    stripe: 'border-l-amber-500',
    chip: 'bg-amber-100 text-amber-800',
  },
  sin_hallazgos: {
    stripe: 'border-l-green-500',
    chip: 'bg-green-100 text-green-800',
  },
}

export default function ChecksPanel({ checks, summary, documents, evaluatedAt }: Props) {
  const [openPassed, setOpenPassed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const documentsById = new Map(documents.map((d) => [d.id, d]))

  /**
   * Open the cited document at the cited page.
   *
   * The link is minted per click and expires; the page fragment is what most
   * PDF viewers use to jump straight to the evidence rather than page one.
   */
  const openCitation = async (documentId: string | null, page: number | null) => {
    if (!documentId) return
    setError(null)
    try {
      const { url } = await reviewerApi.documentUrl(documentId)
      window.open(page ? `${url}#page=${page}` : url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo abrir el documento')
    }
  }

  if (!summary || checks.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-6 text-center">
        Aun no se han evaluado las reglas para este expediente.
      </p>
    )
  }

  const grouped = ORDER.map((status) => ({
    status,
    items: checks.filter((c) => c.status === status),
  }))

  return (
    <div className="space-y-5">
      {/* ---------- Summary. State in form, not only in number. ---------- */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {ORDER.map((status) => {
          const count = summary[status]
          return (
            <div
              key={status}
              className={`border border-gray-200 border-l-4 ${STATUS_STYLES[status].stripe} bg-white rounded-r-lg px-4 py-3`}
            >
              <div className="text-2xl font-semibold text-gray-900 tabular-nums">
                {count}
              </div>
              <div className="text-xs text-gray-600 mt-0.5 leading-snug">
                {DECISION_STATES[status]}
              </div>
            </div>
          )
        })}
      </div>

      <p className="text-xs text-gray-500">
        {summary.total_evaluadas} verificaciones cubiertas
        {evaluatedAt ? ` · evaluado ${formatDate(evaluatedAt)}` : ''}. Este resumen
        describe unicamente las reglas evaluadas; no constituye una determinacion
        sobre la solicitud completa.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* ---------- The checks ---------- */}
      {grouped.map(({ status, items }) => {
        if (items.length === 0) return null

        const collapsible = status === 'sin_hallazgos'
        const visible = !collapsible || openPassed

        return (
          <section key={status}>
            <div className="flex items-center justify-between gap-3 mb-2">
              <h3 className="text-sm font-semibold text-gray-900">
                {DECISION_STATES[status]}{' '}
                <span className="text-gray-500 font-normal tabular-nums">
                  ({items.length})
                </span>
              </h3>
              {collapsible && (
                <button
                  type="button"
                  onClick={() => setOpenPassed(!openPassed)}
                  className="text-sm text-primary-700 hover:underline"
                >
                  {openPassed ? 'Ocultar' : 'Mostrar'}
                </button>
              )}
            </div>

            {visible && (
              <div className="space-y-2">
                {items.map((check) => (
                  <CheckCard
                    key={check.id}
                    check={check}
                    documentsById={documentsById}
                    onOpenCitation={openCitation}
                  />
                ))}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}

function CheckCard({
  check,
  documentsById,
  onOpenCitation,
}: {
  check: ComplianceCheck
  documentsById: Map<string, CaseDocument>
  onOpenCitation: (documentId: string | null, page: number | null) => void
}) {
  // Citations that point at a real page are the ones a reviewer can act on.
  const locatable = check.citations.filter((c) => c.document_id && c.page)

  return (
    <article
      className={`bg-white border border-gray-200 border-l-4 ${
        STATUS_STYLES[check.status].stripe
      } rounded-r-lg p-4`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs text-gray-500">{check.rule_code}</span>
            <span className="font-medium text-gray-900">
              {check.rule_title || 'Regla sin titulo'}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span
              className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                STATUS_STYLES[check.status].chip
              }`}
            >
              {DECISION_STATES[check.status]}
            </span>
            <BandaChip band={check.band} />
            <span className="inline-flex px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">
              {FAMILY_LABELS[check.family] || check.family}
            </span>
          </div>
        </div>
      </div>

      {/* Why it escalated, in words rather than a code. */}
      {check.status === 'requiere_criterio' && check.reason_code && (
        <p className="text-sm text-amber-800 mt-2">
          {REASON_LABELS[check.reason_code] || check.reason_code}
        </p>
      )}

      <p className="text-sm text-gray-700 mt-2">{check.explanation}</p>

      {/* Evidence. Clicking opens the document at the cited page. */}
      {locatable.length > 0 && (
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <span className="text-xs text-gray-500">Evidencia:</span>
          {locatable.map((citation, index) => (
            <CitationChip
              key={`${citation.field_key}-${index}`}
              citation={citation}
              document={documentsById.get(citation.document_id!)}
              onOpen={onOpenCitation}
            />
          ))}
        </div>
      )}

      {check.rule_citation && (
        <p className="text-xs text-gray-500 mt-2">
          Fundamento: {check.rule_citation}
        </p>
      )}
    </article>
  )
}

function CitationChip({
  citation,
  document,
  onOpen,
}: {
  citation: Citation
  document?: CaseDocument
  onOpen: (documentId: string | null, page: number | null) => void
}) {
  const name = document?.doc_type_label || document?.filename || 'Documento'

  return (
    <button
      type="button"
      onClick={() => onOpen(citation.document_id, citation.page)}
      title={citation.value ? `Valor leido: ${citation.value}` : 'Abrir documento'}
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded border border-gray-300 bg-gray-50 hover:bg-white hover:border-primary-500 transition-colors"
    >
      <span className="text-gray-700">{name}</span>
      <span className="font-mono text-gray-500">p. {citation.page}</span>
    </button>
  )
}
