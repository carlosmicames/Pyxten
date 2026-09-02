'use client'

import {
  Band,
  BAND_LABELS,
  OCR_LABELS,
  OcrStatus,
  PROCESSING_LABELS,
  ProcessingStatus,
} from '@/lib/reviewerApi'

/**
 * Confidence band.
 *
 * Categorical only - the API has no numeric confidence to render, and this
 * component would have nowhere to put a percentage even if it did. A `baja`
 * band is what forces a case to "Requiere criterio del revisor", so it is
 * styled to be noticed rather than tucked away.
 */
export function BandaChip({ band }: { band: Band | null }) {
  if (!band) {
    return (
      <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
        Sin evaluar
      </span>
    )
  }

  const styles: Record<Band, string> = {
    alta: 'bg-green-100 text-green-800',
    media: 'bg-amber-100 text-amber-800',
    baja: 'bg-red-100 text-red-800',
  }

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${styles[band]}`}>
      {BAND_LABELS[band]}
    </span>
  )
}

export function ProcesamientoChip({ status }: { status: ProcessingStatus }) {
  const styles: Record<ProcessingStatus, string> = {
    recibido: 'bg-gray-100 text-gray-700',
    extrayendo: 'bg-blue-100 text-blue-800',
    clasificando: 'bg-blue-100 text-blue-800',
    listo: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
  }

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${styles[status]}`}>
      {PROCESSING_LABELS[status]}
    </span>
  )
}

/**
 * Whether the PDF carried readable text.
 *
 * Worth surfacing to the reviewer: a scanned document was classified from its
 * page images and can never reach the highest band, and that is a fact about the
 * evidence, not a defect to hide.
 */
export function OcrChip({ status }: { status: OcrStatus }) {
  const styles: Record<OcrStatus, string> = {
    pendiente: 'bg-gray-100 text-gray-600',
    texto_incrustado: 'bg-gray-100 text-gray-700',
    parcial: 'bg-amber-50 text-amber-700',
    sin_texto: 'bg-amber-50 text-amber-700',
    error: 'bg-red-50 text-red-700',
  }

  return (
    <span className={`inline-flex px-2 py-0.5 text-xs rounded ${styles[status]}`}>
      {OCR_LABELS[status]}
    </span>
  )
}

/**
 * Where a classification came from. A reviewer's own correction outranks the
 * model, and the interface says so plainly.
 */
export function FuenteChip({ source }: { source: 'pendiente' | 'modelo' | 'revisor' }) {
  if (source === 'revisor') {
    return (
      <span className="inline-flex px-2 py-0.5 text-xs rounded bg-primary-50 text-primary-700 font-medium">
        Confirmado por revisor
      </span>
    )
  }
  if (source === 'modelo') {
    return (
      <span className="inline-flex px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">
        Sugerido automaticamente
      </span>
    )
  }
  return (
    <span className="inline-flex px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-500">
      Pendiente
    </span>
  )
}
