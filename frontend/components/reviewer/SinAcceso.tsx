'use client'

import Link from 'next/link'

/**
 * Shown to anyone who reaches a reviewer route without a permit-office
 * membership. This is the normal state for applicant accounts, so the copy
 * explains rather than accuses.
 */
export default function SinAcceso() {
  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900">Consola del revisor</h1>
      <p className="text-gray-600 mt-3">
        Su cuenta no esta asociada a una oficina de permisos, por lo que esta seccion no
        esta disponible.
      </p>
      <p className="text-gray-600 mt-2">
        Si trabaja en una oficina municipal y necesita acceso, comuniquese con el
        administrador de su oficina.
      </p>
      <Link href="/dashboard" className="btn-secondary inline-block mt-6">
        Volver al inicio
      </Link>
    </div>
  )
}
