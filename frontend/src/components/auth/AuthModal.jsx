import { useState } from 'react'
import { useAuth } from '../../store/AuthContext.jsx'
import { Icon, LogoMark } from '../ui/Icon.jsx'

export function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, setAuthModalTab, login, register, sessionNotice } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nombre, setNombre] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  if (!isAuthModalOpen) return null

  const isLogin = authModalTab === 'login'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (isLogin) {
        await login(email, password)
      } else {
        if (!nombre.trim()) {
          throw new Error('Por favor ingrese su nombre o razón social.')
        }
        await register(email, password, nombre)
      }
      // Limpiar campos tras éxito
      setEmail('')
      setPassword('')
      setNombre('')
    } catch (err) {
      console.error('Error de autenticación:', err)
      setError(err.message || 'Error al procesar la solicitud.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity"
        onClick={closeAuthModal}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        {/* Cabecera con Logo */}
        <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <LogoMark className="h-7 w-7" />
            <div>
              <p className="text-sm font-bold text-slate-900">LicitLens</p>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Acceso a la Plataforma</p>
            </div>
          </div>
          <button
            onClick={closeAuthModal}
            className="icon-btn h-8 w-8 text-slate-400 hover:text-slate-700"
            title="Cerrar modal"
          >
            <Icon name="x" className="h-4 w-4" />
          </button>
        </div>

        {/* Selector de Pestañas: Login / Registro */}
        <div className="flex border-b border-slate-100 bg-slate-50/30 p-1.5">
          <button
            type="button"
            onClick={() => {
              setAuthModalTab('login')
              setError(null)
            }}
            className={`flex-1 rounded-lg py-2 text-xs font-bold transition-all ${
              isLogin ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Iniciar Sesión
          </button>
          <button
            type="button"
            onClick={() => {
              setAuthModalTab('register')
              setError(null)
            }}
            className={`flex-1 rounded-lg py-2 text-xs font-bold transition-all ${
              !isLogin ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Crear Cuenta
          </button>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {sessionNotice && !error && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-start gap-2">
              <Icon name="hourglass" className="h-4 w-4 flex-shrink-0 text-amber-500 mt-0.5" />
              <span>{sessionNotice}</span>
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex items-start gap-2">
              <Icon name="alert-triangle" className="h-4 w-4 flex-shrink-0 text-red-500 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {!isLogin && (
            <div>
              <label className="field-label mb-1">Nombre o Razón Social</label>
              <input
                type="text"
                required
                placeholder="Ej. Consorcio Tecnológico SAC"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="field h-9 text-xs"
              />
            </div>
          )}

          <div>
            <label className="field-label mb-1">Correo Electrónico</label>
            <input
              type="email"
              required
              placeholder="correo@ejemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field h-9 text-xs"
            />
          </div>

          <div>
            <label className="field-label mb-1">Contraseña</label>
            <input
              type="password"
              required
              minLength={isLogin ? 1 : 8}
              maxLength={128}
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field h-9 text-xs"
            />
            {!isLogin && (
              <p className="mt-1 text-[11px] text-slate-400">Mínimo 8 caracteres, combinando letras y números.</p>
            )}
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-10 text-xs font-bold justify-center shadow-md active:scale-[0.99] disabled:opacity-60"
            >
              {loading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : isLogin ? (
                'Ingresar a mi cuenta'
              ) : (
                'Registrar cuenta gratuita'
              )}
            </button>
          </div>

          <p className="text-center text-[11px] text-slate-400 pt-1">
            {isLogin ? (
              <>
                ¿No tienes una cuenta aún?{' '}
                <button
                  type="button"
                  onClick={() => setAuthModalTab('register')}
                  className="font-bold text-brand-600 hover:underline"
                >
                  Regístrate aquí
                </button>
              </>
            ) : (
              <>
                ¿Ya tienes una cuenta registrada?{' '}
                <button
                  type="button"
                  onClick={() => setAuthModalTab('login')}
                  className="font-bold text-brand-600 hover:underline"
                >
                  Inicia sesión
                </button>
              </>
            )}
          </p>
        </form>
      </div>
    </div>
  )
}

export default AuthModal

