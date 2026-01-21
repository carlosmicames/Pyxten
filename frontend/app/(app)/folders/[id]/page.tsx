'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { foldersApi, getApiUrl, Folder, FolderItem } from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'

export default function FolderDetailPage() {
  const params = useParams()
  const router = useRouter()
  const folderId = params.id as string

  const [folder, setFolder] = useState<Folder | null>(null)
  const [items, setItems] = useState<FolderItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (folderId) {
      loadFolderData()
    }
  }, [folderId])

  const loadFolderData = async () => {
    try {
      setLoading(true)
      const [folderData, itemsData] = await Promise.all([
        foldersApi.get(folderId),
        foldersApi.listItems(folderId),
      ])
      setFolder(folderData)
      setItems(itemsData)
    } catch (err: any) {
      setError(err.message || 'Error cargando carpeta')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveItem = async (itemId: string) => {
    if (!confirm('Esta seguro de remover este elemento de la carpeta?')) {
      return
    }

    try {
      await foldersApi.removeItem(folderId, itemId)
      setItems(items.filter((item) => item.id !== itemId))
    } catch (err: any) {
      setError(err.message || 'Error removiendo elemento')
    }
  }

  const handleDeleteFolder = async () => {
    if (!confirm('Esta seguro de eliminar esta carpeta y todos sus elementos?')) {
      return
    }

    try {
      await foldersApi.delete(folderId)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Error eliminando carpeta')
    }
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

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
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

  if (!folder) {
    return (
      <div className="text-center text-gray-500 py-12">
        Carpeta no encontrada
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            Volver al Dashboard
          </button>
          <h1 className="text-2xl font-bold text-gray-900">{folder.name}</h1>
        </div>
        <button
          onClick={handleDeleteFolder}
          className="btn-danger"
        >
          Eliminar Carpeta
        </button>
      </div>

      {items.length === 0 ? (
        <div className="card text-center text-gray-500 py-12">
          No se ha seleccionado proyectos.
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
                  Fecha de Validacion
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Viable
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {item.project_name || 'Sin nombre'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {item.project_address || 'N/A'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(item.validation_date)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        item.viable
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {item.viable ? 'Viable' : 'No Viable'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-2">
                    <button
                      onClick={() => handleDownloadPdf(item.validation_id)}
                      className="text-primary-600 hover:text-primary-800"
                    >
                      PDF
                    </button>
                    <button
                      onClick={() => handleRemoveItem(item.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Remover
                    </button>
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
