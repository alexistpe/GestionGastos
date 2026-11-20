-- Schema SQLite de GestionGastos
-- Se aplica de forma idempotente desde database/db.py::init_db.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS etiquetas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL UNIQUE,
    es_rutina   INTEGER NOT NULL DEFAULT 0 CHECK (es_rutina IN (0, 1))
);

CREATE TABLE IF NOT EXISTS comprobantes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT    NOT NULL CHECK (
                        fecha GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    ),
    destino         TEXT,
    monto           REAL    NOT NULL CHECK (monto > 0),
    balance         TEXT    NOT NULL CHECK (balance IN ('INGRESO', 'EGRESO')),
    id_etiqueta     INTEGER NOT NULL,
    FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS avisos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT    NOT NULL CHECK (tipo IN ('ETIQUETA', 'MONTO_TOTAL')),
    id_etiqueta     INTEGER,
    monto_limite    REAL    NOT NULL CHECK (monto_limite > 0),
    activo          INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    CHECK (
        (tipo = 'ETIQUETA' AND id_etiqueta IS NOT NULL)
        OR (tipo = 'MONTO_TOTAL' AND id_etiqueta IS NULL)
    ),
    FOREIGN KEY (id_etiqueta) REFERENCES etiquetas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sesion_estado (
    chat_id             INTEGER PRIMARY KEY,
    nombre_conversacion TEXT    NOT NULL DEFAULT 'comprobante',
    estado_actual       TEXT    NOT NULL,
    contexto_json       TEXT,
    id_comprobante      INTEGER,
    timestamp           TEXT    NOT NULL,
    FOREIGN KEY (id_comprobante) REFERENCES comprobantes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS avisos_disparados (
    clave        TEXT NOT NULL,
    periodo      TEXT NOT NULL,
    disparado_en TEXT NOT NULL,
    PRIMARY KEY (clave, periodo)
);

CREATE INDEX IF NOT EXISTS idx_comprobantes_fecha
    ON comprobantes(fecha);

CREATE INDEX IF NOT EXISTS idx_comprobantes_etiqueta
    ON comprobantes(id_etiqueta);

CREATE INDEX IF NOT EXISTS idx_avisos_etiqueta
    ON avisos(id_etiqueta);

CREATE INDEX IF NOT EXISTS idx_sesion_estado_timestamp
    ON sesion_estado(timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS ux_avisos_etiqueta
    ON avisos(id_etiqueta)
    WHERE tipo = 'ETIQUETA';

CREATE UNIQUE INDEX IF NOT EXISTS ux_avisos_total
    ON avisos(tipo)
    WHERE tipo = 'MONTO_TOTAL';
