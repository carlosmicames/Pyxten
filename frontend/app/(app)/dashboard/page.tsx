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
      // Create new folder first
      const newFolder = await foldersApi.create(newFolderName)
      targetFolderId = newFolder.id
      // Refresh folders list
      const foldersData = await foldersApi.list()
      setFolders(foldersData)
    }

    // Add validation to folder
    await foldersApi.addItem(targetFolderId, selectedValidationId)

    setSuccessMessage('Guardado exitosamente')
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const handleDownloadPdf = async (validationId: string) => {
    const token = await getAccessToken()
    const url = getApiUrl(`/validations/${validationId}/report.pdf`)

    // Open in new window with auth header
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

  // Filter validations by search query (client-side)
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
        <div className="text-gray-500">Cargando...</div>
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
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

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
          {/* Optional search */}
          <input
            type="text"
            placeholder="Buscar por direccion..."
            className="input-field w-64"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {filteredValidations.length === 0 ? (
          <div className="card text-center text-gray-500 py-12">
            No hay validaciones recientes
          </div>
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
                    Viable
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
                  <tr key={validation.id}>
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
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          validation.viable
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {validation.viable ? 'Viable' : 'No Viable'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(validation.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                      <button
                        onClick={() => handleSaveToFolder(validation.id)}
                        className="text-primary-600 hover:text-primary-800"
                      >
                        Guardar en Carpeta
                      </button>
                      <button
                        onClick={() => handleDownloadPdf(validation.id)}
                        className="text-gray-600 hover:text-gray-800"
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

      {/* Folders Section */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Mis Proyectos
        </h2>

        {folders.length === 0 ? (
          <div className="card text-center text-gray-500 py-12">
            No hay carpetas creadas
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {folders.map((folder) => (
              <Link
                key={folder.id}
                href={`/folders/${folder.id}`}
                className="card hover:shadow-md transition-shadow"
              >
                <h3 className="font-medium text-gray-900">{folder.name}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {folder.item_count} elemento{folder.item_count !== 1 ? 's' : ''}
                </p>
              </Link>
            ))}
          </div>
        )}
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
