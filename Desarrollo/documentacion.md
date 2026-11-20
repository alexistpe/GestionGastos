# Bitácora de desarrollo — GestionGastos

- **Proyecto:** GestionGastos (bot personal de gastos por Telegram)
- **Repositorio:** `git@github.com:alexistpe/GestionGastos.git`
- **Rama:** `main`
- **Código:** `Desarrollo/`
- **Inicio:** 2026-11-20
- **Estado general:** Instancia 1 completada; pendiente de aprobación (C1)

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
| 1 | Núcleo de datos: schema, acceso y parsers | C1 | PENDIENTE DE OK |
| 2 | Motor de negocio: resumen, avisos y gestión | C2 | PENDIENTE |
| 3 | Extracción con Gemini | C3 | PENDIENTE |
| 4 | Interfaz Telegram completa | C4 | PENDIENTE |
| 5 | Despliegue y operación | C5 | PENDIENTE |

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
| DEC-004 | `google-genai` + modelo configurable (`GEMINI_MODEL`, por defecto `gemini-2.5-flash`) | El SDK `google-generativeai` está deprecado; el modelo debe poder cambiarse sin tocar código |
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

---

## Registro de conflictos

| ID | Fecha | Descripción | Impacto | Resolución | Estado |
|---|---|---|---|---|---|
| CONF-001 | 2026-11-20 | El SPEC menciona `google-generativeai` y Gemini 1.5 Flash, pero el SDK está deprecado y el modelo puede no estar disponible | Medio | Se actualiza a `google-genai` y modelo configurable (DEC-004) | Resuelto |
| CONF-002 | 2026-11-20 | El SPEC no define deduplicación de alertas y, evaluando en cada INSERT, la misma alerta se repetiría | Medio | Se agrega `avisos_disparados` (DEC-010) | Resuelto |
| CONF-003 | 2026-11-20 | El SPEC solo permitía editar antes de confirmar; el usuario necesita corregir comprobantes ya guardados | Medio | Se agrega flujo de edición y borrado (DEC-008, DEC-009) | Resuelto |
| CONF-004 | 2026-11-20 | `pytest-asyncio` emitió una advertencia por el alcance del event loop | Bajo | Se agregó `pytest.ini` con `asyncio_default_fixture_loop_scope = function` | Resuelto |

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

## Historial de checkpoints

| Checkpoint | Instancia | Fecha | Estado | Observaciones |
|---|---|---|---|---|
| C0 | 0 | 2026-11-20 | APROBADA | Aprobación explícita del usuario con condiciones incorporadas |
| C1 | 1 | 2026-11-20 | PENDIENTE DE OK | 53 pruebas aprobadas; verificación y riesgos registrados |
