'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [loading, setLoading] = useState(true)
  const [userEmail, setUserEmail] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()

      if (!session) {
        router.replace('/login')
        return
      }

      setUserEmail(session.user.email || null)
      setLoading(false)
    }

    checkAuth()
  }, [router])

  const handleSignOut = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.replace('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Cargando...</div>
      </div>
    )
  }

  const navItems = [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/nueva-validacion', label: 'Nueva Validacion' },
    { href: '/proyectos', label: 'Proyectos' },
    { href: '/asistente-ia', label: 'Asistente IA' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-gray-900">Pyxten</h1>
          <p className="text-sm text-gray-500 mt-1">Validacion de Zonificacion</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${
                pathname === item.href ? 'sidebar-link-active' : ''
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-200">
          <div className="text-sm text-gray-600 truncate mb-3">
            {userEmail}
          </div>
          <button
            onClick={handleSignOut}
            className="w-full text-left text-sm text-gray-600 hover:text-gray-900"
          >
            Cerrar Sesion
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto flex flex-col">
        <div className="flex-1 p-8">
          {children}
        </div>

        {/* Global Footer Disclaimer */}
        <footer className="border-t border-gray-200 bg-gray-50 px-8 py-4">
          <p className="text-xs text-gray-500 text-center">
            Pyxten LLC © 2026. Este informe es una pre-validacion automatizada. No sustituye aprobaciones oficiales de OGPe o la Junta de Planificacion.
          </p>
        </footer>
      </main>
    </div>
  )
}
