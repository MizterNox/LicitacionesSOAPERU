# Plataforma de Inteligencia de Licitaciones y Contrataciones Menores
### SOAPERU S.R.L. · Sistema de Prospección Comercial y Compras Públicas del Estado Peruano

Plataforma web empresarial full-stack diseñada para la captura, procesamiento, calificación automatizada y gestión estratégica de **Contrataciones Menores (montos $\le 8\text{ UIT}$)** y procesos de selección pública convocados por entidades del Estado Peruano (OSCE / SEACE / Portal de Contrataciones Abiertas).

---

## Índice
1. [Características Principales](#características-principales)
2. [Arquitectura y Stack Tecnológico](#arquitectura-y-stack-tecnológico)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Requisitos Previos del Sistema](#requisitos-previos-del-sistema)
5. [Guía de Despliegue e Instalación Paso a Paso](#guía-de-despliegue-e-instalación-paso-a-paso)
   - [Paso 1: Clonar el Repositorio](#paso-1-clonar-el-repositorio)
   - [Paso 2: Configuración de Base de Datos PostgreSQL](#paso-2-configuración-de-base-de-datos-postgresql)
   - [Paso 3: Configurar Variables de Entorno del Backend](#paso-3-configurar-variables-de-entorno-del-backend)
   - [Paso 4: Entorno Virtual e Instalación de Dependencias Backend](#paso-4-entorno-virtual-e-instalación-de-dependencias-backend)
   - [Paso 5: Ejecutar Migraciones de Base de Datos (Alembic)](#paso-5-ejecutar-migraciones-de-base-de-datos-alembic)
   - [Paso 6: Recálculo de Scoring Retroactivo (Backfill)](#paso-6-recálculo-de-scoring-retroactivo-backfill)
   - [Paso 7: Instalación y Configuración del Frontend](#paso-7-instalación-y-configuración-del-frontend)
6. [Cómo Ejecutar la Plataforma en Local](#cómo-ejecutar-la-plataforma-en-local)
7. [Usuarios y Credenciales de Acceso](#usuarios-y-credenciales-de-acceso)
8. [Motor de Clasificación y Scoring de SOAPERU](#motor-de-clasificación-y-scoring-de-soaperu)
9. [Seguridad y Protección OWASP](#seguridad-y-protección-owasp)
10. [Comandos Frecuentes y Mantenimiento](#comandos-frecuentes-y-mantenimiento)

---

## Características Principales

* **Ingesta Automatizada ETL (API OCDS):** Pipeline extractivo resiliente que consume los endpoints estándar del Portal de Contrataciones Abiertas de Perú con paginación defensiva, reintentos y detección de prórrogas/modificaciones de estado.
* **Foco en Contrataciones Menores:** Detección legal automatizada de órdenes de servicio con montos menores o iguales a **8 UIT** (S/ 41,200), agilizando oportunidades de adjudicación rápida sin concurso público formal.
* **Motor Inteligente `SoaPeruOpportunityScorer`:** Algoritmo ponderado (0 a 100 puntos) que analiza títulos, descripciones y códigos CUBSO clasificando las convocatorias dentro de las **7 líneas de negocio de SOAPERU S.R.L.**.
* **Bonificación Territorial:** Priorización de oportunidades en **Lambayeque** (+15 pts) y en la **Macro Región Norte** (+10 pts: Piura, La Libertad, Cajamarca, Tumbes).
* **Filtro Anti-Ruido:** Descarte automático de rubros ajenos a tecnología (mantenimiento civil, jardinería, seguridad armada, catering, alquiler vehicular), con cláusula de inmunidad ante palabras clave de TI explícitas.
* **Frontend SPA con React Router v7:** URLs directas e independientes por licitación (`/licitaciones/:ocid`), semáforo de relevancia visual, chips de línea comercial y carga fluida con skeletons anti-CLS.
* **Ciberseguridad Robusta:** Autenticación JWT con refresh token en cookie `httpOnly`, hashing con **Argon2id / Bcrypt**, protección anti-fuerza bruta (**Rate Limiting** por IP) y control de acceso por roles (RBAC).

---

## Arquitectura y Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND SPA                          │
│  React 18 · React Router v7 · Tailwind CSS · Vite · Recharts │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON (Axios/Fetch)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       BACKEND API                           │
│  FastAPI · Uvicorn · Pydantic v2 · APScheduler · Argon2/JWT  │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
┌─────────────────────────────┐  ┌────────────────────────────┐
│      MOTOR ETL & SCORER     │  │     BASE DE DATOS (PG)     │
│  Extractor OCDS · Scorer    │  │  PostgreSQL 14+            │
│  SoaPeruOpportunityScorer   │  │  SQLAlchemy 2.0 (Async)    │
│  Normalizador Defensivo     │  │  Alembic (Migraciones)     │
└─────────────────────────────┘  └────────────────────────────┘
```

* **Backend:** Python 3.11+, FastAPI 0.110+, SQLAlchemy 2.0 (motor asíncrono con `asyncpg` y `psycopg2`), Pydantic v2, APScheduler 3.10+, Passlib (Argon2 / Bcrypt), PyJWT.
* **Base de Datos:** PostgreSQL 14+ con extensiones de texto y optimización de índices B-Tree.
* **Frontend:** React 18.3, React Router 7.18, Tailwind CSS 3.4, Lucide Icons, Vite 5.4.
* **Proveedor de Datos Públicos:** API OCDS del Portal de Contrataciones Abiertas (OECE / OSCE Perú).

---

## Estructura del Proyecto

```
licitaciones_engine/
├── backend/
│   ├── alembic/                      # Versiones de migración de BD (0001 a 0005)
│   │   ├── versions/
│   │   │   ├── 0004_menor_cuantia.py # Columnas promovidas e índices de menor cuantía
│   │   │   └── 0005_add_soaperu_scoring_fields.py # Campos de scoring e índices SOAPERU
│   │   └── env.py
│   ├── src/
│   │   ├── api/                      # Enrutadores y endpoints de FastAPI
│   │   │   ├── routers/              # auth.py, metrics.py, saved_filters.py, export.py
│   │   │   ├── deps.py               # Inyección de dependencias (get_current_user, etc.)
│   │   │   └── main.py               # Aplicación principal FastAPI y agendador APScheduler
│   │   ├── core/
│   │   │   └── security.py           # Rate limiting en memoria, Argon2, hashing y JWT
│   │   ├── etl/                      # Pipeline de datos OCDS
│   │   │   ├── extractor.py          # Extracción desde API OECE
│   │   │   ├── loader.py             # Orquestador ELT y persistencia
│   │   │   ├── transformer.py        # Normalización de esquemas OCDS
│   │   │   └── backfill_scoring.py   # Script de recálculo retroactivo de scoring
│   │   ├── models/                   # Modelos ORM (UserModel, TenderModel, CronLog, etc.)
│   │   ├── schemas/                  # Validadores Pydantic y OCDS Normalizer
│   │   ├── services/                 # Lógica de negocio (SoaPeruOpportunityScorer, mailer)
│   │   ├── config.py                 # Carga de variables de entorno con Pydantic Settings
│   │   └── database.py               # Conexión SQLAlchemy async y síncrona
│   ├── tests/                        # Batería de pruebas automatizadas con Pytest
│   ├── .env                          # Variables de entorno locales del backend
│   ├── alembic.ini                   # Configuración del gestor de migraciones
│   └── requirements.txt              # Dependencias de Python
│
├── frontend/
│   ├── src/
│   │   ├── components/               # Componentes UI, Search, Dashboard, Layout, Auth
│   │   ├── routes/                   # Definición de rutas con ProtectedRoute (AppRoutes.jsx)
│   │   ├── views/                    # MinorProcurementView, DashboardView, TenderDetailView
│   │   ├── store/                    # Contextos globales (AuthContext, AppState)
│   │   ├── lib/api.js                # Cliente HTTP centralizado y manejo de tokens
│   │   ├── App.jsx                   # Shell principal de la aplicación
│   │   └── main.jsx                  # Entrada Vite
│   ├── package.json                  # Dependencias NPM
│   ├── vite.config.js                # Configuración del servidor de desarrollo Vite (puerto 8080)
│   └── tailwind.config.js            # Sistema de diseño, paleta corporativa y tipografía
│
├── HISTORIAL_PROMPTS_Y_PLANES.md     # Bitácora detallada de auditorías y evolución
└── README.md                         # Este documento
```

---

## Requisitos Previos del Sistema

Asegúrese de contar con las siguientes herramientas instaladas en su equipo o servidor:

1. **Python:** Versión `3.11` o superior ([Descargar Python](https://www.python.org/downloads/)).
2. **Node.js:** Versión `18.x` o `20.x` LTS y **npm** ([Descargar Node.js](https://nodejs.org/)).
3. **PostgreSQL:** Versión `14`, `15` o `16` en ejecución local o remota ([Descargar PostgreSQL](https://www.postgresql.org/download/)).
4. **Git:** Para control de versiones ([Descargar Git](https://git-scm.com/)).

---

## Guía de Despliegue e Instalación Paso a Paso

### Paso 1: Clonar el Repositorio

Abra una consola o terminal y clone el repositorio:

```bash
git clone https://github.com/MizterNox/LicitacionesSOAPERU.git
cd LicitacionesSOAPERU
```

---

### Paso 2: Configuración de Base de Datos PostgreSQL

Inicie sesión en su instancia de PostgreSQL (vía `psql` o pgAdmin) y cree la base de datos destinada para el proyecto:

```sql
CREATE DATABASE "licitacionesELT"
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Spanish_Peru.1252'
    LC_CTYPE = 'Spanish_Peru.1252'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;
```

---

### Paso 3: Configurar Variables de Entorno del Backend

Cree o edite el archivo `.env` dentro de la carpeta `backend/` (`backend/.env`):

```ini
# Configuración de Servidor
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development

# Conexión a Base de Datos PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:admin26@localhost:5432/licitacionesELT
DATABASE_SYNC_URL=postgresql://postgres:admin26@localhost:5432/licitacionesELT

# API del Portal de Contrataciones Abiertas (OECE / SEACE)
API_URL=https://contratacionesabiertas.oece.gob.pe/api/v1/releases

# Seguridad y Autenticación JWT (OWASP)
JWT_SECRET_KEY=soaperu_super_secret_jwt_key_production_2026_change_in_prod
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Usuario Administrador Automático (Bootstrap)
ADMIN_EMAIL=admin@soaperu.pe

# Orígenes Permitidos (CORS estricto)
CORS_ORIGINS=["http://localhost:8080","http://127.0.0.1:8080","http://localhost:5173"]

# Inteligencia Artificial (Google Gemini opcional)
GEMINI_API_KEY=tu_api_key_opcional_aqui
GEMINI_MODEL=gemini-1.5-flash
AI_ENABLED=false
```

> **Nota:** Modifique el usuario, contraseña y puerto de `DATABASE_URL` según las credenciales de su PostgreSQL.

---

### Paso 4: Entorno Virtual e Instalación de Dependencias Backend

1. Ingrese a la raíz del proyecto y cree un entorno virtual de Python:
   ```powershell
   python -m venv venv
   ```

2. Active el entorno virtual:
   * **En Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **En Linux / macOS:**
     ```bash
     source venv/bin/activate
     ```

3. Instale las librerías requeridas:
   ```bash
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```

---

### Paso 5: Ejecutar Migraciones de Base de Datos (Alembic)

Para construir todas las tablas, columnas analíticas e índices B-Tree en PostgreSQL:

```bash
cd backend
alembic upgrade head
```

> Este comando aplicará las 5 migraciones históricas, incluyendo:
> * `0004_menor_cuantia.py`: Columnas promovidas de menor cuantía, CUI, fechas e índices.
> * `0005_add_soaperu_scoring_fields.py`: Columnas `relevance_score`, `primary_tag`, `matched_keywords`, `is_excluded`, `is_minor_contract` e índices B-Tree.

Para verificar que la base de datos se encuentra al día:
```bash
alembic current
```

---

### Paso 6: Recálculo de Scoring Retroactivo (Backfill)

Si su base de datos ya cuenta con registros históricos extraídos previamente, ejecute el script de recálculo para calificarlos con la taxonomía comercial de SOAPERU:

```bash
# Estando dentro de la carpeta backend
python -m etl.backfill_scoring --limit 5000
```

---

### Paso 7: Instalación y Configuración del Frontend

1. Abra una nueva terminal y navegue a la carpeta `frontend/`:
   ```bash
   cd frontend
   ```

2. Instale los paquetes de Node.js:
   ```bash
   npm install
   ```

3. *(Opcional)* Cree un archivo `frontend/.env` si desea cambiar la URL del backend:
   ```ini
   VITE_API_URL=http://localhost:8000
   ```

4. Verifique la compilación limpia del proyecto:
   ```bash
   npm run build
   ```

---

## Cómo Ejecutar la Plataforma en Local

Para operar el sistema completo en modo desarrollo, mantenga abiertas **dos terminales**:

### Terminal 1: Backend (FastAPI + APScheduler)
```powershell
cd C:\Users\Usuario\Desktop\PROYECTOS\licitaciones_engine\backend\src
..\..\venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```
* **API REST:** `http://localhost:8000`
* **Swagger UI interactivo:** `http://localhost:8000/docs`
* **Health Check:** `http://localhost:8000/health`

### Terminal 2: Frontend (React + Vite)
```powershell
cd C:\Users\Usuario\Desktop\PROYECTOS\licitaciones_engine\frontend
npm run dev
```
* **Aplicación Web:** `http://localhost:8080`

---

## Usuarios y Credenciales de Acceso

El sistema cuenta con roles diferenciados (`admin` y `user`) protegidos mediante hash criptográfico **Argon2id**:

| Usuario | Contraseña | Rol | Privilegios |
| :--- | :--- | :--- | :--- |
| **`admin@soaperu.pe`** | `SoaPeru2026!` | `admin` | Acceso total, visualización de licitaciones, recálculo de scoring ETL, configuración de tipos y auditoría. |
| **`analista_test@licitlens.pe`** | `PeruCompras2026!` | `admin` | Cuenta para pruebas de homologación y verificación de funcionalidades. |

> **Bootstrap Automático:** Al iniciar el backend, la función `ensure_admin_user()` verifica la cuenta definida en `ADMIN_EMAIL` (`admin@soaperu.pe`) y le asigna el rol `admin` de forma automática.

---

## Motor de Clasificación y Scoring de SOAPERU

El servicio `SoaPeruOpportunityScorer` evalúa cada contratación pública y genera una puntuación de **0 a 100 puntos** según los siguientes criterios:

### 1. Taxonomía de las 7 Líneas de Negocio Oficiales
1. **`ERP_ODOO`:** Odoo ERP, sistemas integrados de gestión, automatización de procesos empresariales.
2. **`BI_ANALITICA`:** Microsoft Power BI, business intelligence, analítica de datos, tableros de control y dashboards directivos.
3. **`CIBERSEGURIDAD`:** Kaspersky Endpoint Security, antivirus corporativo, EDR, ciberseguridad, firewalls y protección de infraestructura.
4. **`BACKUP_CLOUD`:** Veeam Backup & Replication, copias de seguridad de servidores, almacenamiento en nube, disaster recovery.
5. **`OFIMATICA_M365`:** Microsoft 365, Office 365 empresarial, licencias Microsoft, correo Exchange institucional.
6. **`FACTURACION_ELEC`:** Facturación electrónica, comprobantes de pago digitales, integración con sistemas PSE / OSE y SUNAT.
7. **`DEV_SOFTWARE`:** Desarrollo de software a medida, aplicaciones web, plataformas móviles, portales institucionales y APIs.

### 2. Bonificaciones Ponderadas
* **Códigos CUBSO Oficiales:** +20 pts si el ítem coincide con la familia `8111` (Servicios de Tecnologías de la Información) o `4323` (Software y Licenciamiento).
* **Bonificación Regional Sede Chiclayo:** +15 pts si la entidad convocante pertenece a **Lambayeque**.
* **Bonificación Macro Región Norte:** +10 pts para convocatorias en **Piura, La Libertad, Cajamarca o Tumbes**.

### 3. Semáforo Visual de Relevancia
* 🟢 **Verde Esmeralda ($\ge 75$ pts):** Convocatoria de **Alta Prioridad Comercial**.
* 🟡 **Ámbar ($40$ a $74$ pts):** Relevancia Media / Oportunidad afín.
* ⚪ **Gris ($< 40$ pts):** Baja afinidad tecnológica.
* 🔴 **Rojo (Excluido):** Descartado por filtro anti-ruido (limpieza, seguridad física, obras civiles, jardinería).

---

## Seguridad y Protección OWASP

1. **Rate Limiting por IP y Correo:** Máximo 5 intentos de inicio de sesión erróneos por IP en 15 minutos. Al excederse, la API responde `HTTP 429 Too Many Requests` con la cabecera `Retry-After`.
2. **Mitigación de Timing Attacks:** El login ejecuta verificaciones de dummy hash cuando un correo no existe, impidiendo enumerar cuentas mediante análisis del tiempo de respuesta.
3. **Manejo Estricto de JWT:**
   - `access_token`: Formato Bearer, duración de 30 minutos, claim de tipo explícito.
   - `refresh_token`: Duración de 7 días, persistido en Cookie `httpOnly`, `SameSite=Lax`, protegido contra ataques XSS.
4. **Rutas Protegidas en Frontend:** El componente `ProtectedRoute.jsx` y los interceptores en `frontend/src/lib/api.js` capturan automáticamente respuestas `401 Unauthorized`, revocan el token inválido y redirigen al login sin dejar pantallas congeladas.
5. **Cabeceras HTTP de Seguridad:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## Comandos Frecuentes y Mantenimiento

### Base de Datos y Migraciones (Alembic)
```bash
# Aplicar migraciones pendientes
cd backend
alembic upgrade head

# Revertir la última migración
alembic downgrade -1

# Ver historial de versiones aplicadas
alembic history --verbose
```

### Ejecutar Pruebas Automatizadas
```bash
# Ejecutar toda la suite de pruebas del backend
cd backend
pytest

# Ejecutar únicamente pruebas de seguridad y autenticación
pytest tests/test_auth_security.py -v

# Ejecutar pruebas del motor de scoring de SOAPERU
pytest tests/test_soaperu_scorer.py -v
```

### Ejecución Manual del Pipeline ETL
```bash
# Extraer manualmente una corrida del día para Servicios
cd backend
python -c "import asyncio; from main import job_etl_diario; asyncio.run(job_etl_diario())"
```

---

## Licencia y Confidencialidad

Sistema desarrollado para uso exclusivo de **SOAPERU S.R.L.** (RUC: 20601552528, Chiclayo, Perú).  
Todos los derechos reservados. Prohibida su copia, distribución o comercialización no autorizada.
