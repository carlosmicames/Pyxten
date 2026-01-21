import { createClient } from './supabaseClient'

// Re-export createClient for backward compatibility
export { createClient }

export const getAccessToken = async (): Promise<string | null> => {
  const supabase = createClient()

  // DEBUG: Check Supabase env vars
  console.log('[getAccessToken] SUPABASE_URL exists:', !!process.env.NEXT_PUBLIC_SUPABASE_URL)
  console.log('[getAccessToken] SUPABASE_ANON_KEY exists:', !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)

  // First try getSession (reads from storage/cookies)
  const { data: { session }, error: sessionError } = await supabase.auth.getSession()

  // DEBUG: Session status
  console.log('[getAccessToken] getSession result:', {
    hasSession: !!session,
    hasToken: !!session?.access_token,
    error: sessionError?.message || null,
  })

  if (session?.access_token) {
    console.log('[getAccessToken] Returning token from getSession')
    return session.access_token
  }

  // If no session, try getUser which will also refresh if needed
  console.log('[getAccessToken] No session, trying getUser...')
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  // DEBUG: User status
  console.log('[getAccessToken] getUser result:', {
    hasUser: !!user,
    userId: user?.id || null,
    error: userError?.message || null,
  })

  if (user) {
    // User exists, try to get session again after potential refresh
    console.log('[getAccessToken] User found, fetching refreshed session...')
    const { data: { session: refreshedSession } } = await supabase.auth.getSession()
    console.log('[getAccessToken] Refreshed session has token:', !!refreshedSession?.access_token)
    return refreshedSession?.access_token || null
  }

  console.log('[getAccessToken] No user found, returning null')
  return null
}
