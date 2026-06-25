# FinEx

FinEx ayuda a ordenar las finanzas personales en un solo lugar. Permite registrar gastos e ingresos, importar movimientos desde correos y ver cuánto dinero queda disponible. Es una app local y privada para entender el dinero antes de fin de mes, sin depender de la nube.

El foco inicial es simple: datos locales, dashboard claro, privacidad por defecto y crecimiento por fases. A Fase 10 ya cuenta con registro manual, Gmail real, importacion revisable, obligaciones, cuentas financieras, inversiones separadas de gasto/ingreso, clasificacion por reglas e insights avanzados.

> Aviso: todos los datos mostrados en esta copia son ficticios y corresponden al modo demo.

## Publico

- Repositorio publico: [sebvitaa/finex-public](https://github.com/sebvitaa/finex-public)
- Capturas de la demo: `docs/screenshots/`
- Modo recomendado al abrir: `Demo · Presentación`

## Fases

- La funcionalidad principal del producto llega hasta Fase 10.
- Las secciones F1, F2 y F3 documentan refinamientos posteriores de UX, layout y legibilidad.
- En esta copia publica me enfoqué en empaquetado, privacidad, landing, capturas y publicación.

## Arranque rapido

```bash
cp .env.example .env
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pnpm install
pnpm backend:dev
pnpm dev
```

Si quieres regenerar capturas demo:

```bash
pnpm exec node scripts/capture_screenshots.mjs
```

## Capturas

Las capturas públicas viven en `docs/screenshots/` y se generan sobre la sesión demo.

| Pantalla | Vista |
|---|---|
| Portada | [00-landing.png](docs/screenshots/00-landing.png) |
| Dashboard | [01-dashboard.png](docs/screenshots/01-dashboard.png) |
| Movimientos | [02-movements.png](docs/screenshots/02-movements.png) |
| Obligaciones | [03-obligations.png](docs/screenshots/03-obligations.png) |
| Importar | [04-import.png](docs/screenshots/04-import.png) |
| Correos | [05-mailbox.png](docs/screenshots/05-mailbox.png) |
| Cuentas | [06-accounts.png](docs/screenshots/06-accounts.png) |
| Ajustes | [07-settings.png](docs/screenshots/07-settings.png) |

## Stack definido

| Capa | Tecnologia |
|---|---|
| Frontend | React + TypeScript + Vite |
| UI | Tailwind CSS + componentes propios |
| Graficos | Recharts o Apache ECharts |
| Backend | Python 3.11 + FastAPI |
| Base de datos | SQLite local |
| ORM y migraciones | SQLAlchemy 2 + Alembic |
| Validacion | Pydantic |
| Tests backend | pytest |
| Tests frontend | Vitest + React Testing Library |
| E2E futuro | Playwright |
| Package manager | pnpm |

## Estructura inicial

```text
finex/
  backend/          API local, modelos, servicios y tests backend
  frontend/         Aplicacion React/Vite
  data/             Datos locales, demo e importaciones controladas
  docs/             Arquitectura, privacidad y checklist de seguridad
  scripts/          Utilidades de desarrollo
  tests/            Pruebas de estructura de Fase 0
```

## Requisitos locales

- Node.js 20 o superior.
- pnpm 9 o superior. Si no esta instalado, se puede habilitar con Corepack cuando este disponible:

```bash
corepack enable
corepack prepare pnpm@11.3.0 --activate
```

Si `corepack` no esta en PATH, puedes instalar pnpm con Homebrew:

```bash
brew install pnpm
```

- Python 3.11. La version recomendada para el proyecto queda fijada en `.python-version`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Comandos estandar

```bash
pnpm dev
pnpm backend:dev
pnpm build
pnpm test
pnpm lint
python -m pytest
```

Comandos adicionales de backend:

```bash
pnpm backend:init-db
.venv/bin/alembic upgrade head
```

`pnpm dev` levanta el frontend local en `http://127.0.0.1:5173`. `pnpm backend:dev` levanta la API local en `http://127.0.0.1:8000`. `pnpm test` ejecuta backend y frontend. `pnpm lint` ejecuta chequeo de estructura y TypeScript.

Si quieres recarga automatica del backend fuera del sandbox de Codex:

```bash
pnpm backend:dev:reload
```

## Rutina de cierre por fase

Al terminar cada fase:

```bash
pnpm test
pnpm lint
pnpm build
pnpm backend:init-db
git status --short
git add .
git commit -m "Implement FinEx fase N ..."
git push origin main
```

Si una fase no agrega migraciones, `pnpm backend:init-db` sigue siendo util para confirmar que la base local queda consistente.

## Variables de entorno

Copiar `.env.example` a `.env` cuando se necesite configurar el entorno local. No se deben guardar secretos reales en el repositorio.

```bash
cp .env.example .env
```

Para conectar Gmail en Fase 6, descarga el JSON OAuth desde Google Cloud y guardalo como `data/local/gmail_credentials.json`. La guia completa esta en `docs/gmail-setup.md`.

## Despliegue en Vercel + Render

Esta copia publica funciona mejor separando capas:

- Render hospeda el backend FastAPI.
- Vercel hospeda el frontend Vite.
- El frontend apunta al backend real con `VITE_FINEX_API_URL`.
- El backend debe permitir el dominio de Vercel en `FINEX_ALLOWED_ORIGINS`.

### Backend en Render

1. Crea un nuevo Web Service desde este mismo repositorio.
2. Usa la raiz del repo como directorio de trabajo.
3. Build command:

```bash
python -m pip install --upgrade pip && pip install -e ".[dev]"
```

4. Start command:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

5. Health check path: `/health`.
6. Variables recomendadas:

```bash
FINEX_ENV=production
FINEX_ALLOWED_ORIGINS=https://tu-proyecto.vercel.app
```

Si mantienes SQLite como base de datos por defecto, el demo funciona igual, pero los datos pueden resetearse al reiniciar el servicio. Para datos persistentes conviene migrar a una base gestionada mas adelante.

### Frontend en Vercel

1. Crea un proyecto nuevo desde este repositorio.
2. Define `frontend/` como root directory.
3. Build command:

```bash
pnpm build
```

4. Output directory: `dist`.
5. Variable de entorno:

```bash
VITE_FINEX_API_URL=https://tu-backend.onrender.com
```

6. Despliega primero Render y luego Vercel, para que la UI apunte a una API ya viva.

### Verificacion

- Abre `https://tu-backend.onrender.com/health`.
- Luego abre la URL publica de Vercel.
- Si el dashboard marca backend offline, revisa que `VITE_FINEX_API_URL` apunte a Render y que `FINEX_ALLOWED_ORIGINS` incluya el dominio de Vercel.

Guia ampliada: [docs/deployment.md](docs/deployment.md).

## Estado de la Fase 0

- Estructura de carpetas creada.
- README base creado.
- `.env.example` creado sin secretos reales.
- Documentacion inicial de privacidad y arquitectura creada.
- Checklist de seguridad inicial creado.
- Package manager definido: pnpm.
- Python local recomendado: 3.11.

## Estado de la Fase 1

- FastAPI inicializado.
- SQLAlchemy configurado con SQLite local.
- Alembic configurado con migracion inicial.
- Modelos creados: `Transaction`, `Category`, `ClassificationRule`, `ImportRun`, `EmailMessage`, `GmailSyncState`.
- Seed de 13 categorias base.
- `GET /health` disponible.
- CRUD de categorias disponible en `/api/v1/categories`.
- CRUD de transacciones disponible en `/api/v1/transactions`.
- Tests backend creados para health, categorias y transacciones.

## Estado de la Fase 2

- Frontend React + TypeScript + Vite inicializado.
- Tailwind configurado con tokens oscuros de FinEx.
- Layout principal creado con sidebar, top bar y area de contenido.
- Componentes base creados: `MetricCard`, `DataTable`, `CategoryBadge`, `StatusBadge`, `EmptyState`, `Drawer`, `Modal`.
- Cliente API tipado creado para `/health` y categorias.
- Dashboard inicial con datos demo, metricas, tendencia, ranking y transacciones recientes.
- Tests frontend con Vitest + React Testing Library.

## Estado de la Fase 3

- Registro manual disponible desde la vista `Transacciones`.
- Backend extendido con categorias por tipo, personas, cuentas por cobrar, pagos y desgloses de transaccion.
- Endpoints agregados: `/api/v1/people`, `/api/v1/receivables` y `/api/v1/transactions/{id}/splits`.
- Formulario UI para gastos, ingresos, pagos recibidos, dinero prestado y cuentas por cobrar.
- Desglose manual de compras mixtas, con plantilla para compra en Lider repartida entre Golosinas, Comida, Aseo y Otros.
- Creacion rapida de categorias y personas sin salir del flujo.
- Tabla de transacciones con filtros por texto, tipo, categoria, estado y persona.
- Edicion lateral y cambio rapido de categoria.
- Tests backend y frontend actualizados para Fase 3.

## Estado de la Fase 4

- Dashboard principal alimentado por la API real en `/api/v1/dashboard/overview`.
- Agregaciones mensuales y diarias de gastos e ingresos.
- Balance neto calculado como ingresos menos gastos.
- Ranking de categorias de gasto usando `transaction_splits` cuando existen.
- Vista separada de categorias de ingreso, ranking de comercios y ultimos movimientos reales.
- Resumen de cuentas por cobrar sin mezclarlas con gastos ni ingresos.
- Panel de supermercados por desglosar y deteccion basica de suscripciones mensuales.
- Tests de agregaciones para splits, ingresos, balance, deudas, supermercados y suscripciones.

## Estado de la Fase 5

- Dataset demo creado en `data/demo/sample_emails.json`.
- Parser inicial de correos implementado para monto, comercio, asunto, remitente, tipo sugerido, direccion ingreso/egreso y categoria sugerida.
- Endpoints agregados: `POST /api/v1/import/text`, `/api/v1/import/demo`, `/api/v1/import/confirm` y `/api/v1/import/discard`.
- Cada previsualizacion guarda `ImportRun` y `EmailMessage` con vista previa, hash del cuerpo y estado de parseo.
- La vista `Importar` permite pegar texto de correo, cargar demo, revisar candidatos, ver si son ingreso o egreso, cambiar tipo/categoria y descartar sin guardar.
- Las compras de supermercado sin detalle quedan marcadas como `Por distribuir` antes de confirmar.
- Las transferencias recibidas detectan formatos bancarios frecuentes como `monto recibido`, `has recibido una transferencia` y contrapartes en la frase.
- Las transferencias recibidas pueden confirmarse como ingreso por clases o como pago de cuenta por cobrar.

## Estado de la Fase 6

- Integracion Gmail API agregada con OAuth 2.0 local.
- Endpoints agregados: `GET /api/v1/gmail/status`, `/connect`, `/callback`, `POST /api/v1/gmail/sync` y `/disconnect`.
- Tokens y credenciales se guardan bajo `data/local/`, fuera de git.
- Sincronizacion Gmail manual desde la vista `Importar`, con auto-sync al abrir si ya hay token y polling local configurable.
- La vista `Importar` puede incluir la etiqueta `SPAM` cuando Google manda avisos financieros a spam.
- Discriminador inicial separa correos financieros de correos irrelevantes antes de crear candidatos.
- Deduplicacion por `gmail_message_id`.
- `GmailSyncState` guarda `history_id` y fechas de sincronizacion por label.

## Estado de la Fase 7

- Obligaciones incorporadas con cuentas por pagar y pagos parciales.
- Gmail incremental mejorado con reproceso de mensajes guardados y bandeja historica.
- La vista `Importar` permite crear personas, cuentas por cobrar y cuentas por pagar durante la confirmacion.
- Dashboard y transacciones separan pagos de obligaciones de gasto/ingreso operacional.
- Los movimientos manuales y candidatos Gmail pueden disminuir cuentas por cobrar/pagar existentes o crear nuevas cuentas por cobrar/pagar desde un ingreso o egreso compartido.

## Estado de la Fase 8

- Modelos y endpoints de cuentas financieras, snapshots de saldo, cuentas de inversion y movimientos de inversion.
- Transacciones soportan `investment` y `disinvestment` sin contaminar gasto ni ingreso mensual.
- Parser Gmail detecta institucion, tipo de cuenta/tarjeta, ultimos cuatro digitos y confianza de deteccion.
- Importacion y registro manual permiten asignar cuenta financiera e inversion al movimiento.
- Dashboard muestra saldos estimados, delta mensual, inversiones, rescates y movimientos sin cuenta asignada.

## Estado de la Fase 9

- Motor deterministico de reglas con prioridad, confianza y razon legible.
- Endpoints `/api/v1/rules`, `/api/v1/rules/test`, `/feedback` y `/suggestions`.
- Reglas base sembradas para Spotify, Uber, Rappi, Lider, supermercados, clases, obligaciones, transferencias, bancos e inversiones.
- Importacion Gmail aplica reglas sobre las sugerencias del parser y conserva `classification_method`.
- Ediciones de categoria, tipo, cuenta o inversion generan feedback para sugerir reglas repetidas.
- `Ajustes` permite crear, pausar, probar y aceptar reglas sugeridas.

## Estado de la Fase 10

- Dashboard avanzado con heatmap diario, comparacion contra mes anterior, insights de anomalías y proyeccion de cierre.
- Filtro guardado de periodo mensual/anual para dashboard y exportacion.
- Presupuestos base por categoria para supermercado, golosinas, aseo, comida, transporte y suscripciones.
- Insights por persona para ingresos por clases, cuentas por cobrar y cuentas por pagar.
- Analisis de compras mixtas usando `transaction_splits` para separar comida, golosinas, aseo u otros.
- Exportacion CSV desde `/api/v1/dashboard/export.csv`.
- Las transacciones aprobadas/importadas pueden editarse desde el drawer: tipo, fecha, monto, comercio, contraparte, categoria, cuenta, inversion, persona, enlaces a obligaciones, estado, notas y desgloses.
- Al editar inversiones/desinversiones, FinEx sincroniza el movimiento de inversion asociado y el valor de la cuenta.

## Estado de la Fase F1

- Calculos monetarios del dashboard normalizados a pesos chilenos enteros.
- Parser, desgloses automaticos y ajustes proporcionales redondean a pesos enteros, con el ultimo tramo absorbiendo diferencias.
- El dashboard superior separa liquidez sin credito, inversiones, gasto mensual, ingreso mensual y balance real.
- Las metricas principales evitan truncar montos y usan formato CLP sin decimales.

## Estado de la Fase F2

- Registro manual simplificado: la primera accion visible queda enfocada en tipo, fecha, monto, categoria, origen y guardar.
- Detalles secundarios del movimiento pasan a secciones desplegables: relacion, persona, cuentas, estado, notas, categorias rapidas y desgloses.
- La revision de candidatos importados prioriza clasificar, revisar origen y confirmar; cuentas, obligaciones y desgloses quedan en paneles secundarios.
- Ajustes oculta la creacion/prueba avanzada de reglas hasta que el usuario necesite afinar el clasificador.
- Paneles auxiliares de personas y categorias propias dejan de competir con el registro principal.

## Estado de la Fase F3

- Barra izquierda reorganizada con entradas concretas: Dashboard, Movimientos, Obligaciones, Importar, Correos, Cuentas y Configuracion.
- `Movimientos` queda enfocado en registrar y revisar transacciones, sin mezclar cuentas por cobrar/pagar.
- `Obligaciones` abre directamente cuentas por cobrar, cuentas por pagar, abonos, pagos totales y compensaciones.
- `Importar` mantiene entrada manual, Gmail y carga de candidatos; `Correos` concentra revision de candidatos y bandeja Gmail guardada.
- `Cuentas` separa tarjetas, cuentas e inversiones de `Configuracion`, que queda para reglas y privacidad.

## Estado de la Fase F4

- `Movimientos` ya no muestra administracion completa de personas ni categorias propias.
- `Configuracion` agrega administracion estructural de personas con creacion y edicion inline.
- `Configuracion` agrega administracion de categorias propias con creacion, edicion y eliminacion controlada.
- Las categorias de sistema quedan visibles como referencia, sin competir con el registro operativo.
- Los correos archivados siguen visibles y restaurables desde `Configuracion`.

## Estado de la Fase F5

- `Movimientos` muestra por defecto solo transacciones activas y deja los archivados fuera de la vista normal.
- La tabla agrega una vista `Activos / Archivados / Todos` para revisar movimientos ocultos sin perder trazabilidad.
- Las transacciones se pueden editar y archivar desde la UI normal, pero no existe accion principal de borrado duro.
- Los movimientos archivados se pueden restaurar desde la vista de archivados.
- El cambio rapido de categoria conserva el estado archivado para evitar reactivar movimientos por accidente.

## Estado de la Fase F6

- `Obligaciones` agrega resumen superior de por cobrar, por pagar y balance neto.
- El balance por persona muestra si el remanente queda a favor mio, en contra mia o cuadrado.
- Las cuentas por cobrar y por pagar tienen formularios diferenciados por copy, color y jerarquia visual.
- Los formularios muestran el monto antes que el motivo para acelerar el registro.
- Cada obligacion muestra el monto pendiente como dato principal y abre notas, fechas y pagos en un modal de detalle.

## Estado de la Fase F7

- QA visual ejecutada en desktop `1280x720` y movil `390x844` sobre Dashboard, Movimientos, Obligaciones, Importar, Correos, Cuentas y Configuracion.
- Se corrigio overflow horizontal en dashboard agregando `min-w-0` a la grilla de ultimos movimientos y paneles auxiliares.
- Se contuvo el overflow global movil desde el shell para que la navegacion horizontal no ensanche el documento.
- Las tablas anchas conservan scroll interno controlado sin crear scroll horizontal global.
- Reporte de QA visual agregado en `docs/qa/f7-visual.md`.
