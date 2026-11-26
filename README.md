# GestionGastos — bot personal de gastos por Telegram

## Presentación

**GestionGastos** es un bot de Telegram para registrar, consultar y analizar los gastos e ingresos de una persona. Recibe comprobantes de pago en PDF o foto (Mercado Pago, Lemon Cash, transferencias, tickets), extrae los datos automáticamente con inteligencia artificial y los guarda en una base de datos SQLite local.

El objetivo es tener un registro contable simple y consultable sin planillas manuales: se envía el comprobante por Telegram, se confirma la información y el bot se encarga del resto. Todo el sistema está pensado para funcionar en un **Moto G7 con Termux**, sin servidores propios, sin costos de infraestructura y con un consumo mínimo de CPU.

## Utilidad

- **Registro rápido:** una foto o un PDF alcanza para cargar un gasto o un ingreso.
- **Datos confiables:** la IA extrae fecha, monto, destino y balance; el usuario confirma o corrige antes de guardar.
- **Análisis personal:** informe del mes actual o de un rango de fechas con totales, gastos por etiqueta, ingresos y ahorro.
- **Control de la rutina:** compara los gastos fijos mensuales (gym, peluquería, nafta, seguro, claro) contra lo presupuestado.
- **Alertas automáticas:** avisa cuando el balance se vuelve negativo, cuando una etiqueta supera su límite, cuando se completa la rutina o cuando se extrae demasiado de los ahorros.
- **Autonomía:** funciona en el teléfono, con respaldo periódico del código en GitHub.
- **Privacidad:** los datos financieros quedan en la base local del dispositivo; solo se envían comprobantes a la API de Gemini para su transcripción.

## Funcionalidades

- Recepción de comprobantes en imagen o PDF desde Telegram.
- Extracción automática de `fecha`, `destino`, `monto` y `balance` (`INGRESO` / `EGRESO`).
- Etiquetado de cada comprobante, con selector interactivo cuando no se indica la etiqueta.
- Confirmación y edición antes de guardar.
- Edición y borrado de comprobantes ya guardados.
- Balances manuales por texto (`+ etiqueta monto` / `- etiqueta monto`).
- Análisis por mes actual o por rango de fechas.
- Reporte de ahorro con saldo inicial, depositado, extraído, neto y acumulado.
- Gestión de etiquetas y alertas, incluyendo eliminación de alertas.
- Persistencia del estado de la conversación ante reinicios del proceso.
- Acceso restringido a un único chat autorizado.

## Arquitectura y stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Bot de Telegram | `python-telegram-bot` v21 (long polling) |
| Extracción de comprobantes | Google Gemini (REST API vía `httpx`), modelo configurable |
| Base de datos | SQLite (stdlib `sqlite3`) |
| Estado conversacional | Memoria + tabla `sesion_estado` (persistencia propia) |
| Ejecución en Android | Termux + `nohup` |
| Respaldo | Git + GitHub mediante cron |

No se usan frameworks web ni servidores externos. El bot consulta Telegram por *long polling*, por lo que no expone puertos ni necesita configuración de red.

## Estructura del repositorio

```
gastosBot/
├── README.md                 # Presentación, utilidad y lógica
├── Diseño/                   # Documentos de diseño y diagramas (MODP, CDU, DTE)
└── Desarrollo/               # Código y documentación de desarrollo
    ├── documentacion.md      # Bitácora general por instancias
    ├── docs/
    │   ├── decisiones-arquitectura.md
    │   ├── comandos.md
    │   └── despliegue.md
    ├── database/             # schema.sql, seed.sql y capa de acceso
    ├── modules/              # lógica de negocio, Gemini y persistencia
    ├── handlers/             # handlers de Telegram y flujos interactivos
    ├── utils/                # parsers, formato y teclados
    ├── scripts/              # instalación, arranque, parada y respaldo
    ├── tests/                # pruebas automatizadas
    ├── config.py             # configuración y variables de entorno
    ├── main.py               # punto de entrada
    └── requirements*.txt
```

## Lógica utilizada

### 1. Ciclo de vida de un comprobante

```
Usuario envía foto/PDF (con o sin etiqueta)
        │
        ▼
Bot confirma recepción y descarga el archivo
        │
        ▼
Gemini extrae {fecha, destino, monto, balance, moneda}
        │
        ▼
Validación y normalización en Python
        │
        ├── Si vino etiqueta en el mensaje: se usa
        └── Si no: el bot muestra un selector de etiquetas
        │
        ▼
Pantalla de confirmación con todos los campos editables
        │
        ▼
Confirmar → INSERT en SQLite → evaluación de alertas
```

La extracción es automática. Si el comprobante no permite deducir el balance con claridad, la confirmación lo marca y el usuario elige `Ingreso` o `Egreso`. La edición antes de guardar modifica el contexto en memoria; el registro se inserta recién al confirmar.

### 2. Modelo de datos

- `etiquetas`: categorías de los movimientos. `es_rutina` indica si pertenece a los gastos fijos mensuales.
- `comprobantes`: cada movimiento, con `fecha` ISO 8601, `destino`, `monto` positivo, `balance` (`INGRESO` / `EGRESO`) y una única etiqueta.
- `avisos`: límites por etiqueta o para el gasto total.
- `avisos_disparados`: registro de alertas ya emitidas por período, para no repetirlas.
- `sesion_estado`: estado de la conversación y datos temporales, para sobrevivir reinicios.

El detalle completo está en `Desarrollo/docs/decisiones-arquitectura.md` y en `Desarrollo/database/schema.sql`.

### 3. Período mensual

El “mes actual” no es el mes calendario: comienza en la **fecha del último ingreso con etiqueta `cuota`** y llega hasta hoy. Si todavía no existe una cuota registrada, se usa el primer día del mes calendario. Toda evaluación de alertas y el análisis rápido usan esta ventana.

### 4. Lógica de ahorro

La etiqueta `ahorro` es especial:

- `- ahorro` (egreso hacia la cuenta de ahorro) **suma** al total ahorrado.
- `+ ahorro` (extracción desde los ahorros) **resta** al total ahorrado.

Se muestran dos balances:

- **Neto del período:** depositado - extraído desde la última `cuota`.
- **Acumulado histórico:** saldo inicial configurado + todos los movimientos de ahorro registrados.

El saldo inicial se fija con `ahorro inicial monto` y no cuenta como depósito del período. El comando `ahorro` muestra el saldo inicial, depositado, extraído, neto y saldo al cierre. Para el balance general, los movimientos de ahorro siguen siendo ingresos/egresos normales.

### 5. Alertas y deduplicación

Después de cada alta o modificación se evalúan estas situaciones:

1. balance neto del período negativo;
2. rutina mensual completada;
3. gasto de una etiqueta por encima de su límite;
4. gasto total del período por encima del límite;
5. extracciones de ahorro superiores al ingreso neto;
6. **balance de ahorro del período negativo** (extraído > depositado).

La alerta `AHORRO_NEGATIVO` tiene prioridad sobre la alerta genérica `AHORRO` para no duplicar avisos de ahorro. `alerta ahorro monto` limita **extracciones** de ahorro. Cada alerta se emite una sola vez por período gracias a `avisos_disparados`; al cambiar el período (nueva `cuota`) se vuelven a habilitar. Las alertas se pueden borrar con `eliminar alerta` o `eliminar alerta ID`.

### 6. Estado conversacional

El bot mantiene el estado en memoria y lo respalda en `sesion_estado`. Al arrancar, restaura los estados vigentes y descarta los que tienen más de una hora, notificando al usuario. Así una confirmación pendiente no se pierde si el teléfono reinicia el proceso.

### 7. Seguridad

- El bot solo responde al `TELEGRAM_CHAT_ID` configurado; ignora silenciosamente a cualquier otro remitente.
- Los tokens viven en `.env`, que no se versiona.
- La base de datos y los logs tampoco se versionan.
- El respaldo a GitHub incluye únicamente el código y la documentación.

### 8. Análisis

- **Rápido (`analisis`):** totales del período, comparación con la rutina (gastado y pendiente), gastos no esenciales por etiqueta, balance y desglose de ahorro (saldo inicial, depositado, extraído, neto y saldo al cierre). Los gastos no esenciales excluyen la rutina y la etiqueta `ahorro`.
- **Por rango (`analisis DD.MM.AA [DD.MM.AA]`):** total ingresado, total gastado, neto, gastos ordenados por etiqueta, ingresos detallados y el mismo desglose de ahorro, con saldo acumulado al cierre del rango.
- **Ahorro (`ahorro`):** reporte rápido del período actual con el desglose de ahorro.

## Comandos

La guía completa, con efectos, casos de uso y ejemplos, está en [`Desarrollo/docs/comandos.md`](Desarrollo/docs/comandos.md). Resumen:

| Acción | Sintaxis |
|---|---|
| Registrar comprobante | Enviar foto/PDF, opcionalmente con la etiqueta |
| Ingreso manual | `+ etiqueta monto` |
| Egreso manual | `- etiqueta monto` |
| Análisis del mes | `analisis` |
| Análisis por fecha | `analisis DD.MM.AA [DD.MM.AA]` |
| Alerta por etiqueta | `alerta etiqueta monto` |
| Alerta de extracciones de ahorro | `alerta ahorro monto` |
| Alerta de gasto total | `alerta monto` |
| Eliminar alerta | `eliminar alerta` o `eliminar alerta ID` |
| Reporte de ahorro | `ahorro` |
| Saldo inicial de ahorro | `ahorro inicial monto` |
| Crear etiqueta | `etiqueta nombre` |
| Eliminar etiqueta | `eliminar etiqueta nombre` |
| Editar comprobante | `editar` o `editar ID` |
| Borrar comprobante | `borrar` o `borrar ID` |
| Ayuda | `/ayuda` o `/comandos` |

Todos los comandos aceptan también su forma con barra (`/analisis`, `/editar 42`, etc.).

## Puesta en marcha (desarrollo)

```bash
cd Desarrollo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # completar tokens reales
python -m pytest -q
```

Para ejecutar el bot:

```bash
./scripts/start.sh          # background con PID y logs
./scripts/status.sh
./scripts/stop.sh
```

También se puede ejecutar en primer plano con `python main.py`.

## Despliegue en Termux (Moto G7)

```bash
pkg install python git
git clone git@github.com:alexistpe/GestionGastos.git ~/gastos
cd ~/gastos/Desarrollo
bash scripts/install_termux.sh
nano .env                   # tokens, chat ID, Gemini y DB_PATH
./scripts/start.sh
./scripts/status.sh
```

El respaldo diario se configura con cron y el script incluido:

```cron
0 3 * * * /data/data/com.termux/files/home/gastos/Desarrollo/scripts/backup.sh >> /data/data/com.termux/files/home/gastos/Desarrollo/logs/backup.log 2>&1
```

La guía completa de instalación, operación, respaldo, restauración y diagnóstico está en [`Desarrollo/docs/despliegue.md`](Desarrollo/docs/despliegue.md).

## Estado del proyecto

El desarrollo se organiza en **instancias** con puntos de control. La bitácora completa está en [`Desarrollo/documentacion.md`](Desarrollo/documentacion.md).

| Instancia | Alcance | Estado |
|---|---|---|
| 0 | Planificación, decisiones y guía de comandos | Aprobada |
| 1 | Núcleo de datos: schema, acceso y parsers | Aprobada |
| 2 | Motor de negocio: resumen, avisos y gestión | Aprobada |
| 3 | Extracción con Gemini | Aprobada (validación real con 2 comprobantes) |
| 4 | Interfaz Telegram completa | Aprobada (arranque validado) |
| 5 | Despliegue y operación | Aprobada (prueba real desde Telegram satisfactoria) |
| 6 | Despliegue en dispositivo y transferencia | Aprobada (bot instalado y funcionando en Android/Termux) |
| 7 | Ahorro avanzado, saldo inicial y borrado de alertas | Pendiente de OK |

El bot ya está instalado y funcionando en el dispositivo Android. La suite actual tiene **143 pruebas mock + 2 de integración real** con Gemini. La guía de actualización y respaldo está en [`Desarrollo/docs/despliegue.md`](Desarrollo/docs/despliegue.md).

## Documentación

- [`Desarrollo/documentacion.md`](Desarrollo/documentacion.md): bitácora por instancias, decisiones y conflictos.
- [`Desarrollo/docs/decisiones-arquitectura.md`](Desarrollo/docs/decisiones-arquitectura.md): detalle técnico de las decisiones.
- [`Desarrollo/docs/comandos.md`](Desarrollo/docs/comandos.md): guía de uso del bot.
- [`Desarrollo/docs/despliegue.md`](Desarrollo/docs/despliegue.md): instalación, operación y respaldo en Termux.
- [`Diseño/`](Diseño/): documentos de diseño, MODP, CDU, DTE y SPEC original.
