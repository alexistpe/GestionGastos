# Bitácora de desarrollo — GestionGastos

- **Proyecto:** GestionGastos (bot personal de gastos por Telegram)
- **Repositorio:** `git@github.com:alexistpe/GestionGastos.git`
- **Rama:** `main`
- **Código:** `Desarrollo/`
- **Inicio:** 2026-11-20
- **Estado general:** Instancia 3 completada; pendiente de aprobación (C3)

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
| 3 | Extracción con Gemini | C3 | PENDIENTE DE OK |
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

## Historial de checkpoints

| Checkpoint | Instancia | Fecha | Estado | Observaciones |
|---|---|---|---|---|
| C0 | 0 | 2026-11-20 | APROBADA | Aprobación explícita del usuario con condiciones incorporadas |
| C1 | 1 | 2026-11-20 | APROBADA | Aprobación implícita al indicar “Continua” |
| C2 | 2 | 2026-11-20 | APROBADA | Aprobación implícita al indicar “Continua” |
| C3 | 3 | 2026-11-20 | PENDIENTE DE OK | 96 pruebas aprobadas (94 mock + 2 reales); modelo validado y credenciales fuera del repo |
