'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  CASE_STATUS_LABELS,
  CaseRecord,
  ReviewerIdentity,
  formatDate,
  reviewerApi,
} from '@/lib/reviewerApi'
import SinAcceso from '@/components/reviewer/SinAcceso'

/**
 * The case queue. This is where a reviewer starts their day, so it answers one
 * question first: what is waiting on me.
 */
export default function BandejaPage() {
  const [identity, setIdentity] = useState<ReviewerIdentity | null>(null)
  const [cases, setCases] = useState<CaseRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    const load = async () => {
      const me = await reviewerApi.me()
      setIdentity(me)

      if (me) {
        try {
          setCases(await reviewerApi.listCases(statusFilter || undefined))
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Error cargando expedientes')
        }
      }
      setLoading(false)
    }
    load()
  }, [statusFilter])

  if (loading) return <div className="p-8 text-gray-500">Cargando...</div>
  if (!identity) return <SinAcceso />

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bandeja de expedientes</h1>
          <p className="text-gray-600 mt-1">
            {identity.org_name} · {identity.municipality} ·{' '}
            <span className="capitalize">{identity.role}</span>
          </p>
        </div>
        {identity.can_write && (
          <Link href="/revisor/caso/nuevo" className="btn-primary">
            Nuevo expediente
          </Link>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6 text-sm">
          {error}
        </div>
      )}

      <div className="flex gap-2 mb-4 flex-wrap">
        <FiltroBoton
          label="Todos"
          active={statusFilter === ''}
          onClick={() => setStatusFilter('')}
        />
        {Object.entries(CASE_STATUS_LABELS).map(([value, label]) => (
          <FiltroBoton
            key={value}
            label={label}
            active={statusFilter === value}
            onClick={() => setStatusFilter(value)}
          />
        ))}
      </div>

      {cases.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-600">
            {statusFilter
              ? 'No hay expedientes en este estado.'
              : 'Aun no hay expedientes en esta oficina.'}
          </p>
          {identity.can_write && !statusFilter && (
            <Link href="/revisor/caso/nuevo" className="btn-primary inline-block mt-4">
              Abrir el primero
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <Th>Numero</Th>
                <Th>Solicitante</Th>
                <Th>Direccion</Th>
                <Th>Estado</Th>
                <Th>Abierto</Th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/revisor/caso/${c.id}`}
                      className="font-mono text-primary-700 hover:underline"
                    >
                      {c.case_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-900">
                    {c.applicant_name || <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                    {c.property_address || <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                      {CASE_STATUS_LABELS[c.status] || c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                    {formatDate(c.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
      {children}
    </th>
  )
}

function FiltroBoton({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
        active
          ? 'bg-primary-600 text-white border-primary-600'
          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
      }`}
    >
      {label}
    </button>
  )
}
