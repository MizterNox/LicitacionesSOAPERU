# Guía paso a paso desde cero

Esta guía reconstruye el sistema por ingeniería inversa. Cada hito debe cerrarse con una prueba verificable antes de continuar.

## Paso 1: Configuración inicial

### 1.1 Crear repositorios y estructura

Separar el proyecto en `backend/`, `frontend/` y `docs/`. Mantener un README raíz con requisitos, comandos, variables y decisiones de arquitectura.

### 1.2 Preparar el backend

1. Crear un entorno Python compatible con `>=3.10`.
2. Instalar las dependencias de `backend/requirements.txt`.
3. Configurar `pyproject.toml` con `pythonpath = ["src"]`, Pytest y Ruff.
4. Crear `.env` fuera del control de versiones con `DATABASE_URL`, `API_URL`, `HOST` y `PORT`.
5. Verificar que `uvicorn src.api.main:app --reload --port 8000` importa la aplicación.

### 1.3 Preparar el frontend

1. Crear el proyecto Vite con React.
2. Instalar las versiones declaradas en `frontend/package.json`.
3. Configurar Tailwind, PostCSS y el puerto `8080`.
4. Definir `VITE_API_URL` para conectar con el backend.
5. Añadir linting y formateo explícitos, que actualmente no están declarados.

### 1.4 Criterio de cierre

Ambas aplicaciones arrancan, las variables sensibles no están versionadas, y existe una comprobación automática de importación, build frontend y formato.

## Paso 2: Backend y base de datos

### 2.1 Diseñar el modelo de datos

Crear `TenderModel` con `ocid` como clave primaria e índices para `id_proceso`, `estado`, `objeto_contratacion` y `fecha_lanzamiento`. Conservar el release OCDS completo en JSON para auditoría.

### 2.2 Configurar persistencia

1. Crear el motor async SQLAlchemy y la fábrica `AsyncSessionLocal`.
2. Definir una base declarativa compartida.
3. Crear la primera revisión Alembic para `tenders`.
4. Ejecutar migraciones en un PostgreSQL local o administrado.
5. Comprobar conexión mediante una prueba de salud que distinga disponibilidad de esquema.

### 2.3 Implementar extracción

1. Encapsular la API OECE en `OCESCExtractor`.
2. Normalizar `Servicios`, `Bienes` y `Obras` a los enums OCDS.
3. Enviar `page`, `order`, `startDate`, `endDate` y `mainProcurementCategory`.
4. Validar status HTTP, `Content-Type` y JSON.
5. Reintentar únicamente errores transitorios y registrar el intento y la página.

### 2.4 Implementar transformación

1. Validar presencia de `ocid`.
2. Extraer datos de `tender`, `items`, `value` y `date`.
3. Convertir fechas ISO 8601 a un criterio temporal coherente.
4. Calcular estado y categoría con reglas documentadas.
5. Definir qué hacer con releases incompletos y conservar la causa de descarte.

### 2.5 Implementar carga

1. Insertar registros transformados en una transacción.
2. Actualizar por conflicto de `ocid` para lograr idempotencia.
3. Registrar cantidad extraída, transformada, descartada y persistida.
4. Añadir pruebas con una base aislada o fixtures, sin depender de OECE.

### 2.6 Exponer controladores y rutas

Crear routers separados para salud, licitaciones y ETL. Usar esquemas Pydantic de request/response, paginación, validación de fechas y errores HTTP consistentes. Proteger el disparo ETL con autorización.

### 2.7 Criterio de cierre

Una ejecución reproducible obtiene fixtures OCDS, transforma datos, ejecuta migraciones, hace UPSERT sin duplicados y responde a los endpoints con contratos validados.

## Paso 3: Frontend y UI

### 3.1 Arranque y composición

1. Crear `main.jsx` con `React.StrictMode` y `AppProvider`.
2. Montar `App.jsx` como layout de sidebar, topbar, contenido y panel de detalle.
3. Separar componentes de layout, dashboard y UI reutilizable.

### 3.2 Estado

Definir un estado inicial para vista, convocatorias, carga, error, selección, navegación, consulta, orden y filtros. Implementar acciones explícitas con `useReducer`: carga de datos, selección, vistas, filtros y limpieza.

### 3.3 Consumo y selectores

1. Leer `VITE_API_URL` con fallback local.
2. Construir parámetros de consulta a partir de los filtros.
3. Manejar desmontaje para evitar actualizar un componente no montado.
4. Guardar resultados en el reducer.
5. Aplicar filtrado y ordenamiento derivado en selectores puros.

### 3.4 Componentes de negocio

- `KpiRow`: calcula vigentes, sugeridas, cierres en 48 horas y monto.
- `FilterBar`: permite objeto, estado, fecha, proceso, entidad, región, valor y plazo.
- `BiddingTable`: muestra oportunidades y permite seleccionar una.
- `DetailPanel`: presenta detalle, documentos e hitos.
- `Timeline`: presenta hitos del proceso.
- `Sidebar` y `Topbar`: navegación y acciones globales.

### 3.5 Estilos y responsive

Usar Tailwind y las clases compartidas de `index.css`. Mantener diseño responsive, panel de detalle móvil y estados de carga/error. El proyecto actual usa datos visuales derivados y algunos botones sin handlers; estos deben convertirse en estados funcionales o marcarse como no disponibles.

### 3.6 Criterio de cierre

`npm run build` produce un bundle, la UI carga fixtures mediante un mock controlado o backend local y los selectores tienen pruebas para búsqueda, filtros, orden y fechas.

## Paso 4: Integración frontend-backend

### 4.1 Contrato

Documentar el objeto de convocatoria que consume React: identificador, entidad, objeto, estado, fechas, monto, región, hitos, documentos y datos crudos. Preferir un esquema versionado o un cliente generado para evitar divergencias.

### 4.2 CORS y configuración

Permitir solo el origen del frontend en desarrollo y producción. Configurar la URL mediante entorno y verificar health check, conectividad a PostgreSQL y disponibilidad de la API OECE por separado.

### 4.3 Autenticación y permisos

Incorporar identidad y roles antes de exponer datos o ETL. El endpoint de lectura puede requerir autenticación según el modelo de negocio; el disparo ETL debe restringirse a operadores autorizados y auditarse.

### 4.4 Errores y observabilidad

Definir formato de error común, códigos de correlación, timeouts y política de reintento. El frontend debe distinguir error de red, respuesta inválida, ausencia de resultados y sesión no autorizada.

### 4.5 Criterio de cierre

Un flujo de aceptación crea/actualiza un registro desde un fixture OCDS, lo consulta en `/api/licitaciones`, lo filtra en React, abre el detalle y verifica estados de error y carga.

## Paso 5: Despliegue y configuraciones finales

1. Ejecutar migraciones Alembic como paso explícito del despliegue.
2. Construir frontend con `npm run build` y servir el resultado mediante el hosting elegido.
3. Ejecutar FastAPI con Uvicorn detrás de un proxy TLS.
4. Configurar PostgreSQL administrado, backups, índices y límites de conexión.
5. Definir secretos en el proveedor, nunca en el repositorio.
6. Configurar CORS, dominios, time zone del scheduler y política de logs.
7. Añadir health checks de aplicación, base de datos y dependencia OECE.
8. Elegir entre scheduler embebido o worker externo; no ejecutar ambos para evitar duplicados.
9. Activar alertas para fallos ETL, latencia, volumen anómalo y errores de API.
10. Publicar documentación de operación, rollback y recuperación.

## Secuencia de validación recomendada

```text
configuración -> migración -> fixture OCDS -> extracción -> transformación
-> UPSERT -> endpoint -> store React -> filtros -> build -> despliegue
```