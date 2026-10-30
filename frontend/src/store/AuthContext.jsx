import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authApi, tokenStore, SESSION_EXPIRED_EVENT } from '../lib/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => tokenStore.get())
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [authModalTab, setAuthModalTab] = useState('login') // 'login' | 'register'
  const [sessionNotice, setSessionNotice] = useState(null)

  const clearSession = useCallback(() => {
    tokenStore.clear()
    setToken(null)
    setUser(null)
  }, [])

  // Verificación de sesión al iniciar la aplicación
  useEffect(() => {
    let isMounted = true
    const checkAuth = async () => {
      if (!tokenStore.get()) {
        setIsLoading(false)
        return
      }

      try {
        // apiFetch renueva el access token automáticamente si recibe 401
        const userData = await authApi.getMe()
        if (isMounted) {
          setUser(userData)
          setToken(tokenStore.get())
        }
      } catch {
        if (isMounted) clearSession()
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    checkAuth()
    return () => {
      isMounted = false
    }
  }, [clearSession])

  // Cierre de sesión limpio cuando el interceptor detecta que el refresh token caducó
  useEffect(() => {
    const onExpired = () => {
      clearSession()
      setSessionNotice('Tu sesión ha expirado. Inicia sesión nuevamente para continuar.')
      setAuthModalTab('login')
      setIsAuthModalOpen(true)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [clearSession])

  // Sincronización entre pestañas: logout en una pestaña cierra la sesión en todas
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'access_token' && !e.newValue) {
        setToken(null)
        setUser(null)
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const applySession = (data) => {
    tokenStore.set(data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    setSessionNotice(null)
    setIsAuthModalOpen(false)
    return data.user
  }

  const login = async (email, password) => applySession(await authApi.login({ email, password }))

  const register = async (email, password, nombre) =>
    applySession(await authApi.register({ email, password, nombre }))

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore: la sesión local se limpia igualmente
    }
    clearSession()
  }

  const openAuthModal = (tab = 'login') => {
    setAuthModalTab(tab)
    setIsAuthModalOpen(true)
  }

  const closeAuthModal = () => {
    setIsAuthModalOpen(false)
    setSessionNotice(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        isAuthModalOpen,
        openAuthModal,
        closeAuthModal,
        authModalTab,
        setAuthModalTab,
        sessionNotice,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth debe usarse dentro de un AuthProvider')
  }
  return ctx
}
