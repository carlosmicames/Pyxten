'use client'

import { useState } from 'react'
import { CaseProfile, reviewerApi } from '@/lib/reviewerApi'

interface Props {
  caseId: string
  profile: CaseProfile
  filingDate: string | null
  canWrite: boolean
  onSaved: (profile: CaseProfile, filingDate: string | null) => void
}

type Option = { value: string; label: string }

const FIELDS: {
  key: keyof CaseProfile
  label: string
  help: string
  options: Option[]
}[] = [
  {
    key: 'forma_juridica',
    label: 'Forma juridica',
    help: 'Decide si los nombres se comparan como persona o como entidad',
    options: [
      { value: 'persona_natural', label: 'Persona natural' },
      { value: 'entidad_juridica', label: 'Entidad juridica' },
    ],
  },
  {
    key: 'tenencia',
    label: 'Tenencia del local',
    help: 'Decide si se exige escritura o contrato de arrendamiento',
    options: [
      { value: 'dueno', label: 'Dueno' },
      { value: 'arrendatario', label: 'Arrendatario' },
    ],
  },
  {
    key: 'tipo_tramite',
    label: 'Tipo de tramite',
    help: '',
    options: [
      { value: 'nueva', label: 'Nueva solicitud' },
      { value: 'renovacion', label: 'Renovacion' },
    ],
  },
  {
    key: 'categoria_uso',
    label: 'Categoria de uso',
    help: 'Decide si se exige certificado de salud',
    options: [
      { value: 'alimentos', label: 'Alimentos' },
      { value: 'salud', label: 'Salud' },
      { value: 'comercio_general', label: 'Comercio general' },
      { value: 'entretenimiento', label: 'Entretenimiento' },
      { value: 'industrial', label: 'Industrial' },
    ],
  },
  {
    key: 'acceso_publico',
    label: 'Local de acceso publico',
    help: 'Decide si se exige certificacion ADA',
    options: [
      { value: 'true', label: 'Si' },
      { value: 'false', label: 'No' },
    ],
  },
  {
    key: 'radica_representante',
    label: 'Radica un representante',
    help: 'Decide si se exige poder de representacion',
    options: [
      { value: 'true', label: 'Si' },
      { value: 'false', label: 'No' },
    ],
  },
]

const BOOLEAN_KEYS: (keyof CaseProfile)[] = ['acceso_publico', 'radica_representante']

/**
 * The answers that decide which rules apply to this case.
 *
 * Leaving a question blank is safe rather than silently wrong: an unanswered
 * key makes the affected rule escalate to "Requiere criterio del revisor"
 * instead of being read as "no". The copy says so, because a reviewer who
 * assumes blank means no will misread the results.
 */
export default function PerfilCaso({
  caseId,
  profile,
  filingDate,
  canWrite,
  onSaved,
}: Props) {
  const [draft, setDraft] = useState<CaseProfile>(profile || {})
  const [date, setDate] = useState(filingDate || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const unanswered = FIELDS.filter((f) => draft[f.key] === undefined).length

  const setValue = (key: keyof CaseProfile, raw: string) => {
    setSaved(false)
    const next = { ...draft }
    if (raw === '') {
      delete next[key]
    } else if (BOOLEAN_KEYS.includes(key)) {
      // @ts-expect-error narrowed by BOOLEAN_KEYS
      next[key] = raw === 'true'
    } else {
      // @ts-expect-error the option values match the union members
      next[key] = raw
    }
    setDraft(next)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await reviewerApi.updateCase(caseId, {
        profile: draft,
        ...(date ? { filing_date: date } : {}),
      })
      onSaved(updated.profile || draft, updated.filing_date ?? date ?? null)
      setSaved(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el perfil')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4 flex-wrap mb-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Perfil de la solicitud
          </h2>
          <p className="text-sm text-gray-600 mt-1 max-w-2xl">
            Estas respuestas determinan cuales reglas aplican. Dejar una en blanco
            no equivale a &quot;no&quot;: la regla correspondiente pasa a{' '}
            <span className="font-medium">Requiere criterio del revisor</span> en
            lugar de darse por cumplida.
          </p>
        </div>
        {unanswered > 0 && (
          <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-800 whitespace-nowrap">
            {unanswered} sin responder
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FIELDS.map((field) => (
          <div key={field.key}>
            <label className="label">{field.label}</label>
            <select
              className="input-field text-sm"
              disabled={!canWrite}
              value={
                draft[field.key] === undefined ? '' : String(draft[field.key])
              }
              onChange={(e) => setValue(field.key, e.target.value)}
            >
              <option value="">Sin responder</option>
              {field.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {field.help && (
              <p className="text-xs text-gray-500 mt-1">{field.help}</p>
            )}
          </div>
        ))}

        <div>
          <label className="label">Fecha de radicacion</label>
          <input
            type="date"
            className="input-field text-sm"
            disabled={!canWrite}
            value={date}
            onChange={(e) => {
              setSaved(false)
              setDate(e.target.value)
            }}
          />
          <p className="text-xs text-gray-500 mt-1">
            Contra esta fecha se mide la vigencia de las certificaciones
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mt-4">
          {error}
        </div>
      )}

      {canWrite && (
        <div className="flex items-center gap-3 mt-4">
          <button
            type="button"
            className="btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Guardando...' : 'Guardar perfil'}
          </button>
          {saved && (
            <span className="text-sm text-green-700">
              Guardado. Vuelva a evaluar para aplicar los cambios.
            </span>
          )}
        </div>
      )}
    </div>
  )
}
