# Backend

API local de FinEx implementada con FastAPI, SQLAlchemy, Alembic, SQLite y Pydantic.

## Comandos

```bash
pnpm backend:init-db
pnpm dev
pnpm test
```

## Endpoints de Fase 1

- `GET /health`
- `GET /api/v1/categories`
- `POST /api/v1/categories`
- `GET /api/v1/categories/{category_id}`
- `PATCH /api/v1/categories/{category_id}`
- `DELETE /api/v1/categories/{category_id}`
- `GET /api/v1/transactions`
- `POST /api/v1/transactions`
- `GET /api/v1/transactions/{transaction_id}`
- `PATCH /api/v1/transactions/{transaction_id}`
- `DELETE /api/v1/transactions/{transaction_id}`

La base local vive en `data/local/finex.db` y queda ignorada por git.

## Endpoints de Fase 5

- `POST /api/v1/import/text`: previsualiza una transaccion candidata desde texto pegado.
- `POST /api/v1/import/demo`: previsualiza candidatos desde `data/demo/sample_emails.json`.
- `POST /api/v1/import/confirm`: crea una transaccion desde un candidato, incluyendo desgloses opcionales.
- `POST /api/v1/import/discard`: descarta el correo sin crear transaccion.

El parser inicial vive en `backend/app/services/email_parser.py` y se mantiene desacoplado de Gmail; `backend/app/services/gmail_client.py` solo trae y normaliza mensajes.

## Endpoints de Fase 6

- `GET /api/v1/gmail/status`: estado de credenciales, token, scopes y ultima sincronizacion.
- `GET /api/v1/gmail/connect`: genera URL OAuth de Google.
- `GET /api/v1/gmail/callback`: recibe el codigo OAuth y guarda el token local.
- `POST /api/v1/gmail/sync`: lee Gmail, descarta irrelevantes y crea candidatos revisables.
- `POST /api/v1/gmail/disconnect`: elimina el token local.

Credenciales locales:

```text
data/local/gmail_credentials.json
data/local/gmail_token.json
```

## Endpoints de Fase 8

- `GET /api/v1/financial-accounts`: lista cuentas y tarjetas activas.
- `POST /api/v1/financial-accounts`: crea una cuenta financiera.
- `PATCH /api/v1/financial-accounts/{account_id}`: actualiza datos de cuenta.
- `POST /api/v1/financial-accounts/{account_id}/snapshots`: guarda un saldo observado.
- `GET /api/v1/financial-accounts/{account_id}/balance`: estima saldo actual desde snapshot y movimientos.
- `GET /api/v1/investment-accounts`: lista cuentas de inversion activas.
- `POST /api/v1/investment-accounts`: crea una cuenta de inversion.
- `PATCH /api/v1/investment-accounts/{account_id}`: actualiza datos de inversion.
- `POST /api/v1/investment-accounts/{account_id}/movements`: registra aporte o rescate manual.

`investment` y `disinvestment` se guardan como transacciones de balance: afectan cuentas e inversiones, pero no se suman a gasto ni ingreso mensual.

## Endpoints de Fase 9

- `GET /api/v1/rules`: lista reglas de clasificacion.
- `POST /api/v1/rules`: crea una regla con categoria, tipo, cuenta o inversion como destino.
- `PATCH /api/v1/rules/{rule_id}`: actualiza o pausa una regla.
- `DELETE /api/v1/rules/{rule_id}`: elimina una regla.
- `POST /api/v1/rules/test`: prueba reglas contra texto, correo guardado o transaccion.
- `GET /api/v1/rules/feedback`: lista correcciones guardadas.
- `GET /api/v1/rules/suggestions`: sugiere reglas desde correcciones repetidas.

Las reglas se aplican sobre candidatos importados y guardan confianza, metodo y razon explicable.
