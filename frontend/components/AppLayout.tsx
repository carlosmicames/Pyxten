'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'

const SIDEBAR_COLLAPSED_KEY = 'pyxten_sidebar_collapsed'

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [loading, setLoading] = useState(true)
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    // Load sidebar state from localStorage
    const savedState = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    if (savedState !== null) {
      setSidebarCollapsed(savedState === 'true')
    }
  }, [])

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

  const toggleSidebar = () => {
    const newState = !sidebarCollapsed
    setSidebarCollapsed(newState)
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(newState))
  }

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
    { href: '/validacion-pcoc', label: 'Validacion PCOC' },
    { href: '/validacion-documentos', label: 'Validacion de Documentos' },
    { href: '/proyectos', label: 'Proyectos' },
    { href: '/planes', label: 'Planes' },
    { href: '/asistente-ia', label: 'Asistente IA' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside
        className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${
          sidebarCollapsed ? 'w-16' : 'w-64'
        }`}
      >
        {/* Logo / Toggle */}
        <div className={`border-b border-gray-200 flex items-center ${sidebarCollapsed ? 'p-4 justify-center' : 'p-6'}`}>
          {sidebarCollapsed ? (
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md hover:bg-gray-100 text-gray-600 hover:text-gray-900"
              title="Expandir menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              </svg>
            </button>
          ) : (
            <div className="flex items-center justify-between w-full">
              <div>
                <h1 className="text-xl font-bold text-gray-900">Pyxten</h1>
                <p className="text-sm text-gray-500 mt-1">Validacion de Zonificacion</p>
              </div>
              <button
                onClick={toggleSidebar}
                className="p-2 rounded-md hover:bg-gray-100 text-gray-600 hover:text-gray-900"
                title="Colapsar menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className={`flex-1 space-y-1 ${sidebarCollapsed ? 'p-2' : 'p-4'}`}>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${
                pathname === item.href ? 'sidebar-link-active' : ''
              } ${sidebarCollapsed ? 'justify-center px-2' : ''}`}
              title={sidebarCollapsed ? item.label : undefined}
            >
              {sidebarCollapsed ? (
                <span className="w-2 h-2 rounded-full bg-current"></span>
              ) : (
                item.label
              )}
            </Link>
          ))}
        </nav>

        {/* User section */}
        <div className={`border-t border-gray-200 ${sidebarCollapsed ? 'p-2' : 'p-4'}`}>
          {!sidebarCollapsed && (
            <div className="text-sm text-gray-600 truncate mb-3">
              {userEmail}
            </div>
          )}
          <button
            onClick={handleSignOut}
            className={`text-sm text-gray-600 hover:text-gray-900 ${
              sidebarCollapsed ? 'w-full flex justify-center p-2' : 'w-full text-left'
            }`}
            title={sidebarCollapsed ? 'Cerrar Sesion' : undefined}
          >
            {sidebarCollapsed ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            ) : (
              'Cerrar Sesion'
            )}
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
