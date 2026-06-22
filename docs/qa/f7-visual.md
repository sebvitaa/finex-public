# F7 Visual QA

Fecha: 2026-06-05

## Alcance

Se revisaron las vistas principales de FinEx en navegador local:

- Dashboard
- Movimientos
- Obligaciones
- Importar
- Correos
- Cuentas
- Configuracion

## Viewports

- Desktop: `1280x720`
- Movil: `390x844`

## Verificacion

- Cada vista mantiene su heading principal visible.
- Desktop queda sin overflow horizontal global.
- Movil queda sin overflow horizontal global en todas las vistas revisadas.
- La tabla de movimientos conserva overflow interno controlado dentro de su contenedor scrollable.
- Obligaciones mantiene resumen, balance por persona y modales de detalle sin ensanchar la pagina.

## Correcciones aplicadas

- `DashboardPage`: se agrego `min-w-0` a los hijos de la grilla de ultimos movimientos y paneles auxiliares para evitar que una columna empuje el layout fuera del viewport.
- `AppShell`: se agrego `overflow-x-hidden` al contenedor raiz para impedir que la navegacion horizontal movil ensanche el documento.

## Nota de captura

El adaptador de captura del navegador embebido hizo timeout al intentar `Page.captureScreenshot`. La QA se cerro con inspeccion real de DOM, headings y mediciones de `scrollWidth`/`bodyScrollWidth` por vista.
