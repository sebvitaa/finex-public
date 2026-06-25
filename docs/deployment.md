# Deployment

FinEx se despliega mejor en dos servicios separados:

- Backend en Render.
- Frontend en Vercel.

La UI solo ve el dashboard real si el frontend recibe la URL publica del backend en `VITE_FINEX_API_URL`.

## Render

Usa este repositorio como un Web Service de Python.

Configuracion recomendada:

- Root directory: raiz del repo.
- Build command: `python -m pip install --upgrade pip && pip install -e ".[dev]"`
- Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

Variables de entorno:

```bash
FINEX_ENV=production
FINEX_ALLOWED_ORIGINS=https://tu-proyecto.vercel.app
FINEX_ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app
```

En produccion, si `FINEX_ALLOWED_ORIGIN_REGEX` queda vacio, el backend acepta por defecto dominios `https://*.vercel.app` para simplificar la demo publica. Si necesitas mantener datos entre reinicios, mas adelante conviene migrar de SQLite a una base gestionada. Para el demo publico actual, el arranque inicial vuelve a sembrar datos de muestra y el servicio sigue siendo util aunque el disco sea efimero.

## Vercel

En Vercel selecciona solo la carpeta `frontend/`.

Configuracion recomendada:

- Root directory: `frontend`
- Build command: `pnpm build`
- Output directory: `dist`

Variable de entorno:

```bash
VITE_FINEX_API_URL=https://tu-backend.onrender.com
```

## Orden correcto

1. Despliega primero Render.
2. Copia la URL publica del backend.
3. Configura `VITE_FINEX_API_URL` en Vercel.
4. Configura `FINEX_ALLOWED_ORIGINS` en Render con el dominio publico de Vercel.
5. Vuelve a desplegar Vercel.

## Verificacion rapida

- `https://tu-backend.onrender.com/health`
- La URL publica de Vercel
- El indicador de estado en la barra superior debe mostrar backend OK
