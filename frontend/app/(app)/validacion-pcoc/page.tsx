'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import {
  pcocApi,
  projectsApi,
  PCOCValidation,
  Project,
  ExemptCategory,
  getApiUrl,
} from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'

type TabType = 'filter1' | 'filter2' | 'filter3' | 'filter4' | 'result'

const TABS: { id: TabType; label: string; step: number }[] = [
  { id: 'filter1', label: 'Filtro 1: Requiere Permiso?', step: 1 },
  { id: 'filter2', label: 'Filtro 2: Ubicacion', step: 2 },
  { id: 'filter3', label: 'Filtro 3: Clasificacion', step: 3 },
  { id: 'filter4', label: 'Filtro 4: Ambiental', step: 4 },
  { id: 'result', label: 'Resultado', step: 5 },
]

export default function ValidacionPCOCPage() {
  const searchParams = useSearchParams()
  const pcocIdParam = searchParams.get('id')

  const [activeTab, setActiveTab] = useState<TabType>('filter1')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // PCOC validation state
  const [pcocValidation, setPcocValidation] = useState<PCOCValidation | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [exemptCategories, setExemptCategories] = useState<{
    obras_exentas: ExemptCategory[]
    obras_menores: ExemptCategory[]
  } | null>(null)

  // Form state
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [projectName, setProjectName] = useState('')
  const [propertyAddress, setPropertyAddress] = useState('')
  const [municipality, setMunicipality] = useState('')
  const [zoningCode, setZoningCode] = useState('')

  // Filter 1 state
  const [proposedUse, setProposedUse] = useState('')
  const [selectedExemptions, setSelectedExemptions] = useState<string[]>([])

  // Filter 2 state
  const [zonaHistorica, setZonaHistorica] = useState(false)
  const [zonaTuristica, setZonaTuristica] = useState(false)
  const [zonaInundacion, setZonaInundacion] = useState(false)

  // Filter 3 state
  const [projectParams, setProjectParams] = useState<Record<string, string>>({
    altura: '',
    area_ocupacion: '',
    tamano_solar: '',
  })

  // Load initial data
  useEffect(() => {
    loadInitialData()
  }, [])

  // Load existing PCOC if ID provided
  useEffect(() => {
    if (pcocIdParam) {
      loadPCOCValidation(pcocIdParam)
    }
  }, [pcocIdParam])

  const loadInitialData = async () => {
    try {
      setLoading(true)
      const [projectsData, categoriesData] = await Promise.all([
        projectsApi.list(),
        pcocApi.getExemptCategories(),
      ])
      setProjects(projectsData)
      setExemptCategories(categoriesData)
    } catch (err: any) {
      setError(err.message || 'Error cargando datos')
    } finally {
      setLoading(false)
    }
  }

  const loadPCOCValidation = async (id: string) => {
    try {
      setLoading(true)
      const data = await pcocApi.get(id)
      setPcocValidation(data)

      // Populate form from loaded data
      setProjectName(data.project_name || '')
      setPropertyAddress(data.property_address || '')
      setMunicipality(data.municipality || '')
      setZoningCode(data.zoning_code || '')

      if (data.filter1_data) {
        setProposedUse((data.filter1_data as any).proposed_use || '')
        setSelectedExemptions((data.filter1_data as any).exempt_selections || [])
      }

      if (data.filter2_data) {
        setZonaHistorica((data.filter2_data as any).zona_historica || false)
        setZonaTuristica((data.filter2_data as any).zona_turistica || false)
        setZonaInundacion((data.filter2_data as any).zona_inundacion || false)
      }

      if (data.filter3_data) {
        setProjectParams((data.filter3_data as any).project_params || {})
      }

      // Set active tab based on current step
      const stepTab = TABS.find(t => t.step === data.current_step)
      if (stepTab) {
        setActiveTab(stepTab.id)
      }
    } catch (err: any) {
      setError(err.message || 'Error cargando validacion')
    } finally {
      setLoading(false)
    }
  }

  const handleProjectSelect = (projectId: string) => {
    setSelectedProjectId(projectId)
    if (projectId) {
      const project = projects.find(p => p.id === projectId)
      if (project) {
        setProjectName(project.name)
        setPropertyAddress(project.address || '')
        setMunicipality(project.municipality || '')
        setZoningCode(project.zoning_code || '')
      }
    }
  }

  const handleStartValidation = async (skipProjectInfo = false) => {
    if (!skipProjectInfo && !projectName.trim()) {
      setError('Debe ingresar un nombre de proyecto')
      return
    }

    try {
      setSaving(true)
      setError(null)

      const newValidation = await pcocApi.create({
        project_id: skipProjectInfo ? undefined : (selectedProjectId || undefined),
        project_name: skipProjectInfo ? 'Validacion sin proyecto' : projectName,
        property_address: skipProjectInfo ? undefined : propertyAddress,
        municipality: skipProjectInfo ? undefined : municipality,
        zoning_code: skipProjectInfo ? undefined : zoningCode,
      })

      setPcocValidation(newValidation)
    } catch (err: any) {
      setError(err.message || 'Error creando validacion')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveFilter1 = async () => {
    if (!pcocValidation) return

    try {
      setSaving(true)
      setError(null)

      // Save filter 1 data
      await pcocApi.update(pcocValidation.id, {
        filter1_data: {
          proposed_use: proposedUse,
          exempt_selections: selectedExemptions,
        },
        current_step: 1,
      })

      // Analyze filter 1
      const result = await pcocApi.analyzeFilter1(pcocValidation.id)
      const updatedValidation = await pcocApi.get(pcocValidation.id)
      setPcocValidation(updatedValidation)

      // Check if exempt - show action items
      const isExempt = (updatedValidation.filter1_data as any)?.is_exempt
      if (isExempt) {
        // Stay on filter 1 to show the result
      } else {
        // Move to filter 2
        setActiveTab('filter2')
      }
    } catch (err: any) {
      setError(err.message || 'Error guardando filtro 1')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveFilter2 = async () => {
    if (!pcocValidation) return

    try {
      setSaving(true)
      setError(null)

      // Save filter 2 data
      await pcocApi.update(pcocValidation.id, {
        filter2_data: {
          zona_historica: zonaHistorica,
          zona_turistica: zonaTuristica,
          zona_inundacion: zonaInundacion,
        },
        current_step: 2,
      })

      // Analyze filter 2
      await pcocApi.analyzeFilter2(pcocValidation.id)
      const updatedValidation = await pcocApi.get(pcocValidation.id)
      setPcocValidation(updatedValidation)

      // Move to filter 3
      setActiveTab('filter3')
    } catch (err: any) {
      setError(err.message || 'Error guardando filtro 2')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveFilter3 = async () => {
    if (!pcocValidation) return

    try {
      setSaving(true)
      setError(null)

      // Save filter 3 data
      await pcocApi.update(pcocValidation.id, {
        filter3_data: {
          project_params: projectParams,
        },
        current_step: 3,
      })

      // Analyze filter 3
      await pcocApi.analyzeFilter3(pcocValidation.id)
      const updatedValidation = await pcocApi.get(pcocValidation.id)
      setPcocValidation(updatedValidation)

      // Move to filter 4
      setActiveTab('filter4')
    } catch (err: any) {
      setError(err.message || 'Error guardando filtro 3')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveFilter4 = async () => {
    if (!pcocValidation) return

    try {
      setSaving(true)
      setError(null)

      // Analyze filter 4 (uses proposed_use from filter 1)
      await pcocApi.analyzeFilter4(pcocValidation.id)

      // Generate final result
      await pcocApi.generateResult(pcocValidation.id)

      const updatedValidation = await pcocApi.get(pcocValidation.id)
      setPcocValidation(updatedValidation)

      // Move to result
      setActiveTab('result')
    } catch (err: any) {
      setError(err.message || 'Error generando resultado')
    } finally {
      setSaving(false)
    }
  }

  const handleDownloadPdf = async () => {
    if (!pcocValidation) return

    try {
      const token = await getAccessToken()
      const response = await fetch(getApiUrl(`/pcoc/${pcocValidation.id}/report.pdf`), {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        const blob = await response.blob()
        const blobUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = blobUrl
        link.download = `pcoc_validacion_${pcocValidation.id}.pdf`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(blobUrl)
      } else {
        setError('Error descargando PDF')
      }
    } catch (err: any) {
      setError(err.message || 'Error descargando PDF')
    }
  }

  const toggleExemption = (code: string) => {
    setSelectedExemptions(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  // If no validation started yet, show the start form
  if (!pcocValidation) {
    return (
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Validacion PCOC</h1>
        <p className="text-gray-600 mb-8">
          Checklist de pre-validacion para Permisos de Construccion segun el Reglamento Conjunto.
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        <div className="card space-y-6">
          <h2 className="text-lg font-semibold">Iniciar Nueva Validacion</h2>

          {/* Optional: Link to existing project */}
          <div>
            <label className="label">Vincular a Proyecto Existente (Opcional)</label>
            <select
              className="input-field"
              value={selectedProjectId}
              onChange={(e) => handleProjectSelect(e.target.value)}
            >
              <option value="">-- Seleccionar proyecto --</option>
              {projects.filter(p => p.phase1_completed).map(project => (
                <option key={project.id} value={project.id}>
                  {project.name} - {project.address || 'Sin direccion'}
                </option>
              ))}
            </select>
            <p className="text-sm text-gray-500 mt-1">
              Si vincula un proyecto, se auto-completaran los datos de direccion y zonificacion.
            </p>
            <button
              type="button"
              onClick={() => handleStartValidation(true)}
              disabled={saving}
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline mt-2"
            >
              o continuar sin proyecto
            </button>
          </div>

          {/* Project info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Nombre del Proyecto *</label>
              <input
                type="text"
                className="input-field"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Ej: Residencia Rodriguez"
              />
            </div>
            <div>
              <label className="label">Municipio</label>
              <input
                type="text"
                className="input-field"
                value={municipality}
                onChange={(e) => setMunicipality(e.target.value)}
                placeholder="Ej: San Juan"
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Direccion de la Propiedad</label>
              <input
                type="text"
                className="input-field"
                value={propertyAddress}
                onChange={(e) => setPropertyAddress(e.target.value)}
                placeholder="Ej: Calle Luna 123, Santurce"
              />
            </div>
            <div>
              <label className="label">Codigo de Zonificacion</label>
              <input
                type="text"
                className="input-field"
                value={zoningCode}
                onChange={(e) => setZoningCode(e.target.value)}
                placeholder="Ej: R-I, C-L"
              />
            </div>
          </div>

          <button
            onClick={() => handleStartValidation()}
            disabled={saving || !projectName.trim()}
            className="btn-primary w-full"
          >
            {saving ? 'Iniciando...' : 'Iniciar Validacion PCOC'}
          </button>
        </div>
      </div>
    )
  }

  // Main validation interface with tabs
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Validacion PCOC</h1>
          <p className="text-gray-600">{pcocValidation.project_name}</p>
        </div>
        {pcocValidation.status === 'completado' && (
          <button onClick={handleDownloadPdf} className="btn-primary">
            Descargar PDF
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-800 font-semibold">×</button>
        </div>
      )}

      {/* Horizontal Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-4 overflow-x-auto" aria-label="Tabs">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            const isCompleted = pcocValidation.current_step > tab.step
            const isDisabled = tab.step > pcocValidation.current_step + 1

            return (
              <button
                key={tab.id}
                onClick={() => !isDisabled && setActiveTab(tab.id)}
                disabled={isDisabled}
                className={`
                  whitespace-nowrap py-3 px-4 border-b-2 font-medium text-sm transition-colors
                  ${isActive
                    ? 'border-primary-600 text-primary-600'
                    : isCompleted
                    ? 'border-green-500 text-green-600 hover:text-green-700'
                    : isDisabled
                    ? 'border-transparent text-gray-400 cursor-not-allowed'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {isCompleted && <span className="mr-1">✓</span>}
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="card">
        {activeTab === 'filter1' && (
          <Filter1Content
            proposedUse={proposedUse}
            setProposedUse={setProposedUse}
            selectedExemptions={selectedExemptions}
            toggleExemption={toggleExemption}
            exemptCategories={exemptCategories}
            filter1Data={pcocValidation.filter1_data}
            onSave={handleSaveFilter1}
            saving={saving}
          />
        )}

        {activeTab === 'filter2' && (
          <Filter2Content
            zonaHistorica={zonaHistorica}
            setZonaHistorica={setZonaHistorica}
            zonaTuristica={zonaTuristica}
            setZonaTuristica={setZonaTuristica}
            zonaInundacion={zonaInundacion}
            setZonaInundacion={setZonaInundacion}
            filter2Data={pcocValidation.filter2_data}
            onSave={handleSaveFilter2}
            saving={saving}
          />
        )}

        {activeTab === 'filter3' && (
          <Filter3Content
            projectParams={projectParams}
            setProjectParams={setProjectParams}
            zoningCode={pcocValidation.zoning_code || ''}
            filter3Data={pcocValidation.filter3_data}
            onSave={handleSaveFilter3}
            saving={saving}
          />
        )}

        {activeTab === 'filter4' && (
          <Filter4Content
            filter4Data={pcocValidation.filter4_data}
            onSave={handleSaveFilter4}
            saving={saving}
          />
        )}

        {activeTab === 'result' && (
          <ResultContent
            result={pcocValidation.result}
            onDownloadPdf={handleDownloadPdf}
          />
        )}
      </div>
    </div>
  )
}

// Filter 1 Component
function Filter1Content({
  proposedUse,
  setProposedUse,
  selectedExemptions,
  toggleExemption,
  exemptCategories,
  filter1Data,
  onSave,
  saving,
}: {
  proposedUse: string
  setProposedUse: (v: string) => void
  selectedExemptions: string[]
  toggleExemption: (code: string) => void
  exemptCategories: { obras_exentas: ExemptCategory[]; obras_menores: ExemptCategory[] } | null
  filter1Data: Record<string, unknown> | null
  onSave: () => void
  saving: boolean
}) {
  const isExempt = (filter1Data as any)?.is_exempt
  const exemptReason = (filter1Data as any)?.exempt_reason
  const actionRequired = (filter1Data as any)?.action_required

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Filtro 1: Requiere Permiso de Construccion?</h3>
        <p className="text-gray-600 text-sm mb-4">
          Segun la Seccion 3.2 del Reglamento Conjunto, se requiere Permiso de Construccion para:
          Construccion, Reconstruccion, Remodelacion, Demolicion, Urbanizacion, Restauracion,
          Rehabilitacion, Ampliacion, o Alteracion.
        </p>
      </div>

      {/* Proposed use text input */}
      <div>
        <label className="label">Describa el uso propuesto o tipo de obra</label>
        <textarea
          className="input-field min-h-[100px]"
          value={proposedUse}
          onChange={(e) => setProposedUse(e.target.value)}
          placeholder="Ej: Remodelacion de cocina con instalacion de gabinetes nuevos, pintura interior..."
        />
      </div>

      {/* Exempt categories checklist */}
      {exemptCategories && (
        <div>
          <label className="label">Seleccione si la obra corresponde a alguna de estas categorias exentas (Sec. 3.2.4)</label>

          <div className="mt-2 space-y-2 max-h-64 overflow-y-auto border rounded-md p-3">
            <p className="text-sm font-medium text-gray-700 mb-2">Obras Exentas:</p>
            {exemptCategories.obras_exentas.map((cat) => (
              <label key={cat.code} className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedExemptions.includes(cat.code)}
                  onChange={() => toggleExemption(cat.code)}
                  className="mt-1"
                />
                <span className="text-sm text-gray-700">{cat.name_es}</span>
              </label>
            ))}

            <p className="text-sm font-medium text-gray-700 mt-4 mb-2">Obras de Caracter Menor Exentas (Sec. 3.2.4.2):</p>
            {exemptCategories.obras_menores.map((cat) => (
              <label key={cat.code} className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedExemptions.includes(cat.code)}
                  onChange={() => toggleExemption(cat.code)}
                  className="mt-1"
                />
                <span className="text-sm text-gray-700">{cat.name_es}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Analysis result */}
      {filter1Data && (
        <div className={`p-4 rounded-md ${isExempt ? 'bg-green-50 border border-green-200' : 'bg-blue-50 border border-blue-200'}`}>
          <h4 className="font-semibold mb-2">
            {isExempt ? 'Obra Exenta Detectada' : 'Requiere Permiso de Construccion'}
          </h4>
          {exemptReason && <p className="text-sm mb-2">{exemptReason}</p>}
          {actionRequired && (
            <p className="text-sm font-medium">{actionRequired}</p>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? 'Analizando...' : 'Analizar y Continuar'}
        </button>
      </div>
    </div>
  )
}

// Filter 2 Component
function Filter2Content({
  zonaHistorica,
  setZonaHistorica,
  zonaTuristica,
  setZonaTuristica,
  zonaInundacion,
  setZonaInundacion,
  filter2Data,
  onSave,
  saving,
}: {
  zonaHistorica: boolean
  setZonaHistorica: (v: boolean) => void
  zonaTuristica: boolean
  setZonaTuristica: (v: boolean) => void
  zonaInundacion: boolean
  setZonaInundacion: (v: boolean) => void
  filter2Data: Record<string, unknown> | null
  onSave: () => void
  saving: boolean
}) {
  const hasOverlays = (filter2Data as any)?.has_overlays
  const requiredRecs = (filter2Data as any)?.required_recommendations || []
  const actionItems = (filter2Data as any)?.action_items || []

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Filtro 2: Ubicacion - Zonas Sobrepuestas o Especiales</h3>
        <p className="text-gray-600 text-sm mb-4">
          Indique si la propiedad se encuentra en alguna de las siguientes zonas especiales.
        </p>
      </div>

      <div className="space-y-4">
        <label className="flex items-center gap-3 p-4 border rounded-md cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={zonaHistorica}
            onChange={(e) => setZonaHistorica(e.target.checked)}
            className="w-5 h-5"
          />
          <div>
            <span className="font-medium">Zona Historica (ZH) o Sitio Historico (SH)</span>
            <p className="text-sm text-gray-500">Sec. 10.2.2.3 - Requiere recomendacion del ICP</p>
          </div>
        </label>

        <label className="flex items-center gap-3 p-4 border rounded-md cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={zonaTuristica}
            onChange={(e) => setZonaTuristica(e.target.checked)}
            className="w-5 h-5"
          />
          <div>
            <span className="font-medium">Zona de Interes Turistico (ZIT)</span>
            <p className="text-sm text-gray-500">Requiere recomendacion de la Compania de Turismo</p>
          </div>
        </label>

        <label className="flex items-center gap-3 p-4 border rounded-md cursor-pointer hover:bg-gray-50">
          <input
            type="checkbox"
            checked={zonaInundacion}
            onChange={(e) => setZonaInundacion(e.target.checked)}
            className="w-5 h-5"
          />
          <div>
            <span className="font-medium">Zona de Riesgo de Inundacion o Deslizamiento</span>
            <p className="text-sm text-gray-500">Sec. 3.2.1.2 - Requiere Certificacion de Inundabilidad de la JP</p>
          </div>
        </label>
      </div>

      {/* Analysis result */}
      {filter2Data && (
        <div className={`p-4 rounded-md ${hasOverlays ? 'bg-yellow-50 border border-yellow-200' : 'bg-green-50 border border-green-200'}`}>
          <h4 className="font-semibold mb-2">
            {hasOverlays ? 'Recomendaciones Requeridas' : 'No se Requieren Recomendaciones Adicionales'}
          </h4>

          {requiredRecs.length > 0 && (
            <div className="mt-2 space-y-2">
              {requiredRecs.map((rec: any, i: number) => (
                <div key={i} className="text-sm">
                  <span className="font-medium">{rec.agency}:</span> {rec.requirement}
                  <span className="text-gray-500 ml-2">(Plazo: {rec.deadline_days} dias)</span>
                </div>
              ))}
            </div>
          )}

          {actionItems.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium">Acciones requeridas:</p>
              <ul className="list-disc list-inside text-sm mt-1">
                {actionItems.map((item: string, i: number) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? 'Analizando...' : 'Analizar y Continuar'}
        </button>
      </div>
    </div>
  )
}

// Filter 3 Component
function Filter3Content({
  projectParams,
  setProjectParams,
  zoningCode,
  filter3Data,
  onSave,
  saving,
}: {
  projectParams: Record<string, string>
  setProjectParams: (v: Record<string, string>) => void
  zoningCode: string
  filter3Data: Record<string, unknown> | null
  onSave: () => void
  saving: boolean
}) {
  const isMinisterial = (filter3Data as any)?.is_ministerial
  const comparisonResults = (filter3Data as any)?.comparison_results || []
  const nonCompliantParams = (filter3Data as any)?.non_compliant_params || []
  const districtReqs = (filter3Data as any)?.district_requirements || {}

  const updateParam = (key: string, value: string) => {
    setProjectParams({ ...projectParams, [key]: value })
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Filtro 3: Clasificacion del Tramite</h3>
        <p className="text-gray-600 text-sm mb-4">
          Ingrese los parametros del proyecto para determinar si es un asunto Ministerial o Discrecional.
          El proyecto debe cumplir con todos los parametros del distrito {zoningCode || 'seleccionado'}.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="label">Altura del Proyecto</label>
          <input
            type="text"
            className="input-field"
            value={projectParams.altura || ''}
            onChange={(e) => updateParam('altura', e.target.value)}
            placeholder="Ej: 2 pisos, 8 metros"
          />
          {districtReqs.max_height && (
            <p className="text-sm text-gray-500 mt-1">Maximo permitido: {districtReqs.max_height}</p>
          )}
        </div>

        <div>
          <label className="label">Area de Ocupacion (%)</label>
          <input
            type="text"
            className="input-field"
            value={projectParams.area_ocupacion || ''}
            onChange={(e) => updateParam('area_ocupacion', e.target.value)}
            placeholder="Ej: 35%"
          />
          {districtReqs.max_coverage && (
            <p className="text-sm text-gray-500 mt-1">Maximo permitido: {districtReqs.max_coverage}</p>
          )}
        </div>

        <div>
          <label className="label">Tamano del Solar</label>
          <input
            type="text"
            className="input-field"
            value={projectParams.tamano_solar || ''}
            onChange={(e) => updateParam('tamano_solar', e.target.value)}
            placeholder="Ej: 500 m2"
          />
          {districtReqs.min_lot_size && (
            <p className="text-sm text-gray-500 mt-1">Minimo requerido: {districtReqs.min_lot_size}</p>
          )}
        </div>
      </div>

      {/* Analysis result */}
      {filter3Data && isMinisterial !== undefined && (
        <div className={`p-4 rounded-md ${isMinisterial ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'}`}>
          <h4 className="font-semibold mb-2">
            {isMinisterial ? 'Tramite Ministerial' : 'Tramite Discrecional'}
          </h4>
          <p className="text-sm mb-2">
            {isMinisterial
              ? 'El proyecto cumple con todos los parametros del distrito. Puede ser evaluado por OGPe, Municipio (I-III) o Profesional Autorizado (PA).'
              : 'El proyecto no cumple con algunos parametros. Requiere evaluacion por la Junta Adjudicativa.'}
          </p>

          {comparisonResults.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium">Comparacion de parametros:</p>
              <div className="mt-2 space-y-1">
                {comparisonResults.map((result: any, i: number) => (
                  <div key={i} className="text-sm flex items-center gap-2">
                    <span className={result.compliant ? 'text-green-600' : 'text-red-600'}>
                      {result.compliant ? '✓' : '✗'}
                    </span>
                    <span className="font-medium">{result.param}:</span>
                    <span>{result.project_value}</span>
                    <span className="text-gray-500">(Req: {result.requirement})</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {nonCompliantParams.length > 0 && (
            <p className="text-sm mt-2 text-red-600">
              Parametros no conformes: {nonCompliantParams.join(', ')}
            </p>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? 'Analizando...' : 'Analizar y Continuar'}
        </button>
      </div>
    </div>
  )
}

// Filter 4 Component
function Filter4Content({
  filter4Data,
  onSave,
  saving,
}: {
  filter4Data: Record<string, unknown> | null
  onSave: () => void
  saving: boolean
}) {
  const isCategoricalExclusion = (filter4Data as any)?.is_categorical_exclusion
  const exclusionCategory = (filter4Data as any)?.exclusion_category
  const requiresEaDia = (filter4Data as any)?.requires_ea_dia
  const message = (filter4Data as any)?.message

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Filtro 4: Cumplimiento Ambiental</h3>
        <p className="text-gray-600 text-sm mb-4">
          Verificacion automatica contra las Exclusiones Categoricas de la OA 10-2025 de DRNA.
          El sistema analizara el uso propuesto para determinar si cualifica como Exclusion Categorica (EXC)
          o si requiere una Evaluacion Ambiental (EA) o Declaracion de Impacto Ambiental (DIA).
        </p>
      </div>

      {!filter4Data && (
        <div className="p-4 bg-gray-50 border rounded-md">
          <p className="text-gray-600">
            Presione el boton para analizar el cumplimiento ambiental y generar el resultado final.
          </p>
        </div>
      )}

      {/* Analysis result */}
      {filter4Data && (
        <div className={`p-4 rounded-md ${isCategoricalExclusion ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'}`}>
          <h4 className="font-semibold mb-2">
            {isCategoricalExclusion ? 'Exclusion Categorica Aplica' : 'Requiere Evaluacion Ambiental'}
          </h4>

          {exclusionCategory && (
            <p className="text-sm mb-2">
              <span className="font-medium">Categoria:</span> {exclusionCategory}
            </p>
          )}

          {message && <p className="text-sm">{message}</p>}

          {requiresEaDia && (
            <p className="text-sm mt-2 text-yellow-700">
              Debe presentar una Evaluacion Ambiental (EA) o Declaracion de Impacto Ambiental (DIA) ante la DECA.
            </p>
          )}
        </div>
      )}

      <div className="flex justify-end">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? 'Generando Resultado...' : 'Generar Resultado Final'}
        </button>
      </div>
    </div>
  )
}

// Result Component
function ResultContent({
  result,
  onDownloadPdf,
}: {
  result: Record<string, unknown> | null
  onDownloadPdf: () => void
}) {
  if (!result) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">Complete todos los filtros para ver el resultado.</p>
      </div>
    )
  }

  const permitType = (result as any).permit_type
  const summary = (result as any).summary
  const actionItems = (result as any).action_items || []
  const recommendations = (result as any).recommendations || []
  const filterSummary = (result as any).filter_summary || {}

  const permitTypeDisplay: Record<string, { label: string; color: string }> = {
    obra_exenta: { label: 'OBRA EXENTA', color: 'bg-green-100 text-green-800' },
    ministerial: { label: 'TRAMITE MINISTERIAL', color: 'bg-blue-100 text-blue-800' },
    discrecional: { label: 'TRAMITE DISCRECIONAL', color: 'bg-yellow-100 text-yellow-800' },
  }

  const typeInfo = permitTypeDisplay[permitType] || { label: permitType, color: 'bg-gray-100 text-gray-800' }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <span className={`inline-block px-4 py-2 rounded-full text-lg font-semibold ${typeInfo.color}`}>
          {typeInfo.label}
        </span>
        <p className="mt-4 text-gray-700">{summary}</p>
      </div>

      {/* Filter Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 bg-gray-50 rounded-md text-center">
          <p className="text-sm text-gray-500">Filtro 1</p>
          <p className="font-semibold">{filterSummary.filter1_exempt ? 'Exenta' : 'Requiere Permiso'}</p>
        </div>
        <div className="p-3 bg-gray-50 rounded-md text-center">
          <p className="text-sm text-gray-500">Filtro 2</p>
          <p className="font-semibold">{filterSummary.filter2_has_overlays ? 'Con Zonas' : 'Sin Zonas'}</p>
        </div>
        <div className="p-3 bg-gray-50 rounded-md text-center">
          <p className="text-sm text-gray-500">Filtro 3</p>
          <p className="font-semibold">{filterSummary.filter3_ministerial ? 'Ministerial' : 'Discrecional'}</p>
        </div>
        <div className="p-3 bg-gray-50 rounded-md text-center">
          <p className="text-sm text-gray-500">Filtro 4</p>
          <p className="font-semibold">{filterSummary.filter4_categorical_exclusion ? 'EXC' : 'EA/DIA'}</p>
        </div>
      </div>

      {/* Action Items */}
      {actionItems.length > 0 && (
        <div>
          <h4 className="font-semibold mb-3">Acciones Requeridas</h4>
          <div className="space-y-3">
            {actionItems.map((item: any, i: number) => (
              <div key={i} className="p-3 bg-gray-50 rounded-md">
                <p className="font-medium">{item.action}</p>
                {item.description && <p className="text-sm text-gray-600">{item.description}</p>}
                {item.deadline && <p className="text-sm text-gray-500">Plazo: {item.deadline}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div>
          <h4 className="font-semibold mb-3">Recomendaciones</h4>
          <ul className="list-disc list-inside space-y-1">
            {recommendations.map((rec: string, i: number) => (
              <li key={i} className="text-gray-700">{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 pt-4 border-t">
        <button onClick={onDownloadPdf} className="btn-primary flex-1">
          Descargar PDF
        </button>
        <button
          className="btn-secondary flex-1"
          onClick={() => alert('Proximamente: Pre-validacion profesional')}
        >
          Quieres pre-validar tu solicitud?
        </button>
      </div>
    </div>
  )
}
