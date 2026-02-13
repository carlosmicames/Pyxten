'use client'

import { useState, useEffect, useRef } from 'react'
import {
  documentsApi,
  pcocApi,
  DocumentValidation,
  DocumentRequirement,
  DocumentValidationResult,
  PCOCValidation,
} from '@/lib/api'
import { uploadDocument, deleteDocument } from '@/lib/storage'

type ValidationTypeOption = 'select' | 'pcoc' | 'permiso_unico'

export default function ValidacionDocumentosPage() {
  const [validationType, setValidationType] = useState<ValidationTypeOption>('select')
  const [validations, setValidations] = useState<DocumentValidation[]>([])
  const [pcocValidations, setPcocValidations] = useState<PCOCValidation[]>([])
  const [selectedValidation, setSelectedValidation] = useState<DocumentValidation | null>(null)
  const [requirements, setRequirements] = useState<DocumentRequirement[]>([])
  const [validationResult, setValidationResult] = useState<DocumentValidationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Upload state
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null)
  const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  // Form state for creating new validation
  const [showNewForm, setShowNewForm] = useState(false)
  const [showPcocLinkModal, setShowPcocLinkModal] = useState(false)
  const [newFormData, setNewFormData] = useState({
    pcoc_validation_id: '',
    project_name: '',
    property_address: '',
    municipality: '',
  })

  // Load existing document validations
  useEffect(() => {
    if (validationType !== 'select') {
      loadValidations()
      loadRequirements()
    }
  }, [validationType])

  // Load PCOC validations for linking
  useEffect(() => {
    if (validationType === 'pcoc') {
      loadPcocValidations()
    }
  }, [validationType])

  const loadValidations = async () => {
    try {
      setLoading(true)
      const data = await documentsApi.list(validationType === 'select' ? undefined : validationType)
      setValidations(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar validaciones')
    } finally {
      setLoading(false)
    }
  }

  const loadPcocValidations = async () => {
    try {
      const data = await pcocApi.list()
      setPcocValidations(data.filter(p => p.status === 'completado'))
    } catch (err) {
      console.error('Error loading PCOC validations:', err)
    }
  }

  const loadRequirements = async () => {
    try {
      const data = validationType === 'pcoc'
        ? await documentsApi.getPCOCRequirements()
        : await documentsApi.getPermisoUnicoRequirements()
      setRequirements(data)
    } catch (err) {
      console.error('Error loading requirements:', err)
    }
  }

  const handleSelectValidationType = (type: 'pcoc' | 'permiso_unico') => {
    setValidationType(type)
    setSelectedValidation(null)
    setValidationResult(null)
  }

  const handleCreateValidation = async () => {
    try {
      setLoading(true)
      setError(null)
      const newValidation = await documentsApi.create({
        validation_type: validationType === 'select' ? 'pcoc' : validationType,
        pcoc_validation_id: newFormData.pcoc_validation_id || undefined,
        project_name: newFormData.project_name || undefined,
        property_address: newFormData.property_address || undefined,
        municipality: newFormData.municipality || undefined,
      })
      setValidations([newValidation, ...validations])
      setSelectedValidation(newValidation)
      setShowNewForm(false)
      setNewFormData({ pcoc_validation_id: '', project_name: '', property_address: '', municipality: '' })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear validacion')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectValidation = (validation: DocumentValidation) => {
    setSelectedValidation(validation)
    setValidationResult(null)
  }

  const handleDocumentToggle = async (docCode: string, uploaded: boolean) => {
    if (!selectedValidation) return

    try {
      const result = await documentsApi.updateDocumentStatus(selectedValidation.id, docCode, { uploaded })
      // Update local state
      setSelectedValidation({
        ...selectedValidation,
        documents: result.documents,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al actualizar documento')
    }
  }

  const handleFileUpload = async (docCode: string, file: File) => {
    if (!selectedValidation) return

    setUploadingDoc(docCode)
    setError(null)

    try {
      const uploadResult = await uploadDocument(file, selectedValidation.id, docCode)

      if (!uploadResult.success) {
        setError(uploadResult.error || 'Error al subir el archivo')
        return
      }

      // Update the document status in the backend
      const result = await documentsApi.updateDocumentStatus(selectedValidation.id, docCode, {
        uploaded: true,
        file_url: uploadResult.url,
        file_name: uploadResult.fileName,
      })

      // Update local state
      setSelectedValidation({
        ...selectedValidation,
        documents: result.documents,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al subir el documento')
    } finally {
      setUploadingDoc(null)
    }
  }

  const handleRemoveDocument = async (docCode: string) => {
    if (!selectedValidation) return

    const docStatus = selectedValidation.documents?.[docCode]
    if (!docStatus?.file_url) return

    if (!confirm('Esta seguro que desea eliminar este documento?')) return

    try {
      // Delete from storage
      await deleteDocument(docStatus.file_url)

      // Update backend
      const result = await documentsApi.updateDocumentStatus(selectedValidation.id, docCode, {
        uploaded: false,
        file_url: '',
        file_name: '',
      })

      // Update local state
      setSelectedValidation({
        ...selectedValidation,
        documents: result.documents,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar el documento')
    }
  }

  const handleLinkPcocValidation = async (pcocId: string) => {
    const pcoc = pcocValidations.find(p => p.id === pcocId)
    if (!pcoc) return

    setNewFormData({
      pcoc_validation_id: pcocId,
      project_name: pcoc.project_name || '',
      property_address: pcoc.property_address || '',
      municipality: pcoc.municipality || '',
    })
    setShowPcocLinkModal(false)
    setShowNewForm(true)
  }

  const handleValidateDocuments = async () => {
    if (!selectedValidation) return

    try {
      setLoading(true)
      const result = await documentsApi.validate(selectedValidation.id)
      setValidationResult(result.validation_result)
      setSelectedValidation({
        ...selectedValidation,
        status: result.status,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al validar documentos')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateMemorial = async () => {
    if (!selectedValidation) return

    try {
      setLoading(true)
      const result = await documentsApi.generateMemorial(selectedValidation.id)
      setSelectedValidation({
        ...selectedValidation,
        memorial_explicativo: result.memorial_explicativo,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al generar Memorial Explicativo')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteValidation = async (id: string) => {
    if (!confirm('Esta seguro que desea eliminar esta validacion?')) return

    try {
      await documentsApi.delete(id)
      setValidations(validations.filter(v => v.id !== id))
      if (selectedValidation?.id === id) {
        setSelectedValidation(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al eliminar validacion')
    }
  }

  // Selection screen
  if (validationType === 'select') {
    return (
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Validacion de Documentos</h1>
        <p className="text-gray-600 mb-8">
          Seleccione el tipo de validacion para verificar los documentos requeridos.
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          {/* PCOC Option */}
          <button
            onClick={() => handleSelectValidationType('pcoc')}
            className="bg-white border-2 border-gray-200 rounded-lg p-6 text-left hover:border-blue-500 hover:shadow-md transition-all"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">PCOC</h2>
                <p className="text-sm text-gray-500">Permiso de Construccion</p>
              </div>
            </div>
            <p className="text-gray-600 text-sm">
              Validacion de documentos para permisos de construccion. Incluye planos, certificaciones y Memorial Explicativo.
            </p>
          </button>

          {/* Permiso Unico Option */}
          <button
            onClick={() => handleSelectValidationType('permiso_unico')}
            className="bg-white border-2 border-gray-200 rounded-lg p-6 text-left hover:border-green-500 hover:shadow-md transition-all opacity-50 cursor-not-allowed"
            disabled
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Permiso Unico</h2>
                <p className="text-sm text-gray-500">Proximamente</p>
              </div>
            </div>
            <p className="text-gray-600 text-sm">
              Validacion de documentos para Permiso Unico. Incluye legitimacion activa, identificacion y certificaciones.
            </p>
          </button>
        </div>
      </div>
    )
  }

  // PCOC Document Validation Screen
  return (
    <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setValidationType('select')}
              className="text-gray-500 hover:text-gray-700"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Validacion de Documentos - {validationType === 'pcoc' ? 'PCOC' : 'Permiso Unico'}
              </h1>
              <p className="text-gray-600">
                Verifique que tiene todos los documentos requeridos para su solicitud.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            {validationType === 'pcoc' && pcocValidations.length > 0 && (
              <button
                onClick={() => setShowPcocLinkModal(true)}
                className="btn-secondary flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Vincular PCOC
              </button>
            )}
            <button
              onClick={() => setShowNewForm(true)}
              className="btn-primary"
            >
              Nueva Validacion
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* New Validation Form Modal */}
        {showNewForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h2 className="text-lg font-semibold mb-4">Nueva Validacion de Documentos</h2>

              {validationType === 'pcoc' && pcocValidations.length > 0 && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Vincular a Validacion PCOC (opcional)
                  </label>
                  <select
                    value={newFormData.pcoc_validation_id}
                    onChange={(e) => {
                      const pcoc = pcocValidations.find(p => p.id === e.target.value)
                      setNewFormData({
                        ...newFormData,
                        pcoc_validation_id: e.target.value,
                        project_name: pcoc?.project_name || newFormData.project_name,
                        property_address: pcoc?.property_address || newFormData.property_address,
                        municipality: pcoc?.municipality || newFormData.municipality,
                      })
                    }}
                    className="input-field"
                  >
                    <option value="">Sin vincular</option>
                    {pcocValidations.map(pcoc => (
                      <option key={pcoc.id} value={pcoc.id}>
                        {pcoc.project_name || pcoc.property_address || pcoc.id.slice(0, 8)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Proyecto
                </label>
                <input
                  type="text"
                  value={newFormData.project_name}
                  onChange={(e) => setNewFormData({ ...newFormData, project_name: e.target.value })}
                  className="input-field"
                  placeholder="Ej: Residencia Rodriguez"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Direccion de la Propiedad
                </label>
                <input
                  type="text"
                  value={newFormData.property_address}
                  onChange={(e) => setNewFormData({ ...newFormData, property_address: e.target.value })}
                  className="input-field"
                  placeholder="Ej: Calle Principal #123"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Municipio
                </label>
                <input
                  type="text"
                  value={newFormData.municipality}
                  onChange={(e) => setNewFormData({ ...newFormData, municipality: e.target.value })}
                  className="input-field"
                  placeholder="Ej: San Juan"
                />
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowNewForm(false)}
                  className="btn-secondary"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCreateValidation}
                  disabled={loading}
                  className="btn-primary"
                >
                  {loading ? 'Creando...' : 'Crear'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* PCOC Link Modal */}
        {showPcocLinkModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Vincular Validacion PCOC</h2>
                <button
                  onClick={() => setShowPcocLinkModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Seleccione una validacion PCOC completada para vincular los documentos.
              </p>

              {pcocValidations.length === 0 ? (
                <p className="text-gray-500 text-sm py-4">No hay validaciones PCOC completadas.</p>
              ) : (
                <div className="space-y-2">
                  {pcocValidations.map(pcoc => (
                    <button
                      key={pcoc.id}
                      onClick={() => handleLinkPcocValidation(pcoc.id)}
                      className="w-full text-left p-4 rounded-lg border border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-colors"
                    >
                      <div className="font-medium text-gray-900">
                        {pcoc.project_name || 'Sin nombre'}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {pcoc.property_address || 'Sin direccion'}
                        {pcoc.municipality && ` - ${pcoc.municipality}`}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(pcoc.created_at).toLocaleDateString('es-PR')}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left: Validation List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="font-semibold text-gray-900 mb-4">Validaciones</h2>

              {loading && validations.length === 0 ? (
                <p className="text-gray-500 text-sm">Cargando...</p>
              ) : validations.length === 0 ? (
                <p className="text-gray-500 text-sm">No hay validaciones. Cree una nueva para comenzar.</p>
              ) : (
                <div className="space-y-2">
                  {validations.map(v => (
                    <div
                      key={v.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedValidation?.id === v.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => handleSelectValidation(v)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-gray-900 truncate">
                          {v.project_name || v.property_address || 'Sin nombre'}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeleteValidation(v.id)
                          }}
                          className="text-gray-400 hover:text-red-500"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                      <div className="text-sm text-gray-500 truncate">{v.municipality}</div>
                      <div className="mt-2">
                        <span className={`inline-block px-2 py-1 text-xs rounded-full ${
                          v.status === 'completo'
                            ? 'bg-green-100 text-green-800'
                            : v.status === 'requiere_documentos'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {v.status === 'completo' ? 'Completo' : v.status === 'requiere_documentos' ? 'Requiere Documentos' : 'En Progreso'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right: Document Checklist & Details */}
          <div className="lg:col-span-2">
            {selectedValidation ? (
              <div className="space-y-6">
                {/* Project Info */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h2 className="font-semibold text-gray-900 mb-4">Informacion del Proyecto</h2>
                  <div className="grid md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Proyecto:</span>
                      <p className="font-medium">{selectedValidation.project_name || '-'}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Direccion:</span>
                      <p className="font-medium">{selectedValidation.property_address || '-'}</p>
                    </div>
                    <div>
                      <span className="text-gray-500">Municipio:</span>
                      <p className="font-medium">{selectedValidation.municipality || '-'}</p>
                    </div>
                  </div>
                </div>

                {/* Document Checklist */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-semibold text-gray-900">Lista de Documentos</h2>
                    <button
                      onClick={handleValidateDocuments}
                      disabled={loading}
                      className="btn-secondary text-sm"
                    >
                      {loading ? 'Validando...' : 'Validar Documentos'}
                    </button>
                  </div>

                  {/* Progress Bar */}
                  {validationResult && (
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progreso: {validationResult.uploaded_required}/{validationResult.total_required} requeridos</span>
                        <span>{validationResult.progress_percent}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${validationResult.is_complete ? 'bg-green-500' : 'bg-blue-500'}`}
                          style={{ width: `${validationResult.progress_percent}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    {requirements.map(req => {
                      const docStatus = selectedValidation.documents?.[req.code]
                      const isUploaded = docStatus?.uploaded || false
                      const hasFile = docStatus?.file_url || false

                      return (
                        <div
                          key={req.code}
                          className={`flex items-start gap-3 p-3 rounded-lg border ${
                            isUploaded ? 'border-green-200 bg-green-50' : 'border-gray-200'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isUploaded}
                            onChange={(e) => handleDocumentToggle(req.code, e.target.checked)}
                            className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                          />
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className={`font-medium ${isUploaded ? 'text-green-800' : 'text-gray-900'}`}>
                                {req.name}
                              </span>
                              {req.required ? (
                                <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded">Requerido</span>
                              ) : (
                                <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">Opcional</span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{req.description}</p>
                            {req.conditional && (
                              <p className="text-xs text-amber-600 mt-1">
                                Condicion: {req.conditional}
                              </p>
                            )}
                            {/* Uploaded file info */}
                            {hasFile && docStatus?.file_name && (
                              <div className="flex items-center gap-2 mt-2 text-sm">
                                <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <a
                                  href={docStatus.file_url!}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:underline truncate max-w-[200px]"
                                >
                                  {docStatus.file_name}
                                </a>
                                <button
                                  onClick={() => handleRemoveDocument(req.code)}
                                  className="text-red-500 hover:text-red-700"
                                  title="Eliminar documento"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                </button>
                              </div>
                            )}
                          </div>
                          {/* Upload button */}
                          <div className="flex-shrink-0">
                            <input
                              type="file"
                              accept="application/pdf"
                              ref={(el) => { fileInputRefs.current[req.code] = el }}
                              onChange={(e) => {
                                const file = e.target.files?.[0]
                                if (file) handleFileUpload(req.code, file)
                                e.target.value = ''
                              }}
                              className="hidden"
                            />
                            <button
                              onClick={() => fileInputRefs.current[req.code]?.click()}
                              disabled={uploadingDoc === req.code}
                              className={`p-2 rounded-lg transition-colors ${
                                hasFile
                                  ? 'text-green-600 bg-green-100 hover:bg-green-200'
                                  : 'text-gray-500 bg-gray-100 hover:bg-gray-200'
                              } ${uploadingDoc === req.code ? 'opacity-50 cursor-not-allowed' : ''}`}
                              title={hasFile ? 'Reemplazar documento' : 'Subir documento PDF'}
                            >
                              {uploadingDoc === req.code ? (
                                <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                              ) : (
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                                </svg>
                              )}
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Memorial Explicativo */}
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="font-semibold text-gray-900">Memorial Explicativo</h2>
                    <button
                      onClick={handleGenerateMemorial}
                      disabled={loading}
                      className="btn-primary text-sm"
                    >
                      {loading ? 'Generando...' : selectedValidation.memorial_explicativo?.generated ? 'Regenerar' : 'Generar'}
                    </button>
                  </div>

                  {selectedValidation.memorial_explicativo?.generated ? (
                    <div className="space-y-4 text-sm">
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Descripcion del Proyecto</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.project_description}
                        </p>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Ubicacion</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.location_description}
                        </p>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Informacion de Zonificacion</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.zoning_info}
                        </p>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Detalles de Construccion</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.construction_details}
                        </p>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Cumplimiento Ambiental</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.environmental_compliance}
                        </p>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-700 mb-1">Justificacion del Tipo de Permiso</h3>
                        <p className="text-gray-600 whitespace-pre-wrap">
                          {selectedValidation.memorial_explicativo.permit_type_justification}
                        </p>
                      </div>
                      {selectedValidation.memorial_explicativo.additional_notes && (
                        <div>
                          <h3 className="font-medium text-gray-700 mb-1">Notas Adicionales</h3>
                          <p className="text-gray-600 whitespace-pre-wrap">
                            {selectedValidation.memorial_explicativo.additional_notes}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">
                      El Memorial Explicativo sera generado automaticamente basado en la informacion del proyecto
                      y los resultados de la validacion PCOC (si esta vinculada).
                    </p>
                  )}
                </div>

                {/* Validation Result Summary */}
                {validationResult && (
                  <div className={`rounded-lg border p-4 ${
                    validationResult.is_complete
                      ? 'border-green-200 bg-green-50'
                      : 'border-yellow-200 bg-yellow-50'
                  }`}>
                    <h2 className={`font-semibold mb-2 ${
                      validationResult.is_complete ? 'text-green-800' : 'text-yellow-800'
                    }`}>
                      {validationResult.is_complete
                        ? 'Todos los documentos requeridos estan completos'
                        : 'Faltan documentos requeridos'}
                    </h2>

                    {!validationResult.is_complete && validationResult.missing_required.length > 0 && (
                      <div className="mt-3">
                        <h3 className="text-sm font-medium text-yellow-800 mb-2">Documentos faltantes:</h3>
                        <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                          {validationResult.missing_required.map(doc => (
                            <li key={doc.code}>{doc.name}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
                <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-gray-500">
                  Seleccione una validacion de la lista o cree una nueva para comenzar.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }
