# Checklist de seguridad inicial

## Fase 0

- [x] `.env` queda ignorado por git.
- [x] `.env.example` no contiene secretos reales.
- [x] `data/local/` queda ignorado por git.
- [x] No se incluyen bases SQLite reales.
- [x] No se solicitan credenciales bancarias.
- [x] No se implementa scraping bancario.
- [x] Gmail queda documentado como integracion posterior.
- [x] Los datos demo deben vivir en `data/demo/`.
- [x] La documentacion de privacidad existe en `docs/privacy.md`.

## Antes de usar correos reales

- [x] Fase 5 usa solo texto pegado o dataset demo, sin permisos reales de Gmail.
- [x] El dataset demo en `data/demo/sample_emails.json` contiene datos ficticios.
- [x] La previsualizacion guarda vista previa y hash del cuerpo, no una copia completa del correo.
- [x] El usuario debe confirmar o descartar cada candidato antes de crear transacciones.
- [x] Confirmar permisos exactos de Gmail API para Fase 6: `gmail.readonly`.
- [x] Implementar flujo de desconexion de Gmail que elimina `data/local/gmail_token.json`.
- [x] Discriminar correos no financieros antes de crear candidatos.
- [x] Guardar credenciales y tokens bajo `data/local/`, carpeta ignorada por git.
- [x] Evitar duplicados usando `gmail_message_id`.
- [ ] Evitar guardar cuerpos completos si bastan campos extraidos.
- [ ] Registrar origen de importacion sin exponer informacion innecesaria.
- [ ] Documentar como borrar datos locales.

## Antes de demo publica

- [ ] Revisar que `data/local/` no tenga archivos trackeados.
- [ ] Reemplazar datos reales por datos inventados.
- [ ] Confirmar que capturas de pantalla no expongan montos sensibles reales.
- [ ] Confirmar que personas, alumnos o deudores usados en demos sean ficticios.
- [ ] Confirmar que cuentas por cobrar demo no usen contactos reales.
- [ ] Confirmar que capturas de dashboard no mezclen datos reales con datos demo.
- [ ] Ejecutar `pnpm lint`.
- [ ] Ejecutar `pnpm test`.
- [ ] Ejecutar `pnpm build`.
