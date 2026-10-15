# Inventario de archivos

El inventario se limita a archivos de aplicación, configuración y pruebas relevantes. Se excluyen caches, bytecode, entorno virtual y artefactos generados.

## Raíz

- **Ruta:** `docs/`
- **Propósito:** Documentación técnica y guía de reconstrucción del sistema.
- **Relaciones:** Se alimenta del análisis de `backend/` y `frontend/`; no participa en runtime.
- **Componentes / Funciones clave:** Arquitectura, flujo, guía paso a paso e inventario.

## Backend

- **Ruta:** `backend/pyproject.toml`
- **Propósito:** Metadatos del paquete, requisitos de Python, Ruff y configuración de Pytest.
- **Relaciones:** Define `pythonpath = ["src"]` y `tests` como directorio de pruebas.
- **Componentes / Funciones clave:** Proyecto `licitaciones-engine`, Python `>=3.10`, Ruff y `asyncio_mode = auto`.

- **Ruta:** `backend/requirements.txt`
- **Propósito:** Dependencias instalables del backend.
- **Relaciones:** Soporta FastAPI, SQLAlchemy, PostgreSQL, HTTPX, Tenacity, APScheduler y pruebas.
- **Componentes / Funciones clave:** FastAPI/Uvicorn, `asyncpg`, Pydantic, `httpx`, `tenacity`, `apscheduler`, Pytest.

- **Ruta:** `backend/alembic.ini`
- **Propósito:** Punto de configuración del sistema de migraciones.
- **Relaciones:** Debería coordinarse con `backend/alembic/env.py` y `versions/`.
- **Componentes / Funciones clave:** Configuración declarativa de Alembic; las revisiones aún no están implementadas.

- **Ruta:** `backend/alembic/env.py`
- **Propósito:** Archivo de entorno para ejecutar migraciones.
- **Relaciones:** Debe importar metadata de `database.py` y usar `settings.DATABASE_URL`.
- **Componentes / Funciones clave:** Actualmente es un placeholder sin configuración funcional.

- **Ruta:** `backend/main.py`
- **Propósito:** Ejecutable independiente para el scheduler ETL.
- **Relaciones:** Usa `OCESCExtractor`, `ELTOrchestrator` y `settings`; no inicia FastAPI.
- **Componentes / Funciones clave:** Agenda trabajos a las 02:00 y 14:00 y mantiene un bucle async.

- **Ruta:** `backend/src/config.py`
- **Propósito:** Configuración centralizada mediante Pydantic Settings.
- **Relaciones:** Es consumida por el motor SQLAlchemy, la API y el scheduler.
- **Componentes / Funciones clave:** `Settings`, `DATABASE_URL`, `API_URL`, `HOST`, `PORT` y carga de `.env`.

- **Ruta:** `backend/src/database.py`
- **Propósito:** Inicialización de persistencia async.
- **Relaciones:** Importa `settings`; expone `engine`, `AsyncSessionLocal` y `Base` a modelos y loader.
- **Componentes / Funciones clave:** `create_async_engine`, `async_sessionmaker`, base declarativa.

- **Ruta:** `backend/src/models/tenders.py`
- **Propósito:** Modelo SQLAlchemy de procesos de contratación.
- **Relaciones:** Usa `Base`; es consultado por la API y actualizado por el loader.
- **Componentes / Funciones clave:** `TenderModel`, tabla `tenders`, clave `ocid`, campos de proceso, importe, fechas y `raw_payload` JSON.

- **Ruta:** `backend/src/models/entities.py`
- **Propósito:** Reservado para modelos de compradores/proveedores.
- **Relaciones:** No tiene todavía relaciones ejecutables con `TenderModel`.
- **Componentes / Funciones clave:** Placeholder para RUC y nombres de entidades.

- **Ruta:** `backend/src/etl/extractor.py`
- **Propósito:** Cliente de extracción de releases OCDS desde OECE.
- **Relaciones:** Es usado por `ELTOrchestrator` y el scheduler.
- **Componentes / Funciones clave:** `OCESCExtractor`, `CATEGORIA_MAP`, normalización de URL, parámetros de consulta, validación JSON y reintentos.

- **Ruta:** `backend/src/etl/transformer.py`
- **Propósito:** Convertir releases OCDS a registros persistibles.
- **Relaciones:** Recibe la salida del extractor y entrega diccionarios al loader.
- **Componentes / Funciones clave:** `transform_and_filter_releases`, estado vigente, categoría, fechas, importes y payload crudo.

- **Ruta:** `backend/src/etl/loader.py`
- **Propósito:** Orquestar ETL y persistir registros.
- **Relaciones:** Coordina extractor y transformer; usa `AsyncSessionLocal` y `TenderModel`.
- **Componentes / Funciones clave:** `guardar_releases_en_db` con UPSERT por `ocid`; `ELTOrchestrator.run_pipeline` con paginación.

- **Ruta:** `backend/src/api/main.py`
- **Propósito:** Aplicación FastAPI y superficie HTTP principal.
- **Relaciones:** Consulta modelo y sesiones; dispara extractor/orquestador; habilita CORS y scheduler.
- **Componentes / Funciones clave:** lifespan APScheduler, `health_check`, `get_licitaciones`, opciones ETL, estado y `trigger_etl`; helpers de entidad, región, proceso y fecha.

- **Ruta:** `backend/src/schemas/ocds_schema.py`
- **Propósito:** Reservado para validación estricta de JSON OCDS.
- **Relaciones:** Debería interponerse entre extractor y transformer.
- **Componentes / Funciones clave:** Placeholder; no hay modelos Pydantic implementados.

- **Ruta:** `backend/src/services/notifier.py`
- **Propósito:** Reservado para búsquedas por palabras clave y alertas.
- **Relaciones:** No está conectado con API, scheduler ni frontend.
- **Componentes / Funciones clave:** Placeholder sin motor de notificaciones.

- **Ruta:** `backend/tests/test_etl.py`
- **Propósito:** Prueba/probe de conectividad con la API OECE.
- **Relaciones:** Llama directamente a OECE y no al extractor productivo.
- **Componentes / Funciones clave:** `test_extraccion_etl` imprime respuestas y analiza un release; carece de aserciones deterministas y depende de red externa.

## Frontend

- **Ruta:** `frontend/package.json`
- **Propósito:** Manifiesto y scripts del cliente web.
- **Relaciones:** Define React, Vite, Tailwind, PostCSS y Autoprefixer.
- **Componentes / Funciones clave:** Scripts `dev`, `build`, `preview`; React `18.3.1`; Vite `5.4.11`.

- **Ruta:** `frontend/vite.config.js`
- **Propósito:** Configuración del servidor y build Vite.
- **Relaciones:** Carga el plugin React y sirve la aplicación en el puerto 8080.
- **Componentes / Funciones clave:** `defineConfig`, `react()`, `host: true`, `strictPort: true`, `allowedHosts: true`.

- **Ruta:** `frontend/tailwind.config.js`
- **Propósito:** Configuración de tokens y escaneo de clases Tailwind.
- **Relaciones:** Es consumido por Tailwind y `frontend/src/index.css`.
- **Componentes / Funciones clave:** Tema visual, colores y rutas de contenido del frontend.

- **Ruta:** `frontend/src/main.jsx`
- **Propósito:** Punto de entrada de React.
- **Relaciones:** Monta `App` dentro de `AppProvider` e importa estilos globales.
- **Componentes / Funciones clave:** `ReactDOM.createRoot`, `React.StrictMode`, `AppProvider`.

- **Ruta:** `frontend/src/App.jsx`
- **Propósito:** Composición principal de la aplicación y carga de licitaciones.
- **Relaciones:** Usa store, selectores, layout y componentes del dashboard; consume `/api/licitaciones`.
- **Componentes / Funciones clave:** `App`, `MainContent`, `PlaceholderView`, `VIEW_META`, efectos de fetch y tecla Escape.

- **Ruta:** `frontend/src/store/AppState.jsx`
- **Propósito:** Estado global local del dashboard.
- **Relaciones:** Provee contexto a todos los componentes y recibe datos desde `App.jsx`.
- **Componentes / Funciones clave:** `DEFAULT_FILTERS`, `initialState`, `reducer`, `AppProvider`, `useApp`.

- **Ruta:** `frontend/src/store/selectors.js`
- **Propósito:** Derivar filas visibles y registro seleccionado.
- **Relaciones:** Lee el estado del contexto y usa utilidades de fecha.
- **Componentes / Funciones clave:** `selectVisible`, `useVisibleConvocatorias`, `useSelectedConvocatoria`; filtros y orden por match, valor o deadline.

- **Ruta:** `frontend/src/utils/format.js`
- **Propósito:** Formatear importes, fechas y plazos.
- **Relaciones:** Es usado por selectores y componentes KPI/dashboard.
- **Componentes / Funciones clave:** `fmtPEN`, `parseISO`, `fmtDate`, `fmtDateShort`, `daysUntil`, `TODAY`.

- **Ruta:** `frontend/src/components/layout/Sidebar.jsx`
- **Propósito:** Navegación lateral entre vistas.
- **Relaciones:** Consume `useApp` y despacha cambios de vista/nav.
- **Componentes / Funciones clave:** Menú de dashboard, buscador y módulos placeholder.

- **Ruta:** `frontend/src/components/layout/Topbar.jsx`
- **Propósito:** Barra superior y franja de urgencia.
- **Relaciones:** Lee estado global y conecta acciones de navegación/consulta.
- **Componentes / Funciones clave:** `Topbar`, `UrgentStrip`, controles de usuario y búsqueda visual.

- **Ruta:** `frontend/src/components/dashboard/KpiRow.jsx`
- **Propósito:** Mostrar métricas resumidas del conjunto cargado.
- **Relaciones:** Consume `state.convocatorias` y utilidades de fecha.
- **Componentes / Funciones clave:** vigentes, sugeridas, cierres en 48 horas y monto total.

- **Ruta:** `frontend/src/components/dashboard/FilterBar.jsx`
- **Propósito:** Controles de filtrado de convocatorias.
- **Relaciones:** Lee y modifica `state.filters`; deriva entidades y regiones desde los datos cargados.
- **Componentes / Funciones clave:** objeto, estado, fecha, tipo de proceso, entidad, región, valor y plazo.

- **Ruta:** `frontend/src/components/dashboard/BiddingTable.jsx`
- **Propósito:** Tabla/listado de oportunidades.
- **Relaciones:** Recibe `rows` desde `App.jsx` y despacha selección al store.
- **Componentes / Funciones clave:** filas, estado, importe, plazo, score y selección de convocatoria.

- **Ruta:** `frontend/src/components/dashboard/DetailPanel.jsx`
- **Propósito:** Panel de detalle de la convocatoria seleccionada.
- **Relaciones:** Recibe un `bid`, muestra documentos e hitos y permite cerrar el detalle.
- **Componentes / Funciones clave:** resumen, entidad, monto, timeline, documentos y acciones visuales.

- **Ruta:** `frontend/src/components/dashboard/Timeline.jsx`
- **Propósito:** Representar hitos temporales de un proceso.
- **Relaciones:** Consume la lista `hitos` del contrato de la API.
- **Componentes / Funciones clave:** estados y fechas de publicación, consultas, ofertas y apertura.

- **Ruta:** `frontend/src/components/dashboard/badges.jsx`
- **Propósito:** Componentes visuales de estados, tipos o etiquetas.
- **Relaciones:** Son reutilizables por tabla y detalle.
- **Componentes / Funciones clave:** badges de proceso y estado según las props recibidas.

- **Ruta:** `frontend/src/components/ui/Icon.jsx`
- **Propósito:** Abstracción de iconos de la interfaz.
- **Relaciones:** Es usada por layout, dashboard y controles.
- **Componentes / Funciones clave:** componente `Icon` con selección por nombre y clases CSS.

- **Ruta:** `frontend/src/index.css`
- **Propósito:** Estilos globales, componentes Tailwind y animaciones.
- **Relaciones:** Se importa desde `main.jsx`; define clases usadas en toda la UI.
- **Componentes / Funciones clave:** `.card`, botones, campos, chips, scrollbars, score ring y animaciones de timeline/panel.

## Archivos de documentación y control

- **Ruta:** `frontend/index.html`
- **Propósito:** Documento HTML raíz donde Vite monta React.
- **Relaciones:** Contiene el elemento raíz consumido por `main.jsx`.
- **Componentes / Funciones clave:** Metadata y `<div id="root">`.

- **Ruta:** `frontend/postcss.config.js`
- **Propósito:** Configuración del procesamiento CSS.
- **Relaciones:** Conecta Tailwind y Autoprefixer con Vite.
- **Componentes / Funciones clave:** Plugins PostCSS del frontend.

- **Ruta:** `frontend/README.md`
- **Propósito:** Instrucciones y contexto del cliente.
- **Relaciones:** Debe mantenerse sincronizado con `package.json` y el flujo API actual.
- **Componentes / Funciones clave:** Guía de desarrollo; revisar referencias heredadas a datos mock.

- **Ruta:** `backend/alembic/versions/`
- **Propósito:** Directorio de revisiones de esquema.
- **Relaciones:** Lo consume Alembic desde `alembic.ini`/`env.py`.
- **Componentes / Funciones clave:** Actualmente no contiene una migración funcional.