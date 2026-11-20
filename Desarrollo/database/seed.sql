-- Etiquetas iniciales del sistema.
-- es_rutina = 1 identifica los gastos fijos mensuales.

INSERT OR IGNORE INTO etiquetas (nombre, es_rutina) VALUES
    ('gym',        1),
    ('peluqueria', 1),
    ('nafta',      1),
    ('seguro',     1),
    ('claro',      1),
    ('cuota',      0),
    ('ahorro',     0);
