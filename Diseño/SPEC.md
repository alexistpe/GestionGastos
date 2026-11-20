# SPEC — Sistema de Gestión de Gastos
> Documento de especificación técnica completa para el agente de desarrollo.
> Versión: 1.0 — 2026-11-20

---

## 1. Visión General

Bot de Telegram que corre íntegramente en un Moto G7 bajo Termux. Recibe comprobantes de pago (PDF/foto), los procesa con la API de Gemini, y almacena los datos en SQLite local. Permite análisis financieros personales, alertas automáticas y gestión de etiquetas, todo desde el chat de Telegram.

**Restricciones de diseño:**
- Ligero: sin frameworks pesados, sin servidores externos propios.
- Portable: todo en el Moto G7, respaldo en GitHub.
- CPU mínima: Long Polling, sin procesamiento continuo.
- Límite API: 60–100 requests/mes a Gemini.

---

## 2. Stack Tecnológico (DECIDIDO)

| Componente | Decisión | Razón |
|---|---|---|
| Lenguaje | Python 3.11+ | SDK maduro para Gemini y PTB; nativo en Termux |
| Bot Telegram | `python-telegram-bot` v21 (PTB) | `ConversationHandler` resuelve el DTE sin FSM manual |
| Conexión Telegram | Long Polling | Sin servidor expuesto, cero configuración de red |
| OCR / Extracción | Google Gemini 1.5 Flash (`google-generativeai`) | Límite suficiente, multimodal PDF+imagen |
| Base de datos | SQLite vía `sqlite3` (stdlib) | Cero dependencias, local, liviana |
| Estado conversacional | Híbrido: memoria RAM + respaldo en SQLite | Sobrevive reinicios del Moto G7 |
| Ejecución en Android | Termux + `nohup` | Background persistente, sin root |
| Respaldo | Git + GitHub via cron en Termux | Automatizado, sin intervención manual |

---

## 3. Schema SQLite (Modelo Físico)

El agente debe generar el archivo `schema.sql` con las siguientes tablas. Los tipos siguen las convenciones de SQLite.

### 3.1 Tabla `etiquetas`
```sql
CREATE TABLE etiquetas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    es_rutina   INTEGER NOT NULL DEFAULT 0  -- 0=false, 1=true (booleano SQLite)
);
```
**Notas:** `nombre` en minúsculas, sin tildes, sin espacios (ej: `gym`, `nafta`). `es_rutina` define si pertenece al gasto mensual fijo.

### 3.2 Tabla `comprobantes`
```sql
CREATE TABLE comprobantes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT    NOT NULL,          -- ISO 8601: 'YYYY-MM-DD'
    destino         TEXT,                      -- Nombre/descripción del comprobante
    monto           REAL    NOT NULL,          -- Siempre positivo
    balance         TEXT    NOT NULL           -- 'INGRESO' | 'EGRESO'
        CHECK(balance IN ('INGRESO', 'EGRESO')),
    id_etiqueta     INTEGER NOT NULL,
    FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id)
);
```
**Notas:** `balance` como TEXT con CHECK constraint. `monto` siempre positivo; el signo semántico lo da `balance`. `fecha` como TEXT ISO 8601 para ordenamiento lexicográfico correcto.

### 3.3 Tabla `avisos`
```sql
CREATE TABLE avisos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT    NOT NULL           -- 'ETIQUETA' | 'MONTO_TOTAL'
        CHECK(tipo IN ('ETIQUETA', 'MONTO_TOTAL')),
    id_etiqueta     INTEGER,                   -- NULL si tipo='MONTO_TOTAL'
    monto_limite    REAL    NOT NULL,
    activo          INTEGER NOT NULL DEFAULT 1, -- 0=false, 1=true
    FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id)
);
```

### 3.4 Tabla `sesion_estado` (Estado conversacional híbrido)
```sql
CREATE TABLE sesion_estado (
    chat_id         INTEGER PRIMARY KEY,       -- ID del chat de Telegram
    estado_actual   TEXT    NOT NULL,          -- Nombre del estado PTB
    contexto_json   TEXT,                      -- JSON con datos temporales del flujo
    id_comprobante  INTEGER,                   -- Comprobante en edición (si aplica)
    timestamp       TEXT    NOT NULL           -- ISO 8601 del último update
);
```
**Propósito:** Al arrancar el bot, verifica si hay estados pendientes. Si el `timestamp` tiene más de 1 hora, limpia el estado gracefully y notifica al usuario.

### 3.5 Datos semilla obligatorios
El agente debe generar un `seed.sql` con las etiquetas de la rutina predefinidas:
```sql
INSERT INTO etiquetas (nombre, es_rutina) VALUES
    ('gym',      1),
    ('peluqueria', 1),
    ('nafta',    1),
    ('seguro',   1),
    ('claro',    1),
    ('cuota',    0),  -- Ingreso mensual de referencia
    ('ahorro',   0);  -- Etiqueta especial para manejo de ahorros
```

---

## 4. Flujo Principal — Diagrama de Secuencia

### 4.1 Registro de Comprobante (flujo feliz)

```
Usuario          Telegram API       Bot (Termux/Moto G7)      Gemini API        SQLite
   |                  |                     |                       |               |
   |-- Envía foto --->|                     |                       |               |
   |                  |-- Long Polling ---->|                       |               |
   |                  |                     |-- "Procesando..." --->|               |
   |<-- ACK inmediato (mensaje bot) --------|                       |               |
   |                  |                     |-- POST imagen ------->|               |
   |                  |                     |   (async, ~2-5 seg)   |               |
   |                  |                     |<-- JSON {fecha,       |               |
   |                  |                     |    destino, monto} ---|               |
   |                  |                     |                                       |
   |                  |                     |-- Si etiqueta en mensaje: direct ---->|
   |                  |                     |-- Si no: muestra botones etiquetas    |
   |<-- Botones inline (seleccionar etiq.) -|                       |               |
   |-- Selecciona etiqueta --------------->|                        |               |
   |<-- Mensaje confirmación (monto/etiq.) -|                       |               |
   |-- [Confirma | Editar monto | Editar etiq.] ------------------->|               |
   |                  |                     |-- INSERT comprobante ----------------->|
   |                  |                     |-- evaluarAvisos() ------------------->|
   |<-- "✅ Guardado" -------------------- |                       |               |
```

### 4.2 Manejo de timeout / error Gemini

- **Mensaje ACK inmediato:** Al recibir la imagen, antes de llamar a Gemini, el bot envía: *"📎 Comprobante recibido. Procesando..."*
- **Timeout Gemini (>15 seg):** El bot envía: *"⚠️ El servicio tardó más de lo esperado. Intentando de nuevo..."* y reintenta 1 vez.
- **Fallo definitivo:** *"❌ No se pudo procesar el comprobante. Podés reenviarlo o ingresarlo manualmente con: `- [monto] [etiqueta]`"*
- **Comportamiento:** El flujo es **síncrono con ACK temprano**. No hay cola de mensajes; el bot bloquea el handler pero el ACK ya llegó al usuario.

---

## 5. Estructura de Módulos

```
gastos/
├── main.py               # Entry point: inicializa bot PTB y registra handlers
├── config.py             # Variables de entorno y constantes
├── database/
│   ├── schema.sql        # DDL completo
│   ├── seed.sql          # Datos iniciales (etiquetas rutina)
│   └── db.py             # Capa de acceso: funciones CRUD puras
├── modules/
│   ├── gestion.py        # Clase Gestion: orquestadora principal
│   ├── traductor.py      # Wrapper API Gemini: imagen → JSON
│   ├── resumen.py        # Clase Resumen: cálculos de análisis
│   └── aviso.py          # Clase Aviso: evaluación y disparo de alertas
├── handlers/
│   ├── comprobante_handler.py  # ConversationHandler registro de comprobantes
│   ├── balance_handler.py      # Handler para mensajes de balance (texto puro)
│   ├── analisis_handler.py     # Handler para comandos de análisis
│   ├── alerta_handler.py       # Handler para configurar alertas
│   └── etiqueta_handler.py     # Handler para gestión de etiquetas
├── utils/
│   └── parsers.py        # Parsing de sintaxis de comandos
├── requirements.txt
└── .env                  # NO versionar. Contiene tokens.
```

---

## 6. Variables de Entorno

Archivo `.env` en el root del proyecto:

```env
TELEGRAM_BOT_TOKEN=...        # Token del bot de @BotFather
TELEGRAM_CHAT_ID=...          # Chat ID del usuario autorizado (único usuario)
GEMINI_API_KEY=...            # API Key de Google AI Studio
DB_PATH=/data/data/com.termux/files/home/gastos/data/gastos.db
```

**Seguridad:** El bot verifica que cada mensaje entrante provenga del `TELEGRAM_CHAT_ID` configurado. Rechaza cualquier otro remitente con log silencioso (sin respuesta al remitente no autorizado).

---

## 7. Estado Conversacional — Implementación Híbrida

### 7.1 Estados del ConversationHandler (mapeados del DTE)

```python
# Estados PTB (enteros constantes)
COMPROBANTE_RECIBIDO      = 0
CONSULTANDO_SERVICIO      = 1
ESPERANDO_SELEC_ETIQUETA  = 2
ESPERANDO_CONFIRMACION    = 3
CORRIGIENDO_MONTO         = 4
CORRIGIENDO_ETIQUETA      = 5
```

### 7.2 Estrategia híbrida RAM + SQLite

```
Al recibir mensaje:
  → Escribir estado en RAM (dict: {chat_id: estado})
  → Escribir estado en sesion_estado (SQLite) — async, no bloquea

Al arrancar el bot (main.py):
  → Leer sesion_estado de SQLite
  → Si timestamp > 1 hora: DELETE + notificar usuario "sesión anterior expirada"
  → Si timestamp < 1 hora: restaurar estado en RAM del ConversationHandler
```

PTB v21 permite inyectar un `PicklePersistence` custom. El agente evaluará si usar ese mecanismo o una solución manual con `sesion_estado`, priorizando SQLite sobre pickle por coherencia del proyecto.

---

## 8. Sintaxis de Comandos

| Acción | Sintaxis | Ejemplo |
|---|---|---|
| Balance (ingreso) | `+ [etiqueta]` | `+ cuota` |
| Balance (egreso) | `- [etiqueta]` | `- nafta` |
| Análisis mensual | `analisis` | `analisis` |
| Análisis por rango | `analisis DD.MM.AA` | `analisis 01.11.26` |
| Alerta por etiqueta | `alerta [etiqueta] [monto]` | `alerta nafta 15000` |
| Alerta monto total | `alerta [monto]` | `alerta 100000` |
| Nueva etiqueta | `etiqueta [nombre]` | `etiqueta supermercado` |
| Eliminar etiqueta | `eliminar etiqueta [nombre]` | `eliminar etiqueta supermercado` |

**Nota para el agente:** El parser debe ser tolerante a mayúsculas y espacios extra. Usar regex con `re.IGNORECASE`.

---

## 9. Reglas de Negocio Críticas

### 9.1 Definición de "mes actual"
No es el mes calendario. Es el período desde **el último registro con etiqueta `cuota` (INGRESO)** hasta hoy. Todas las consultas de análisis mensual y evaluación de avisos usan esta ventana temporal.

### 9.2 Lógica de ahorro (etiqueta especial `ahorro`)
- `- ahorro` = egreso hacia cuenta de ahorros → **suma** al total ahorrado
- `+ ahorro` = extracción desde ahorros → **resta** al total ahorrado
- El ahorro impacta en el balance neto pero tiene su propia métrica de "cuánto se ahorró"

### 9.3 Evaluación de avisos (se dispara post-registro)
Evaluar siempre después de cada INSERT en `comprobantes`:
1. Balance neto del mes negativo → alerta general
2. Rutina completada (todos los `esRutina=1` tienen al menos un registro en el mes) → alerta rutina
3. Suma de egreso por etiqueta supera `monto_limite` del aviso → alerta etiqueta
4. Extracciones de ahorro (`+ ahorro`) superan el ingreso neto del mes → alerta ahorro

### 9.4 Inline keyboards (botones de Telegram)
- En selección de etiqueta: botones inline con todas las etiquetas existentes, paginados si hay más de 8.
- En confirmación de comprobante: botones `✅ Confirmar`, `✏️ Monto`, `🏷️ Etiqueta`.
- **Restricción:** Los botones inline solo se usan si el mensaje de respuesta puede almacenarse. PTB garantiza esto en el flujo síncrono con `callback_query_handler`.

---

## 10. Despliegue en Termux — Moto G7

### 10.1 Estructura de directorios en el dispositivo
```
/data/data/com.termux/files/home/
└── gastos/
    ├── [código fuente]      # Clonado desde GitHub
    ├── data/
    │   └── gastos.db        # Base de datos SQLite (NO versionar)
    ├── logs/
    │   └── bot.log          # Rotación manual o logrotate
    └── .env                 # NO versionar
```

### 10.2 Ejecución en background
```bash
# Iniciar bot en background persistente
nohup python main.py >> logs/bot.log 2>&1 &
echo $! > bot.pid

# Verificar que está corriendo
cat bot.pid | xargs ps -p

# Detener
cat bot.pid | xargs kill
```

### 10.3 Respaldo automático a GitHub (cron en Termux)
```bash
# crontab -e en Termux
# Respaldo diario a las 3:00 AM
0 3 * * * cd /data/data/com.termux/files/home/gastos && git add -A && git commit -m "backup: $(date +%Y-%m-%d)" && git push origin main
```
**Nota:** `.gitignore` debe excluir `data/gastos.db`, `.env` y `logs/`. El respaldo versiona solo el código fuente.

### 10.4 Dependencias Termux
```bash
pkg install python git
pip install python-telegram-bot google-generativeai python-dotenv
```

---

## 11. Lo que el Agente Decide (autonomía explícita)

Estas decisiones se delegan al agente con la condición de que documente la razón elegida:

1. **Schema SQLite completo:** El agente puede agregar índices, triggers o constraints adicionales que mejoren performance o integridad, siempre respetando la estructura base del punto 3.
2. **Mecanismo de persistencia de estado:** Evalúa `PicklePersistence` de PTB vs tabla `sesion_estado` manual. Elige el que mejor integre con el resto del código.
3. **Diagrama de Despliegue final:** El agente produce el diagrama de despliegue como artefacto de documentación post-implementación.
4. **Logging:** Define el formato y nivel de logs. Recomendado: `logging` stdlib con rotación por tamaño.
5. **Manejo de errores de la DB:** Decide si usar transacciones explícitas o confiar en el autocommit de `sqlite3`.

---

## 12. Restricciones que el Agente NO puede cambiar

- Stack: Python + PTB + Gemini 1.5 Flash + SQLite. No agregar dependencias externas sin justificación explícita.
- Balance es siempre `INGRESO` o `EGRESO` (no numérico con signo).
- Una etiqueta por comprobante (regla de negocio del MODP).
- El bot solo responde al `TELEGRAM_CHAT_ID` configurado.
- El estado conversacional debe sobrevivir a reinicios del proceso.
- Los mensajes de error al usuario deben ser claros y en español.

---

## 13. Proceso de Inicio con el Agente

Antes de que el agente arranque a codear, debe:

1. Leer este SPEC completo y los documentos de diseño (MODP, CDU, DTE, Diseño.md).
2. Generar un **informe de decisiones de arquitectura** con todas las elecciones del punto 11, antes de escribir una línea de código.
3. Presentar el informe para aprobación.
4. Solo tras aprobación: comenzar por `schema.sql` → `db.py` → `traductor.py` → `gestion.py` → handlers → `main.py`.

---

*Fin del SPEC. Fecha de generación: 2026-11-20.*
