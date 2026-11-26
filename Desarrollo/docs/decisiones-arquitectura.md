# Decisiones de arquitectura — GestionGastos

Documento técnico de referencia. Complementa el SPEC original y registra las decisiones tomadas durante el desarrollo. La bitácora cronológica está en `documentacion.md`.

---

## 1. Contexto y restricciones

- **Objetivo:** registrar comprobantes de pago, convertirlos en datos contables y analizarlos desde Telegram.
- **Dispositivo:** Moto G7 con Termux, sin root y sin servidor propio.
- **Consumo:** long polling, sin procesamiento continuo; CPU mínima.
- **API externa:** Gemini con un límite estimado de 60–100 solicitudes por mes.
- **Persistencia:** SQLite local; respaldo del código en GitHub.
- **Usuario:** único chat autorizado.

---

## 2. Stack

| Componente | Decisión |
|---|---|
| Lenguaje | Python 3.11+ |
| Bot | `python-telegram-bot` v21 |
| Extracción | Gemini REST vía `httpx`, modelo y versión configurables |
| Base de datos | `sqlite3` (stdlib) |
| Configuración | `.env` + `python-dotenv` |
| Estado | memoria + `sesion_estado` |
| Ejecución | Termux + `nohup` |
| Respaldo | Git + cron |

---

## 3. Modelo de datos

### 3.1 Tablas base

El schema parte de las tablas del SPEC y agrega tres elementos justificados:

1. `avisos_disparados`, para emitir cada alerta una sola vez por período.
2. `sesion_estado.nombre_conversacion`, para la persistencia de PTB.
3. `configuracion`, para el saldo inicial de ahorro y futuras preferencias.

Tablas:

- **`etiquetas`**: `id`, `nombre` único y normalizado, `es_rutina`.
- **`comprobantes`**: `id`, `fecha` ISO, `destino`, `monto > 0`, `balance` (`INGRESO`/`EGRESO`), `id_etiqueta`.
- **`avisos`**: `tipo` (`ETIQUETA`/`MONTO_TOTAL`), `id_etiqueta`, `monto_limite > 0`, `activo`.
- **`sesion_estado`**: `chat_id` (PK), `nombre_conversacion`, `estado_actual`, `contexto_json`, `id_comprobante`, `timestamp`.
- **`avisos_disparados`**: `clave`, `periodo`, `disparado_en`, PK compuesta.
- **`configuracion`**: `clave` (PK), `valor`; guarda `saldo_inicial_ahorro`.

### 3.2 Integridad

- `PRAGMA foreign_keys = ON` en cada conexión.
- `comprobantes.id_etiqueta` con `ON DELETE RESTRICT`: no se puede borrar una etiqueta en uso.
- `avisos.id_etiqueta` con `ON DELETE CASCADE`: al borrar una etiqueta se eliminan sus alertas.
- `CHECK` para montos positivos, fechas ISO, enums y consistencia de avisos.
- Índices en `comprobantes(fecha)`, `comprobantes(id_etiqueta)` y `avisos(id_etiqueta)`.
- Índices únicos parciales para garantizar una alerta por etiqueta y una alerta total.

### 3.3 Decisiones deliberadas

- **Sin triggers:** la lógica de negocio vive en Python para poder testearla y mantener el schema simple.
- **Una etiqueta por comprobante:** regla del modelo de dominio; los subtotales no se reparten.
- **Montos en `REAL`:** suficiente para el caso de uso; se documenta que no se usa aritmética decimal exacta.
- **Fechas en `TEXT` ISO 8601:** ordenamiento lexicográfico correcto y compatibilidad con SQLite.

El DDL completo está en `database/schema.sql`.

---

## 4. Persistencia del estado conversacional

**Decisión:** implementar `SQLitePersistence(BasePersistence)` sobre `sesion_estado`.

- `estado_actual` guarda el estado del `ConversationHandler` como texto.
- `contexto_json` guarda `context.user_data`, que incluye el borrador del comprobante y los datos temporales de edición.
- `nombre_conversacion` identifica el flujo (`comprobante` o `edicion`).
- `get_conversations` devuelve claves `(chat_id, chat_id)` porque el bot es privado y de un único usuario.
- `store_data` solo persiste `user_data`; chat, bot y callback data quedan en memoria.
- Al arrancar, se restauran los estados vigentes y se eliminan los que superan una hora; el usuario recibe un aviso.
- El timeout en proceso se apoya en `python-telegram-bot[job-queue]`.
- Se prefiere SQLite a `PicklePersistence` por coherencia, inspeccionabilidad y posibilidad de limpieza con SQL.
- La implementación se validó con PTB 21.11; no fue necesario el fallback a pickle.

**Concurrencia:** una sola conversación multi-paso por chat. Los entry points de registro y edición consultan `sesion_estado` y rechazan solapamientos. Los comandos stateless no requieren estado. Si el usuario inicia un flujo con otro abierto, el bot pide terminarlo o usar `/cancelar`.

---

## 5. Extracción con Gemini

### 5.1 Cliente HTTP y modelo

- Cliente: `httpx.AsyncClient` directamente contra la API REST de Gemini.
- Endpoint: `https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent`.
- Versión: `GEMINI_API_VERSION`, por defecto `v1beta`.
- Modelo: variable `GEMINI_MODEL`, por defecto `gemini-3.1-flash-lite`.
- Se documenta que el nombre del modelo puede cambiar; no se hardcodea en la lógica.
- **Motivo de la migración:** `google-genai` arrastra `pydantic-core`, `google-auth` y `cryptography`, que no tienen wheels Android y obligan a compilar en Termux. Con REST/`httpx` el despliegue queda en Python puro.
- `gemini-2.5-flash` dejó de estar disponible para cuentas nuevas (CONF-006).
- `gemini-3.8-flash` y `gemini-3.7-flash` respondieron 503 por alta demanda durante la validación (CONF-007); se eligió `gemini-3.1-flash-lite` por disponibilidad y funcionamiento comprobado con dos comprobantes reales. Se puede configurar un modelo más potente por entorno cuando esté disponible.

### 5.2 Entrada

- Imágenes: `image/jpeg`, `image/png`, `image/webp`.
- PDF: `application/pdf`.
- Se descarga el archivo desde Telegram y se envía como `inlineData` con `mimeType` y `data` en base64.
- El prompt pide devolver únicamente JSON con el esquema acordado.
- Se puede pasar el texto del caption como contexto para ayudar a interpretar el destino y el balance.
- La API key viaja en el header `x-goog-api-key`, nunca en la URL.

### 5.3 Salida

```json
{
  "fecha": "YYYY-MM-DD",
  "destino": "texto",
  "monto": 15000.0,
  "balance": "INGRESO | EGRESO | null",
  "moneda": "ARS"
}
```

- `balance` se deduce del sentido de la operación.
- Si no es concluyente, se devuelve `null` y la confirmación lo resuelve con botones.
- Se usa `generationConfig.responseMimeType="application/json"` y `responseSchema` para reducir texto libre.
- `temperature=0`.
- El texto útil se extrae de `candidates[0].content.parts[].text`.
- Se contempla `promptFeedback.blockReason` y respuestas sin candidatos.

### 5.4 Resiliencia y validación

- `asyncio.wait_for` con timeout de 15 segundos.
- Un reintento ante timeout (`httpx.TimeoutException`) y errores transitorios (429/5xx o `httpx.TransportError`).
- Si falla definitivamente, se informa al usuario y se ofrece el alta manual.
- El JSON se valida en Python: fecha ISO, monto positivo, balance `INGRESO`/`EGRESO` y moneda (ARS por defecto).
- Los campos faltantes o inválidos se devuelven como `None` con una advertencia, para que la confirmación los complete.
- El módulo registra modelo, MIME y resultado en el logger; la configuración de handlers y rotación queda en la capa de bot.
- No se implementa caché por hash en la v1; queda como mejora futura.

### 5.5 Prueba de integración

- La lógica se prueba con `httpx.MockTransport`, sin red.
- Existe un test que llama a Gemini real si se define `RUN_GEMINI_INTEGRATION=1`, hay `GEMINI_API_KEY` y hay comprobantes en `TEST_RECEIPT_PATH` o `tests/fixtures/`.
- La validación real se ejecutó con dos comprobantes PNG y `gemini-3.1-flash-lite`; ambos devolvieron monto, fecha y balance.
- También se validó en un venv limpio con solo `requirements-dev.txt`, sin `google-genai`, pydantic ni cryptography.
- Por defecto el test se omite para no consumir la cuota mensual en cada corrida.
- Los comprobantes reales y el `.env` están ignorados por `.gitignore`: no se versionan ni se exponen claves o datos financieros.

---

## 6. Flujo de registro y edición

### 6.1 Registro

1. Llega una foto o PDF.
2. El bot confirma la recepción de inmediato.
3. Se intenta extraer la etiqueta del caption; si no hay, se pide por selector.
4. Gemini extrae los datos.
5. Se valida y normaliza.
6. Se muestra la ficha de confirmación con todos los campos editables.
7. Al confirmar se inserta y se evalúan las alertas.

### 6.2 Edición antes de guardar

Los botones de la confirmación modifican el contexto en memoria. El registro no existe en la base hasta confirmar. Cancelar descarta el contexto.

### 6.3 Edición después de guardar

- `editar` lista los últimos 10 comprobantes.
- `editar ID` abre la ficha del comprobante.
- Campos editables: monto, etiqueta, fecha, balance y destino.
- Cada cambio se valida, se actualiza la base y se vuelve a mostrar la ficha.
- `borrar` y `borrar ID` eliminan con confirmación inline.
- Las alertas ya emitidas no se duplican; los análisis se recalculan.

---

## 7. Reglas de negocio

### 7.1 Período actual

- Inicio: fecha del último comprobante `INGRESO` con etiqueta `cuota`, considerando solo fechas menores o iguales a hoy.
- Si no existe: primer día del mes calendario actual.
- Fin: hoy.
- Se usa para el análisis rápido y para la evaluación de alertas.

### 7.2 Ahorro

- `- ahorro` es un depósito: suma al ahorro.
- `+ ahorro` es una extracción: resta al ahorro.
- Para el balance general, el signo contable se mantiene.
- **Período:** `ahorro_depositado`, `ahorro_extraido` y `monto_ahorro = depositado - extraído`.
- **Acumulado:** `ahorro_inicial` (saldo configurado + movimientos anteriores al período) + `monto_ahorro`.
- El saldo inicial se guarda en `configuracion.saldo_inicial_ahorro` y se fija con `ahorro inicial monto`.
- El saldo acumulado solo refleja movimientos registrados en el bot más el saldo inicial configurado.
- La alerta `AHORRO_NEGATIVO` usa el neto del período; el saldo acumulado negativo solo se advierte en el análisis.

### 7.3 Alertas

Se evalúan después de cada alta o modificación:

1. balance neto negativo;
2. rutina completada;
3. etiqueta por encima de su límite;
4. gasto total del período por encima del límite configurado;
5. extracciones de ahorro mayores al ingreso neto;
6. balance de ahorro del período negativo (extraído > depositado).

Para no duplicar avisos de ahorro, si se dispara `AHORRO_NEGATIVO` se omite `AHORRO` en ese período.

La tabla `avisos_disparados` evita repetir una alerta en el mismo período. Claves:

- `ETIQUETA:{id}`
- `ETIQUETA_AHORRO:{id}` (límite de extracciones de ahorro)
- `MONTO_TOTAL`
- `BALANCE_NEGATIVO`
- `RUTINA`
- `AHORRO`
- `AHORRO_NEGATIVO`

El período se identifica por la fecha de inicio del período actual.

Las alertas se pueden eliminar con `eliminar alerta` (selector) o `eliminar alerta ID`.

### 7.4 Rutina

- Las etiquetas con `es_rutina = 1` son gastos fijos.
- La rutina se considera completa cuando todas tienen al menos un `EGRESO` en el período.
- El presupuesto de rutina se toma del `monto_limite` de las alertas de tipo `ETIQUETA`; si no hay alerta, se informa “sin presupuesto definido”.
- El pendiente total suma solo las etiquetas que tienen presupuesto definido.

### 7.5 Gastos no esenciales

- Se calculan agrupando los `EGRESO` que no pertenecen a etiquetas de rutina.
- Se excluye la etiqueta `ahorro`, porque es una transferencia entre cuentas y tiene su propio análisis.
- Se ordenan de mayor a menor monto.

### 7.6 Total gastado y alerta de monto total

- El total gastado (`monto_saliente`) incluye todos los `EGRESO`, incluido `ahorro`, porque la definición contable del SPEC son los registros con `-`.
- La alerta `MONTO_TOTAL` compara ese total contra el límite configurado.
- El ahorro se informa por separado para no confundir consumo con transferencia.

---

## 8. Parsers

### 8.1 Normalización

- Texto en minúsculas y sin tildes.
- Etiquetas con `[a-z0-9_]`; los espacios se convierten en `_`.
- Tolerancia a mayúsculas, acentos y espacios extra.

### 8.2 Montos

Se aceptan formatos argentinos e internacionales:

- `15000`
- `15.000`
- `15.000,50`
- `15,50`
- `$ 15.000`
- `1.234.567`
- `1,234.56`

Reglas:

- Si hay `.` y `,`, el último separador es el decimal.
- Si solo hay `,`, se interpreta como decimal.
- Si solo hay `.` y el patrón es de miles, se interpreta como separador de miles.
- Se rechazan montos negativos o iguales a cero.

### 8.3 Fechas

- Formatos aceptados: `DD.MM.AA`, `DD.MM.AAAA`, `DD/MM/AA`, `DD-MM-AA`, `YYYY-MM-DD`.
- Los años de dos dígitos se interpretan como `2000 + AA`.
- Se valida la fecha real (por ejemplo, `31.02.26` es inválido).
- Se devuelve siempre ISO `YYYY-MM-DD`.

### 8.4 Comandos

- Se aceptan con y sin barra inicial.
- Se toleran mayúsculas, acentos y espacios.
- Los comandos desconocidos devuelven `None`; los comandos reconocidos con argumentos inválidos lanzan `ErrorParseo` con un mensaje en español.

---

## 9. Logging

- `logging` de la stdlib.
- `RotatingFileHandler` de 1 MB con 3 backups.
- Formato: `%(asctime)s %(levelname)s %(name)s :: %(message)s`.
- Nivel `INFO` por defecto, configurable con `LOG_LEVEL`.
- Nunca se registran tokens, claves ni el contenido completo de los comprobantes.
- Un filtro de redacción reemplaza `TELEGRAM_BOT_TOKEN` y `GEMINI_API_KEY` por `***` en cualquier mensaje de log.
- `httpx` y `httpcore` se fijan en `WARNING` porque sus logs INFO incluyen la URL de Telegram con el token.
- Si un token llega a exponerse, debe rotarse con @BotFather y actualizar el `.env`.

---

## 10. Transacciones y errores

- Una conexión por operación mediante context manager.
- `with conn:` para commit/rollback automático.
- `PRAGMA foreign_keys = ON`, `journal_mode = WAL` y `busy_timeout = 5000`.
- Los errores de integridad se traducen a mensajes claros en los handlers.
- Las validaciones de negocio se hacen en Python; los `CHECK` son la última barrera.

---

## 11. Seguridad

- El bot solo responde al `TELEGRAM_CHAT_ID` configurado.
- Los mensajes de remitentes no autorizados se ignoran sin respuesta.
- `.env`, `data/`, `logs/` y los comprobantes de prueba no se versionan.
- El respaldo a GitHub incluye solo código y documentación.
- No se registran datos sensibles en logs; además, los secretos se redactan.
- Las claves que se expongan accidentalmente deben rotarse.

---

## 12. Despliegue

- Código en `~/gastos/Desarrollo` dentro de Termux.
- Base en `data/gastos.db`, logs de la app en `logs/bot.log` y salida cruda en `logs/nohup.log`.
- Ejecución con `scripts/start.sh`, PID en `bot.pid`, parada con `scripts/stop.sh` y estado con `scripts/status.sh`.
- Instalación con `scripts/install_termux.sh`.
- Respaldo diario con cron a las 03:00 mediante `scripts/backup.sh`.
- El respaldo crea una copia consistente de SQLite en `data/backups/` y sube solo código y documentación a GitHub.
- Dependencia `python-telegram-bot[job-queue]` para los timeouts de conversación.
- En Python 3.14 se crea y setea un event loop antes de `run_polling`; en Termux (3.11/3.12) el mismo código funciona.
- La copia local de desarrollo usa `DB_PATH=./data/gastos.db`; el `.env` de Termux puede usar la ruta absoluta del dispositivo.
- El diagrama de despliegue y la guía operativa están en `docs/despliegue.md`.

---

## 13. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Límite mensual de Gemini | Registro de consumo y diseño de un único llamado por comprobante |
| Modelo de Gemini no disponible | `GEMINI_MODEL` configurable por entorno |
| Reinicio del proceso en Android | Persistencia en `sesion_estado` y expiración controlada |
| Alertas repetidas | `avisos_disparados` por período |
| Errores de OCR | Confirmación editable y edición posterior |
| Crecimiento de logs | Rotación por tamaño |
| Tokens en logs | Redacción de secretos y `httpx/httpcore` en `WARNING`; rotación ante exposición |
| Python 3.14 sin event loop implícito | Crear y setear el loop antes de `run_polling` |
| Pérdida del teléfono | Respaldo del código en GitHub; la base puede respaldarse aparte |

---

## 14. Decisiones futuras

- Evaluar caché por hash de comprobante para evitar llamadas duplicadas a Gemini.
- Evaluar respaldo de la base SQLite (no solo del código).
- Evaluar soporte de moneda múltiple.
- Evaluar exportación de análisis a CSV/PDF.
