# Guía para publicar FinEx en GitHub (versión demo, sin datos sensibles)

Esta guía explica, paso a paso, cómo empaquetar el proyecto **FinEx** en un repositorio
público y presentable: con datos 100 % ficticios, sin credenciales ni información
personal, y con una landing pulida que lo deje como un producto vendible.

> **Carpeta destino:** `finex-public/` (este mismo directorio). Es una copia limpia
> y separada del repo de trabajo. Nunca se publica el repo original tal cual, porque
> contiene tu base de datos real, tokens de Gmail y archivos personales.

La estructura que vas a poblar ya está creada aquí:

```text
finex-public/
  backend/    → código de la API (copiado y sanitizado)
  frontend/   → app React/Vite
  data/demo/  → solo datos de ejemplo (sample_emails.json)
  docs/       → documentación pública
  scripts/    → utilidades de desarrollo
```

---

## 0. Resultado esperado

Al terminar tendrás, en `finex-public/`, un repositorio que:

- Arranca con un solo comando y muestra **datos demo generados al vuelo**.
- No contiene `finex.db`, tokens, credenciales, logs ni archivos `.docx/.pdf` personales.
- Tiene una **landing presentable** y screenshots tomados sobre la demo (no sobre datos reales).
- Tiene `README`, `LICENSE` y `.env.example` claros para que cualquiera lo levante.

---

## 1. Inventario de datos sensibles (qué NUNCA se sube)

Antes de copiar nada, ten claro qué hay que dejar fuera. En el repo de trabajo:

| Ruta | Qué es | Acción |
|---|---|---|
| `data/local/finex.db` | Tu base de datos real (transacciones reales) | **Excluir** |
| `data/local/finex_demo.db` | DB demo cacheada | **Excluir** (se regenera sola) |
| `data/local/gmail_credentials.json` | Credenciales OAuth de Google | **Excluir** |
| `data/local/gmail_token.json` | Token de acceso a tu Gmail | **Excluir** |
| `.env` | Variables con rutas/llaves locales | **Excluir** (solo va `.env.example`) |
| `logs/` | Logs de ejecución (pueden tener datos) | **Excluir** |
| `Copia de INFOGRAFÍA FORMATO - FERIA EXPLORATEC.pdf` | Material personal de feria | **Excluir** |
| `Ficha Técnica Showcase ExploraTec.docx` | Documento personal | **Excluir** |
| `entrega/*.pdf` | Informes/infografías personales | **Revisar y excluir** (regenerar si quieres versión pública) |
| `FinEx.app/`, `build/`, `finex.egg-info/` | Artefactos de build locales | **Excluir** |
| `.DS_Store`, `__pycache__/`, `.venv/`, `node_modules/` | Basura del SO / dependencias | **Excluir** |
| `assets/screenshots/*.png` | Capturas — pueden mostrar datos reales | **Regenerar desde la demo** |

> **Buena noticia:** el `.gitignore` actual ya ignora `.env`, `data/local/*`, `*.db`,
> `logs/`, `__pycache__/`, `.venv/`, `node_modules/`, `build/` y `dist/`. El riesgo real
> está en los archivos **no rastreados** que se copian por error (PDFs, DOCX, `FinEx.app/`,
> `.DS_Store`). Por eso copiamos por inclusión, no clonando la carpeta entera.

---

## 2. Copiar el código limpio (no clonar la carpeta entera)

Trabaja desde la raíz del repo de trabajo (`finex/`). Copia **solo** lo que es código y
configuración pública hacia `../finex-public/`.

```bash
# Desde la carpeta del proyecto de trabajo:
cd "/Users/seba/Documents/Visual Studio/Lat Ex/CTAIA/finex"
DEST="../finex-public"

# Backend (sin __pycache__)
rsync -a --exclude='__pycache__' --exclude='*.pyc' backend/ "$DEST/backend/"

# Frontend (sin dependencias ni build)
rsync -a --exclude='node_modules' --exclude='dist' --exclude='*.tsbuildinfo' \
  frontend/ "$DEST/frontend/"

# Scripts de desarrollo (sin cachés)
rsync -a --exclude='__pycache__' scripts/ "$DEST/scripts/"

# Documentación pública
rsync -a docs/ "$DEST/docs/"

# Solo los datos de DEMO (nunca data/local)
cp data/demo/sample_emails.json "$DEST/data/demo/"

# Configuración y manifiestos de proyecto
cp .env.example .gitignore .python-version package.json pnpm-lock.yaml \
   pnpm-workspace.yaml pyproject.toml alembic.ini README.md "$DEST/"

# Placeholders para que git conserve las carpetas de datos vacías
mkdir -p "$DEST/data/local" "$DEST/data/imports"
touch "$DEST/data/local/.gitkeep" "$DEST/data/imports/.gitkeep" "$DEST/data/demo/.gitkeep"
```

> No copies: `data/local/`, `logs/`, `entrega/`, `assets/` (de momento), `FinEx.app/`,
> `build/`, `finex.egg-info/`, `.venv/`, ni los `*.pdf`/`*.docx` de la raíz.

---

## 3. Limpiar restos antes de versionar

```bash
cd "../finex-public"

# Borra cualquier .DS_Store que se haya colado
find . -name '.DS_Store' -delete

# Asegúrate de que NO existan datos reales ni secretos
rm -f data/local/finex.db data/local/finex_demo.db \
      data/local/gmail_credentials.json data/local/gmail_token.json
```

### Verificación de fugas (hazla siempre)

```bash
# 1) No debe aparecer ningún .db, token o credencial
find . -name '*.db' -o -name '*token*.json' -o -name '*credential*.json'   # → vacío

# 2) Busca tu correo personal o nombres reales en todo el árbol
grep -rIn "TU_USUARIO_O_NOMBRE" .  # → vacío
grep -rIn "TU_NOMBRE_REAL" .      # → vacío (reemplaza por tu nombre/apellido)

# 3) Revisa que no haya .env (solo .env.example)
ls -a | grep -E '^\.env$'         # → vacío
```

Si algo aparece, elimínalo o anonímalo **antes** del primer commit.

---

## 4. Reemplazar transacciones y correos por datos ficticios

El proyecto ya separa lo real de lo demo, así que esto es sobre todo *verificar*:

- **Transacciones demo:** las genera `backend/app/db/seed_demo.py`, que crea un dataset
  ficticio de ~6 meses (ingresos por clases, suscripciones, gastos variados, transferencias,
  inversiones y obligaciones). No hay datos reales: se regeneran cada vez que arranca la app
  o al pulsar "Reiniciar datos demo".
- **Correos demo:** viven en `data/demo/sample_emails.json`. Ya usan remitentes ficticios
  (`avisos@banco.demo`, `no-reply@spotify.demo`) y personas inventadas (`Camila Alumna`).
  Revísalos y confirma que ningún monto, comercio o nombre corresponda a algo real tuyo.
- **Fixtures de tests:** los tests en `backend/tests/` usan dominios de bancos reales
  (`bancochile.cl`, `bancoedwards.cl`, etc.) **solo como remitentes de ejemplo** para
  validar el parser. No contienen datos personales, pero si quieres una versión 100 %
  neutra, reemplázalos por dominios `*.demo` o `*.example`.

**Modo demo por defecto en el repo público:** para que cualquiera vea la app con datos al
abrirla, deja la sesión `demo` como predeterminada. Revisa `backend/app/main.py` (al arranque
ya ejecuta `init_demo_db()`) y la selección de sesión en `backend/app/api/v1/sessions.py`.
Documenta en el README que la sesión "Demo · Presentación" es la recomendada para evaluar.

> Importante: la sesión real (`finex.db`) no se incluye, así que en el repo público solo
> existirá la demo. No hace falta borrar datos: simplemente nunca se copian.

---

## 5. Mejorar la landing y dejarla presentable

La landing vive en `frontend/src/features/landing/LandingPage.tsx` y ya tiene hero, tour de
features, flujo "de correos a dashboard", sección de privacidad y CTA final. Para dejarla a
nivel producto, aplica (en el repo público) estas mejoras:

1. **Hero con propuesta de valor clara.** Un titular de una línea (qué es y para quién),
   un subtítulo de beneficio y dos botones: "Ver demo" (entra a la app en modo demo) y
   "Ver en GitHub".
2. **Prueba social / métricas.** La sección de `Stat` ya anima números; úsala para hitos
   creíbles (fases completadas, nº de insights, categorías) — sin inventar usuarios.
3. **Tour de features con mockups.** Mantén los componentes `MockDashboard`, `MockMovements`,
   `MockObligations`, `MockImport`, `MockAccounts`, `MockRules` con datos ficticios.
4. **Sección de privacidad.** Refuerza el mensaje "local-first, tus datos no salen de tu
   equipo": es el principal diferenciador del producto.
5. **Pie con enlaces:** GitHub, licencia, stack y un disclaimer de "datos de demostración".
6. **Pulido visual:** consistencia de espaciados, modo claro/oscuro, foco accesible en
   botones, `alt` en imágenes, y que la landing sea responsive en móvil.
7. **Meta tags / Open Graph** en `frontend/index.html` (título, descripción, imagen de
   preview) para que el enlace se vea bien al compartirlo.

> Regla de oro: cualquier número, nombre o monto que se vea en la landing debe ser ficticio.

---

## 6. Regenerar los screenshots desde la demo

Los screenshots de `assets/screenshots/` pueden mostrar datos reales. Regéneralos **siempre
sobre la sesión demo**:

```bash
cd "../finex-public"
# Levanta backend + frontend en modo demo y corre el capturador
node scripts/capture_screenshots.mjs   # ajusta el script para apuntar a la sesión "demo"
```

Guárdalos en `frontend/public/assets/` o en `docs/screenshots/` y referéncialos desde el
README y la landing. Verifica una por una que no aparezca tu nombre, correo ni saldos reales.

---

## 7. Documentación pública: README, LICENSE y .env.example

1. **README.md** — adapta el actual para audiencia pública:
   - Qué es FinEx y el problema que resuelve (1 párrafo).
   - Capturas de la demo.
   - Stack y arquitectura (enlaza `docs/architecture.md`).
   - **Cómo levantarlo** (sección 8 de esta guía).
   - Aviso destacado: *"Todos los datos mostrados son ficticios (modo demo)."*
   - Estado del proyecto / roadmap por fases y, opcional, sección de contribución.

2. **LICENSE** — añade una licencia (p. ej. MIT) si quieres permitir reutilización:

   ```bash
   # En finex-public/, crea el archivo LICENSE con el texto de la licencia elegida.
   ```

3. **.env.example** — ya existe y no tiene secretos. Revisa que todas las variables
   apunten a valores de ejemplo (`data/local/...`) y deja Gmail como **opcional**:
   documenta que la app funciona en modo demo **sin** configurar Gmail.

4. **docs/** — deja `architecture.md` y la checklist de privacidad. Borra cualquier doc que
   mencione tu instalación personal.

---

## 8. Sección "Cómo levantarlo" (para el README público)

```bash
# 1. Backend (Python 3.11)
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

# 2. Frontend
corepack enable && corepack prepare pnpm@11.3.0 --activate   # o: brew install pnpm
pnpm install

# 3. Configuración
cp .env.example .env       # los valores por defecto bastan para la demo

# 4. Arrancar (la demo se siembra sola al iniciar)
pnpm backend:dev           # API en http://127.0.0.1:8000
pnpm dev                   # Frontend en http://127.0.0.1:5173

# 5. Tests
pnpm test
```

---

## 9. Inicializar git y subir a GitHub

```bash
cd "../finex-public"

# Repo limpio y sin historial del repo de trabajo (evita arrastrar datos antiguos)
git init
git add -A

# REVISIÓN FINAL antes del commit: confirma que no entra nada sensible
git status
git ls-files | grep -iE 'env$|\.db$|token|credential|\.pdf$|\.docx$|\.DS_Store'   # → vacío

git commit -m "FinEx: versión demo pública"
```

> El `git init` parte de cero a propósito: el historial del repo original puede contener
> commits con tu `finex.db` o tokens antiguos. Un repo nuevo garantiza un historial limpio.

Crear el repo y publicar (requiere `gh` autenticado o crear el repo en la web):

```bash
gh repo create finex --public --source=. --remote=origin --push
# o, manual:
# git remote add origin git@github.com:TU_USUARIO/finex.git
# git branch -M main
# git push -u origin main
```

---

## 10. Checklist final (antes de hacer público el repo)

- [ ] No existe ningún `*.db`, `*token*.json` ni `*credential*.json` en el árbol.
- [ ] `grep -rIn "TU_USUARIO_O_NOMBRE"` y tu nombre real no devuelven nada.
- [ ] Solo está `.env.example` (no `.env`).
- [ ] No hay `.DS_Store`, `__pycache__/`, `node_modules/`, `.venv/`, `build/`, `dist/`.
- [ ] No se copiaron los PDF/DOCX personales ni `entrega/` ni `FinEx.app/`.
- [ ] Los screenshots son de la **demo** y no muestran datos reales.
- [ ] La app arranca con `pnpm backend:dev` + `pnpm dev` y muestra datos demo.
- [ ] La landing está pulida, es responsive y todos sus datos son ficticios.
- [ ] README, LICENSE y `.env.example` están completos y son claros.
- [ ] `git ls-files` no lista ningún archivo sensible.

Cuando todos los puntos estén marcados, el repositorio está listo para hacerse público.
