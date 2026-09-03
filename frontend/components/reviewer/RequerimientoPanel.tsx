'use client'

import { useState } from 'react'
import {
  Requerimiento,
  formatDate,
  getApiBase,
  reviewerApi,
} from '@/lib/reviewerApi'

interface Props {
  caseId: string
  requerimiento: Requerimiento | null
  findingCount: number
  pendingCount: number
  canWrite: boolean
  onChanged: (requerimiento: Requerimiento) => void
}

/**
 * The deficiency notice.
 *
 * Two things this screen is careful about. It never offers to send anything -
 * approval marks the document ready for a person to serve, and serving happens
 * outside this system. And it says plainly which paragraphs were drafted
 * automatically and which came from the engine's own wording, because a
 * reviewer signing this needs to know what they are signing.
 */
export default function RequerimientoPanel({
  caseId,
  requerimiento,
  findingCount,
  pendingCount,
  canWrite,
  onChanged,
}: Props) {
  const [busy, setBusy] = useState<null | 'draft' | 'approve'>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDraft = async () => {
    setBusy('draft')
    setError(null)
    try {
      onChanged(await reviewerApi.draftRequerimiento(caseId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo generar el borrador')
    } finally {
      setBusy(null)
    }
  }

  const handleApprove = async () => {
    if (!requerimiento) return
    if (
      !confirm(
        'Al aprobar, el documento deja de marcarse como borrador. ' +
          'La notificacion al solicitante sigue siendo un acto suyo, fuera del sistema. ' +
          '¿Confirma la aprobacion?'
      )
    ) {
      return
    }

    setBusy('approve')
    setError(null)
    try {
      onChanged(await reviewerApi.approveRequerimiento(requerimiento.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo aprobar el requerimiento')
    } finally {
      setBusy(null)
    }
  }

  const pdfUrl = `${getApiBase()}/reviewer/cases/${caseId}/requerimiento.pdf`
  const approved = requerimiento?.status === 'aprobado'
  const body = requerimiento?.body

  return (
    <div className="space-y-5">
      {/* ---------- What a notice would be built from ---------- */}
      <div className="card">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Requerimiento de subsanacion
            </h2>
            <p className="text-sm text-gray-600 mt-1 max-w-2xl">
              Se redacta a partir de los hallazgos identificados. Las
              verificaciones que requieren criterio del revisor no se incluyen:
              el sistema no puede senalar como deficiencia algo que no logro
              determinar.
            </p>
          </div>

          {canWrite && findingCount > 0 && (
            <button
              type="button"
              className="btn-primary whitespace-nowrap"
              onClick={handleDraft}
              disabled={busy !== null}
            >
              {busy === 'draft'
                ? 'Redactando...'
                : requerimiento
                  ? 'Generar nueva version'
                  : 'Generar borrador'}
            </button>
          )}
        </div>

        <div className="flex gap-6 mt-4 text-sm">
          <div>
            <div className="text-2xl font-semibold text-gray-900 tabular-nums">
              {findingCount}
            </div>
            <div className="text-xs text-gray-600">
              {findingCount === 1 ? 'hallazgo incluido' : 'hallazgos incluidos'}
            </div>
          </div>
          <div>
            <div className="text-2xl font-semibold text-amber-700 tabular-nums">
              {pendingCount}
            </div>
            <div className="text-xs text-gray-600">
              pendientes de criterio (no se incluyen)
            </div>
          </div>
        </div>

        {findingCount === 0 && (
          <p className="text-sm text-gray-600 mt-4 bg-gray-50 border border-gray-200 rounded-md px-4 py-3">
            No hay hallazgos identificados en este expediente, por lo que no
            procede un requerimiento.
            {pendingCount > 0 &&
              ` Quedan ${pendingCount} verificaciones que requieren su criterio; resuelvalas primero.`}
          </p>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* ---------- The draft ---------- */}
      {requerimiento && body && (
        <div className="card">
          <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-gray-900">
                  Version {requerimiento.version}
                </span>
                <span
                  className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                    approved
                      ? 'bg-green-100 text-green-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}
                >
                  {approved ? 'Aprobado' : 'Borrador'}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Generado {formatDate(requerimiento.generated_at)}
                {requerimiento.approved_at
                  ? ` · aprobado ${formatDate(requerimiento.approved_at)}`
                  : ''}
                {requerimiento.model_used
                  ? ` · redaccion asistida (${requerimiento.model_used})`
                  : ' · redaccion generada por el sistema'}
              </p>
            </div>

            <div className="flex gap-2">
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                Ver PDF
              </a>
              {canWrite && !approved && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleApprove}
                  disabled={busy !== null}
                >
                  {busy === 'approve' ? 'Aprobando...' : 'Aprobar borrador'}
                </button>
              )}
            </div>
          </div>

          {!approved && (
            <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-md px-4 py-3 mb-4">
              Este documento es un borrador y lleva marca de agua. Aprobarlo
              retira la marca; notificarlo al solicitante sigue siendo un acto
              suyo, fuera de este sistema.
            </p>
          )}

          {/* ---------- Readable preview ---------- */}
          <article className="prose-sm max-w-none">
            <p className="text-sm text-gray-800 mb-4">{body.introduccion}</p>

            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              Senalamientos ({body.hallazgos.length})
            </h3>

            <ol className="space-y-4">
              {body.hallazgos.map((item) => (
                <li
                  key={item.rule_code}
                  className="border-l-2 border-gray-200 pl-4"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-900 text-sm">
                      {item.numero}. {item.titulo}
                    </span>
                    <span className="font-mono text-xs text-gray-500">
                      {item.rule_code}
                    </span>
                    {/* Which paragraphs a reviewer should read hardest. */}
                    <span
                      className={`inline-flex px-2 py-0.5 text-xs rounded ${
                        item.generado === 'modelo'
                          ? 'bg-blue-50 text-blue-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                      title={
                        item.descartado_por
                          ? `La redaccion automatica se descarto: ${item.descartado_por}`
                          : undefined
                      }
                    >
                      {item.generado === 'modelo'
                        ? 'Redaccion asistida'
                        : 'Redaccion del sistema'}
                    </span>
                  </div>

                  <p className="text-sm text-gray-700 mt-1">{item.parrafo}</p>
                  {item.subsanacion && (
                    <p className="text-sm text-gray-700 mt-1">
                      <span className="font-medium">Subsanacion requerida:</span>{' '}
                      {item.subsanacion}
                    </p>
                  )}

                  {item.evidencia.map((evidence, index) => (
                    <p
                      key={index}
                      className="text-xs text-gray-500 mt-1 font-mono"
                    >
                      Evidencia: {evidence.documento}, pag. {evidence.pagina}
                      {evidence.valor ? ` — “${evidence.valor}”` : ''}
                    </p>
                  ))}

                  {item.fundamento && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      Fundamento: {item.fundamento}
                    </p>
                  )}
                </li>
              ))}
            </ol>

            <p className="text-sm text-gray-800 mt-5">{body.cierre}</p>
          </article>
        </div>
      )}
    </div>
  )
}
