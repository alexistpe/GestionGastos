# Guía de comandos — GestionGastos

Esta guía explica cómo interactuar con el bot por Telegram: qué escribir, qué efecto tiene cada acción y en qué casos conviene usarla. Todos los comandos aceptan su forma con barra (`analisis` o `/analisis`). No distinguen mayúsculas, tildes ni espacios extra.

---

## 1. Registrar un comprobante

### 1.1 Enviar una foto o un PDF

**Sintaxis:** enviar la imagen o el archivo, opcionalmente con la etiqueta en el texto del mensaje.

**Efecto:**
1. El bot confirma la recepción.
2. Extrae automáticamente `fecha`, `destino`, `monto` y `balance`.
3. Si el mensaje incluye una etiqueta válida, la usa; si no, muestra un selector.
4. Muestra una ficha de confirmación con todos los campos editables.
5. Al confirmar, guarda el comprobante y evalúa las alertas.

**Cuándo usarlo:** para cualquier pago o ingreso del que tengas el comprobante (Mercado Pago, Lemon Cash, transferencia, ticket, factura).

**Ejemplos:**
- Enviar una foto sin texto → el bot pide la etiqueta.
- Enviar una foto con el texto `nafta` → usa la etiqueta `nafta`.

**Notas:**
- Si el balance no se puede deducir, la ficha lo marca con `⚠️` y ofrece los botones `Ingreso` / `Egreso`.
- Antes de confirmar podés corregir monto, etiqueta, fecha, balance o destino.
- Si el archivo ya fue cargado y querés corregirlo después, usá `editar`.

### 1.2 Confirmación de comprobante

La ficha muestra:

```
📅 Fecha: 15.11.26
💰 Monto: $15.000,00
🔄 Balance: Egreso
🏷️ Etiqueta: nafta
📝 Destino: Estación de servicio
```

Botones disponibles:

| Botón | Efecto |
|---|---|
| `✏️ Monto` | Pide el nuevo monto |
| `🏷️ Etiqueta` | Abre el selector de etiquetas |
| `📅 Fecha` | Pide la nueva fecha |
| `🔄 Balance` | Alterna entre ingreso y egreso |
| `📝 Destino` | Pide el nuevo destino |
| `✅ Confirmar` | Guarda el comprobante |
| `❌ Cancelar` | Descarta el comprobante |

**Cuándo usarlo:** siempre que quieras revisar o corregir antes de guardar.

---

## 2. Balances manuales

### 2.1 Ingreso

**Sintaxis:** `+ etiqueta monto`

**Efecto:** registra un ingreso con la fecha de hoy y la etiqueta indicada. Evalúa alertas.

**Cuándo usarlo:** cuando entra dinero y no tenés un comprobante para enviar.

**Ejemplos:**
- `+ cuota 850000`
- `+ ahorro 50000` (extracción de ahorros)

### 2.2 Egreso

**Sintaxis:** `- etiqueta monto`

**Efecto:** registra un egreso con la fecha de hoy y la etiqueta indicada. Evalúa alertas.

**Cuándo usarlo:** cuando sale dinero y no tenés un comprobante para enviar.

**Ejemplos:**
- `- nafta 15000`
- `- ahorro 100000` (transferencia a la cuenta de ahorro)

**Notas:**
- El monto debe ser positivo; el signo lo define el `+` o el `-`.
- Se aceptan formatos como `15.000`, `15000` o `$15.000,50`.
- La etiqueta debe existir. Si no existe, creala primero con `etiqueta nombre`.

---

## 3. Análisis

### 3.1 Análisis del mes actual

**Sintaxis:** `analisis`

**Efecto:** devuelve un informe desde la fecha del último ingreso con etiqueta `cuota` hasta hoy:
- total ingresado, total gastado y neto;
- gastos por etiqueta, de mayor a menor;
- ingresos detallados;
- cálculo de ahorro;
- comparación con la rutina (gastado y pendiente);
- gastos no esenciales por etiqueta, excluyendo la rutina y `ahorro`.

**Cuándo usarlo:** para revisar cómo va el mes sin indicar fechas.

**Ejemplo:** `analisis`

### 3.2 Análisis desde una fecha

**Sintaxis:** `analisis DD.MM.AA`

**Efecto:** analiza desde esa fecha hasta hoy.

**Cuándo usarlo:** para consultar un período que empezó en una fecha puntual.

**Ejemplo:** `analisis 01.11.26`

### 3.3 Análisis por rango cerrado

**Sintaxis:** `analisis DD.MM.AA DD.MM.AA`

**Efecto:** analiza el rango entre ambas fechas, inclusive.

**Cuándo usarlo:** para comparar o revisar un período completo.

**Ejemplo:** `analisis 01.11.26 15.11.26`

**Notas:**
- La fecha inicial no puede ser posterior a la final.
- Se aceptan también `DD/MM/AA` y `YYYY-MM-DD`.

---

## 4. Alertas

### 4.1 Alerta por etiqueta

**Sintaxis:** `alerta etiqueta monto`

**Efecto:** crea o actualiza un límite para esa etiqueta. Si el gasto del período la supera, el bot avisa una sola vez por período.

**Cuándo usarlo:** para controlar el gasto de una categoría específica.

**Ejemplos:**
- `alerta nafta 15000`
- `alerta gym 20000`

### 4.2 Alerta de gasto total

**Sintaxis:** `alerta monto`

**Efecto:** crea o actualiza un límite para el gasto total del período. Avisa una sola vez por período.

**Cuándo usarlo:** para fijar un techo mensual de gasto.

**Ejemplo:** `alerta 100000`

### 4.3 Listar alertas

**Sintaxis:** `alertas`

**Efecto:** muestra las alertas activas con su tipo, etiqueta y monto límite.

**Cuándo usarlo:** para revisar la configuración vigente.

**Notas:**
- Las alertas se evalúan después de cada alta o modificación de comprobante.
- Si el período cambia (nueva `cuota`), las alertas vuelven a habilitarse.

---

## 5. Etiquetas

### 5.1 Crear etiqueta

**Sintaxis:** `etiqueta nombre`

**Efecto:** crea una etiqueta nueva. El nombre se normaliza a minúsculas, sin tildes y sin espacios.

**Cuándo usarlo:** antes de usar una categoría que todavía no existe.

**Ejemplos:**
- `etiqueta supermercado`
- `etiqueta Tarjeta Crédito` → se guarda como `tarjeta_credito`

### 5.2 Eliminar etiqueta

**Sintaxis:** `eliminar etiqueta nombre`

**Efecto:** elimina la etiqueta si no tiene comprobantes asociados. Si está en uso, el bot lo informa y no la borra.

**Cuándo usarlo:** para limpiar categorías que ya no usás.

**Ejemplo:** `eliminar etiqueta supermercado`

### 5.3 Listar etiquetas

**Sintaxis:** `etiquetas`

**Efecto:** muestra todas las etiquetas y marca las que pertenecen a la rutina.

**Cuándo usarlo:** para consultar los nombres exactos antes de usarlos.

---

## 6. Edición y borrado de comprobantes

### 6.1 Editar un comprobante guardado

**Sintaxis:** `editar` o `editar ID`

**Efecto:**
- `editar` muestra los últimos 10 comprobantes con botones.
- `editar ID` abre la ficha del comprobante indicado.
- Desde la ficha podés modificar monto, etiqueta, fecha, balance o destino.
- Al terminar, `Listo` cierra la edición.

**Cuándo usarlo:** si confirmaste un comprobante y luego detectaste un error.

**Ejemplos:**
- `editar` → elegís uno de la lista.
- `editar 42` → abrís el comprobante #42.

### 6.2 Borrar un comprobante

**Sintaxis:** `borrar` o `borrar ID`

**Efecto:**
- `borrar` muestra los últimos 10 comprobantes para elegir.
- `borrar ID` pide confirmación para eliminar ese comprobante.
- La eliminación es definitiva.

**Cuándo usarlo:** para quitar un registro duplicado o cargado por error.

**Ejemplos:**
- `borrar 42`
- `borrar` → elegís de la lista y confirmás.

**Notas:**
- Los análisis se recalculan después de editar o borrar.
- Las alertas ya emitidas no se repiten.

---

## 7. Sistema

### 7.1 Ayuda

**Sintaxis:** `/ayuda` o `/comandos`

**Efecto:** muestra una versión resumida de esta guía en el chat.

**Cuándo usarlo:** cuando no recordás una sintaxis.

### 7.2 Inicio

**Sintaxis:** `/start`

**Efecto:** muestra el mensaje de bienvenida y el estado general del bot.

**Cuándo usarlo:** en el primer uso o después de un reinicio.

### 7.3 Cancelar

**Sintaxis:** `/cancelar`

**Efecto:** cancela el flujo multi-paso en curso (confirmación, edición, selección de etiqueta) y limpia el estado temporal.

**Cuándo usarlo:** si te equivocaste de comando o querés salir de una conversación.

---

## 8. Resumen rápido

| Acción | Comando |
|---|---|
| Registrar comprobante | Enviar foto/PDF (opcional: etiqueta) |
| Ingreso manual | `+ etiqueta monto` |
| Egreso manual | `- etiqueta monto` |
| Análisis del mes | `analisis` |
| Análisis desde una fecha | `analisis DD.MM.AA` |
| Análisis por rango | `analisis DD.MM.AA DD.MM.AA` |
| Alerta por etiqueta | `alerta etiqueta monto` |
| Alerta de gasto total | `alerta monto` |
| Listar alertas | `alertas` |
| Crear etiqueta | `etiqueta nombre` |
| Eliminar etiqueta | `eliminar etiqueta nombre` |
| Listar etiquetas | `etiquetas` |
| Editar comprobante | `editar` / `editar ID` |
| Borrar comprobante | `borrar` / `borrar ID` |
| Ayuda | `/ayuda` / `/comandos` |
| Cancelar flujo | `/cancelar` |
| Inicio | `/start` |

---

## 9. Reglas de uso

- El bot solo responde al chat autorizado.
- Una etiqueta por comprobante.
- Los montos son siempre positivos; el balance lo define `+`/`-` o la interpretación del comprobante.
- El “mes actual” empieza en el último ingreso con etiqueta `cuota`.
- `- ahorro` suma al ahorro; `+ ahorro` resta.
- Si un comando no se entiende, el bot responde con la sintaxis esperada y un ejemplo.
