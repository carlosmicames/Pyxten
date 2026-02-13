'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { billingApi, Subscription } from '@/lib/api'

interface PlanFeature {
  name: string
  included: boolean
  highlight?: boolean
}

interface Plan {
  id: string
  stripeTier: 'professional' | 'empresarial' | null
  name: string
  price: number | 'Gratis'
  period: string
  description: string
  features: PlanFeature[]
  highlighted?: boolean
  buttonText: string
}

const plans: Plan[] = [
  {
    id: 'free',
    stripeTier: null,
    name: 'Gratis',
    price: 'Gratis',
    period: '',
    description: 'Perfecto para explorar y validaciones basicas',
    features: [
      { name: 'Pre-Validacion de Zonificacion', included: true },
      { name: 'Hasta 5 validaciones por mes', included: true },
      { name: 'Reportes PDF basicos', included: true },
      { name: 'Organizacion en carpetas', included: true },
      { name: 'Validacion PCOC', included: false },
      { name: 'Validacion de Documentos', included: false },
      { name: 'Memorial Explicativo automatico', included: false },
      { name: 'Soporte prioritario', included: false },
    ],
    buttonText: 'Plan Actual',
  },
  {
    id: 'professional',
    stripeTier: 'professional',
    name: 'Profesional',
    price: 17,
    period: '/mes',
    description: 'Para profesionales que necesitan validaciones PCOC',
    highlighted: true,
    features: [
      { name: 'Pre-Validacion de Zonificacion', included: true },
      { name: 'Validaciones ilimitadas', included: true, highlight: true },
      { name: 'Reportes PDF completos', included: true },
      { name: 'Organizacion en carpetas', included: true },
      { name: 'Validacion PCOC completa', included: true, highlight: true },
      { name: 'Analisis de 4 filtros PCOC', included: true },
      { name: 'Validacion de Documentos', included: false },
      { name: 'Memorial Explicativo automatico', included: false },
    ],
    buttonText: 'Suscribirse',
  },
  {
    id: 'empresarial',
    stripeTier: 'empresarial',
    name: 'Empresarial',
    price: 37,
    period: '/mes',
    description: 'Solucion completa para firmas y empresas',
    features: [
      { name: 'Pre-Validacion de Zonificacion', included: true },
      { name: 'Validaciones ilimitadas', included: true },
      { name: 'Reportes PDF completos', included: true },
      { name: 'Organizacion en carpetas', included: true },
      { name: 'Validacion PCOC completa', included: true },
      { name: 'Analisis de 4 filtros PCOC', included: true },
      { name: 'Validacion de Documentos', included: true, highlight: true },
      { name: 'Memorial Explicativo automatico', included: true, highlight: true },
    ],
    buttonText: 'Suscribirse',
  },
]

export default function PlanesPage() {
  const searchParams = useSearchParams()
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'annual'>('monthly')
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [subscribing, setSubscribing] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Load current subscription on mount
  useEffect(() => {
    loadSubscription()
  }, [])

  // Check for success/canceled params
  useEffect(() => {
    if (searchParams.get('success') === '1') {
      setSuccessMessage('Su suscripcion ha sido activada exitosamente.')
      // Reload subscription to get updated status
      loadSubscription()
      // Clear the URL params
      window.history.replaceState({}, '', '/planes')
    } else if (searchParams.get('canceled') === '1') {
      setError('El proceso de pago fue cancelado.')
      window.history.replaceState({}, '', '/planes')
    }
  }, [searchParams])

  const loadSubscription = async () => {
    try {
      setLoading(true)
      const sub = await billingApi.getSubscription()
      setSubscription(sub)
    } catch (err) {
      console.error('Error loading subscription:', err)
      // Default to free tier on error
      setSubscription({ user_id: '', tier: 'free', status: 'inactive', stripe_customer_id: null, stripe_subscription_id: null, current_period_end: null })
    } finally {
      setLoading(false)
    }
  }

  const handleSubscribe = async (planId: string, stripeTier: 'professional' | 'empresarial' | null) => {
    if (!stripeTier) return // Free plan, no action needed

    setSubscribing(planId)
    setError(null)

    try {
      const { url } = await billingApi.createCheckoutSession(stripeTier, billingPeriod)
      // Redirect to Stripe Checkout
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar el proceso de pago')
      setSubscribing(null)
    }
  }

  const handleManageBilling = async () => {
    setError(null)
    try {
      const { url } = await billingApi.createPortalSession()
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al abrir el portal de facturacion')
    }
  }

  const getCurrentTier = (): string => {
    if (!subscription) return 'free'
    if (subscription.status === 'active' || subscription.status === 'trialing') {
      return subscription.tier
    }
    return 'free'
  }

  const currentTier = getCurrentTier()

  const getAnnualPrice = (monthlyPrice: number | 'Gratis') => {
    if (monthlyPrice === 'Gratis') return 'Gratis'
    return Math.round(monthlyPrice * 10) // 2 months free
  }

  const getButtonState = (plan: Plan) => {
    const isCurrentPlan = plan.id === currentTier
    const isUpgrade = (plan.id === 'professional' && currentTier === 'free') ||
                      (plan.id === 'empresarial' && (currentTier === 'free' || currentTier === 'professional'))
    const isDowngrade = (plan.id === 'free' && currentTier !== 'free') ||
                        (plan.id === 'professional' && currentTier === 'empresarial')

    if (isCurrentPlan) {
      return { text: 'Plan Actual', disabled: true, action: 'current' }
    }
    if (plan.id === 'free') {
      return { text: 'Administrar Plan', disabled: false, action: 'manage' }
    }
    if (isUpgrade) {
      return { text: 'Suscribirse', disabled: false, action: 'subscribe' }
    }
    if (isDowngrade) {
      return { text: 'Cambiar Plan', disabled: false, action: 'manage' }
    }
    return { text: 'Suscribirse', disabled: false, action: 'subscribe' }
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Success/Error Messages */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 flex items-center justify-between">
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-green-500 hover:text-green-700">×</button>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">×</button>
        </div>
      )}

      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Planes y Precios</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Elija el plan que mejor se adapte a sus necesidades. Todos los planes incluyen acceso
          a nuestra plataforma de validacion de zonificacion para Puerto Rico.
        </p>
      </div>

      {/* Current Subscription Status */}
      {!loading && subscription && subscription.status === 'active' && (
        <div className="mb-8 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
          <div>
            <span className="text-blue-800 font-medium">Plan actual: {currentTier === 'professional' ? 'Profesional' : currentTier === 'empresarial' ? 'Empresarial' : 'Gratis'}</span>
            {subscription.current_period_end && (
              <span className="text-blue-600 text-sm ml-2">
                (Renueva: {new Date(subscription.current_period_end).toLocaleDateString('es-PR')})
              </span>
            )}
          </div>
          <button
            onClick={handleManageBilling}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Administrar Facturacion
          </button>
        </div>
      )}

      {/* Billing Toggle */}
      <div className="flex justify-center mb-8">
        <div className="bg-gray-100 p-1 rounded-lg inline-flex">
          <button
            onClick={() => setBillingPeriod('monthly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'monthly'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Mensual
          </button>
          <button
            onClick={() => setBillingPeriod('annual')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'annual'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Anual
            <span className="ml-1 text-xs text-green-600 font-semibold">-17%</span>
          </button>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        {plans.map((plan) => {
          const displayPrice = billingPeriod === 'annual'
            ? getAnnualPrice(plan.price)
            : plan.price

          const buttonState = getButtonState(plan)
          const isSubscribing = subscribing === plan.id

          return (
            <div
              key={plan.id}
              className={`bg-white rounded-xl border-2 p-6 flex flex-col ${
                plan.highlighted
                  ? 'border-blue-500 shadow-lg relative'
                  : plan.id === currentTier
                  ? 'border-green-500 relative'
                  : 'border-gray-200'
              }`}
            >
              {plan.highlighted && plan.id !== currentTier && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Mas Popular
                  </span>
                </div>
              )}

              {plan.id === currentTier && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-green-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Tu Plan
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h2 className="text-xl font-bold text-gray-900">{plan.name}</h2>
                <p className="text-gray-600 text-sm mt-1">{plan.description}</p>
              </div>

              <div className="mb-6">
                <div className="flex items-baseline">
                  {displayPrice === 'Gratis' ? (
                    <span className="text-4xl font-bold text-gray-900">Gratis</span>
                  ) : (
                    <>
                      <span className="text-4xl font-bold text-gray-900">${displayPrice}</span>
                      <span className="text-gray-600 ml-1">
                        {billingPeriod === 'annual' ? '/ano' : plan.period}
                      </span>
                    </>
                  )}
                </div>
                {billingPeriod === 'annual' && plan.price !== 'Gratis' && (
                  <p className="text-sm text-green-600 mt-1">
                    Ahorra ${(plan.price as number) * 2}/ano
                  </p>
                )}
              </div>

              <ul className="space-y-3 mb-6 flex-1">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2">
                    {feature.included ? (
                      <svg
                        className={`w-5 h-5 flex-shrink-0 ${
                          feature.highlight ? 'text-green-500' : 'text-blue-500'
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    ) : (
                      <svg
                        className="w-5 h-5 text-gray-300 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    )}
                    <span
                      className={`text-sm ${
                        feature.included
                          ? feature.highlight
                            ? 'text-gray-900 font-medium'
                            : 'text-gray-700'
                          : 'text-gray-400'
                      }`}
                    >
                      {feature.name}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => {
                  if (buttonState.action === 'subscribe') {
                    handleSubscribe(plan.id, plan.stripeTier)
                  } else if (buttonState.action === 'manage') {
                    handleManageBilling()
                  }
                }}
                disabled={buttonState.disabled || isSubscribing || loading}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                  buttonState.disabled
                    ? 'bg-gray-100 text-gray-500 cursor-default'
                    : plan.id === currentTier
                    ? 'bg-green-100 text-green-700 cursor-default'
                    : plan.highlighted
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-900 text-white hover:bg-gray-800'
                } ${isSubscribing ? 'opacity-50 cursor-wait' : ''}`}
              >
                {isSubscribing ? 'Procesando...' : buttonState.text}
              </button>
            </div>
          )
        })}
      </div>

      {/* FAQ Section */}
      <div className="mt-16">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Preguntas Frecuentes</h2>

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-2">
              Puedo cambiar de plan en cualquier momento?
            </h3>
            <p className="text-gray-600 text-sm">
              Si, puede actualizar o degradar su plan en cualquier momento. Los cambios se aplican
              inmediatamente y se prorratea el costo.
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-2">
              Que metodos de pago aceptan?
            </h3>
            <p className="text-gray-600 text-sm">
              Aceptamos tarjetas de credito y debito (Visa, MasterCard, American Express) y
              PayPal para su conveniencia.
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-2">
              Hay algun contrato o compromiso?
            </h3>
            <p className="text-gray-600 text-sm">
              No hay contratos a largo plazo. Puede cancelar su suscripcion en cualquier momento
              sin penalidades.
            </p>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-2">
              Ofrecen descuentos para firmas grandes?
            </h3>
            <p className="text-gray-600 text-sm">
              Si, ofrecemos precios especiales para firmas con multiples usuarios. Contactenos
              para obtener una cotizacion personalizada.
            </p>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="mt-16 bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-8 text-center text-white">
        <h2 className="text-2xl font-bold mb-3">Tiene preguntas?</h2>
        <p className="text-blue-100 mb-6 max-w-xl mx-auto">
          Nuestro equipo esta disponible para ayudarle a elegir el plan adecuado para sus necesidades.
        </p>
        <a
          href="mailto:soporte@pyxten.com"
          className="inline-block bg-white text-blue-600 font-medium px-6 py-3 rounded-lg hover:bg-blue-50 transition-colors"
        >
          Contactar Soporte
        </a>
      </div>
    </div>
  )
}
