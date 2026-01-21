import { createClient } from './supabaseClient'

// Re-export createClient for backward compatibility
export { createClient }

export const getAccessToken = async (): Promise<string | null> => {
  const supabase = createClient()

  // First try getSession (reads from storage/cookies)
  const { data: { session } } = await supabase.auth.getSession()

  if (session?.access_token) {
    return session.access_token
  }

  // If no session, try getUser which will also refresh if needed
  const { data: { user } } = await supabase.auth.getUser()

  if (user) {
    // User exists, try to get session again after potential refresh
    const { data: { session: refreshedSession } } = await supabase.auth.getSession()
    return refreshedSession?.access_token || null
  }

  return null
}
