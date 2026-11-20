# Diseño

## Concepto:

Se diseñara un software y arquitectura capaz de Recibir los comprobantes de pagos, procesarlos y convertirlos en datos utiles y posteriormente realizar un analisis sobre esos datos.

El flujo de accion es: Se recibe un comprobante de pago -> se procesa adecuadamente para procesarlo como un dato contable -> se guarda el dato en una base de datos correspondiente -> Se consultan esos datos segun se requieran -> Se realizan analisis correspondiente a esos datos.

El usuario podra enviar estos comprobantes y posteriormente visualizar los analisis hechos sobre ese mes y a nivel global.

**Rutina contiene:** Gym, Peluqueria, Nafta, Seguro, Claro.

## Detalles:

- **Comprobantes:** Pueden ser archivos PDF o fotos de mercado pago y lemon cash.
    - Se etiquetaran los gastos realizados (datos de los comprobantes) segun se especifique en el mensaje.
    - Se determinara etiquetas que representan las etiquetas correspondientes a cada comprobante.
    - Cada comprobante se enviara con un unico mensaje que representa a que etiquetas pertenece ese comprobante, y posteriormente se etiquetara como tal.
- **Balance:** Los mensajes sin imagenes se interpretaran como cambios de balance segun la siguiente sitanxis:
    - ER: [+|-].[ ].E ; Donde es el lenguaje "etiquetas" que contiene todas las posibles palabras definidas como las etiquetas (E).
        - “+” al inicio simboliza un ingreso de dinero, “-” simboliza un gasto, cada uno tiene etiquetas particulares, sin embargo puede darse el caso de que ambos compartan etiquetas.
- **Procesamiento:** Los datos extraidos se guardaran en una base de datos que se pueda consultar constantemente segun se necesite.
    - Se filtrara por fecha para determinar las transacciones relevantes y en base a eso se extraeran sus fechas, montos (total de dinero transferido), nombres (propuestos en los atributos de los comprobantes) y etiquetas.
    - En el caso de obtener los ingresos de dinero, se obtendran unicamente la fecha, monto (total de dinero especificado) y la etiqueta correspondiente.
- **Analisis:** Una vez con los datos consultados, la etapa de analisis consistira en devolver un informe con:
    - Se debera poder pedir un analisis personalizados al especificar los rangos de fecha mediante la sintaxis [analisis].[ ].[0-9]{2}.[0-9]{2}.[0-9]{2}:
        1. El total ingresado (Registros con ”+”), el total gastado (Registros con ”-”), y el total neto restante (total ingresado - total gastado).
        2. Una lista con todas los gastos realizados ordenadas por etiquetas de mayor a menor monto. Con el total por etiqueta.
        3. Ademas se mostrara una lista con todos los ingresos de dinero registrados, sumarizados en un total y detallados individualmente en una lista.
        4. Se especificara una seccion donde se evaluen los montos “ahorrados”, mediante la etiqueta “ahorro”, se realizara un calculo para determinar el total ahorrado por el usuario, sumarizando los ingresos y egresos de dinero para la etiqueta “ahorro”.
            1. Se mostrara el valor neto ahorrado (total gastado - total ingresado), el ahorro es un gasto mas, determinado con [+|-].[ ].ahorro, sin embargo cuanto hay un ingreso en esta etiqueta, simboliza que se extrajo dinero de los ahorros. Sigue siendo dinero positivo para el balance final, pero balance negativo para el ahorro. Por lo que para este analisis especifico de “Cuanto se ahorro” se interpreta:  + ahorro como una resta al valor total ahorrado, y  - ahorro como una suma al valor total ahorrado. Ya que la etiqueta ahorro se toma como un gasto mas, sin embargo este gasto no es mas que un movimiento de dinero a otra cuenta, no una desaparicion del dinero. Por lo tanto al recuperarlo ({+ ahorro}) se debe restar del total ahorrado.
    - Si se desea un analisis rapido del mes, se debera poder pedir mediante la palabra “analisis”, esto devolvera:
        - Una comparacion con los gatos de la rutina: Cuanto dinero se gasto en ella, y cuanto dinero falta gastar. Junto al balance total para ese mes (Puntos 1).
            - La rutina son gastos mensuales fijos que se especifican con anterioridad y permiten analizar segun las etiquetas asignadas cuales fueron efectuados y cuales no; Habran etiquetas especificas que referencian a la rutina.
        - Ademas se especificara cuanto dinero se gasto en total en gastos no esenciales.
            - Los gastos no esenciales son los que exluyen los datos de la rutina, osea todo gasto externo a las etiquetas que referencian a la rutina.
            - Esta lista se realiza por etiqueta y se organiza de mayor a menor monto.
        - Este analisis se realizara tomando en cuenta desde la fecha de la ultima “cuota” que ingreso hasta el dia actual.
            - “cuota” hace referencia a un ingreso de dinero  con la etiqueta “cuota”. Al poder variar el monto, se basa en el ultimo ingreso de dinero con la etiqueta “cuota”.
    - El software sera capaz de enviar alertas cuanto sucedan ciertos eventos determinados.
        - Se realizaran alertas cuando: Se gaste una cantidad mayor de dinero que el ingresado hasta ese mes (Donde mes es el ultimo ingreso de cuota, osea el dia mas cercano del ingreso, hasta el dia actual). En sintesis, cuando el balance neto sea negativo.
        - Cuando se haya completado el gasto total de la rutina (Se realizaron los gastos propuestos de la rutina).
        - Una cierta etiqueta durante ese mes (Donde mes es el ultimo ingreso de cuota, osea el mas cercano, hasta el dia actual) supere el monto asignado al sumarizar sus gastos.
            - El usuario puede asignarle un monto especifico a una etiqueta para su posterior alerta mediante: [alerta].E.[0-9]* ; Donde E representa la etiqueta designada.
        - Cuando las extracciones (egreso de dinero) de la etiqueta ahorro ({+ ahorro}) del mes actual (Donde mes es el ultimo ingreso de cuota, osea el mas cercano, hasta el dia actual) represente mas de lo ingresado (valor neto). Se representa el egreso de dinero desde ahorros con una suma positiva ya que el dinero ahorrado entra a la cuenta nuvamente, sin embargo para la cuenta de ahorros, esta simboliza un balance negativo.
- **Mantenimiento:** Esta seccion esta diseñada para de forma sencilla, poder añadir diferentes alertas, etiquetas a la rutina, y modificaciones para no tener que modificar el codigo directamente.
    - Opciones interactivas: Al ingresar una transferencia por foto, el bot enviara un mensaje de confirmacion especificando los atributos de esa transaccion.
        - Contendra opciones para modificar el monto o la etiquetas, permitiendo enviar un nuevo mensaje unicamente con el dato pedido a cambiar y de esa forma actualizar la transaccion.
        - -Para evaluar- Se plantea la definicion de etiquetas y su posterior eleccion en un seleccionable, ya que escribirla puede traer malinterpretaciones. (Aplicar solo si la respuesta se puede almacenar, y no queda inservible si el servidor no esta disponible en ese momento). Si no se puede asegurar ese dato, se especifica por escrito y las opciones no se toman.
    - Definir alertas: Se podran definir varios tipos de alerta segun.
        - Alerta Etiqueta: [alerta].[ ].E.[ ].[0-9]*
            - Esta alerta permite delimitar un monto asignado a una etiqueta, para alertar cuando durante ese mes (Donde mes es el ultimo ingreso de cuota, osea el mas cercano, hasta el dia actual) se gasto un monto mayor en esa etiqueta.
        - Alerta Monto: [alerta].[ ].[0-9]*
            - Sirve para definir una alerta cuando el monto total gastado (G) (Donde mes es el ultimo ingreso de cuota, osea el mas cercano, hasta el dia actual) supero un cierto valor especificado.
    - Definicion de etiquetas: Se deberan definir las etiquetas individualemente antes de asignarlas.
        - Esto se debera poder hacer con: [etiqueta].[ ].[a-z]*
        - Y poder eliminar una etiqueta con [eliminar etiqueta].[ ].E
            - Donde E es etiqueta.
- **ACLARACIONES:** Se debe intentar tener un seleccionable en cada lugar donde se deban especificar valores repetidos, esto incluye principalmente las etiquetas. En todo comando relacionado a las etiquetas, debe poder haber un seleccionable que pueda determinar la etiqueta correcta. Evitando errores de ortografia y duplicacion de etiquetas. EN CASO DE QUE LA RESPUESTA SE PUEDA ALMACENAR SIN NECESIDAD DE QUE EL SERVIDOR ESTE PROCESANDO EN ESE MOMENTO.

### ¿Donde funcionara el software?

El software obtendra los datos desde telegram, como fotos de comprobantes. Al enviar este comprobante, el bot respondera con un mensaje para confirmar como se guardo, con opciones interactivas incluidas para cambiar el monto o categoria.

Extraera los datos con un protocolo desarrollado en un android moto g7.

Los datos extraidos los almacenara en una base de datos para posteriormente consultarlos.

Luego estos datos se consultaran para hacer un analisis. Este analisis se realizara en el mismo chat de telegram.

### Dificultades:

¿El moto G7 estara enchufado 24/7? ¿Debe tener un script para la bateria? ¿Estara procesando constantemente?

- Al ser una conexion long pooling, no consume CPU 24/7.
- Ademas al tener API externa y SQLlte, reuslta muy barato.

¿Que API sirve para procesar estas imagenes? Debe tener limites suficientes para aguntar 60 - 100 peticiones de traduccion (Imagen → texto en .json) al mes.

- La API de google gemini 1.5 puede procesar ese tipo de solicitudes,

¿Que tegnologias se utilizaran? ¿Como se conectaran entre si? Referido a lenguajes, protocolos, configuraciones de telegram, tipos de archivo, consulta a la base de datos, donde se encontrara esta, etc…

- Esto se analiza una vez terminado el flujo de diseño.

Mas alla de estas cuestiones y otras que se pueden plantear, se quiere crear una arquitectura de software que sea ligera, practica y simple, que permita mantener todo en el motoG7, y subir un respaldo del servidor a la nube (github) para tener todo respaldado. Junto a eso se quiere que el moto G7 no este procesando constantemente sino que use lo minimo e indispensable para almacenar y consultar, no necesariamente que este procesando datos 24/7 con la CPU al 100%.
Se quiere aplicar los conocimiento de la carrera para poner en marcha una base de datos local que permita almacenar, consultar y modificar los diferentes comprobantes y balances que se van agregando. Se necesita una especificacion tecnica seccion por seccion de como se va a implementar esta arquitectura.

### Flujo de diseño restante:

Entre ellos esta: Digramas de estado (Permite definir cuando y como actura el sistema ante determinada situacion), Secuencia (Representa un BPMN que permita visualizar el flujo de ejecucion y determinar cuellos de botella), Modelo real (Consiste en pasar el MODP a una version util para la base de datos en SQLite), listado de despliegue (Requisitos fundamentales y utiliades necesarias para la correcta ejecucion de la arquitectura planteada).

- **Diagramas de Estado (FSM - Finite State Machine):** Es el corazón de cualquier bot interactivo. Tu sistema no procesa datos linealmente; reacciona a eventos. Si el usuario toca "Editar Monto", el bot entra en un estado temporal (`ESPERANDO_NUEVO_MONTO`). Si estando ahí el usuario manda un sticker en lugar de un número, el sistema debe saber cómo reaccionar sin crashear. Esto define la robustez de la interfaz en el chat.
    - **TERMINADO.**
- **Diagrama de Secuencia:** Necesitás mapear el ciclo de vida de un evento asíncrono. ¿Cómo viaja la petición? (Usuario -> Servidor Telegram -> Script Termux (Long Polling) -> Controlador `Gestion` -> API Gemini -> Base de Datos -> Interfaz Bot). Esto expone cuellos de botella temporales, como qué hace el Moto G7 mientras espera los 2 segundos de respuesta de la API.
    - **Delegado a la IA.**
- **Modelo de Datos Físico (DER):** Tu Diagrama de Clases Conceptual (MODP) debe traducirse a un Modelo Entidad-Relación duro para SQLite. Hay que definir claves primarias (PK), claves foráneas (FK), tipos de datos exactos (`REAL` para montos, `TEXT` para fechas ISO 8601) y la estructura de las tablas intermedias para resolver las relaciones de muchos a muchos.
    - **Delegado a la IA.**
- **Diagrama de Despliegue y Arquitectura:** Un croquis de la infraestructura física y lógica. Dónde vive el ejecutable, cómo se exponen los puertos (o cómo el Long Polling los evade), qué librerías manejan el acceso a disco en Android y el esquema del cronjob para los respaldos en GitHub.
    - **Delegado a la IA.**

## MODP: Diagrama de clases.

![image.png](Dise%C3%B1o/image.png)

## CDU: Diagrama de casos de uso.

![image.png](Dise%C3%B1o/image%201.png)

## DTE: Diagrama de transicion de estados (Maquina de estados para la transaccion).

![DTE.svg](Dise%C3%B1o/DTE.svg)

## Objetivos casos de uso:

1. **Registrar comprobante:** Registrar los datos relacionados al comprobante en el sistema (fecha, destino, monto, balance) asignando la etiqueta, nroComprobante. Donde balance hace referencia a una transferencia entrante (+) o saliente (-).
2. **Emitir Alerta:** Emite una alerta sobre una situacion especificada, ya sea del monto general mensual o especifico de una etiqueta.
3. **Emitir Analisis:** Emite un analisis sobre lo especificado en el mensaje, ya sea uno general o uno especifico por etiqueta.
4. **Configurar Alerta:** Registra o modifica alertas, definiendolas por etiqueta o por monto gastado.
5. **Modificar Comprobante:** Modifica los atributos guardados en el comprobante original, permitiendo modificar la etiqueta o monto de la misma mediante un mensaje de confirmacion.
6. **Gestionar Etiqueta:** Agrega una nueva cierta etiqueta especificada o elimina una etiqueta todo especificado con una cierta sintaxis.

## Codigo plantuml:

#### MODP:

@startuml

'La clase gestion es la clase orquestadora, y responsable de la generacion.

class Gestion{

comprobantes : Comprobante

etiquetas : Etiqueta

resumenes : Resumen

avios : Aviso

traductor : Traductor

iniciarTraduccion()

corregirComprobante()

generarResumen()

generarAviso()

conocerComprobante()

conocerEtiqueta()

conocerRsumen()

conocerAviso()

conocerTraductor()

}

class Comprobante{

nroComprobante

fecha

destino

etiqueta : Etiqueta

monto

balance : Balance

crear()

mostrar()

conocerEtiqueta()

conocerBalance()

}

'El balance simboliza si fue un ingreso o egreso.

enum Balance{

nombre

descripcion

}

'El atributo esRutina simboliza un boleano que permite determinar si esa categoria pertenece a la rutina o no.

class Etiqueta{

nro

nombre

esRutina

crear()

mostrar()

}

'Al ser una clase procesadora, unicamente contiene metodos.

class Traductor{

crear()

mostrar()

traducirComprobante()

conocerComprobante()

}

class Resumen{

tipoResumen : TipoResumen

montoNeto

montoIngresado

montoSaliente

montoAhorro

montoGastadoRutina

montoPedienteRutina

montos: Comprobante

crear()

mostrar()

calcularMontoNeto()

calcularAhorro()

calcularGastoRutina()

calcularMontoPedienteRutina()

conocerTipoResumen()

conocerComprobante()

}

'Permite definir el tipo de resumen a pedir, si mensual, o rango de fechas.

enum TipoResumen{

nombre

descripcion

}

'Aviso tiene ciclo de vida distinto a Resumen, usa metodos independientes.

class Aviso{

nombre

tipo : Tipo

etiqueta : Etiqueta

montoLimite

mes

crear()

mostrar()

conocerTipo()

conocerEtiqueta()

añadirAviso()

evaluarAviso()

}

enum Tipo{

nombre

descripcion

}

'Relaciones:

Comprobante -> "1" Etiqueta

Comprobante -> "1" Balance

Traductor -> "1" Comprobante

Resumen -> "1..*" Comprobante

Resumen -> "1" TipoResumen

Aviso -> "1..*" Comprobante

Aviso -> "1" Tipo

Gestion -> Comprobante

Gestion -> Aviso

Gestion -> Resumen

Gestion -> Traductor

Gestion -> Etiqueta

/'Regla de negocios:

- Una etiqueta por comprobante, se aftrae los subtotales.

'/

@enduml

#### CU:

@startuml

:Usuario: as u

:ServicioOCR: as a

rectangle "Sistema Gestion Gastos"{

u -> (1. Registrar Comprobante)

(1. Registrar Comprobante) <.. (2. Emitir Alerta): <<ext>>

(1. Registrar Comprobante) --> a

u --> (3. Emitir Analisis)

u --> (4. Configurar Alerta)

u --> (5. Modificar Comprobante)

u --> (6. Gestionar Etiqueta)

}

@enduml

#### DTE:

'Diagrama de maquina de estados para gastos.

'FB: Flujo basico; FA: Flujo alternativo.

@startuml

state "Comprobante Recibido" as CR

state "Consultando Servicio" as CS

state "Esperando Confirmacion" as EC

state "Envio seleccion etiqueta" as ESE

state "Corrigiendo monto/etiqueta" as CME

state "Registrando Transaccion" as RT

state "Alertando" as A

state "Confirmado" as C

[*] --> CR: 1. Registrar Comprobante

CR --> CS: 1. Registrar Comprobante (FB, Se confirmo que es una imagen)

CS --> EC: 1. Registrar Comprobante (FA, Se especifico la etiqueta)

CS --> ESE: 1. Registrar Comprobante (FB, sin especificar etiqueta)

ESE --> EC: 1. Registrar Comprobante (FB, El usuario selecciono la etiqueta)

EC --> CME: 1. Registrar Comprobante (FA, Paso 6 FB)

CME --> EC: 1. Registrar Comprobante (FA, Alertnativa 7)

EC --> C: 1. Registrar Comprobante (Comprobante confirmado)

C --> RT: 1. Registrar Comprobante (Fin del FB)

C --> A: 2. Emitir Alerta (FA, Alternativo 10)

RT --> [*]

A --> [*]

@enduml