'use client'

import { useEffect } from 'react'

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('App error:', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center px-4">
      <div className="text-red-500">
        <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      </div>
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Algo salio mal</h2>
        <p className="text-gray-600 text-sm mb-1">
          {error.message || 'Ocurrio un error al cargar esta pagina.'}
        </p>
        <p className="text-gray-400 text-xs">
          Verifique su conexion y que el servidor este disponible.
        </p>
      </div>
      <button
        onClick={reset}
        className="btn-primary"
      >
        Intentar de nuevo
      </button>
    </div>
  )
}
