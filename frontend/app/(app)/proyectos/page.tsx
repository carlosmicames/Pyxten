'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { projectsApi, foldersApi, Project, Folder, getApiUrl } from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'

// Status pill component
function Phase1StatusPill({ completed }: { completed: boolean }) {
  if (completed) {
    return (
      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
        Completado
      </span>
    )
  }
  return (
    <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
      Pendiente
    </span>
  )
}

export default function ProyectosPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [folders, setFolders] = useState<Folder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [projectsData, foldersData] = await Promise.all([
        projectsApi.list(),
        foldersApi.list(),
      ])
      setProjects(projectsData)
      setFolders(foldersData)
    } catch (err: any) {
      setError(err.message || 'Error cargando datos')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    if (!confirm('Esta seguro de eliminar este proyecto?')) {
      return
    }

    try {
      await projectsApi.delete(projectId)
      setProjects(projects.filter((p) => p.id !== projectId))
    } catch (err: any) {
      setError(err.message || 'Error eliminando proyecto')
    }
  }

  const handleDeleteFolder = async (folderId: string) => {
    if (!confirm('Esta seguro de eliminar esta carpeta?')) {
      return
    }

    try {
      await foldersApi.delete(folderId)
      setFolders(folders.filter((f) => f.id !== folderId))
    } catch (err: any) {
      setError(err.message || 'Error eliminando carpeta')
    }
  }

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return

    try {
      setCreatingFolder(true)
      await foldersApi.create(newFolderName.trim())
      const foldersData = await foldersApi.list()
      setFolders(foldersData)
      setNewFolderName('')
    } catch (err: any) {
      setError(err.message || 'Error creando carpeta')
    } finally {
      setCreatingFolder(false)
    }
  }

  const handleDownloadPdf = async (projectId: string, validationId?: string) => {
    // Projects store their validation result in phase1_result
    // We need to find the validation associated with this project
    const project = projects.find(p => p.id === projectId)
    if (!project?.phase1_completed) {
      alert('Este proyecto no tiene una validacion completada.')
      return
    }

    try {
      const token = await getAccessToken()
      // Get the project's validations to find the PDF
      const response = await fetch(getApiUrl(`/validations?project_id=${projectId}&limit=1`), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const validations = await response.json()
        if (validations.length > 0) {
          const validation = validations[0]
          const pdfResponse = await fetch(getApiUrl(`/validations/${validation.id}/report.pdf`), {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          })

          if (pdfResponse.ok) {
            const blob = await pdfResponse.blob()
            const blobUrl = URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = blobUrl
            link.download = `validacion_${validation.id}.pdf`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(blobUrl)
          }
        } else {
          alert('No se encontro validacion para este proyecto.')
        }
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

  // Filter projects by search query
  const filteredProjects = projects.filter((p) => {
    if (!searchQuery) return true
    const searchLower = searchQuery.toLowerCase()
    return (
      p.name?.toLowerCase().includes(searchLower) ||
      p.address?.toLowerCase().includes(searchLower) ||
      p.municipality?.toLowerCase().includes(searchLower)
    )
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Proyectos</h1>
        <Link href="/nueva-validacion" className="btn-primary">
          Nuevo Proyecto
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      {/* Search Bar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Buscar por nombre, direccion o municipio..."
            className="input-field pl-10"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Projects Table */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Proyectos</h2>
        {filteredProjects.length === 0 ? (
          <div className="card text-center text-gray-500 py-12">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <p className="mb-4">No hay proyectos creados</p>
            <Link href="/nueva-validacion" className="btn-primary inline-block">
              Crear Primer Proyecto
            </Link>
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nombre
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
                    Fase 1
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    PDF
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredProjects.map((project) => (
                  <tr key={project.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {project.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {project.address || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {project.municipality || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {project.status || 'En Progreso'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Phase1StatusPill completed={project.phase1_completed} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(project.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {project.phase1_completed ? (
                        <button
                          onClick={() => handleDownloadPdf(project.id)}
                          className="text-primary-600 hover:text-primary-800 font-medium"
                        >
                          Descargar
                        </button>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      <button
                        onClick={() => handleDeleteProject(project.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Eliminar
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
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Carpetas</h2>
        </div>

        {/* Create Folder Form */}
        <div className="flex items-center gap-3 mb-4">
          <input
            type="text"
            placeholder="Nombre de nueva carpeta..."
            className="input-field flex-1 max-w-xs"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleCreateFolder()
              }
            }}
          />
          <button
            onClick={handleCreateFolder}
            disabled={creatingFolder || !newFolderName.trim()}
            className="btn-primary"
          >
            {creatingFolder ? 'Creando...' : 'Crear Carpeta'}
          </button>
        </div>

        {folders.length === 0 ? (
          <div className="card text-center text-gray-500 py-10">
            <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <p>No hay carpetas creadas</p>
            <p className="text-sm mt-1">Usa el formulario de arriba para crear tu primera carpeta</p>
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nombre
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Elementos
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Fecha Creacion
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {folders.map((folder) => (
                  <tr key={folder.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link
                        href={`/folders/${folder.id}`}
                        className="flex items-center gap-3 text-sm font-medium text-gray-900 hover:text-primary-600"
                      >
                        <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                          <svg className="w-4 h-4 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                          </svg>
                        </div>
                        {folder.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {folder.item_count} elemento{folder.item_count !== 1 ? 's' : ''}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(folder.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm space-x-3">
                      <Link
                        href={`/folders/${folder.id}`}
                        className="text-primary-600 hover:text-primary-800 font-medium"
                      >
                        Ver
                      </Link>
                      <button
                        onClick={() => handleDeleteFolder(folder.id)}
                        className="text-red-600 hover:text-red-800"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
