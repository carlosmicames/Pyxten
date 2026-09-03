'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  CaseDocument,
  CaseRecord,
  DocumentType,
  ReviewerIdentity,
  reviewerApi,
} from '@/lib/reviewerApi'
import DocumentUploader from '@/components/reviewer/DocumentUploader'
import SinAcceso from '@/components/reviewer/SinAcceso'

/**
 * Open a case and load its documents.
 *
 * Two steps on one page: the reviewer records the basics, then drops the PDFs
 * and watches each one get classified. The case is created first so that every
 * uploaded file has a durable home even if the reviewer walks away mid-upload.
 */
export default function NuevoCasoPage() {
  const router = useRouter()

  const [identity, setIdentity] = useState<ReviewerIdentity | null>(null)
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState({
    case_number: '',
    applicant_name: '',
    property_address: '',
    catastro: '',
  })
  const [creating, setCreating] = useState(false)

  const [openCase, setOpenCase] = useState<CaseRecord | null>(null)
  const [documents, setDocuments] = useState<CaseDocument[]>([])

  useEffect(() => {
    const load = async () => {
      const me = await reviewerApi.me()
      setIdentity(me)

      if (me) {
        try {
          const [types, suggestion] = await Promise.all([
            reviewerApi.taxonomy(),
            reviewerApi.nextCaseNumber(),
          ])
          setDocumentTypes(types)
          setForm((f) => ({ ...f, case_number: suggestion.case_number }))
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error cargando la configuracion')
        }
      }

      setLoading(false)
    }
    load()
  }, [])

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    setCreating(true)
    setError(null)

    try {
      const created = await reviewerApi.createCase({
        case_number: form.case_number.trim() || undefined,
        applicant_name: form.applicant_name.trim() || undefined,
        property_address: form.property_address.trim() || undefined,
        catastro: form.catastro.trim() || undefined,
      })
      setOpenCase(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo crear el expediente')
    } finally {
      setCreating(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-gray-500">Cargando...</div>
  }

  if (!identity) {
    return <SinAcceso />
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6">
        <Link href="/revisor/bandeja" className="text-sm text-primary-700 hover:underline">
          ← Bandeja de expedientes
        </Link>
        <h1 className="text-2xl font-bold text-gray-900 mt-2">Nuevo expediente</h1>
        <p className="text-gray-600 mt-1">
          {identity.org_name} · {identity.municipality}
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6 text-sm">
          {error}
        </div>
      )}

      {/* ---------- Step 1: the case ---------- */}
      <section className="card mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              1. Datos del expediente
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Estos datos identifican la solicitud. Se pueden corregir despues.
            </p>
          </div>
          {openCase && (
            <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 whitespace-nowrap">
              Expediente abierto
            </span>
          )}
        </div>

        {openCase ? (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 mt-4 text-sm">
            <Campo label="Numero" value={openCase.case_number} mono />
            <Campo label="Solicitante" value={openCase.applicant_name} />
            <Campo label="Direccion" value={openCase.property_address} />
            <Campo label="Catastro" value={openCase.catastro} mono />
            {/* The ruleset stamp is permanent; showing it makes that visible. */}
            <div className="sm:col-span-2">
              <dt className="text-gray-500 text-xs uppercase tracking-wide">
                Version de reglamento aplicada
              </dt>
              <dd className="font-mono text-xs text-gray-700 mt-0.5">
                {openCase.ruleset_version_id}
              </dd>
              <p className="text-xs text-gray-500 mt-1">
                Queda fija para este expediente. Si el reglamento cambia, este caso se
                sigue evaluando bajo las reglas vigentes al abrirlo.
              </p>
            </div>
          </dl>
        ) : (
          <form onSubmit={handleCreate} className="mt-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Numero de expediente</label>
                <input
                  className="input-field font-mono"
                  value={form.case_number}
                  onChange={(e) => setForm({ ...form, case_number: e.target.value })}
                  placeholder="SJ-2026-0001"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Sugerido automaticamente. Puede escribir el suyo.
                </p>
              </div>
              <div>
                <label className="label">Numero de catastro</label>
                <input
                  className="input-field font-mono"
                  value={form.catastro}
                  onChange={(e) => setForm({ ...form, catastro: e.target.value })}
                  placeholder="123-456-789-01"
                />
              </div>
              <div>
                <label className="label">Solicitante</label>
                <input
                  className="input-field"
                  value={form.applicant_name}
                  onChange={(e) => setForm({ ...form, applicant_name: e.target.value })}
                  placeholder="Nombre del solicitante"
                />
              </div>
              <div>
                <label className="label">Direccion de la propiedad</label>
                <input
                  className="input-field"
                  value={form.property_address}
                  onChange={(e) => setForm({ ...form, property_address: e.target.value })}
                  placeholder="Calle, sector, municipio"
                />
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? 'Abriendo expediente...' : 'Abrir expediente'}
            </button>
          </form>
        )}
      </section>

      {/* ---------- Step 2: the documents ---------- */}
      <section className="card">
        <h2 className="text-lg font-semibold text-gray-900">
          2. Documentos del expediente
        </h2>
        <p className="text-sm text-gray-600 mt-1 mb-4">
          Cada documento se clasifica automaticamente. &quot;Desconocido&quot; es un
          resultado valido: el sistema no adivina cuando la evidencia no alcanza.
        </p>

        {openCase ? (
          <DocumentUploader
            caseId={openCase.id}
            documents={documents}
            documentTypes={documentTypes}
            canWrite={identity.can_write}
            onDocumentsChanged={setDocuments}
          />
        ) : (
          <p className="text-sm text-gray-500 py-6 text-center">
            Abra el expediente para poder subir documentos.
          </p>
        )}
      </section>

      {openCase && (
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            className="btn-primary"
            onClick={() => router.push(`/revisor/caso/${openCase.id}`)}
          >
            Ir al expediente
          </button>
          <Link href="/revisor/bandeja" className="btn-secondary">
            Volver a la bandeja
          </Link>
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
