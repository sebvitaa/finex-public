# Frontend

Aplicacion React + TypeScript + Vite de FinEx.

## Comandos

```bash
pnpm dev
pnpm build
pnpm test:frontend
pnpm lint
```

La pantalla inicial es un dashboard financiero oscuro con datos demo y estado de conexion al backend local.

## Fase 3

La vista `Transacciones` agrega el registro manual completo:

- Crear gastos, ingresos y pagos recibidos.
- Crear categorias y personas desde el mismo flujo.
- Desglosar compras mixtas por categoria.
- Registrar cuentas por cobrar y pagos parciales.
- Filtrar y editar movimientos contra la API local.

## Fase 4

El dashboard inicial ahora consume `/api/v1/dashboard/overview`:

- Muestra gasto, ingresos, balance, proyeccion, cuentas por cobrar y movimientos por revisar.
- Grafica gasto e ingreso diario desde la base local.
- Usa desgloses para ranking de categorias de gasto.
- Separa categorias de ingreso, comercios, deudas, supermercados sin desglose y posibles suscripciones.

## Fase 5

La vista `Importar` agrega importacion controlada:

- Pegar texto de correo y previsualizar una transaccion candidata.
- Cargar correos demo desde el backend.
- Revisar monto, comercio, asunto, categoria sugerida y confianza.
- Cambiar tipo entre gasto, ingreso, transferencia recibida, suscripcion o pago de cuenta por cobrar.
- Desglosar compras mixtas antes de confirmar.
- Confirmar para crear la transaccion o descartar el correo sin guardar movimiento.

## Fase 6

La vista `Importar` ahora conecta Gmail real:

- Muestra estado de credenciales, conexion y ruta local usada, sin exponer rutas absolutas en la UI.
- Abre OAuth con `Conectar Gmail`.
- Ejecuta `Actualizar Gmail` para traer mensajes recientes desde `INBOX`.
- Hace una sincronizacion automatica al abrir si Gmail ya esta conectado.
- Mantiene polling local configurable entre 5 y 15 minutos o mas.
- Agrega solo candidatos financieros a la bandeja y reporta irrelevantes/duplicados.

## Fase 8

La UI agrega saldos e inversiones:

- `Ajustes` permite crear cuentas/tarjetas, cargar snapshots de saldo y crear cuentas de inversion.
- `Transacciones` permite asignar cuenta financiera y cuenta de inversion en registros manuales.
- `Importar` muestra la cuenta detectada desde Gmail y permite corregirla antes de confirmar.
- El dashboard muestra saldos estimados, delta mensual, aportes, rescates y movimientos sin cuenta.

## Fase 9

La UI agrega reglas corregibles:

- `Ajustes` permite crear reglas por texto, remitente, asunto, comercio, banco o ultimos 4 digitos.
- Las reglas pueden sugerir categoria, tipo de movimiento, cuenta financiera o cuenta de inversion.
- La misma vista permite probar reglas con texto libre antes de guardarlas.
- Las correcciones repetidas aparecen como sugerencias que se pueden convertir en reglas.
