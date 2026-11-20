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
- Gestión de etiquetas y de alertas.
- Persistencia del estado de la conversación ante reinicios del proceso.
- Acceso restringido a un único chat autorizado.

## Arquitectura y stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Bot de Telegram | `python-telegram-bot` v21 (long polling) |
| Extracción de comprobantes | Google Gemini (`google-genai`), modelo configurable |
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
    │   └── comandos.md
    ├── database/             # schema.sql, seed.sql y capa de acceso
    ├── modules/              # lógica de negocio (a partir de Instancia 2)
    ├── handlers/             # handlers de Telegram (a partir de Instancia 4)
    ├── utils/                # parsers y utilidades
    ├── tests/                # pruebas automatizadas
    ├── config.py             # configuración y variables de entorno
    ├── main.py               # punto de entrada (a partir de Instancia 4)
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

Para el balance general sigue siendo un movimiento más; para la métrica “cuánto se ahorró” se invierte el signo, porque transferir dinero a ahorro no es un gasto que desaparezca.

### 5. Alertas y deduplicación

Después de cada alta o modificación se evalúan cuatro situaciones:

1. balance neto del período negativo;
2. rutina mensual completada;
3. gasto de una etiqueta por encima de su límite;
4. extracciones de ahorro superiores al ingreso neto del período.

Cada alerta se emite una sola vez por período gracias a `avisos_disparados`. Al cambiar el período (nueva `cuota`) las alertas vuelven a habilitarse.

### 6. Estado conversacional

El bot mantiene el estado en memoria y lo respalda en `sesion_estado`. Al arrancar, restaura los estados vigentes y descarta los que tienen más de una hora, notificando al usuario. Así una confirmación pendiente no se pierde si el teléfono reinicia el proceso.

### 7. Seguridad

- El bot solo responde al `TELEGRAM_CHAT_ID` configurado; ignora silenciosamente a cualquier otro remitente.
- Los tokens viven en `.env`, que no se versiona.
- La base de datos y los logs tampoco se versionan.
- El respaldo a GitHub incluye únicamente el código y la documentación.

### 8. Análisis

- **Rápido (`analisis`):** totales del período, comparación con la rutina (gastado y pendiente), gastos no esenciales por etiqueta y balance. Los gastos no esenciales excluyen la rutina y la etiqueta `ahorro`, que se informa por separado.
- **Por rango (`analisis DD.MM.AA [DD.MM.AA]`):** total ingresado, total gastado, neto, gastos ordenados por etiqueta, ingresos detallados y cálculo de ahorro.

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
| Alerta de gasto total | `alerta monto` |
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

Para ejecutar el bot (a partir de la Instancia 4):

```bash
python main.py
```

## Despliegue en Termux (Moto G7)

```bash
pkg install python git
cd ~/gastos
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # completar tokens reales
nohup python main.py >> logs/bot.log 2>&1 &
echo $! > bot.pid
```

El respaldo diario se configura con cron:

```cron
0 3 * * * cd ~/gastos && git add -A && git commit -m "backup: $(date +%Y-%m-%d)" && git push origin main
```

## Estado del proyecto

El desarrollo se organiza en **instancias** con puntos de control. La bitácora completa está en [`Desarrollo/documentacion.md`](Desarrollo/documentacion.md).

| Instancia | Alcance | Estado |
|---|---|---|
| 0 | Planificación, decisiones y guía de comandos | Aprobada |
| 1 | Núcleo de datos: schema, acceso y parsers | Aprobada |
| 2 | Motor de negocio: resumen, avisos y gestión | Aprobada |
| 3 | Extracción con Gemini | Pendiente de OK (96 pruebas, incluida validación real) |
| 4 | Interfaz Telegram completa | Pendiente |
| 5 | Despliegue y operación | Pendiente |

## Documentación

- [`Desarrollo/documentacion.md`](Desarrollo/documentacion.md): bitácora por instancias, decisiones y conflictos.
- [`Desarrollo/docs/decisiones-arquitectura.md`](Desarrollo/docs/decisiones-arquitectura.md): detalle técnico de las decisiones.
- [`Desarrollo/docs/comandos.md`](Desarrollo/docs/comandos.md): guía de uso del bot.
- [`Diseño/`](Diseño/): documentos de diseño, MODP, CDU, DTE y SPEC original.
