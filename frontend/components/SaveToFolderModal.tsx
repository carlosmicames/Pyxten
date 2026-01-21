'use client'

import { useState, useEffect } from 'react'
import { foldersApi, Folder } from '@/lib/api'

interface SaveToFolderModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (folderId: string, isNewFolder: boolean, newFolderName?: string) => Promise<void>
  validationId: string
}

export default function SaveToFolderModal({
  isOpen,
  onClose,
  onSave,
  validationId,
}: SaveToFolderModalProps) {
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolderId, setSelectedFolderId] = useState<string>('')
  const [newFolderName, setNewFolderName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      loadFolders()
    }
  }, [isOpen])

  const loadFolders = async () => {
    try {
      const data = await foldersApi.list()
      setFolders(data)
    } catch (err) {
      console.error('Error loading folders:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (newFolderName.trim()) {
        // Create new folder and add validation to it
        await onSave('', true, newFolderName.trim())
      } else if (selectedFolderId) {
        // Add to existing folder
        await onSave(selectedFolderId, false)
      } else {
        setError('Selecciona una carpeta o crea una nueva')
        setLoading(false)
        return
      }

      onClose()
      setNewFolderName('')
      setSelectedFolderId('')
    } catch (err: any) {
      setError(err.message || 'Error guardando')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Guardar en Carpeta
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                {error}
              </div>
            )}

            {/* Row 1: Select existing folder */}
            <div>
              <label className="label">Seleccionar carpeta</label>
              <select
                className="input-field"
                value={selectedFolderId}
                onChange={(e) => {
                  setSelectedFolderId(e.target.value)
                  if (e.target.value) {
                    setNewFolderName('')
                  }
                }}
                disabled={!!newFolderName}
              >
                <option value="">-- Seleccionar --</option>
                {folders.map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Row 2: Create new folder */}
            <div>
              <label className="label">Crear carpeta nueva</label>
              <input
                type="text"
                className="input-field"
                placeholder="Nombre de la carpeta"
                value={newFolderName}
                onChange={(e) => {
                  setNewFolderName(e.target.value)
                  if (e.target.value) {
                    setSelectedFolderId('')
                  }
                }}
              />
            </div>

            {/* Buttons */}
            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="btn-secondary"
                disabled={loading}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={loading}
              >
                {loading ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
