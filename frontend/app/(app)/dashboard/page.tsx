'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  validationsApi,
  foldersApi,
  getApiUrl,
  ValidationListItem,
  Folder,
} from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'
import SaveToFolderModal from '@/components/SaveToFolderModal'

// Status pill component
function StatusPill({ viable, analyzing }: { viable?: boolean; analyzing?: boolean }) {
  if (analyzing) {
    return (
      <span className="inline-flex px-2.5 py-1 text-xs font-semibold rounded-full bg-yellow-100 text-yellow-800">
        Analizando
      </span>
    )
  }

  if (viable === true) {
    return (
      <span className="inline-flex px-2.5 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
        Viable
      </span>
    )
  }

  return (
    <span className="inline-flex px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
      No Viable
    </span>
  )
}

// Empty state for validations
function EmptyValidationsState() {
  return (
    <div className="card text-center py-12 px-6">
      {/* Simple illustration */}
      <div className="mx-auto w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mb-6">
        <svg className="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Valida zonificacion en minutos y genera reporte PDF
      </h3>

      <div className="text-sm text-gray-600 mb-6 space-y-1">
        <p>1. Entra direccion</p>
        <p>2. Confirmamos catastro/coordenadas</p>
        <p>3. Generamos informe</p>
      </div>

      <Link
        href="/nueva-validacion"
        className="btn-primary inline-flex items-center"
      >
        Crear tu primera validacion
      </Link>
    </div>
  )
}

// Empty state for projects
function EmptyProjectsState() {
  return (
    <div className="card text-center py-10 px-6">
      <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
      </div>

      <h3 className="text-base font-semibold text-gray-900 mb-1">
        Organiza validaciones por proyecto
      </h3>

      <p className="text-sm text-gray-500 mb-4">
        No hay proyectos creados
      </p>

      <Link
        href="/proyectos"
        className="text-primary-600 hover:text-primary-800 text-sm font-medium"
      >
        Crear proyecto
      </Link>
    </div>
  )
}

export default function DashboardPage() {
  const [validations, setValidations] = useState<ValidationListItem[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedValidationId, setSelectedValidationId] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Usage tracking (placeholder - TODO: connect to backend quota system)
  const [monthlyUsage] = useState(0)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [validationsData, foldersData] = await Promise.all([
        validationsApi.list(undefined, 20),
        foldersApi.list(),
      ])
      setValidations(validationsData)
      setFolders(foldersData)
    } catch (err: any) {
      setError(err.message || 'Error cargando datos')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveToFolder = (validationId: string) => {
    setSelectedValidationId(validationId)
    setModalOpen(true)
  }

  const handleSaveFolder = async (
    folderId: string,
    isNewFolder: boolean,
    newFolderName?: string
  ) => {
    if (!selectedValidationId) return

    let targetFolderId = folderId

    if (isNewFolder && newFolderName) {
      const newFolder = await foldersApi.create(newFolderName)
      targetFolderId = newFolder.id
      const foldersData = await foldersApi.list()
      setFolders(foldersData)
    }

    await foldersApi.addItem(targetFolderId, selectedValidationId)

    setSuccessMessage('Guardado exitosamente')
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const handleDownloadPdf = async (validationId: string) => {
    const token = await getAccessToken()
    const url = getApiUrl(`/validations/${validationId}/report.pdf`)

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (response.ok) {
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      window.open(blobUrl, '_blank')
    }
  }

  // Filter validations by search query
  const filteredValidations = validations.filter((v) => {
    if (!searchQuery) return true
    const searchLower = searchQuery.toLowerCase()
    return (
      (v.project_address?.toLowerCase().includes(searchLower)) ||
      (v.project_name?.toLowerCase().includes(searchLower))
    )
  })

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-PR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {/* Primary action buttons */}
        <div className="flex justify-center gap-4">
          <Link href="/nueva-validacion" className="btn-primary">
            + Nueva Validacion
          </Link>
          <Link href="/proyectos" className="btn-secondary">
            Crear Proyecto/Carpeta
          </Link>
        </div>
      </div>

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          {successMessage}
        </div>
      )}

      {/* Recent Validations Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Validaciones Recientes
          </h2>
          {validations.length > 0 && (
            <input
              type="text"
              placeholder="Buscar por direccion..."
              className="input-field w-64"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          )}
        </div>

        {filteredValidations.length === 0 ? (
          <EmptyValidationsState />
        ) : (
          <div className="card overflow-hidden p-0">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Proyecto
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Direccion
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Municipio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredValidations.map((validation) => (
                  <tr key={validation.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {validation.project_name || 'Sin nombre'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {validation.project_address || validation.property_address || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {validation.project_municipality || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusPill viable={validation.viable} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(validation.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-3">
                      <button
                        onClick={() => handleSaveToFolder(validation.id)}
                        className="text-primary-600 hover:text-primary-800 font-medium"
                      >
                        Guardar
                      </button>
                      <button
                        onClick={() => handleDownloadPdf(validation.id)}
                        className="text-gray-600 hover:text-gray-800 font-medium"
                      >
                        PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Projects Section */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Mis Proyectos
        </h2>

        {folders.length === 0 ? (
          <EmptyProjectsState />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {folders.map((folder) => (
              <Link
                key={folder.id}
                href={`/folders/${folder.id}`}
                className="card hover:shadow-md transition-shadow"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{folder.name}</h3>
                    <p className="text-sm text-gray-500">
                      {folder.item_count} elemento{folder.item_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Usage Section */}
      <section className="border-t pt-6">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
          Uso del Mes
        </h3>
        <p className="text-2xl font-semibold text-gray-900">
          {monthlyUsage} <span className="text-base font-normal text-gray-500">validaciones utilizadas</span>
        </p>
      </section>

      {/* Save to Folder Modal */}
      <SaveToFolderModal
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false)
          setSelectedValidationId(null)
        }}
        onSave={handleSaveFolder}
        validationId={selectedValidationId || ''}
      />
    </div>
  )
}
