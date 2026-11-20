# Bitácora de desarrollo — GestionGastos

- **Proyecto:** GestionGastos (bot personal de gastos por Telegram)
- **Repositorio:** `git@github.com:alexistpe/GestionGastos.git`
- **Rama:** `main`
- **Código:** `Desarrollo/`
- **Inicio:** 2026-11-20
- **Estado general:** Instancia 6 en curso; pendiente de prueba en el dispositivo (C6)

Este documento es la bitácora general del proyecto. Registra cada cambio, decisión, conflicto y proceso relevante. Se organiza por **instancias** y cada instancia cierra con un **checkpoint** que requiere aprobación explícita antes de continuar.

---

## Convenciones

- **Instancia:** bloque de trabajo con un alcance funcional verificable. Reemplaza el término “época”.
- **Checkpoint:** punto de control al final de una instancia. Incluye un mini informe y el estado `APROBADA`, `OBSERVADA` o `BLOQUEADA`.
- **IDs de bitácora:** `I{n}-{secuencia}` (por ejemplo, `I1-003`).
- **IDs de decisión:** `DEC-{n}`.
- **IDs de conflicto:** `CONF-{n}`.
- **Tipos de entrada:** `agregado`, `cambio`, `corrección`, `decisión`, `conflicto`, `proceso`, `verificación`.
- **Actualización:** una entrada por cambio lógico, con archivos afectados y verificación ejecutada. Nunca se registran tokens, claves ni datos sensibles.

---

## Índice de instancias

| Instancia | Alcance | Checkpoint | Estado |
|---|---|---|---|
| 0 | Planificación y arquitectura | C0 | APROBADA |
| 1 | Núcleo de datos: schema, acceso y parsers | C1 | APROBADA |
| 2 | Motor de negocio: resumen, avisos y gestión | C2 | APROBADA |
| 3 | Extracción con Gemini | C3 | APROBADA |
| 4 | Interfaz Telegram completa | C4 | APROBADA |
| 5 | Despliegue y operación | C5 | APROBADA |
| 6 | Despliegue en dispositivo y transferencia | C6 | PENDIENTE DE PRUEBA EN DISPOSITIVO |

---

## Política de cambios y consulta

**Se consulta antes de ejecutar** cuando el cambio:

- Modifica el stack, el schema base, las reglas de negocio o la sintaxis de comandos.
- Cambia el modelo de despliegue, la seguridad o el alcance funcional.
- Requiere una dependencia externa no aprobada.
- Es un problema que no se puede resolver de forma autónoma o afecta funciones macro.

**No se consulta** (queda a criterio del agente y solo se registra):

- Refactors internos que preservan el comportamiento.
- Organización de archivos, nombres, tests y correcciones menores.
- Decisiones de estructura básica que no alteran el uso ni el resultado del software.

Toda consulta se registra como `CONF-{n}` con las opciones planteadas y la decisión final.

---

## Registro de decisiones

| ID | Decisión | Motivo |
|---|---|---|
| DEC-001 | Python 3.11+, PTB v21, SQLite, long polling | Stack definido en el SPEC; portabilidad y bajo consumo |
| DEC-002 | Schema base del SPEC + `avisos_disparados` + `sesion_estado.nombre_conversacion` | Deduplicar alertas y soportar persistencia de PTB sin romper las tablas base |
| DEC-003 | Persistencia conversacional con `BasePersistence` respaldado por SQLite | Coherencia con el proyecto y trazabilidad por SQL; se prioriza SQLite sobre pickle |
| DEC-004 | `google-genai` + modelo configurable (`GEMINI_MODEL`, por defecto `gemini-3.1-flash-lite`) | El SDK `google-generativeai` está deprecado; el modelo debe poder cambiarse sin tocar código y funcionar con la cuenta disponible |
| DEC-005 | Gemini extrae `fecha`, `destino`, `monto`, `balance` y `moneda`; `balance` puede ser nulo si es ambiguo | El usuario envía el comprobante y el sistema interpreta automáticamente; la confirmación resuelve la ambigüedad |
| DEC-006 | Logging con `RotatingFileHandler` (1 MB × 3) y nivel configurable | Diagnóstico liviano y sin crecimiento indefinido en el teléfono |
| DEC-007 | Transacciones explícitas con `with conn:` y `PRAGMA foreign_keys=ON` por conexión | Integridad de datos y rollback consistente |
| DEC-008 | Edición antes y después de guardar, con campos monto, etiqueta, fecha, balance y destino | El usuario puede corregir errores sin borrar y volver a cargar |
| DEC-009 | Comandos `editar`, `editar ID`, `borrar` y `borrar ID`, con confirmación inline para borrar | Cubre la corrección y la eliminación de comprobantes guardados |
| DEC-010 | Deduplicación de alertas por período mediante `avisos_disparados` | Evita repetir la misma alerta en cada comprobante |
| DEC-011 | Guía canónica en `docs/comandos.md`, `/ayuda`, alias con barra y menú de Telegram | Descubribilidad y claridad para el usuario |
| DEC-012 | Zona horaria `America/Argentina/Buenos_Aires`; fechas `YYYY-MM-DD` | Consistencia en el ordenamiento y en el cálculo del período |
| DEC-013 | Período actual desde el último ingreso `cuota`; si no existe, primer día del mes | Regla de negocio del SPEC y del diseño |
| DEC-014 | Parseo de montos tolerante al formato argentino (`15.000,50`) | Los comprobantes y los mensajes usan separadores locales |
| DEC-015 | La nomenclatura del proceso pasa de “épocas” a “instancias” | Pedido explícito del usuario |
| DEC-016 | Push a GitHub en cada cambio significativo, con mensaje descriptivo | Pedido explícito del usuario |
| DEC-017 | El bot acepta comandos con y sin barra (`analisis` y `/analisis`) | Comodidad de uso en Telegram |
| DEC-018 | Una sola conversación multi-paso activa por chat | Simplifica el estado y evita condiciones de carrera; los comandos stateless siguen disponibles |
| DEC-019 | Los gastos no esenciales excluyen la etiqueta `ahorro` | El ahorro es una transferencia entre cuentas, no consumo; se analiza en su propia sección |
| DEC-020 | El total gastado y la alerta de monto total incluyen todos los `EGRESO`, incluido `ahorro` | Coherencia con la definición de “gastos = registros con `-`”; el ahorro se informa aparte |
| DEC-021 | El pendiente de rutina se calcula solo para etiquetas con presupuesto (alerta `ETIQUETA`) | No existe un presupuesto por etiqueta en el schema; sin alerta se informa “sin presupuesto definido” |
| DEC-022 | Gemini devuelve JSON con `fecha`, `destino`, `monto`, `balance` y `moneda`; Python valida y normaliza | Evita confiar ciegamente en el modelo y permite completar datos faltantes en la confirmación |
| DEC-023 | Timeout de 15 s con un reintento y errores en español | Cumple el SPEC y evita esperas indefinidas en el teléfono |
| DEC-024 | La prueba real con Gemini es un test de integración opcional que requiere `GEMINI_API_KEY` y un comprobante | No se fuerzan credenciales ni se envían datos personales sin autorización |
| DEC-025 | Los comprobantes reales de prueba y el `.env` no se versionan; `tests/fixtures/*` está ignorado | Proteger datos financieros personales y claves del repositorio |
| DEC-026 | Persistencia PTB: `estado_actual` guarda el estado y `contexto_json` guarda `context.user_data` (incluido el borrador) | PTB 21 guarda solo el estado de la conversación; el contexto de trabajo vive en `user_data` |
| DEC-027 | Una sola conversación multi-paso por chat; los entry points consultan `sesion_estado` y rechazan solapamientos | Evita que registro y edición se pisen en una tabla con una fila por chat |
| DEC-028 | Logging con redacción de secretos y `httpx`/`httpcore` en `WARNING` | Evita que la URL de Telegram con el token quede en los logs |
| DEC-029 | Crear y setear un event loop antes de `run_polling` | Python 3.14 ya no crea un loop implícito; el workaround también funciona en 3.11 |
| DEC-030 | Instalar `python-telegram-bot[job-queue]` | Habilita `conversation_timeout` para expirar conversaciones en memoria |
| DEC-031 | `scripts/start.sh` redirige stdout/stderr a `logs/nohup.log`; la app sigue usando `logs/bot.log` con rotación | Evita doble escritura y conflictos con el `RotatingFileHandler` |
| DEC-032 | `scripts/backup.sh` usa la raíz real de Git, evita commits vacíos y crea una copia local consistente de SQLite | Respaldo confiable del código y de la base sin versionar datos sensibles |
| DEC-033 | `scripts/install_termux.sh` automatiza Termux; la guía completa vive en `docs/despliegue.md` | Reduce errores de instalación y deja operación reproducible |
| DEC-034 | La exposición local del token en un equipo personal se considera aceptable siempre que no se versione | Decisión del usuario; se mantienen redacción de logs y `.gitignore` |
| DEC-035 | El respaldo sube solo código y documentación; la base se copia localmente en `data/backups/` | Proteger datos financieros y mantener una copia recuperable |
| DEC-036 | El proyecto es portable entre dispositivos Android con Termux; solo cambian rutas y dependencias del entorno | No hay código específico del Moto G7 |
| DEC-037 | Transferencia recomendada por `git clone`; alternativa `scripts/empaquetar.sh` con `.tar.gz` sin secretos, base, venv ni fixtures | Evita copiar archivos innecesarios o sensibles |
| DEC-038 | No copiar `.venv` entre dispositivos; recrearlo con `scripts/install_termux.sh` | Los entornos virtuales no son portables entre Linux y Android |

---

## Registro de conflictos

| ID | Fecha | Descripción | Impacto | Resolución | Estado |
|---|---|---|---|---|---|
| CONF-001 | 2026-11-20 | El SPEC menciona `google-generativeai` y Gemini 1.5 Flash, pero el SDK está deprecado y el modelo puede no estar disponible | Medio | Se actualiza a `google-genai` y modelo configurable (DEC-004) | Resuelto |
| CONF-002 | 2026-11-20 | El SPEC no define deduplicación de alertas y, evaluando en cada INSERT, la misma alerta se repetiría | Medio | Se agrega `avisos_disparados` (DEC-010) | Resuelto |
| CONF-003 | 2026-11-20 | El SPEC solo permitía editar antes de confirmar; el usuario necesita corregir comprobantes ya guardados | Medio | Se agrega flujo de edición y borrado (DEC-008, DEC-009) | Resuelto |
| CONF-004 | 2026-11-20 | `pytest-asyncio` emitió una advertencia por el alcance del event loop | Bajo | Se agregó `pytest.ini` con `asyncio_default_fixture_loop_scope = function` | Resuelto |
| CONF-005 | 2026-11-20 | El entorno no tiene `GEMINI_API_KEY` ni un comprobante de prueba disponible | Medio | Se implementó un test de integración opcional; el usuario proveyó la clave, dos comprobantes y la validación real se ejecutó | Resuelto |
| CONF-006 | 2026-11-20 | `gemini-2.5-flash` ya no está disponible para cuentas nuevas (404) | Medio | Se actualizó el modelo configurable y se validó con la lista de modelos de la cuenta (DEC-004) | Resuelto |
| CONF-007 | 2026-11-20 | `gemini-3.8-flash` y `gemini-3.7-flash` devolvieron 503 por alta demanda durante la validación | Medio | Se adoptó `gemini-3.1-flash-lite` como default por disponibilidad; los dos comprobantes reales se procesaron correctamente | Resuelto |
| CONF-008 | 2026-11-20 | PTB 21.11 con Python 3.14 falló en `run_polling` por falta de event loop implícito | Medio | Se crea y setea un event loop antes de `run_polling` (DEC-029) | Resuelto |
| CONF-009 | 2026-11-20 | PTB emitió una advertencia por `per_message=False` con `CallbackQueryHandler` | Bajo | Se silencia la advertencia conocida en `main.py` y `pytest.ini` | Resuelto |
| CONF-010 | 2026-11-20 | `httpx` registró en `logs/bot.log` la URL de Telegram con el token durante el arranque | Alto | Se eliminó el log, se agregó redacción de secretos y se bajó `httpx`/`httpcore` a `WARNING`. El usuario aceptó la circulación local del token por ser un equipo personal; no se subió al repositorio | Mitigado y aceptado |
| CONF-011 | 2026-11-20 | El `.env` de Diseño apunta `DB_PATH` a Termux; el bot local intentaba usar esa ruta | Bajo | La copia local `Desarrollo/.env` usa `DB_PATH=./data/gastos.db`; el original queda para Termux | Resuelto |
| CONF-012 | 2026-11-20 | Sin `job-queue`, `conversation_timeout` no tenía efecto | Bajo | Se instaló `python-telegram-bot[job-queue]` y se actualizó `requirements.txt` | Resuelto |
| CONF-013 | 2026-11-20 | El SPEC redirige `nohup` a `logs/bot.log`, pero la app ya usa un `RotatingFileHandler` sobre ese archivo | Bajo | `start.sh` redirige la salida cruda a `logs/nohup.log` y deja `bot.log` para la app (DEC-031) | Resuelto |
| CONF-014 | 2026-11-20 | El cron original falla si no hay cambios para commitear | Bajo | `backup.sh` verifica `git diff --cached --quiet` y termina sin error (DEC-032) | Resuelto |
| CONF-015 | 2026-11-20 | El directorio de código (`Desarrollo`) no coincide con la raíz del repositorio | Bajo | `backup.sh` usa `git rev-parse --show-toplevel` para respaldar todo el repo (DEC-032) | Resuelto |
| CONF-016 | 2026-11-20 | La versión de Termux de Play Store está desactualizada y rompe paquetes | Medio | La guía recomienda instalar Termux desde F-Droid o GitHub | Resuelto |
| CONF-017 | 2026-11-20 | El `.venv` de Linux no es portable a Android | Medio | Se excluye de la transferencia y se recrea con `install_termux.sh` (DEC-038) | Resuelto |
| CONF-018 | 2026-11-20 | El `.env` original tiene una ruta absoluta de Termux que puede no coincidir con el nuevo clon | Bajo | La guía indica usar `DB_PATH=./data/gastos.db` o ajustar la ruta | Resuelto |

---

# Instancia 0 — Planificación y arquitectura

## Objetivo y alcance

Definir la arquitectura, el modelo de datos, la guía de comandos y el proceso de trabajo por instancias antes de escribir código.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I0-001 | 2026-11-20 13:30 | proceso | Lectura del SPEC y del documento de diseño (MODP, CDU, DTE) | `Diseño/SPEC.md`, `Diseño/PLANTILLAS/Diseño.md` | Revisión manual | OK |
| I0-002 | 2026-11-20 13:40 | decisión | Definición de ubicación, stack, alcance y entorno de desarrollo | — | Confirmación del usuario | OK |
| I0-003 | 2026-11-20 13:50 | decisión | Actualización de Gemini a `google-genai` y modelo configurable | — | Confirmación del usuario | OK |
| I0-004 | 2026-11-20 14:00 | proceso | Incorporación de bitácora por instancias, checkpoints y política de consulta | — | Confirmación del usuario | OK |
| I0-005 | 2026-11-20 14:10 | decisión | Extracción automática de balance; edición de comprobantes; guía de comandos | — | Confirmación del usuario | OK |
| I0-006 | 2026-11-20 14:15 | decisión | Deduplicación de alertas, edición completa con borrado y alias con barra | — | Confirmación del usuario | OK |
| I0-007 | 2026-11-20 14:35 | proceso | Cambio de nomenclatura a “instancias”; push a GitHub en cambios significativos; README con presentación y lógica | — | Confirmación del usuario | OK |
| I0-008 | 2026-11-20 14:42 | agregado | Creación de la documentación inicial y la guía de comandos | `README.md`, `documentacion.md`, `docs/decisiones-arquitectura.md`, `docs/comandos.md` | Revisión de contenido | OK |

## Mini informe de checkpoint C0

- **Objetivo:** cerrar la planificación y dejar aprobadas las decisiones estructurales.
- **Construido:** informe de arquitectura, bitácora, política de cambios y guía de comandos.
- **Verificación:** revisión de consistencia entre SPEC, diseño y aclaraciones del usuario.
- **Conflictos:** SDK de Gemini deprecado, deduplicación de alertas y edición posterior al guardado; todos resueltos y registrados.
- **Pendientes:** implementación del núcleo de datos (Instancia 1).
- **Estado:** APROBADA por el usuario el 2026-11-20, con las condiciones de nomenclatura, push y README incorporadas.

---

# Instancia 1 — Núcleo de datos

## Objetivo y alcance

Construir la base del proyecto: configuración, schema SQLite, datos semilla, capa de acceso a datos y parsers de comandos. Todo debe funcionar sin Telegram ni Gemini.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I1-001 | 2026-11-20 14:40 | agregado | Estructura de directorios y andamiaje del proyecto | `Desarrollo/{database,utils,tests,docs,data,logs}` | `ls` | OK |
| I1-002 | 2026-11-20 14:54 | agregado | Configuración de entorno y dependencias | `.gitignore`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `config.py` | Importación de `config` y revisión manual | OK |
| I1-003 | 2026-11-20 14:55 | agregado | Schema, seed y capa de acceso a SQLite | `database/schema.sql`, `database/seed.sql`, `database/db.py` | `pytest tests/test_db.py` | OK (20 pruebas) |
| I1-004 | 2026-11-20 14:58 | agregado | Parsers de comandos, montos, fechas y etiquetas | `utils/parsers.py` | `pytest tests/test_parsers.py` | OK (33 pruebas) |
| I1-005 | 2026-11-20 15:00 | agregado | Pruebas automatizadas de DB y parsers | `tests/conftest.py`, `tests/test_db.py`, `tests/test_parsers.py` | `pytest -q` | 53 pruebas aprobadas |
| I1-006 | 2026-11-20 15:02 | corrección | Configuración explícita de `pytest-asyncio` para eliminar la advertencia de loop scope | `pytest.ini` | `pytest -q` | 53 pruebas aprobadas, sin advertencias |
| I1-007 | 2026-11-20 15:05 | verificación | Compilación de todos los módulos | `Desarrollo/` | `python -m compileall -q . -x '/\\.venv/'` | `compileall OK` |

## Verificación ejecutada

Entorno local: Python 3.14.8, SQLite 3.54.0, pytest 9.2.0. Se creó un `venv` local y se instalaron solo las dependencias de prueba (`pytest`, `pytest-asyncio`); las dependencias de ejecución (PTB, `google-genai`, `python-dotenv`) se instalarán en las instancias 3 y 4 para no bloquear el trabajo offline.

```text
$ .venv/bin/python -m pytest -q
.....................................................                    [100%]
53 passed in 0.15s

$ .venv/bin/python -m compileall -q . -x '/\.venv/'
compileall OK
```

Cobertura funcional verificada:

- `init_db` es idempotente y crea las cinco tablas, índices y datos semilla.
- CRUD completo de etiquetas y comprobantes.
- Restricción de borrado de etiquetas en uso y cascada de avisos.
- Upsert de avisos por etiqueta y por monto total, con validaciones.
- Registro y consulta de alertas disparadas por período.
- Persistencia, actualización, borrado y expiración del estado conversacional.
- Parseo de montos argentinos e internacionales, fechas, etiquetas, balances, análisis, alertas, edición y borrado.
- Tolerancia a mayúsculas, tildes, espacios extra, comandos con barra y menciones `@bot`.

## Conflictos de la instancia

| ID | Descripción | Resolución | Estado |
|---|---|---|---|
| CONF-004 | La primera ejecución de `pytest` mostró una advertencia de `pytest-asyncio` por el alcance del event loop | Se agregó `pytest.ini` con `asyncio_default_fixture_loop_scope = function` | Resuelto |

## Observaciones y riesgos

- El desarrollo local corre sobre Python 3.14.8, mientras que Termux suele tener Python 3.11/3.12. El código evita sintaxis exclusiva de versiones nuevas y se revalidará en el dispositivo durante la Instancia 5.
- Las dependencias de ejecución todavía no están instaladas en el `venv` local; esto es intencional para mantener la Instancia 1 offline. Se instalarán y probarán en las instancias 3 y 4.
- La base local `data/gastos.db` y los logs están excluidos por `.gitignore`; no se versionan.

## Archivos entregados

- `.gitignore`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `config.py`.
- `database/__init__.py`, `database/schema.sql`, `database/seed.sql`, `database/db.py`.
- `utils/__init__.py`, `utils/parsers.py`.
- `tests/conftest.py`, `tests/test_db.py`, `tests/test_parsers.py`.
- `documentacion.md`, `docs/decisiones-arquitectura.md`, `docs/comandos.md`, `../README.md`.

## Mini informe de checkpoint C1

- **Objetivo:** dejar operativo el núcleo de datos y la interpretación de comandos, sin dependencias de red.
- **Construido:** schema SQLite con integridad y deduplicación, datos semilla, capa de acceso completa, parsers tolerantes y 53 pruebas automatizadas.
- **Verificación:** `pytest -q` → 53 aprobadas; `compileall` → OK. Sin advertencias tras `pytest.ini`.
- **Conflictos:** advertencia de `pytest-asyncio` resuelta (CONF-004). Sin conflictos abiertos.
- **Pendientes/riesgos:** instalar dependencias de ejecución en instancias posteriores; revalidar en Python 3.11 de Termux.
- **Estado:** PENDIENTE DE APROBACIÓN. No se avanza a la Instancia 2 hasta recibir el OK del usuario.

---

# Instancia 2 — Motor de negocio

## Objetivo y alcance

Implementar los cálculos de análisis, la evaluación y deduplicación de alertas y la orquestación de la lógica de negocio sin Telegram ni Gemini.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I2-001 | 2026-11-20 15:20 | agregado | Formato de montos y fechas | `utils/formato.py` | `pytest tests/test_formato.py` | OK |
| I2-002 | 2026-11-20 15:24 | agregado | Cálculos de totales, ahorro, rutina y gastos no esenciales | `modules/resumen.py` | `pytest tests/test_resumen.py` | OK (5 pruebas) |
| I2-003 | 2026-11-20 15:28 | agregado | Evaluación de alertas internas y configuradas con deduplicación | `modules/aviso.py` | `pytest tests/test_aviso.py` | OK (9 pruebas) |
| I2-004 | 2026-11-20 15:32 | agregado | Orquestador de comprobantes, análisis, alertas y etiquetas | `modules/gestion.py` | `pytest tests/test_gestion.py` | OK (8 pruebas) |
| I2-005 | 2026-11-20 15:35 | agregado | Pruebas de la instancia | `tests/test_formato.py`, `tests/test_resumen.py`, `tests/test_aviso.py`, `tests/test_gestion.py` | `pytest -q` | 77 pruebas aprobadas |
| I2-006 | 2026-11-20 15:37 | verificación | Compilación de módulos y pruebas | `modules/`, `utils/`, `tests/` | `compileall` | OK |
| I2-007 | 2026-11-20 15:40 | decisión | Exclusión de `ahorro` de gastos no esenciales; total gastado incluye todo `EGRESO`; pendiente de rutina solo con presupuesto | `documentacion.md`, `docs/decisiones-arquitectura.md` | Revisión de consistencia | OK |

## Verificación ejecutada

```text
$ .venv/bin/python -m pytest -q
........................................................................ [ 93%]
.....                                                                    [100%]
77 passed in 0.31s

$ .venv/bin/python -m compileall -q . -x '/\.venv/'
compileall OK
```

Cobertura funcional verificada:

- Totales de ingresos, egresos y neto.
- Cálculo de ahorro con `+ ahorro` y `- ahorro`.
- Agrupación de gastos por etiqueta de mayor a menor.
- Ingresos detallados y ordenados.
- Rutina: gasto, presupuesto, pendiente y completitud.
- Gastos no esenciales, excluyendo rutina y ahorro.
- Período mensual desde la última `cuota` y análisis por rango cerrado.
- Alertas de balance negativo, rutina completa, etiqueta, monto total y extracciones de ahorro.
- Deduplicación por período y reactivación al cambiar de período.
- Validaciones de comprobantes, etiquetas y alertas en `Gestion`.
- Formato argentino de montos y fechas.

## Decisiones y observaciones

- Los gastos no esenciales excluyen `ahorro` porque es una transferencia, no consumo (DEC-019).
- El total gastado y la alerta de monto total incluyen todos los `EGRESO`, incluido `ahorro` (DEC-020).
- El pendiente de rutina solo suma etiquetas con presupuesto; el resto se informa “sin presupuesto definido” (DEC-021).
- La evaluación de alertas usa el resumen del período actual y se dispara una sola vez por período.
- La presentación definitiva de los textos de análisis se ajustará en la Instancia 4, cuando se integre Telegram.

## Archivos entregados

- `utils/formato.py`.
- `modules/__init__.py`, `modules/resumen.py`, `modules/aviso.py`, `modules/gestion.py`.
- `tests/test_formato.py`, `tests/test_resumen.py`, `tests/test_aviso.py`, `tests/test_gestion.py`.

## Mini informe de checkpoint C2

- **Objetivo:** dejar funcionando el motor de negocio completo y verificable, sin dependencias de red.
- **Construido:** cálculos de análisis, rutina, ahorro y gastos no esenciales; evaluación y deduplicación de cinco tipos de alerta; orquestador de comprobantes, etiquetas y alertas; 24 pruebas nuevas.
- **Verificación:** `pytest -q` → 77 aprobadas; `compileall` → OK.
- **Conflictos:** sin conflictos nuevos. Se documentaron tres decisiones de negocio (DEC-019, DEC-020, DEC-021).
- **Pendientes/riesgos:** los textos finales de los informes se ajustan en la Instancia 4; las dependencias de ejecución siguen pendientes de instalar.
- **Estado:** PENDIENTE DE APROBACIÓN. No se avanza a la Instancia 3 hasta recibir el OK del usuario.

---

# Instancia 3 — Extracción con Gemini

## Objetivo y alcance

Implementar la extracción automática de datos de comprobantes (imagen o PDF) con `google-genai`, incluyendo validación, normalización, timeout, reintento e integración con `Gestion`.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I3-001 | 2026-11-20 15:50 | proceso | Instalación de `google-genai` y `python-dotenv` en el venv local | `.venv/` (no versionado) | `google-genai 3.6.1` importado | OK |
| I3-002 | 2026-11-20 15:55 | agregado | Wrapper de Gemini con esquema JSON, validación, timeout y reintento | `modules/traductor.py` | `pytest tests/test_traductor.py` | OK (15 pruebas) |
| I3-003 | 2026-11-20 15:58 | agregado | Integración de traducción en el orquestador | `modules/gestion.py` | `pytest tests/test_gestion.py` | OK |
| I3-004 | 2026-11-20 16:00 | agregado | Test de integración real opcional, protegido por credenciales y archivo | `tests/test_traductor_integracion.py` | `pytest -q` | Creado; omitido inicialmente sin credenciales |
| I3-005 | 2026-11-20 16:02 | verificación | Suite completa y compilación (antes de la validación real) | `modules/`, `tests/` | `pytest -q` y `compileall` | 92 aprobadas, 1 omitida; `compileall OK` |
| I3-006 | 2026-11-20 16:05 | agregado | Registro de modelo, MIME y resultado en el logger del traductor | `modules/traductor.py` | `pytest tests/test_traductor.py` | OK |
| I3-007 | 2026-11-20 16:15 | verificación | Validación real con 2 comprobantes locales y credenciales del `.env` | `tests/fixtures/`, `tests/test_traductor_integracion.py` | `pytest tests/test_traductor_integracion.py` | 2 aprobadas |
| I3-008 | 2026-11-20 16:20 | corrección | `gemini-2.5-flash` devolvió 404 y `gemini-3.8/3.7-flash` 503; se adoptó `gemini-3.1-flash-lite` y se agregó reintento para errores transitorios | `config.py`, `.env.example`, `modules/traductor.py`, `tests/test_traductor.py` | `pytest -q` | 94 pruebas mock aprobadas |
| I3-009 | 2026-11-20 16:23 | proceso | Protección de fixtures reales y `.env` en `.gitignore` | `.gitignore`, `tests/fixtures/.gitkeep` | `git check-ignore` | Claves y comprobantes ignorados |
| I3-010 | 2026-11-20 16:25 | verificación | Suite completa con validación real y compilación | `modules/`, `tests/` | `pytest -q` y `compileall` | 96 aprobadas; `compileall OK` |

## Verificación ejecutada

```text
$ .venv/bin/python -m pytest -q
........................................................................ [ 75%]
......................ss                                                 [100%]
94 passed, 2 skipped in 4.85s

$ RUN_GEMINI_INTEGRATION=1 .venv/bin/python -m pytest -q tests/test_traductor_integracion.py
..                                                                       [100%]
2 passed in 10.14s

$ .venv/bin/python -m compileall -q . -x '/\.venv/'
compileall OK
```

La integración real queda desactivada por defecto para no consumir la cuota de Gemini en cada corrida; se habilita con `RUN_GEMINI_INTEGRATION=1`.

Cobertura funcional verificada:

- Construcción del request a Gemini con modelo configurable, `response_mime_type="application/json"` y `response_schema`.
- Envío del archivo como `Part.from_bytes` con MIME validado (`jpeg`, `png`, `webp`, `pdf`).
- Parseo de JSON, incluyendo respuestas con cercas de código.
- Normalización de fecha, monto, balance y moneda.
- Detección de campos faltantes con advertencias para la confirmación.
- Reintento ante timeout y errores transitorios (429/5xx) con backoff.
- Propagación de errores de configuración (falta de API key).
- Integración `Gestion.iniciar_traduccion()` con inyección de un traductor falso.
- **Validación real:** dos comprobantes PNG procesados por `gemini-3.1-flash-lite`; monto, fecha y balance detectados en ambos.

## Conflictos y observaciones

- **CONF-005 (resuelto):** el usuario proveyó la clave y dos comprobantes; la validación real se ejecutó con éxito.
- **CONF-006 (resuelto):** `gemini-2.5-flash` ya no está disponible para cuentas nuevas (404); el modelo es configurable.
- **CONF-007 (resuelto):** `gemini-3.8-flash` y `gemini-3.7-flash` devolvieron 503 por alta demanda; se adoptó `gemini-3.1-flash-lite` como default y se agregó reintento para 5xx/429.
- Los comprobantes reales y el `.env` están ignorados por `.gitignore`; no se versionaron ni se expusieron claves.
- El módulo registra modelo, MIME y resultado en el logger; la configuración de handlers y rotación queda para la Instancia 4.

## Archivos entregados

- `modules/traductor.py`.
- `modules/gestion.py` (integración de traducción).
- `tests/test_traductor.py`.
- `tests/test_traductor_integracion.py` (se activa con credenciales y fixtures locales).
- `tests/fixtures/.gitkeep` (los comprobantes reales no se versionan).
- `.gitignore`, `.env.example` y `config.py` actualizados.

## Mini informe de checkpoint C3

- **Objetivo:** dejar funcionando la extracción automática de comprobantes con Gemini, validada con comprobantes reales.
- **Construido:** wrapper de Gemini, esquema de salida, validación/normalización, timeout/reintento, integración con `Gestion`, 17 pruebas mock nuevas + 2 de integración real y protección de fixtures/claves.
- **Verificación:** `pytest -q` → 94 aprobadas, 2 omitidas; `RUN_GEMINI_INTEGRATION=1 pytest tests/test_traductor_integracion.py` → 2 aprobadas; `compileall` → OK.
- **Conflictos:** CONF-005, CONF-006 y CONF-007 resueltos. Sin conflictos abiertos.
- **Pendientes/riesgos:** la disponibilidad del modelo puede variar; `GEMINI_MODEL` permite cambiarlo. La cuota mensual se monitoreará en la capa de bot.
- **Estado:** PENDIENTE DE APROBACIÓN. No se avanza a la Instancia 4 hasta recibir el OK del usuario.

---

# Instancia 4 — Interfaz Telegram completa

## Objetivo y alcance

Implementar la interfaz completa del bot: persistencia del estado, registro de comprobantes con confirmación y edición, edición/borrado posterior, comandos de balance, análisis, alertas, etiquetas, ayuda, autenticación y arranque en polling.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I4-001 | 2026-11-20 17:05 | agregado | Listado de estados y persistencia PTB sobre SQLite | `database/db.py`, `modules/persistencia.py` | `pytest tests/test_persistencia.py` | OK |
| I4-002 | 2026-11-20 17:10 | agregado | Teclados inline, formatos y guía de ayuda | `utils/telegram.py` | `pytest tests/test_ui.py` | OK |
| I4-003 | 2026-11-20 17:20 | agregado | Flujo de comprobantes con extracción, selector, confirmación y edición previa | `handlers/comprobante_handler.py` | `pytest -q` | OK |
| I4-004 | 2026-11-20 17:30 | agregado | Edición y borrado de comprobantes guardados | `handlers/edicion_handler.py` | `pytest -q` | OK |
| I4-005 | 2026-11-20 17:40 | agregado | Handlers de balance, análisis, alertas, etiquetas y sistema | `handlers/balance_handler.py`, `handlers/analisis_handler.py`, `handlers/alerta_handler.py`, `handlers/etiqueta_handler.py`, `handlers/sistema_handler.py` | `pytest tests/test_handlers.py` | OK |
| I4-006 | 2026-11-20 17:50 | agregado | Arranque, autenticación, logging, menú y registro de handlers | `main.py` | `pytest tests/test_main.py` | OK |
| I4-007 | 2026-11-20 17:55 | agregado | Pruebas de persistencia, UI, handlers y wiring | `tests/test_persistencia.py`, `tests/test_ui.py`, `tests/test_handlers.py`, `tests/test_main.py` | `pytest -q` | 125 aprobadas, 2 omitidas |
| I4-008 | 2026-11-20 18:00 | corrección | Instalación de `job-queue` para timeouts de conversación | `requirements.txt` | `APScheduler 3.11.3`; `aplicacion.job_queue` disponible | OK |
| I4-009 | 2026-11-20 18:05 | verificación | Validación de token y arranque real con polling | `main.py` | `getMe`, `setMyCommands`, `deleteWebhook`; `Application started` | OK, con incidente CONF-010 |
| I4-010 | 2026-11-20 18:10 | corrección | Redacción de secretos en logs, `httpx/httpcore` en WARNING y eliminación del log expuesto | `main.py`, `tests/test_main.py` | `pytest` y revisión del log | OK |
| I4-011 | 2026-11-20 18:15 | corrección | Ajuste del `.env` local a `DB_PATH=./data/gastos.db` | `Desarrollo/.env` (ignorado) | Arranque local | OK |
| I4-012 | 2026-11-20 18:20 | verificación | Suite completa y compilación | `handlers/`, `utils/`, `main.py`, `tests/` | `pytest -q` y `compileall` | 125 aprobadas, 2 omitidas; `compileall OK` |

## Verificación ejecutada

```text
$ .venv/bin/python -m pytest -q
........................................................................ [ 56%]
........................................ss.............                  [100%]
125 passed, 2 skipped in 5.02s

$ .venv/bin/python -m compileall -q . -x '/\.venv/'
compileall OK

$ getMe
Token OK; bot: GastosG7Bot

$ timeout 12s .venv/bin/python main.py
getMe → 200 OK
setMyCommands → 200 OK
deleteWebhook → 200 OK
Application started
```

Cobertura funcional verificada:

- Persistencia de estado y `user_data` en SQLite, incluyendo borradores y limpieza al terminar.
- Conversaciones con timeout de una hora y `job_queue` activo.
- Flujo de comprobante: descarga, extracción, selector de etiqueta, confirmación, edición previa y borrador persistente.
- Edición posterior de monto, etiqueta, fecha, balance y destino; borrado con confirmación.
- Balances manuales, análisis mensual y por rango, alertas y etiquetas.
- Autenticación por `TELEGRAM_CHAT_ID` y silencio para remitentes no autorizados.
- Redacción de secretos en logs y bloqueo de logs INFO de `httpx`.
- Menú de comandos de Telegram y guía `/ayuda`.

## Conflictos y observaciones

- **CONF-008 (resuelto):** Python 3.14 + PTB 21.11 requería crear y setear un event loop antes de `run_polling`.
- **CONF-009 (resuelto):** advertencia conocida de PTB por `per_message=False`; se silenció en `main.py` y `pytest.ini`.
- **CONF-010 (mitigado y aceptado):** durante la prueba de arranque, `httpx` registró la URL de Telegram con el token en `logs/bot.log`. Se eliminó el log, se agregó un filtro de redacción y se bajó `httpx`/`httpcore` a `WARNING`. El usuario aceptó la circulación local del token por ser un equipo personal, siempre que no se suba al repositorio.
- **CONF-011 (resuelto):** la copia local del `.env` apuntaba a la base de Termux; se ajustó a `./data/gastos.db`. El original de Diseño queda para el dispositivo.
- **CONF-012 (resuelto):** sin `job-queue`, el timeout de conversación no tenía efecto; se instaló el extra y se actualizó `requirements.txt`.
- La interacción completa desde un cliente de Telegram (envío real de `/start`, fotos y comandos) queda para la validación del usuario; no se automatizó por requerir una sesión de usuario.

## Archivos entregados

- `database/db.py` (listado de estados).
- `modules/persistencia.py`.
- `utils/telegram.py`.
- `handlers/comprobante_handler.py`, `handlers/edicion_handler.py`, `handlers/balance_handler.py`, `handlers/analisis_handler.py`, `handlers/alerta_handler.py`, `handlers/etiqueta_handler.py`, `handlers/sistema_handler.py`.
- `main.py`.
- `tests/test_persistencia.py`, `tests/test_ui.py`, `tests/test_handlers.py`, `tests/test_main.py`.
- `requirements.txt` con `python-telegram-bot[job-queue]`.

## Mini informe de checkpoint C4

- **Objetivo:** dejar el bot ejecutable desde Telegram con todos los comandos y flujos definidos.
- **Construido:** persistencia SQLite para PTB, interfaz completa de comprobantes, edición/borrado, comandos stateless, autenticación, logging seguro y arranque en polling.
- **Verificación:** `pytest -q` → 125 aprobadas, 2 omitidas; `compileall` → OK; token validado con `getMe`; arranque real con `Application started`.
- **Conflictos:** CONF-008, CONF-009, CONF-011 y CONF-012 resueltos. CONF-010 mitigado y aceptado por el usuario como entorno personal.
- **Pendientes/riesgos:** probar el flujo completo desde el cliente de Telegram; revalidar en Python 3.11 de Termux; cuidar la cuota de Gemini.
- **Estado:** APROBADA. El usuario pidió continuar con la Instancia 5.

---

# Instancia 5 — Despliegue y operación

## Objetivo y alcance

Dejar el proyecto listo para operar en Termux: scripts de instalación, arranque, parada, estado y respaldo; documentación de despliegue, restauración y diagnóstico; actualización del README.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I5-001 | 2026-11-20 18:30 | agregado | Scripts de arranque, parada y estado con PID y logs separados | `scripts/start.sh`, `scripts/stop.sh`, `scripts/status.sh` | `bash -n`; ejecución sin bot | OK |
| I5-002 | 2026-11-20 18:35 | agregado | Respaldo con copia local consistente de SQLite y push solo de código | `scripts/backup.sh` | `bash -n`; revisión de rutas | OK |
| I5-003 | 2026-11-20 18:40 | agregado | Instalador para Termux (Python, Git, venv, dependencias y `.env`) | `scripts/install_termux.sh` | `bash -n` | OK |
| I5-004 | 2026-11-20 18:45 | agregado | Guía de despliegue con diagrama, operación, cron, restauración y diagnóstico | `docs/despliegue.md` | Revisión de contenido | OK |
| I5-005 | 2026-11-20 18:50 | cambio | README actualizado con scripts, estructura y estado | `README.md` | Revisión de contenido | OK |
| I5-006 | 2026-11-20 18:55 | verificación | Suite completa, compilación y scripts | `scripts/`, `tests/`, `main.py` | `pytest -q`, `compileall`, `bash -n` | 125 aprobadas, 2 omitidas; OK |

## Verificación ejecutada

```text
$ bash -n scripts/*.sh
bash -n OK

$ ./scripts/status.sh
Bot detenido.
Base: 60K

$ ./scripts/stop.sh
No hay bot.pid; el bot no está corriendo (o no se inició con scripts/start.sh).

$ .venv/bin/python -m pytest -q
125 passed, 2 skipped in 5.01s

$ .venv/bin/python -m compileall -q . -x '/\.venv/'
compileall OK
```

No se ejecutó `start.sh` en esta instancia para no volver a usar el token en la terminal; el arranque real ya se validó en la Instancia 4 con `getMe`, `setMyCommands`, `deleteWebhook` y `Application started`.

## Conflictos y observaciones

- **CONF-013 (resuelto):** `nohup` y el `RotatingFileHandler` apuntaban al mismo archivo; la salida cruda va a `logs/nohup.log`.
- **CONF-014 (resuelto):** el respaldo ahora tolera la ausencia de cambios y no falla en cron.
- **CONF-015 (resuelto):** el respaldo se ejecuta desde la raíz real del repositorio, no solo desde `Desarrollo`.
- El respaldo de la base es local (`data/backups/`) y no se versiona; GitHub recibe solo código y documentación.
- El bot está listo para probar desde Telegram; la validación de la interacción real queda a cargo del usuario.
- La instalación en Termux y el cron real deben verificarse en el dispositivo durante el despliegue final.

## Archivos entregados

- `scripts/start.sh`, `scripts/stop.sh`, `scripts/status.sh`, `scripts/backup.sh`, `scripts/install_termux.sh`.
- `docs/despliegue.md`.
- `README.md` actualizado.
- `documentacion.md` actualizado.

## Mini informe de checkpoint C5

- **Objetivo:** dejar el proyecto operable y documentado para Termux.
- **Construido:** scripts de ciclo de vida, respaldo local + GitHub, instalador y guía completa de despliegue.
- **Verificación:** `pytest -q` → 125 aprobadas, 2 omitidas; `compileall` → OK; `bash -n` → OK; `status.sh` y `stop.sh` responden. El usuario probó el flujo desde Telegram con el bot corriendo en Linux y no encontró fallos fundamentales.
- **Conflictos:** CONF-013, CONF-014 y CONF-015 resueltos.
- **Pendientes/riesgos:** desplegar y validar en el Moto G7; revalidar en Python 3.11.
- **Estado:** APROBADA. El usuario confirmó la prueba satisfactoria y pidió continuar.

---

# Instancia 6 — Despliegue en dispositivo y transferencia

## Objetivo y alcance

Preparar el traslado del proyecto a Termux, responder dudas de portabilidad entre dispositivos y dejar un paquete seguro para instalar en el teléfono. La ejecución física y la validación final quedan a cargo del usuario.

## Bitácora

| ID | Fecha/hora | Tipo | Descripción | Archivos | Verificación | Resultado |
|---|---|---|---|---|---|---|
| I6-001 | 2026-11-20 19:00 | verificación | Prueba real desde Telegram con el bot corriendo en Linux | — | Prueba manual del usuario | Satisfactoria, sin fallos fundamentales |
| I6-002 | 2026-11-20 19:10 | proceso | Análisis de portabilidad y guía de transferencia entre Android/Termux | `docs/despliegue.md` | Revisión de contenido | OK |
| I6-003 | 2026-11-20 19:15 | agregado | Script de empaquetado seguro para Termux | `scripts/empaquetar.sh` | `bash -n`; generación del `.tar.gz` | OK |
| I6-004 | 2026-11-20 19:20 | verificación | Revisión del contenido del paquete | `dist/gastosBot-termux-YYYYMMDD-HHMM.tar.gz` | `tar -tzf` sin secretos, base, logs, venv ni fixtures | OK (72K) |
| I6-005 | 2026-11-20 19:25 | cambio | README y `.gitignore` actualizados para transferencia | `README.md`, `.gitignore` | Revisión | OK |
| I6-006 | — | pendiente | Instalar Termux, transferir, configurar `.env` y probar en el dispositivo | — | Checklist de `docs/despliegue.md` §14 | Pendiente |

## Verificación ejecutada

```text
$ ./scripts/empaquetar.sh
Paquete listo: /home/ale/Files/Proyectos/MYSOFT/gastosBot/dist/gastosBot-termux-YYYYMMDD-HHMM.tar.gz
Tamaño: 72K

$ tar -tzf dist/gastosBot-termux-*.tar.gz
README.md
Desarrollo/...
# Sin .env, data/, logs/, .venv, __pycache__, .pytest_cache ni fixtures reales.

$ .venv/bin/python -m pytest -q
125 passed, 2 skipped in 5.01s

$ bash -n scripts/*.sh
bash -n OK
```

## Decisiones y observaciones

- **Portabilidad:** el código no depende del modelo del teléfono. Cualquier Android con Termux (F-Droid/GitHub) y Python 3.11+ puede ejecutarlo. Solo cambian rutas del `.env` y la instalación de dependencias.
- **Transferencia recomendada:** `git clone` del repositorio en Termux y llevar el `.env` por separado. La base es opcional y portable.
- **Alternativa:** paquete `.tar.gz` generado por `scripts/empaquetar.sh`, sin secretos, base, logs, venv ni fixtures.
- **No copiar `.venv`:** se recrea con `scripts/install_termux.sh`.
- **Samsung:** requiere deshabilitar optimización de batería para Termux y, si hace falta, `termux-wake-lock`.
- **Termux:** instalar desde F-Droid o GitHub, no desde Play Store.
- **Base:** se puede migrar copiando `data/gastos.db` con el bot detenido, o empezar de cero.

## Archivos entregados

- `scripts/empaquetar.sh`.
- `docs/despliegue.md` §14 (cambio de dispositivo y transferencia).
- `README.md` y `.gitignore` actualizados.
- Paquete local `dist/gastosBot-termux-YYYYMMDD-HHMM.tar.gz` (no versionado).

## Mini informe de checkpoint C6

- **Objetivo:** preparar y acompañar el despliegue en Termux y el cambio de dispositivo.
- **Construido:** guía de transferencia, paquete seguro y checklist de instalación.
- **Verificación:** paquete sin secretos ni datos; 125 pruebas aprobadas; scripts validados.
- **Pendientes:** instalar en el dispositivo, transferir `.env`, migrar o crear la base, probar `/start` y un comprobante, configurar cron.
- **Estado:** PENDIENTE DE PRUEBA EN DISPOSITIVO. El usuario debe ejecutar el despliegue y reportar el resultado.

---

## Historial de checkpoints

| Checkpoint | Instancia | Fecha | Estado | Observaciones |
|---|---|---|---|---|
| C0 | 0 | 2026-11-20 | APROBADA | Aprobación explícita del usuario con condiciones incorporadas |
| C1 | 1 | 2026-11-20 | APROBADA | Aprobación implícita al indicar “Continua” |
| C2 | 2 | 2026-11-20 | APROBADA | Aprobación implícita al indicar “Continua” |
| C3 | 3 | 2026-11-20 | APROBADA | Aprobación implícita al indicar “Continua”; 96 pruebas con validación real |
| C4 | 4 | 2026-11-20 | APROBADA | Aprobación implícita al pedir continuar; token aceptado en entorno personal |
| C5 | 5 | 2026-11-20 | APROBADA | Prueba real desde Telegram satisfactoria; scripts y guía listos |
| C6 | 6 | 2026-11-20 | PENDIENTE DE PRUEBA EN DISPOSITIVO | Paquete de transferencia y guía listos; falta instalar en el teléfono |
