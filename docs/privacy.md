# Privacidad de FinEx

FinEx trabaja con informacion financiera personal. La privacidad no es una mejora futura: es una condicion de diseno desde la Fase 0.

## Principios

- Guardar datos localmente por defecto.
- No solicitar credenciales bancarias.
- No hacer scraping de bancos ni apps financieras.
- Usar datos demo o anonimizados durante el desarrollo.
- Pedir permisos explicitos antes de leer correos reales.
- Mantener Gmail desacoplado del resto del sistema.
- Permitir que el usuario revise y corrija cualquier clasificacion.

## Datos previstos

| Dato | Uso | Riesgo | Regla inicial |
|---|---|---|---|
| Fecha | Agrupar gastos por dia y mes | Bajo | Guardar localmente |
| Monto | Calcular totales y tendencias | Alto | Guardar localmente |
| Comercio | Detectar categorias y repeticiones | Medio | Guardar localmente |
| Categoria | Dashboard y filtros | Bajo | Editable por usuario |
| Asunto/cuerpo de correo | Extraccion de transacciones | Alto | Usar muestras controladas primero |
| Tokens OAuth | Acceso Gmail futuro | Alto | No implementar en Fase 0 |

## Gmail

La integracion real con Gmail se implementara solo despues de contar con backend, parser, importacion controlada y dashboard. Cuando se active, debera usar Gmail API, OAuth, permisos minimos y una forma clara de desconectar la cuenta.

Permisos objetivo por ahora:

| Permiso | Motivo |
|---|---|
| `https://www.googleapis.com/auth/gmail.metadata` | Leer metadatos como remitente, asunto, fecha, etiquetas e historial cuando baste. |
| `https://www.googleapis.com/auth/gmail.readonly` | Leer snippets o cuerpo solo cuando haga falta extraer monto, comercio o contraparte. |
| Refresh token OAuth | Sincronizacion controlada mientras la cuenta siga conectada. |

En Fase 6 el scope activo por defecto es `https://www.googleapis.com/auth/gmail.readonly`, porque algunos comprobantes pueden requerir snippet o cuerpo para detectar monto y comercio. FinEx no solicita permisos de escritura como `gmail.modify`.

Credenciales y tokens:

- `data/local/gmail_credentials.json`: cliente OAuth descargado desde Google Cloud.
- `data/local/gmail_token.json`: access/refresh token generado al autorizar.
- Ambos archivos quedan fuera de git por estar bajo `data/local/`.

Los correos irrelevantes se registran como descartados y los correos financieros quedan como candidatos revisables; nada se convierte en transaccion sin confirmacion manual.

## Reglas para desarrollo

- `.env` nunca debe subirse al repositorio.
- `.env.example` solo contiene valores vacios o placeholders.
- `data/local/` queda ignorado para evitar subir bases reales.
- Las demos deben usar `data/demo/` con datos inventados o anonimizados.
- Cualquier exportacion de correo real debe revisarse antes de entrar al repo.

## Criterio de seguridad inicial

La Fase 0 queda aceptable si el repositorio no contiene secretos reales, no incluye bases de datos personales y documenta de forma visible como se manejaran datos sensibles.
