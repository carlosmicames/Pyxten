'use client'

import { useState, useRef, useEffect } from 'react'
import { getApiUrl } from '@/lib/api'
import { getAccessToken } from '@/lib/supabase'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const EXAMPLE_QUESTIONS = [
  'Que es una exclusion categorica?',
  'Cual es la diferencia entre permiso ministerial y discrecional?',
  'Que usos estan permitidos en zona R-I?',
  'Cuando necesito un Profesional Autorizado?',
  'Que documentos necesito para un permiso de construccion?',
  'Que es el proceso de OGPe?',
  'Como funciona la zonificacion en Puerto Rico?',
  'Que es el Tomo 6 del Reglamento Conjunto?',
]

export default function AsistenteIAPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setError(null)

    // Add user message to chat
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      const token = await getAccessToken()
      const response = await fetch(getApiUrl('/chat/ask'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage,
          history: messages.slice(-6), // Last 6 messages for context
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Error consultando el asistente')
      }

      const data = await response.json()
      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }])
    } catch (err: any) {
      setError(err.message || 'Error consultando el asistente')
      // Remove the user message if there was an error
      setMessages((prev) => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  const handleExampleClick = (question: string) => {
    setInput(question)
  }

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-200px)] flex flex-col">
      {/* Header */}
      <div className="text-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Asistente IA</h1>
        <p className="text-gray-600">
          Pregunta sobre regulaciones de construccion y zonificacion de Puerto Rico
        </p>
      </div>

      {/* Chat Container */}
      <div className="flex-1 flex flex-col card p-0 overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <div className="mx-auto w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Hola! Soy tu asistente de regulaciones
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Puedo ayudarte con preguntas sobre el Reglamento Conjunto, permisos de construccion, y zonificacion en Puerto Rico.
              </p>

              <div className="text-left">
                <p className="text-sm font-medium text-gray-700 mb-3">Preguntas frecuentes:</p>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_QUESTIONS.slice(0, 4).map((question, i) => (
                    <button
                      key={i}
                      onClick={() => handleExampleClick(question)}
                      className="text-sm px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-gray-400 border-t-transparent"></div>
                  <span className="text-sm text-gray-600">Pensando...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error Message */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Input Area */}
        <form onSubmit={handleSubmit} className="border-t p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu pregunta..."
              className="input-field flex-1"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="btn-primary px-6"
            >
              {loading ? (
                <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Disclaimer */}
      <p className="text-xs text-gray-500 text-center mt-4">
        Este asistente proporciona informacion general. Consulte con un profesional autorizado para casos especificos.
      </p>
    </div>
  )
}
