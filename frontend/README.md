# LicitLens — Dashboard React de Inteligencia SEACE

Plataforma web de inteligencia para licitaciones públicas del **SEACE (Perú)**.
Construido con **React 18 + Vite + Tailwind CSS** y datos simulados.

## Ejecutar

```bash
npm install
npm run dev        # http://localhost:8080 (Vite dev server, HMR)
npm run build      # build de producción → dist/
```

## Estructura

```
seace-dashboard/
├── index.html                      # Shell Vite
├── vite.config.js                  # host 0.0.0.0 : 8080
├── tailwind.config.js              # Tokens: paleta ink/brand, sombras, Inter
├── postcss.config.js
└── src/
    ├── main.jsx                    # Bootstrapping (StrictMode + AppProvider)
    ├── App.jsx                     # Layout split-screen + navegación + Esc
    ├── index.css                   # @tailwind + componentes + custom
    ├── data/
    │   └── mockData.json           # ★ Simulacro de la tabla PostgreSQL `convocatorias`
    ├── store/
    │   ├── AppState.jsx            # Context + useReducer (acciones tipadas)
    │   └── selectors.js            # useVisibleConvocatorias / useSelectedConvocatoria
    ├── utils/
    │   └── format.js               # fmtPEN, fechas, daysUntil
    └── components/
        ├── ui/Icon.jsx             # Iconos Lucide inline (<Icon name=.../>)
        ├── layout/
        │   ├── Sidebar.jsx         # Oscura, colapsable, off-canvas mobile
        │   └── Topbar.jsx          # Header + buscador + UrgentStrip
        └── dashboard/
            ├── KpiRow.jsx          # KPIs calculados del JSON
            ├── FilterBar.jsx       # 8 filtros controlados (funcionales en local)
            ├── BiddingTable.jsx    # Data table + orden + empty state
            ├── badges.jsx          # ScoreRing/ScoreCell, Type/Status/TipoObjeto
            ├── Timeline.jsx        # Hitos SEACE (JSONB) con fase actual
            └── DetailPanel.jsx     # Split-screen: meta, timeline, docs, IA
```

## mockData.json — simulacro PostgreSQL

`src/data/mockData.json` imita un dump de la BD `seace` (tabla `convocatorias`):

| Columna          | Tipo (PG)                          | Notas |
| ---------------- | ---------------------------------- | ----- |
| `id`             | `SERIAL PRIMARY KEY`               |       |
| `codigo_seace`   | `VARCHAR(32) UNIQUE`               | LP-008-2026-OSCE… |
| `entidad`        | `VARCHAR(200)`                     |       |
| `objeto`         | `TEXT`                             | descripción |
| `tipo_objeto`    | `ENUM('Bienes','Servicios','Obras')` | filtra en UI |
| `estado`         | `ENUM('Vigente','Finalizado')`     | filtra en UI |
| `fecha_publicacion` | `DATE`                          |       |
| `fecha_limite`   | `DATE NULL`                        | plazos, KPIs, urgencias |
| `valor_estimado` | `NUMERIC(14,2) NULL`               | rango de valor en filtros |
| `region` / `modalidad` / `tipo_proceso` / `cui` | `VARCHAR` | filtros |
| `match_score`    | `SMALLINT`                         | Score IA (badge circular) |
| `fase_actual`    | `SMALLINT`                         | índice del hito en curso |
| `hitos`          | `JSONB`                            | timeline del panel |
| `documentos`     | `JSONB`                            | lista de documentos |
| `motivos_ia`     | `JSONB`                            | "¿Por qué te sugerimos…" |

Los filtros de la UI (**entidad, tipo de proceso, valor, región, estado, tipo de objeto, plazo** + búsqueda global)
se aplican **100% en local** sobre este JSON vía `selectors.js` — sin backend.
Para conectar la API real: sustituir `DB` en `store/AppState.jsx` por un fetch (SWR/React Query).

## Estado y acciones (store)

`SET_VIEW · SELECT_BID · CLOSE_DETAIL · TOGGLE_SIDEBAR · TOGGLE_MOBILE_NAV · TOGGLE_FILTERS · SET_QUERY · SET_SORT · SET_FILTER · CLEAR_FILTERS · VER_URGENTES`

## Sistema de diseño

| Token        | Uso                                              |
| ------------ | ------------------------------------------------ |
| `ink-950/900`| Sidebar, tarjetas IA (azul pizarra profundo)     |
| `brand-600`  | Púrpura tecnológico (primario, IA)               |
| `emerald-500`| Match ≥ 85%, estado Vigente, éxitos              |
| `amber/red`  | Plazos urgentes (< 48 h / < 24 h)                |

Tipografía Inter. "Hoy" fijado en la demo: 16/09/2026.

## Roadmap

1. API real Perú Comprador/OAS (sustituir `DB`) + WebSocket de alertas.
2. Tema oscuro completo (`dark:` habilitado en el config).
3. Analítica de competidores (Recharts) y Kanban de postulaciones.
4. Paginación real + exportación CSV del listado filtrado.
