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

// Municipalities with their own POT (Plan de Ordenamiento Territorial)
const POT_MUNICIPALITIES: { [key: string]: string[] } = {
  'Barceloneta': ['R.i', 'R.a', 'R.b', 'M.b', 'M.i', 'M.a', 'C.b', 'C.i', 'C.a', 'I.i', 'I.a', 'A.g', 'A.a', 'D.g', 'D.p', 'O.b', 'O.g', 'O.a'],
  'Caguas': ['CUT-8', 'CUT-12', 'CUT-D', 'CUT-P'],
  'Carolina': ['R-1', 'R-2', 'R-3', 'R-4', 'R-5', 'RU-1', 'RU-2', 'RC-1', 'M-1', 'M-2', 'M-3', 'CO-1', 'CO-2', 'C-L', 'C-1', 'C-2', 'C-3', 'C-4', 'C-5', 'C-6', 'CC-1', 'RT-2', 'RT-3', 'RT-4', 'RT-5', 'CT-1', 'CT-2', 'CT-3', 'DTS', 'I-1', 'I-2', 'IL-1', 'IL-2', 'RR-0', 'AD', 'R-0', 'A-1', 'A-2', 'A-3', 'A-G', 'D-A', 'D-C', 'D-E', 'D-I', 'D-O', 'D-P', 'D-T', 'B-1', 'B-2', 'B-U', 'CR-1', 'CR-2', 'CR-3', 'CR-4', 'CRC-3', 'P-R', 'P-P', 'CR-H', 'CR-A', 'RI-1', 'RI-2'],
  'Corozal': ['R.i', 'R.a', 'R.b', 'M.b', 'M.i', 'M.a', 'C.b', 'C.i', 'C.a', 'I.i', 'I.a', 'A.g', 'A.a', 'D.g', 'D.p', 'O.b', 'O.g', 'O.a'],
  'Guaynabo': ['R-1', 'R-2', 'R-3', 'R-4', 'R-5', 'R-A', 'R-O y U', 'R-3-P-A', 'R-5-P-A', 'PACUT', 'R-3-T', 'R-4-T', 'R-5-T', 'CO-1', 'C-1', 'C-1-T', 'C-2', 'C-3', 'C-3-T', 'C-4', 'C-L-PA', 'C-1-PA', 'C-2-PA', 'I-1', 'I-1-T', 'I-2', 'IL-1', 'IL-1-PA', 'IL-2', 'AD', 'D-1', 'D-1-T', 'D-2', 'D-2-T', 'D-3', 'D-3-T', 'DT-G', 'DT-P', 'CR', 'CR-3', 'CR-5', 'CR-C', 'M'],
  'Juncos': ['R-1', 'R-3', 'R-4', 'R-5', 'EC', 'ECN', 'EM', 'M-1', 'C-L', 'C-1', 'C-2', 'I-1', 'I-2', 'IL-1', 'IL-2', 'AD', 'A-1', 'A-2', 'A-3', 'A-G', 'P', 'B-1', 'CR-3', 'AM'],
  'Lajas': ['R.i', 'R.a', 'R.b', 'M.b', 'M.i', 'M.a', 'C.b', 'C.i', 'C.a', 'I.i', 'I.a', 'A.g', 'A.a', 'D.g', 'D.p', 'O.b', 'O.g', 'O.a'],
  'Ponce': ['EH.0', 'EH.1', 'EH.2', 'EH.3', 'EV.1', 'EV.2', 'EV.3', 'EV.4', 'CT', 'ZH', 'SUP', 'SUNP', 'SRC.T', 'DI.1', 'DI.2', 'AP.0', 'AP.1', 'AP.2', 'AP.3', 'AP.4', 'SRC.AR', 'SRC.0', 'SRC.1', 'SRC.2', 'SRC.3', 'SRC.4', 'SREP.A', 'D', 'SREP.N', 'SREP.H', 'CM'],
  'Rincon': ['R.i', 'R.b', 'M.b', 'M.i', 'C.b', 'C.i', 'I.i', 'I.a', 'A.g', 'A.a', 'D.g', 'D.p', 'O.b', 'O.g', 'O.a'],
  'San Juan': ['R-0', 'R-1', 'R-2', 'R-3', 'R-4', 'R-5', 'R-6', 'CO-1', 'CO-2', 'C-L', 'C-1', 'C-2', 'C-3', 'C-4', 'C-5', 'C-6', 'RT-3', 'RT-4', 'RT-5', 'CT-1', 'CT-2', 'CT-3', 'I-1', 'I-2', 'IL-1', 'IL-2', 'SRP', 'D', 'DA', 'DE', 'DS', 'DT', 'DV', 'DD', 'CPN', 'CR-H', 'M'],
  'Santa Isabel': ['PA-1', 'PA-2', 'PA-3', 'PA-4', 'PA-5', 'PE-1', 'PE-2', 'PE-3', 'PE-4', 'PE-5', 'PE-6', 'PE-7'],
  'Vieques': ['R.i', 'R.g', 'M.b', 'M.i', 'C.b', 'C.i', 'I.i', 'I.a', 'A.g', 'A.a', 'D.g', 'D.p', 'O.b', 'O.g', 'O.a'],
}

// Default Reglamento Conjunto calificaciones for non-POT municipalities
const DEFAULT_RC_CALIFICACIONES = [
  'R-B', 'R-I', 'R-U', 'R-C',
  'C-L', 'C-I', 'C-C', 'C-T',
  'RC-E', 'RT-I', 'RT-A', 'DTS',
  'I-L', 'I-P', 'I-E',
  'ARD', 'R-G',
  'A-G', 'A-P',
  'D-G', 'D-A',
  'A-B', 'C-R', 'P-R', 'R-E',
  'P-P', 'S-H', 'C-H', 'M',
]

// Get calificaciones for a municipality
function getCalificacionesForMunicipality(municipality: string): string[] {
  if (POT_MUNICIPALITIES[municipality]) {
    return POT_MUNICIPALITIES[municipality]
  }
  return DEFAULT_RC_CALIFICACIONES
}

// Check if municipality has POT
function isPOTMunicipality(municipality: string): boolean {
  return municipality in POT_MUNICIPALITIES
}

export default function NuevaValidacionPage() {
  const router = useRouter()
  const [submitting, setSubmitting] = useState(false)
  const [validatingAddress, setValidatingAddress] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [address, setAddress] = useState('')
  const [municipality, setMunicipality] = useState('')
  const [calificacion, setCalificacion] = useState('')

  // Address validation results (hidden until validated)
  const [addressValidated, setAddressValidated] = useState(false)
  const [calificacionAutoDetected, setCalificacionAutoDetected] = useState(false)
  const [calificacionMIPRHint, setCalificacionMIPRHint] = useState<string | null>(null)
  const [catastroNumber, setCatastroNumber] = useState('')
  const [coordinates, setCoordinates] = useState<{ lat: number; lng: number } | null>(null)

  // Validation result
  const [validationResult, setValidationResult] = useState<Validation | null>(null)

  // Get available calificaciones based on selected municipality
  const availableCalificaciones = municipality ? getCalificacionesForMunicipality(municipality) : []
  const hasPOT = municipality ? isPOTMunicipality(municipality) : false

  // Reset calificacion when municipality changes
  useEffect(() => {
    setCalificacion('')
  }, [municipality])

  // Reset address validation when address or municipality changes
  useEffect(() => {
    setAddressValidated(false)
    setCalificacionAutoDetected(false)
    setCalificacionMIPRHint(null)
    setCatastroNumber('')
    setCoordinates(null)
  }, [address, municipality])

  const handleValidateAddress = async () => {
    if (!address || !municipality) {
      setError('Direccion y municipio son requeridos para validar')
      return
    }

    setError(null)
    setValidatingAddress(true)

    try {
      // Call backend to validate address with Google Maps + ArcGIS
      const token = await getAccessToken()
      const response = await fetch(getApiUrl('/validate-address'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          address,
          municipality,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Error validando direccion' }))
        setError(errorData.error || errorData.detail || 'No se pudo validar la direccion')
        return
      }

      const result = await response.json()

      if (result.valid) {
        setCoordinates({ lat: result.latitude, lng: result.longitude })
        setCatastroNumber(result.catastro_number || '')
        setAddressValidated(true)

        // Auto-populate calificacion if ArcGIS returned one and it's valid for the municipality
        if (result.calificacion) {
          const available = getCalificacionesForMunicipality(municipality)
          if (available.includes(result.calificacion)) {
            setCalificacion(result.calificacion)
            setCalificacionAutoDetected(true)
            setCalificacionMIPRHint(null)
          } else {
            // MIPR returned a code not in the dropdown list — show it as a hint
            setCalificacionMIPRHint(result.calificacion)
          }
        }
      } else {
        setError(result.error || 'No se pudo validar la direccion')
      }
    } catch (err: any) {
      setError(err.message || 'Error conectando con el servidor')
    } finally {
      setValidatingAddress(false)
    }
  }

  const handleValidate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    setValidationResult(null)

    try {
      if (!address || !municipality) {
        setError('Direccion y municipio son requeridos')
        setSubmitting(false)
        return
      }

      if (!projectDescription.trim()) {
        setError('Describe el uso propuesto del proyecto')
        setSubmitting(false)
        return
      }

      if (!calificacion) {
        setError('Debe seleccionar una calificacion/distrito de zonificacion')
        setSubmitting(false)
        return
      }

      // Create project and run validation
      const createdProject = await projectsApi.create({
        name: projectName || `Validacion ${new Date().toLocaleDateString('es-PR')}`,
        address: address,
        municipality: municipality,
        catastro_number: catastroNumber || undefined,
        calificacion: calificacion,
      })

      // Run validation with user-selected district
      const result = await projectsApi.validateFase1(createdProject.id, projectDescription, calificacion)
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

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Nueva Validacion</h1>
        <p className="text-gray-600 italic">Pre-validacion rapida de zonificacion</p>
      </div>

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
              {(validationResult.result as any).final_result?.recommendations && (
                <div>
                  <span className="font-medium text-gray-700">Recomendaciones:</span>
                  <ul className="list-disc list-inside text-gray-600 mt-1">
                    {(validationResult.result as any).final_result.recommendations.map((rec: string, i: number) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
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
        <h2 className="text-lg font-semibold text-gray-900">Crear Nuevo Proyecto</h2>

        {/* Project Name (optional) */}
        <div>
          <label className="label">Nombre del Proyecto (opcional)</label>
          <input
            type="text"
            className="input-field"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Mi Proyecto"
          />
        </div>

        {/* Project Description */}
        <div>
          <label className="label">
            Descripcion del Uso Propuesto <span className="text-red-500">*</span>
          </label>
          <textarea
            className="input-field"
            rows={3}
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
            placeholder="Ej: Residencia unifamiliar, restaurante con area de estacionamiento, oficina comercial..."
          />
        </div>

        {/* Address and Municipality Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">
              Direccion de la Propiedad <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              className="input-field"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Calle Principal 123"
            />
          </div>

          <div>
            <label className="label">
              Municipio <span className="text-red-500">*</span>
            </label>
            <select
              className="input-field"
              value={municipality}
              onChange={(e) => setMunicipality(e.target.value)}
            >
              <option value="">-- Seleccionar municipio --</option>
              {MUNICIPALITIES.map((muni) => (
                <option key={muni} value={muni}>
                  {muni}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Validate Address Button */}
        <div>
          <button
            type="button"
            onClick={handleValidateAddress}
            disabled={!address || !municipality || validatingAddress}
            className="btn-secondary"
          >
            {validatingAddress ? (
              <>
                <span className="animate-spin inline-block w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full mr-2"></span>
                Validando...
              </>
            ) : (
              'Validar Direccion'
            )}
          </button>
        </div>

        {/* Address Validation Results (shown after validation) */}
        {addressValidated && coordinates && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4 space-y-4">
            <div className="flex items-center gap-2 text-blue-800">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-medium">Direccion Validada</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label text-blue-700">Num de Catastro</label>
                <input
                  type="text"
                  className="input-field bg-white"
                  value={catastroNumber}
                  onChange={(e) => setCatastroNumber(e.target.value)}
                  placeholder="000-000-000-00"
                />
              </div>

              <div>
                <label className="label text-blue-700">Coordenadas</label>
                <input
                  type="text"
                  className="input-field bg-white"
                  value={`${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}`}
                  readOnly
                />
              </div>
            </div>

            {/* GIS Map Link */}
            <div className="text-sm">
              <p className="text-blue-700 mb-2">
                Verifique la informacion en el mapa oficial:
              </p>
              <a
                href="https://gis.jp.pr.gov/mipr/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                Abrir Mapa Interactivo de Puerto Rico (MIPR)
              </a>
              <p className="text-blue-600 text-xs mt-2">
                * Debe verificar esta informacion para confirmar su exactitud antes de continuar.
              </p>
            </div>
          </div>
        )}

        {/* Calificacion Dropdown (shown only after municipality is selected) */}
        {municipality && (
          <div>
            <label className="label">
              Calificacion / Distrito de Zonificacion <span className="text-red-500">*</span>
              {hasPOT && (
                <span className="ml-2 text-xs font-normal text-blue-600">
                  (POT Municipal - {municipality})
                </span>
              )}
            </label>
            <select
              className="input-field"
              value={calificacion}
              onChange={(e) => { setCalificacion(e.target.value); setCalificacionAutoDetected(false); setCalificacionMIPRHint(null) }}
              required
            >
              <option value="">-- Seleccionar calificacion --</option>
              {availableCalificaciones.map((cal) => (
                <option key={cal} value={cal}>
                  {cal}
                </option>
              ))}
            </select>
            {calificacionAutoDetected && (
              <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Calificacion detectada automaticamente desde MIPR · Puede cambiarla si es necesario
              </p>
            )}
            {calificacionMIPRHint && !calificacionAutoDetected && (
              <p className="text-xs text-amber-600 mt-1 flex items-start gap-1">
                <svg className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                MIPR detectó calificación: <strong className="mx-0.5">{calificacionMIPRHint}</strong> · No está en la lista para este municipio. Seleccione manualmente o verifique en el mapa MIPR.
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              {hasPOT
                ? `${municipality} tiene su propio Plan de Ordenamiento Territorial (POT). Verifique la calificacion en el mapa MIPR.`
                : 'Usando calificaciones del Reglamento Conjunto 2020. Verifique la calificacion en el mapa MIPR.'}
            </p>
          </div>
        )}

        {/* Submit Button */}
        <div className="pt-4 border-t">
          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full"
          >
            {submitting ? (
              <>
                <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                Analizando...
              </>
            ) : (
              'Validar Proyecto'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
