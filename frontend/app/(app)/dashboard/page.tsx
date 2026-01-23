'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  validationsApi,
  foldersApi,
  getApiUrl,
  ValidationListItem,
  Folder,
  UsageStats,
} from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'
import SaveToFolderModal from '@/components/SaveToFolderModal'

// Status pill component
function StatusPill({ viable }: { viable?: boolean }) {
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

// Clipboard/Map illustration for validations
function ValidationIllustration() {
  return (
    <div className="mx-auto w-32 h-32 mb-6">
      <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Clipboard background */}
        <rect x="20" y="15" width="80" height="95" rx="4" fill="#f0fdf4" stroke="#16a34a" strokeWidth="2"/>
        {/* Clipboard clip */}
        <rect x="40" y="8" width="40" height="14" rx="2" fill="#16a34a"/>
        <rect x="48" y="4" width="24" height="8" rx="2" fill="#166534"/>
        {/* Map lines */}
        <path d="M35 40 L85 40" stroke="#bbf7d0" strokeWidth="2" strokeLinecap="round"/>
        <path d="M35 55 L75 55" stroke="#bbf7d0" strokeWidth="2" strokeLinecap="round"/>
        <path d="M35 70 L80 70" stroke="#bbf7d0" strokeWidth="2" strokeLinecap="round"/>
        {/* Checkmarks */}
        <circle cx="35" cy="40" r="6" fill="#22c55e"/>
        <path d="M32 40 L34 42 L38 38" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="35" cy="55" r="6" fill="#22c55e"/>
        <path d="M32 55 L34 57 L38 53" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="35" cy="70" r="6" fill="#22c55e"/>
        <path d="M32 70 L34 72 L38 68" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        {/* Map pin */}
        <path d="M75 80 C75 75 80 70 85 70 C90 70 95 75 95 80 C95 88 85 98 85 98 C85 98 75 88 75 80Z" fill="#16a34a"/>
        <circle cx="85" cy="80" r="4" fill="white"/>
      </svg>
    </div>
  )
}

// Folders/Files illustration for projects
function FoldersIllustration() {
  return (
    <div className="mx-auto w-32 h-32 mb-6">
      <svg viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Back folder */}
        <path d="M15 35 L15 90 C15 93 17 95 20 95 L90 95 C93 95 95 93 95 90 L95 45 C95 42 93 40 90 40 L55 40 L48 30 L20 30 C17 30 15 32 15 35Z" fill="#dcfce7" stroke="#16a34a" strokeWidth="2"/>
        {/* Middle folder */}
        <path d="M25 45 L25 85 C25 88 27 90 30 90 L95 90 C98 90 100 88 100 85 L100 55 C100 52 98 50 95 50 L60 50 L53 40 L30 40 C27 40 25 42 25 45Z" fill="#bbf7d0" stroke="#16a34a" strokeWidth="2"/>
        {/* Front folder */}
        <path d="M35 55 L35 80 C35 83 37 85 40 85 L100 85 C103 85 105 83 105 80 L105 65 C105 62 103 60 100 60 L65 60 L58 50 L40 50 C37 50 35 52 35 55Z" fill="#22c55e" stroke="#166534" strokeWidth="2"/>
        {/* Document icon in front folder */}
        <rect x="60" y="65" width="25" height="15" rx="2" fill="white" stroke="#166534" strokeWidth="1"/>
        <path d="M65 70 L80 70" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round"/>
        <path d="M65 75 L75 75" stroke="#16a34a" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
    </div>
  )
}

export default function DashboardPage() {
  const [validations, setValidations] = useState<ValidationListItem[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [selectedValidationId, setSelectedValidationId] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [validationsData, foldersData, statsData] = await Promise.all([
        validationsApi.list(undefined, 20),
        foldersApi.list(),
        validationsApi.getStats(),
      ])
      setValidations(validationsData)
      setFolders(foldersData)
      setUsageStats(statsData)
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
    try {
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
        // Create a link element to trigger download
        const link = document.createElement('a')
        link.href = blobUrl
        link.download = `validacion_${validationId}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(blobUrl)
      } else {
        console.error('Error downloading PDF:', response.statusText)
      }
    } catch (err) {
      console.error('Error downloading PDF:', err)
    }
  }

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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
      </div>

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          {successMessage}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Validaciones Recientes Card */}
        <div className="card flex flex-col items-center text-center">
          <ValidationIllustration />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Validaciones Recientes
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Valida zonificacion en minutos y genera reporte PDF
          </p>
          <Link
            href="/nueva-validacion"
            className="btn-primary inline-flex items-center"
          >
            Nueva Validacion
          </Link>
        </div>

        {/* Middle Column - Mis Proyectos Card */}
        <div className="card flex flex-col items-center text-center">
          <FoldersIllustration />
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Mis Proyectos
          </h2>
          <p className="text-sm text-gray-600 mb-6">
            Organiza tus validaciones por proyecto
          </p>
          <Link
            href="/proyectos"
            className="btn-primary inline-flex items-center"
          >
            Crear proyecto/carpeta
          </Link>
        </div>

        {/* Right Column - Usage Stats */}
        <div className="card">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">
            Uso del Mes
          </h3>
          <p className="text-3xl font-bold text-gray-900 mb-1">
            {usageStats?.total_validations || 0}
          </p>
          <p className="text-sm text-gray-500 mb-6">validaciones utilizadas</p>

          {/* Viability Statistics */}
          <div className="border-t border-gray-200 pt-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="text-sm text-gray-600">Viables</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {usageStats?.viable_validations || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="text-sm text-gray-600">No Viables</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {usageStats?.non_viable_validations || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Access: Recent Validations List (if any) */}
      {validations.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Ultimas Validaciones
          </h2>
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
                {validations.slice(0, 5).map((validation) => (
                  <tr key={validation.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {validation.project_name || 'Sin nombre'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {validation.project_address || validation.property_address || 'N/A'}
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
        </section>
      )}

      {/* Quick Access: Folders Grid (if any) */}
      {folders.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Carpetas
          </h2>
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
        </section>
      )}

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
