'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { projectsApi, getApiUrl, Project, Validation } from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'

// Puerto Rico municipalities
const MUNICIPALITIES = [
  'Adjuntas', 'Aguada', 'Aguadilla', 'Aguas Buenas', 'Aibonito',
  'Anasco', 'Arecibo', 'Arroyo', 'Barceloneta', 'Barranquitas',
  'Bayamon', 'Cabo Rojo', 'Caguas', 'Camuy', 'Canovanas',
  'Carolina', 'Catano', 'Cayey', 'Ceiba', 'Ciales',
  'Cidra', 'Coamo', 'Comerio', 'Corozal', 'Culebra',
  'Dorado', 'Fajardo', 'Florida', 'Guanica', 'Guayama',
  'Guayanilla', 'Guaynabo', 'Gurabo', 'Hatillo', 'Hormigueros',
  'Humacao', 'Isabela', 'Jayuya', 'Juana Diaz', 'Juncos',
  'Lajas', 'Lares', 'Las Marias', 'Las Piedras', 'Loiza',
  'Luquillo', 'Manati', 'Maricao', 'Maunabo', 'Mayaguez',
  'Moca', 'Morovis', 'Naguabo', 'Naranjito', 'Orocovis',
  'Patillas', 'Penuelas', 'Ponce', 'Quebradillas', 'Rincon',
  'Rio Grande', 'Sabana Grande', 'Salinas', 'San German', 'San Juan',
  'San Lorenzo', 'San Sebastian', 'Santa Isabel', 'Toa Alta', 'Toa Baja',
  'Trujillo Alto', 'Utuado', 'Vega Alta', 'Vega Baja', 'Vieques',
  'Villalba', 'Yabucoa', 'Yauco',
]

export default function NuevaValidacionPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [mode, setMode] = useState<'select' | 'create'>('select')
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [projectDescription, setProjectDescription] = useState('')

  // New project form
  const [newProject, setNewProject] = useState({
    name: '',
    address: '',
    municipality: '',
    catastro_number: '',
  })

  // Validation result
  const [validationResult, setValidationResult] = useState<Validation | null>(null)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const data = await projectsApi.list()
      setProjects(data)
    } catch (err: any) {
      setError(err.message || 'Error cargando proyectos')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    setValidationResult(null)

    try {
      let projectId = selectedProjectId

      // If creating new project
      if (mode === 'create') {
        if (!newProject.name || !newProject.address || !newProject.municipality) {
          setError('Nombre, direccion y municipio son requeridos')
          setSubmitting(false)
          return
        }

        const createdProject = await projectsApi.create({
          name: newProject.name,
          address: newProject.address,
          municipality: newProject.municipality,
          catastro_number: newProject.catastro_number || undefined,
        })

        projectId = createdProject.id

        // Refresh projects list
        const projectsData = await projectsApi.list()
        setProjects(projectsData)
      }

      if (!projectId) {
        setError('Selecciona o crea un proyecto')
        setSubmitting(false)
        return
      }

      if (!projectDescription.trim()) {
        setError('Describe el uso propuesto del proyecto')
        setSubmitting(false)
        return
      }

      // Run validation
      const result = await projectsApi.validateFase1(projectId, projectDescription)
      setValidationResult(result)
    } catch (err: any) {
      setError(err.message || 'Error validando proyecto')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownloadPdf = async () => {
    if (!validationResult) return

    const token = await getAccessToken()
    const url = getApiUrl(`/validations/${validationResult.id}/report.pdf`)

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

  const selectedProject = projects.find((p) => p.id === selectedProjectId)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Nueva Validacion</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {/* Validation Result */}
      {validationResult && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Resultado de Validacion
          </h2>

          <div
            className={`p-4 rounded-md mb-4 ${
              validationResult.viable
                ? 'bg-green-50 border border-green-200'
                : 'bg-red-50 border border-red-200'
            }`}
          >
            <h3
              className={`font-semibold ${
                validationResult.viable ? 'text-green-800' : 'text-red-800'
              }`}
            >
              {validationResult.viable ? 'Proyecto Viable' : 'Proyecto No Viable'}
            </h3>
            <p
              className={`mt-1 text-sm ${
                validationResult.viable ? 'text-green-700' : 'text-red-700'
              }`}
            >
              {validationResult.viable
                ? 'El proyecto cumple con los requisitos de zonificacion en esa area.'
                : 'El uso propuesto no es compatible con la zonificacion.'}
            </p>
          </div>

          {/* Result details */}
          {validationResult.result && (
            <div className="space-y-3 text-sm">
              {(validationResult.result as any).final_result?.zoning_code && (
                <div>
                  <span className="font-medium text-gray-700">Zonificacion:</span>{' '}
                  <span className="text-gray-600">
                    {(validationResult.result as any).final_result.zoning_code} -{' '}
                    {(validationResult.result as any).final_result.zoning_name}
                  </span>
                </div>
              )}
              {(validationResult.result as any).final_result?.permit_type && (
                <div>
                  <span className="font-medium text-gray-700">Tipo de Permiso:</span>{' '}
                  <span className="text-gray-600">
                    {(validationResult.result as any).final_result.permit_type}
                  </span>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleDownloadPdf}
            className="btn-primary mt-4"
          >
            Descargar PDF
          </button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleValidate} className="card space-y-6">
        {/* Project Selection Mode */}
        <div>
          <div className="flex space-x-4 mb-4">
            <button
              type="button"
              onClick={() => setMode('select')}
              className={`px-4 py-2 rounded-md ${
                mode === 'select'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Seleccionar Proyecto Existente
            </button>
            <button
              type="button"
              onClick={() => setMode('create')}
              className={`px-4 py-2 rounded-md ${
                mode === 'create'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Crear Nuevo Proyecto
            </button>
          </div>
        </div>

        {/* Select Existing Project */}
        {mode === 'select' && (
          <div>
            <label className="label">Proyecto</label>
            <select
              className="input-field"
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
            >
              <option value="">-- Seleccionar proyecto --</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name} - {project.address || 'Sin direccion'}
                </option>
              ))}
            </select>

            {selectedProject && (
              <div className="mt-3 p-3 bg-gray-50 rounded-md text-sm">
                <p><strong>Direccion:</strong> {selectedProject.address || 'N/A'}</p>
                <p><strong>Municipio:</strong> {selectedProject.municipality || 'N/A'}</p>
                {selectedProject.catastro_number && (
                  <p><strong>Catastro:</strong> {selectedProject.catastro_number}</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Create New Project */}
        {mode === 'create' && (
          <div className="space-y-4">
            <div>
              <label className="label">
                Nombre del Proyecto <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input-field"
                value={newProject.name}
                onChange={(e) =>
                  setNewProject({ ...newProject, name: e.target.value })
                }
                placeholder="Mi Proyecto"
              />
            </div>

            <div>
              <label className="label">
                Direccion <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="input-field"
                value={newProject.address}
                onChange={(e) =>
                  setNewProject({ ...newProject, address: e.target.value })
                }
                placeholder="Calle Principal 123"
              />
            </div>

            <div>
              <label className="label">
                Municipio <span className="text-red-500">*</span>
              </label>
              <select
                className="input-field"
                value={newProject.municipality}
                onChange={(e) =>
                  setNewProject({ ...newProject, municipality: e.target.value })
                }
              >
                <option value="">-- Seleccionar municipio --</option>
                {MUNICIPALITIES.map((muni) => (
                  <option key={muni} value={muni}>
                    {muni}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Numero de Catastro</label>
              <input
                type="text"
                className="input-field"
                value={newProject.catastro_number}
                onChange={(e) =>
                  setNewProject({ ...newProject, catastro_number: e.target.value })
                }
                placeholder="000-000-000-00"
              />
              <p className="text-xs text-gray-500 mt-1">
                Debe verificar esta informacion para confirmar su exactitud.
              </p>
            </div>
          </div>
        )}

        {/* Project Description */}
        <div>
          <label className="label">
            Descripcion del Uso Propuesto <span className="text-red-500">*</span>
          </label>
          <textarea
            className="input-field"
            rows={4}
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
            placeholder="Describa el uso que desea darle a la propiedad, por ejemplo: 'Quiero construir una residencia unifamiliar' o 'Voy a operar un restaurante y oficinas'"
          />
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full"
          >
            {submitting ? 'Validando...' : 'Validar Proyecto'}
          </button>
        </div>
      </form>
    </div>
  )
}
