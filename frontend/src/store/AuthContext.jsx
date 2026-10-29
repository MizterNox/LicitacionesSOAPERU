import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../lib/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('access_token'))
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [authModalTab, setAuthModalTab] = useState('login') // 'login' | 'register'

  // Verificación de sesión al iniciar la aplicación
  useEffect(() => {
    let isMounted = true
    const checkAuth = async () => {
      const storedToken = localStorage.getItem('access_token')
      if (!storedToken) {
        setIsLoading(false)
        return
      }

      try {
        const userData = await authApi.getMe()
        if (isMounted) {
          setUser(userData)
        }
      } catch (err) {
        // Si el access token expiró, intentar renovación silenciosa con refresh_token
        try {
          const refreshRes = await authApi.refresh()
          if (refreshRes.access_token) {
            localStorage.setItem('access_token', refreshRes.access_token)
            if (isMounted) {
              setToken(refreshRes.access_token)
              setUser(refreshRes.user)
            }
          }
        } catch {
          // Sesión caducada completamente
          localStorage.removeItem('access_token')
          if (isMounted) {
            setToken(null)
            setUser(null)
          }
        }
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    checkAuth()
    return () => {
      isMounted = false
    }
  }, [])

  const login = async (email, password) => {
    const data = await authApi.login({ email, password })
    localStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    setIsAuthModalOpen(false)
    return data.user
  }

  const register = async (email, password, nombre) => {
    const data = await authApi.register({ email, password, nombre })
    localStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    setIsAuthModalOpen(false)
    return data.user
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore
    }
    localStorage.removeItem('access_token')
    setToken(null)
    setUser(null)
  }

  const openAuthModal = (tab = 'login') => {
    setAuthModalTab(tab)
    setIsAuthModalOpen(true)
  }

  const closeAuthModal = () => {
    setIsAuthModalOpen(false)
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
