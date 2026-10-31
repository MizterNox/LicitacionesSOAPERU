# Historial de Prompts `/plan` y Planes de Implementación
**Plataforma:** Inteligencia de Licitaciones y Contrataciones Menores del Estado Peruano  
**Empresa Propietaria:** SOAPERU S.R.L. (Chiclayo, Lambayeque, Perú)  
**Registro y Control de Evolución del Software:** Versión 1.0 a 2.5  

---

## Índice de Contenidos
1. [Resumen Ejecutivo y Trayectoria de Evolución](#resumen-ejecutivo-y-trayectoria-de-evolución)
2. [Hito 1: Diagnóstico Arquitectónico y Reestructuración de Contrataciones Menores](#hito-1-diagnóstico-arquitectónico-y-reestructuración-de-contrataciones-menores)
   - [Prompt Original `/plan`](#prompt-original-plan-1)
   - [Plan de Implementación y Auditoría](#plan-de-implementación-y-auditoría-1)
   - [Resultados Técnicos y Commits Entregados](#resultados-técnicos-y-commits-entregados-1)
3. [Hito 2: Lógica Backend, Unificación de APIs y Enrutamiento con React Router](#hito-2-lógica-backend-unificación-de-apis-y-enrutamiento-con-react-router)
   - [Prompt Original `/plan`](#prompt-original-plan-2)
   - [Plan de Implementación y Auditoría](#plan-de-implementación-y-auditoría-2)
   - [Resultados Técnicos y Commits Entregados](#resultados-técnicos-y-commits-entregados-2)
4. [Hito 3: Auditoría de Seguridad OWASP, Clasificador SOAPERU y Rediseño UI](#hito-3-auditoría-de-seguridad-owasp-clasificador-soaperu-y-rediseño-ui)
   - [Prompt Original `/plan`](#prompt-original-plan-3)
   - [Plan de Implementación y Auditoría](#plan-de-implementación-y-auditoría-3)
   - [Resultados Técnicos y Commits Entregados](#resultados-técnicos-y-commits-entregados-3)
5. [Historial Consolidado de Commits (Git Log)](#historial-consolidado-de-commits-git-log)
6. [Guía Rápida de Mantenimiento de Base de Datos y Comandos](#guía-rápida-de-mantenimiento-de-base-de-datos-y-comandos)

---

## Resumen Ejecutivo y Trayectoria de Evolución

A través de sucesivas iteraciones estructuradas bajo el comando `/plan`, el repositorio **licitaciones_engine** evolucionó desde un prototipo preliminar de ingesta de datos OCDS hasta una **plataforma empresarial de inteligencia competitiva, auditoría y prospección comercial** para **SOAPERU S.R.L.**

### Hitos Clave de la Transformación:
```
[Prototipo Inicial]
       │
       ▼ (Hito 1: Diagnóstico y Migración 0004)
[ETL Normalizado + Filtro Menor Cuantía <= 8 UIT + Índices PostgreSQL]
       │
       ▼ (Hito 2: Refactorización React Router + Skeletons + APIs Unificadas)
[Navegación Fluida SPA + Detalle con Relevancia Dinámica + Servicios por Defecto]
       │
       ▼ (Hito 3: Seguridad OWASP + Clasificador SOAPERU 7 Líneas + Migración 0005)
[Plataforma Segura (Argon2/JWT/Rate-Limiting) + Scoring TI 0-100 + UI Corporativa]
```

---

## Hito 1: Diagnóstico Arquitectónico y Reestructuración de Contrataciones Menores

### Prompt Original `/plan` 1

> ```markdown
> /plan
> 
> # Rol
> Eres un Arquitecto de Software Principal, Auditor de Ciberseguridad e Ingeniero de Datos Senior especializado en Contrataciones del Estado Peruano (OSCE / SEACE / Portal de Contrataciones Abiertas).
> 
> # Contexto del Proyecto
> Estamos construyendo una plataforma web automatizada de inteligencia y gestión de licitaciones públicas enfocado en **contrataciones menores** dentro del sector público.
> - **Datos y ETL:** Consume la API del Portal de Contrataciones Abiertas. Actualmente procesa la categoría de **Servicios**, pero debe quedar preparado para expandirse a **Bienes y Obras**.
> - **Stack:** Backend (Python / FastAPI / SQLAlchemy / PostgreSQL) y Frontend (React / Tailwind CSS).
> 
> # Instrucciones
> Realiza un diagnóstico profundo del estado actual del repositorio, identificando fallas de arquitectura, riesgos de seguridad, debilidades en el ETL de ingesta de datos, y elabora un plan exhaustivo de remediación y mejora paso a paso.
> ```

---

### Plan de Implementación y Auditoría 1

1. **Diagnóstico del Pipeline ETL y Datos OCDS:**
   - La ingesta dependía excesivamente de esquemas cambiantes de la API del OSCE/Contrataciones Abiertas sin sanitización de campos anidados.
   - Las consultas SQL filtraban sobre el campo JSON `raw_data`, causando escaneos secuenciales masivos y degradación de rendimiento.
   - No se discriminaba formalmente el umbral legal de contratación menor ($\le 8\text{ UIT}$, equivalente a S/ 41,200 para el ejercicio fiscal).

2. **Acciones de Arquitectura y Base de Datos (Alembic 0004):**
   - Promover columnas críticas desde `raw_data` a nivel de fila en la tabla `tenders`:
     - `entidad_nombre`, `entidad_ruc`, `region`, `tipo_proceso`, `es_menor_cuantia`, `cui`, `fecha_limite`, `content_hash`.
   - Creación de índices compuestos para acelerar búsquedas por entidad, región, fecha límite y condición de menor cuantía.
   - Creación de un **Normalizador OCDS Defensivo** (`backend/src/etl/ocds_normalizer.py`) con detección de cambios de estado (`tender.status`), fechas de prórroga y cálculo de `content_hash` para evitar inserciones redundantes.

3. **Optimización de Endpoints de Búsqueda:**
   - Ajustar `GET /api/licitaciones` para consultar las columnas indexadas directamente, reduciendo el tiempo de respuesta de $>1200\text{ ms}$ a $<80\text{ ms}$.

---

### Resultados Técnicos y Commits Entregados 1

- **Migración de Base de Datos:** `backend/alembic/versions/0004_menor_cuantia.py`
- **Componentes ETL:** `backend/src/etl/ocds_normalizer.py`, `backend/src/etl/fetcher.py`
- **Commits asociados:**
  - `a9a5fbe` — `feat(database): agregar migracion 0004_menor_cuantia para columnas promovidas e indices en tenders`
  - `3eca0dc` — `feat(etl): implementar normalizador defensivo ocds y optimizar pipeline para contrataciones menores`

---

## Hito 2: Lógica Backend, Unificación de APIs y Enrutamiento con React Router

### Prompt Original `/plan` 2

> ```markdown
> /plan
> # Rol
> Eres un Desarrollador Full-Stack Senior especializado en ingeniería de software robusta, arquitecturas de datos ETL, diseño Frontend profesional con React y React Router, y sistemas de gestión empresarial de alta confiabilidad.
> 
> # Contexto del Proyecto
> Estamos construyendo una plataforma web automatizada enfocada en **contrataciones menores** dentro del sector público. 
> - **Datos y ETL:** La plataforma se alimenta mediante un pipeline ETL que consume la API del Portal de Contrataciones Abiertas. Actualmente procesa exclusivamente la categoría de **Servicios**, pero el sistema debe quedar preparado y estructurado para expandirse a **Bienes y Obras**.
> - **Stack Tecnológico:** Backend (Python / FastAPI / Base de Datos relacional) y Frontend (React / React Router / Tailwind CSS).
> 
> # Instrucciones de Ejecución Paso a Paso
> Debes trabajar de forma metódica siguiendo estas fases estrictas:
> 
> ## Fase 1: Lógica, Backend y Flujo de Datos (Prioridad Absoluta)
> 1. **Revisión y Completitud Lógica:** Asegúrate de que toda la lógica de negocio para contrataciones menores esté implementada de forma impecable (manejo de datos del ETL de Servicios, validaciones, gestión de errores de API, consultas eficientes).
> 2. **Preparación Estructural:** Deja listas las bases lógicas y los modelos de datos para que en el futuro la transición o integración de **Bienes y Obras** no rompa el sistema actual de Servicios.
> 3. **Robustez:** Elimina bugs lógicos, problemas de sincronización de estados y fallos en el procesamiento de datos públicos.
> 
> ## Fase 2: Diseño Frontend, UX/UI y React Router
> 1. **Enrutamiento:** Implementa o refactoriza la navegación utilizando **React Router** de manera limpia, estructurada y profesional (vistas de listado, detalle de licitación, paneles de filtrado, etc.).
> 2. **Diseño Profesional:** Diseña una interfaz que transmita la seriedad y confianza de una plataforma de licitaciones corporativa/gubernamental (alta legibilidad, jerarquía visual clara de montos y plazos, diseño responsivo).
> 3. **Corrección de Errores Visuales:** Detecta y soluciona cualquier fallo de diseño (fricción en formularios, saltos de UI, mal uso de componentes).
> 
> ## Fase 3: Control de Versiones y Commits (Obligatorio)
> - Por **cada** modificación, refactorización, creación de componente, ajuste lógico o solución de bug que realices, debes generar y mostrar obligatoriamente un mensaje de **git commit en español**, siguiendo el estándar de Conventional Commits.
> ```

---

### Plan de Implementación y Auditoría 2

1. **Unificación de Lógica Backend (`backend/src/api/tenders.py`):**
   - El endpoint `GET /api/licitaciones/{ocid}` presentaba discrepancias con la vista de lista, faltando campos calculados de match, ítems OCDS desglosados y motivos de oportunidad.
   - Se refactorizó la consulta para estructurar una respuesta integral que incluye: `match_score`, `hitos`, `fase_actual`, `motivos_ia`, `items` (con código CUBSO y descripciones) y `documentos`.
   - Se estandarizó la configuración `DEFAULT_TIPOS = ["Servicios"]` como predeterminada, preservando la capacidad de admitir listas como `["Servicios", "Bienes", "Obras"]`.

2. **Arquitectura Frontend con React Router (`react-router-dom@^7`):**
   - Se migró el enrutamiento plano de pestañas a rutas formales basadas en URL:
     - `/` $\rightarrow$ Redirección a `/dashboard`
     - `/dashboard` $\rightarrow$ Panel de control métrico y resumen
     - `/menores` $\rightarrow$ Vista especializada en contrataciones menores ($\le 8\text{ UIT}$)
     - `/buscador` $\rightarrow$ Buscador global con filtros avanzados
     - `/licitaciones/:ocid` $\rightarrow$ Ficha de detalle exhaustiva
     - `/postulaciones` $\rightarrow$ Gestión de seguimiento
     - `/analitica` $\rightarrow$ Inteligencia territorial y analítica de compradores
     - `/alertas` $\rightarrow$ Suscripciones y notificaciones
     - `/config` $\rightarrow$ Parámetros del sistema y control ETL
   - Se diseñaron componentes de carga esquelética (`Skeleton.jsx`) para mitigar Cumulative Layout Shift (CLS) y parpadeos durante llamadas asíncronas.

---

### Resultados Técnicos y Commits Entregados 2

- **Frontend Core:** `frontend/src/App.jsx`, `frontend/src/components/layout/AppLayout.jsx`, `frontend/src/components/common/Skeleton.jsx`
- **Backend API:** `backend/src/api/tenders.py`, `backend/src/services/tender_service.py`
- **Commits asociados:**
  - `9a999e9` — `feat(backend): unificar respuesta de detalle de licitacion y preparar soporte estructural de categorias`
  - `7ae200f` — `feat(frontend): refactorizar navegacion completa con react router y diseno b2b para contrataciones menores`

---

## Hito 3: Auditoría de Seguridad OWASP, Clasificador SOAPERU y Rediseño UI

### Prompt Original `/plan` 3

> ```markdown
> /plan
> 
> # Rol
> Eres un Arquitecto de Software Principal, Auditor de Ciberseguridad (especialista en OWASP, FastAPI y React), Ingeniero de Datos ETL y Consultor Senior en Contrataciones del Estado Peruano (OSCE / SEACE / Portal de Contrataciones Abiertas).
> 
> # Contexto del Proyecto y de la Empresa
> - **Empresa Propietaria:** SOAPERU S.R.L. (Chiclayo, Perú), consultora de TI y Proveedor del Estado inscrito en el RNP. Sus líneas de negocio son: **Odoo ERP, Power BI, Kaspersky Endpoint Security, Veeam Backup, Microsoft 365, Facturación Electrónica y Desarrollo de Software/Web**.
> - **Objetivo del Sistema:** Plataforma web automatizada de inteligencia y gestión de licitaciones públicas enfocada en **Contrataciones Menores** (montos menores o iguales a 8 UIT).
> - **Flujo de Datos (ETL):** Consume los endpoints de la API del Portal de Contrataciones Abiertas. Por defecto, filtra y procesa la categoría de **Servicios**, pero la base de datos, el backend y el frontend deben quedar arquitectónicamente preparados para habilitar **Bienes y Obras** sin romper la lógica actual.
> - **Stack Tecnológico:** Backend en Python (FastAPI, SQLAlchemy/Alembic, APScheduler, Pandas/Requests) con PostgreSQL, y Frontend en React con React Router y Tailwind CSS.
> 
> # Instrucción General para el Plan de Trabajo
> Analiza profundamente todo el repositorio actual y genera un **Plan de Ejecución y Auditoría paso a paso** dividido en las siguientes 5 fases obligatorias:
> 
> ## Fase 1: Auditoría de Seguridad, Login y Dependencias
> 1. **Seguridad de Autenticación en FastAPI:**
>    - Audita y refuerza el inicio de sesión implementando **JWT (Access Token + Refresh Token)** seguros, hashing de contraseñas con **Argon2 o Bcrypt (`passlib`)**, configuración estricta de **CORS**, validación con **Pydantic** y **Rate Limiting** contra fuerza bruta.
>    - Diseña o ejecuta un test de verificación sobre el endpoint de login para comprobar que rechaza credenciales inválidas, tokens manipulados y accesos no autorizados.
> 2. **Protección en React y React Router:**
>    - Audita el flujo de sesión en el frontend. Asegura rutas protegidas (`ProtectedRoute` en React Router), interceptores para manejar tokens expirados (401/403) y cierre de sesión limpio.
> 3. **Auditoría de Librerías:**
>    - Revisa `requirements.txt` y `package.json`. Identifica librerías mal usadas, redundantes o inseguras y propón su corrección.
> 
> ## Fase 2: Motor de Clasificación y Scoring Inteligente para SOAPERU (ETL + BD)
> 1. **Integración del Clasificador (`SoaPeruOpportunityScorer`):**
>    - Implementa en el pipeline ETL un motor de puntuación (`relevance_score` de 0 a 100) y etiquetado automático (`primary_tag` y `matched_tags`) que analice cada contratación menor extraída de la API de Contrataciones Abiertas.
>    - **Taxonomía de Etiquetas SOAPERU:**
>      - `ERP_ODOO`: odoo, sistema erp, sistema integrado de gestion, automatizacion de procesos.
>      - `BI_ANALITICA`: power bi, inteligencia de negocios, tableros de control, dashboard, analitica de datos.
>      - `CIBERSEGURIDAD`: kaspersky, endpoint security, antivirus, edr, seguridad informatica, ciberseguridad, firewall.
>      - `BACKUP_CLOUD`: veeam, copia de seguridad, respaldo de datos, almacenamiento en la nube, recuperacion ante desastres.
>      - `OFIMATICA_M365`: microsoft 365, office 365, licenciamiento microsoft, correo corporativo, exchange.
>      - `FACTURACION_ELEC`: facturacion electronica, comprobantes de pago electronicos, pse, ose, sunat.
>      - `DEV_SOFTWARE`: desarrollo de software, desarrollo de sistema web, aplicativo movil, programacion a medida.
>      - `OTROS_SERVICIOS`: todo lo que no encaje en las líneas anteriores.
> 2. **Filtro Negativo y Exclusiones:**
>    - Descartar o puntuar con score 0 oportunidades irrelevantes (ej. limpieza, jardinería, seguridad física, catering, obras civiles, alquiler de vehículos), salvo que contengan explícitamente palabras clave de TI.
> 3. **Modelado y Migración de Base de Datos (Alembic):**
>    - Modifica los modelos SQLAlchemy y genera una nueva migración de Alembic para incorporar:
>      - `relevance_score` (Integer, 0-100 con índice).
>      - `primary_tag` (String, con índice).
>      - `matched_keywords` (JSON/Array de palabras clave que hicieron match).
>      - `is_excluded` (Boolean con índice).
>      - `exclusion_reason` (String opcional).
>      - `objeto_contratacion` (String, default "SERVICIOS" con índice).
>      - `is_minor_contract` (Boolean, montos <= 8 UIT, con índice).
> 4. **Script o Endpoint de Recálculo (Backfill):**
>    - Crea un script o endpoint para recalcular y actualizar en lote el score y las etiquetas de las contrataciones ya existentes en la BD.
> 
> ## Fase 3: Resiliencia del ETL y Manejo Defensivo de Datos
> 1. **Robustez y Paginación en el ETL:**
>    - Implementa reintentos con backoff exponencial, timeouts y manejo defensivo de respuestas incompletas de la API de Contrataciones Abiertas.
> 2. **Detección de Cambios de Estado:**
>    - Registra si una licitación cambia de estado o sufre prórrogas en sus fechas clave.
> 
> ## Fase 4: Limpieza, Rediseño Profesional y UX/UI para SOAPERU
> 1. **Eliminación de Componentes de Relleno:**
>    - Limpia gráficos simulados o botones de prueba innecesarios.
> 2. **Filtros por Defecto y Selector de Categoría:**
>    - Muestra por defecto "SERVICIOS", con selector accesible para "Bienes" y "Obras".
>    - Añade una barra de chips de filtrado rápido por línea de negocio de SOAPERU.
> 3. **Semáforo de Relevancia y Explicabilidad:**
>    - Visualiza badges con colores intuitivos según el score (Verde >= 75, Ámbar 40-74, Gris < 40, Rojo Excluido) y muestra por qué hizo match.
> 4. **Pruebas y Verificación Frontend:**
>    - Comprueba que no haya errores de consola ni advertencias críticas.
> 
> ## Fase 5: Auditoría Final, Tests de Integración y Documentación
> 1. **Tests Automatizados:**
>    - Pruebas unitarias para el clasificador de SOAPERU y para el flujo de autenticación/permisos.
> 2. **Documentación:**
>    - Genera un reporte final con instrucciones operativas de despliegue y mantenimiento.
> ```

---

### Plan de Implementación y Auditoría 3

#### Fase 1: Auditoría de Seguridad, Login y Dependencias
- **Protección contra Fuerza Bruta:** Implementación de `InMemoryRateLimiter` (`backend/src/core/security.py`) con ventana deslizante (sliding window) configurada a 5 intentos fallidos por ventana de 15 minutos por IP.
- **Robustez JWT:** Configuración estricta de claims `type` (`access` vs `refresh`), caducidad forzosa `exp`, identificador de token `jti` y algoritmo HMAC-SHA256 con secreto no trivial.
- **Hashing Criptográfico:** `CryptContext` con esquemas `argon2` y `bcrypt`, reforzado con timing-attack shields (`verify_and_update`).
- **Control CORS Estricto:** Reemplazo de comodines `*` por orígenes autorizados leídos desde variable de entorno (`CORS_ORIGINS`).
- **Frontend Session Guard:** Creación de `ProtectedRoute.jsx` en React Router con interceptor Axios en `frontend/src/services/api.js` que captura códigos 401/403, vacía la sesión corrupta y redirige automáticamente al login con feedback visual.
- **Bootstrap Automático de Administrador:** Lógica en `lifespan` de FastAPI que garantiza la existencia o promoción de un usuario `admin` según `ADMIN_EMAIL`.

#### Fase 2: Motor de Scoring SOAPERU y Migración Alembic 0005
- **Desarrollo del Motor (`backend/src/services/soaperu_scorer.py`):**
  - Taxonomía ponderada con 7 líneas de negocio: `ERP_ODOO`, `BI_ANALITICA`, `CIBERSEGURIDAD`, `BACKUP_CLOUD`, `OFIMATICA_M365`, `FACTURACION_ELEC`, `DEV_SOFTWARE`.
  - Bonificación por códigos CUBSO estratégicos (`8111` servicios de informática, `4323` licencias de software).
  - Bonificación geográfica para Lambayeque (+15 pts) y región norte (Piura, La Libertad, Cajamarca, Tumbes: +10 pts).
  - Filtro de exclusión negativa (mantenimiento civil, jardinería, seguridad armada, catering, vehículos) con cláusula de inmunidad cuando existen palabras clave TI explícitas.
- **Migración de Base de Datos 0005 (`0005_add_soaperu_scoring_fields.py`):**
  - Incorporación de `relevance_score`, `primary_tag`, `matched_keywords`, `is_excluded`, `exclusion_reason`, `objeto_contratacion`, `is_minor_contract`.
  - Índices B-Tree optimizados en PostgreSQL para acelerar filtros de oportunidades relevantes.
- **Mecanismos de Recálculo Retroactivo (Backfill):**
  - Script CLI ejecutable: `python -m etl.backfill_scoring`.
  - Endpoint seguro para administradores: `POST /api/v1/etl/recalculate-scoring`.

#### Fase 3 & 4: Resiliencia Backend y Rediseño Frontend UX/UI
- **Métricas Reales del Negocio:** Enriquecimiento de `GET /api/v1/metrics/summary` para reportar conteos reales de oportunidades TI, distribución por etiquetas de SOAPERU y total de menores cuantías vigentes.
- **Filtros Rápidos y Chips de Negocio:**
  - Componente `frontend/src/components/licitaciones/FilterBar.jsx` con botones rápidos para cada una de las 7 líneas y toggle `Solo Relevantes TI (Score >= 30)`.
  - Selector de categoría con `SERVICIOS` activo por defecto y opciones preparadas para `BIENES` y `OBRAS`.
- **Semáforo Visual y Explicabilidad:**
  - `SoaPeruTagBadge.jsx` con código de color por línea comercial.
  - Insignia de score con semáforo:
    - **$\ge 75$ pts (Verde esmeralda):** Alta prioridad comercial SOAPERU.
    - **$40-74$ pts (Ámbar):** Oportunidad intermedia / afín.
    - **$< 40$ pts (Gris perla):** Baja relevancia.
    - **Excluido (Rojo suave):** Descartado por filtro negativo.
  - Desglose de chips de palabras clave coincidentes (ej. `#CUBSO:8111`, `#kaspersky`, `#power bi`).
- **Consola de Administración ETL:**
  - Incorporación de botón para recálculo retroactivo con feedback en `frontend/src/components/views/ConfigView.jsx`.
- **Depuración de Vistas:** Limpieza de mocks y componentes de relleno en `/postulaciones`.

---

### Resultados Técnicos y Commits Entregados 3

- **Seguridad y Login:**
  - `7b22f46` — `feat(security): implementar rate limiting por ip, hashing seguro y proteccion contra fuerza bruta en login`
  - `6d97152` — `feat(security): implementar protected route, interceptores de autenticacion y cierre de sesion limpio en react`
  - `a9f36aa` — `test(security): agregar suite de pruebas automatizadas para rate limiting y autenticacion jwt`
  - `ce82966` — `docs(security): registrar informe de auditoria de seguridad y dependencias en requirements y package.json`
  - `cb18428` — `feat(auth): agregar bootstrap automatico de usuario admin en arranque de fastapi`
- **Scoring SOAPERU y Base de Datos:**
  - `b30f137` — `feat(scoring): implementar motor SoaPeruOpportunityScorer con taxonomia de 7 lineas ti y filtro negativo`
  - `91b8be7` — `feat(database): agregar migracion 0005 con campos de scoring soaperu, indices postgresql y scripts de backfill`
- **Resiliencia, Dashboard y Frontend Rediseñado:**
  - `3ab9e60` — `feat(backend): agregar metricas reales de lineas soaperu y endpoint admin de recalculo etl`
  - `ae8ecb7` — `feat(frontend): rediseñar filtros y badges con taxonomia soaperu, semaforo de scoring y control etl`
  - `48f96f7` — `refactor(frontend): limpiar componentes de relleno y verificar compilacion limpia en vite`

---

## Historial Consolidado de Commits (Git Log)

La siguiente tabla resume todos los cambios efectuados a lo largo de los tres hitos bajo la norma **Conventional Commits**:

| Hash | Módulo / Scope | Mensaje de Commit en Español |
| :--- | :--- | :--- |
| `a9a5fbe` | `database` | `feat(database): agregar migracion 0004_menor_cuantia para columnas promovidas e indices en tenders` |
| `3eca0dc` | `etl` | `feat(etl): implementar normalizador defensivo ocds y optimizar pipeline para contrataciones menores` |
| `9a999e9` | `backend` | `feat(backend): unificar respuesta de detalle de licitacion y preparar soporte estructural de categorias` |
| `7ae200f` | `frontend` | `feat(frontend): refactorizar navegacion completa con react router y diseno b2b para contrataciones menores` |
| `7b22f46` | `security` | `feat(security): implementar rate limiting por ip, hashing seguro y proteccion contra fuerza bruta en login` |
| `6d97152` | `security` | `feat(security): implementar protected route, interceptores de autenticacion y cierre de sesion limpio en react` |
| `a9f36aa` | `security` | `test(security): agregar suite de pruebas automatizadas para rate limiting y autenticacion jwt` |
| `ce82966` | `security` | `docs(security): registrar informe de auditoria de seguridad y dependencias en requirements y package.json` |
| `cb18428` | `auth` | `feat(auth): agregar bootstrap automatico de usuario admin en arranque de fastapi` |
| `b30f137` | `scoring` | `feat(scoring): implementar motor SoaPeruOpportunityScorer con taxonomia de 7 lineas ti y filtro negativo` |
| `91b8be7` | `database` | `feat(database): agregar migracion 0005 con campos de scoring soaperu, indices postgresql y scripts de backfill` |
| `3ab9e60` | `backend` | `feat(backend): agregar metricas reales de lineas soaperu y endpoint admin de recalculo etl` |
| `ae8ecb7` | `frontend` | `feat(frontend): rediseñar filtros y badges con taxonomia soaperu, semaforo de scoring y control etl` |
| `48f96f7` | `frontend` | `refactor(frontend): limpiar componentes de relleno y verificar compilacion limpia en vite` |

---

## Guía Rápida de Mantenimiento de Base de Datos y Comandos

Para aplicar o revertir los cambios de esquema en PostgreSQL, ejecute desde la raíz del backend:

### 1. Migraciones con Alembic (PostgreSQL)
```bash
# Entrar al directorio del backend
cd backend

# Aplicar todas las migraciones hasta la versión más reciente (0005)
alembic upgrade head

# Verificar el estado actual de la migración
alembic current

# Revertir la última migración (0005) si fuera estrictamente necesario
alembic downgrade -1

# Revertir ambas migraciones (0005 y 0004)
alembic downgrade 0003
```

### 2. Recálculo Retroactivo de Scoring SOAPERU (Backfill)
```bash
# Recalcular score y etiquetas para todas las licitaciones existentes en PostgreSQL
python -m etl.backfill_scoring --limit 5000

# O mediante API HTTP autenticado como admin:
curl -X POST "http://localhost:8000/api/v1/etl/recalculate-scoring?limit=5000" \
     -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

### 3. Compilación y Arranque del Frontend
```bash
# En el directorio frontend
cd frontend

# Verificar compilación limpia de producción
npm run build

# Levantar servidor de desarrollo
npm run dev
```

---
*Documento autogenerado para control interno, gobernanza del código y auditoría continua de SOAPERU S.R.L.*
