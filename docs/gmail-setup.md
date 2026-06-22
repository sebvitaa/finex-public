# Configuracion de Gmail para FinEx

FinEx Fase 6 usa Gmail API con OAuth 2.0 local. No se suben credenciales ni tokens al repositorio.

## Archivos locales

Coloca el archivo OAuth descargado desde Google Cloud en:

```text
data/local/gmail_credentials.json
```

FinEx creara el token de usuario despues de autorizar en:

```text
data/local/gmail_token.json
```

Ambos viven bajo `data/local/`, carpeta ignorada por git.

## Google Cloud

1. Entra a Google Cloud Console y crea o selecciona un proyecto.
2. Habilita Gmail API para ese proyecto.
3. Configura la pantalla de consentimiento OAuth.
4. Crea un cliente OAuth. Para desarrollo local usa tipo Desktop app o Web application con redirect local.
5. Si usas Web application, agrega este redirect autorizado:

```text
http://127.0.0.1:8000/api/v1/gmail/callback
```

6. Descarga el JSON del cliente OAuth.
7. Renombra el archivo a `gmail_credentials.json`.
8. Muevelo a `data/local/gmail_credentials.json`.

## Variables

Los valores por defecto estan en `.env.example`:

```env
GMAIL_CREDENTIALS_PATH=data/local/gmail_credentials.json
GMAIL_TOKEN_PATH=data/local/gmail_token.json
GMAIL_REDIRECT_URI=http://127.0.0.1:8000/api/v1/gmail/callback
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly
GMAIL_DEFAULT_QUERY=newer_than:30d
```

## Uso

1. Levanta el backend con `pnpm backend:dev`.
2. Levanta el frontend con `pnpm dev`.
3. Abre FinEx y entra a `Importar`.
4. Presiona `Conectar Gmail`.
5. Autoriza en Google.
6. Al volver a FinEx, presiona `Actualizar Gmail`.
7. Si Google esta mandando avisos financieros a spam, marca `Incluir correos de spam` antes de sincronizar.

FinEx trae mensajes recientes, descarta correos sin evidencia financiera, evita duplicados por `gmail_message_id` y deja los correos financieros como candidatos revisables.
Por defecto sincroniza `INBOX`; con la opcion de spam activa consulta tambien la etiqueta `SPAM` usando el mismo permiso de solo lectura.

## Permisos

El scope por defecto es `https://www.googleapis.com/auth/gmail.readonly`. Permite leer mensajes y metadatos sin modificar ni borrar correos. No uses `gmail.modify` para esta fase.
