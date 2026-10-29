import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../../store/AppState.jsx'
import { tendersApi } from '../../lib/api.js'
import { useDebounce } from '../../hooks/useDebounce.js'
import { Icon } from '../ui/Icon.jsx'

export default function SearchBar({ className = '' }) {
  const { state, dispatch } = useApp()
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState(state.query || '')
  const [suggestions, setSuggestions] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const inputRef = useRef(null)
  const containerRef = useRef(null)

  const debouncedInput = useDebounce(inputValue, 250)

  // Sincronizar input local si state.query cambia externamente (ej. CLEAR_FILTERS)
  useEffect(() => {
    setInputValue(state.query || '')
  }, [state.query])

  // Atajo global Ctrl+K / Cmd+K para enfocar el buscador
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
        setIsOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Buscar sugerencias en la API cuando cambia debouncedInput
  useEffect(() => {
    const q = debouncedInput.trim()
    if (q.length < 2) {
      setSuggestions([])
      setLoading(false)
      return
    }

    const controller = new AbortController()
    setLoading(true)

    tendersApi
      .getSuggestions(q, controller.signal)
      .then((data) => {
        setSuggestions(Array.isArray(data) ? data : [])
        setLoading(false)
        setActiveIndex(-1)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setLoading(false)
        }
      })

    return () => controller.abort()
  }, [debouncedInput])

  // Cerrar al hacer clic fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const commitSearch = (val) => {
    dispatch({ type: 'SET_QUERY', query: val })
    setIsOpen(false)
    setActiveIndex(-1)
  }

  const handleSelectSuggestion = (sugg) => {
    if (sugg.tipo === 'rubro') {
      dispatch({ type: 'SET_FILTER', key: 'rubro', value: sugg.texto })
      dispatch({ type: 'SET_QUERY', query: '' })
      setInputValue('')
    } else {
      setInputValue(sugg.texto)
      commitSearch(sugg.texto)
      if (sugg.ocid) {
        dispatch({ type: 'SELECT_BID', id: sugg.ocid })
        navigate(`/licitaciones/${sugg.ocid}`)
      }
    }
    setIsOpen(false)
  }

  const handleKeyDown = (e) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'Enter') {
        commitSearch(inputValue)
      }
      return
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        handleSelectSuggestion(suggestions[activeIndex])
      } else {
        commitSearch(inputValue)
      }
    } else if (e.key === 'Escape') {
      setIsOpen(false)
    }
  }

  return (
    <div ref={containerRef} className={`relative w-full max-w-xl ${className}`}>
      <div className="relative">
        <Icon
          name="search"
          className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        />
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            setIsOpen(true)
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar entidad, objeto, código SEACE o palabras clave..."
          className="field h-10 w-full rounded-full bg-slate-50 pl-10 pr-20 text-xs transition-all focus:bg-white focus:ring-2 focus:ring-brand-500/20 sm:text-sm"
        />

        <div className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
          {loading && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          )}

          {inputValue && (
            <button
              type="button"
              onClick={() => {
                setInputValue('')
                commitSearch('')
                inputRef.current?.focus()
              }}
              className="grid h-5 w-5 place-items-center rounded-full text-slate-400 hover:bg-slate-200 hover:text-slate-600"
              title="Borrar búsqueda"
            >
              <Icon name="x" className="h-3 w-3" />
            </button>
          )}

          <kbd className="pointer-events-none hidden rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-bold text-slate-400 shadow-sm lg:block">
            Ctrl K
          </kbd>
        </div>
      </div>

      {/* Menú flotante de sugerencias */}
      {isOpen && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl animate-in fade-in zoom-in-95 duration-100">
          <div className="border-b border-slate-100 bg-slate-50/80 px-3 py-1.5 text-[11px] font-semibold text-slate-500 flex items-center justify-between">
            <span>Sugerencias de búsqueda inteligente</span>
            <span className="text-[10px] font-normal text-slate-400">↑↓ para navegar · Enter para elegir</span>
          </div>

          <ul className="max-h-80 overflow-y-auto py-1 scroll-thin">
            {suggestions.map((sugg, idx) => {
              const isSelected = idx === activeIndex
              const isRubro = sugg.tipo === 'rubro'

              return (
                <li
                  key={`${sugg.tipo}-${sugg.texto}-${idx}`}
                  onClick={() => handleSelectSuggestion(sugg)}
                  className={`flex cursor-pointer items-center gap-3 px-3.5 py-2.5 text-xs transition-colors ${
                    isSelected ? 'bg-brand-50 text-brand-900 font-medium' : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span
                    className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg ${
                      isRubro ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    <Icon name={isRubro ? 'tag' : 'file-text'} className="h-3.5 w-3.5" />
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-slate-900">
                      {isRubro ? (
                        <span>
                          Rubro: <strong className="text-indigo-600">{sugg.texto}</strong>
                        </span>
                      ) : (
                        sugg.label
                      )}
                    </div>
                    {sugg.rubro && !isRubro && (
                      <span className="text-[10px] text-slate-400 truncate block">
                        {sugg.rubro} · {sugg.ocid}
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] font-bold text-slate-400 opacity-60">
                    {isRubro ? 'Filtrar por rubro' : 'Ver licitación'}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
