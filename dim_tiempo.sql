-- =============================================
-- DIMENSIÓN TIEMPO (DATE DIMENSION)
-- =============================================
-- Script para crear y poblar una tabla de dimensión temporal
-- Compatible con SQL Server, PostgreSQL, MySQL (ajustar tipos según sea necesario)

-- Crear tabla de dimensión tiempo
CREATE TABLE dim_tiempo (
    id_fecha INT PRIMARY KEY,              -- Formato YYYYMMDD como clave
    fecha DATE NOT NULL,                    -- Fecha completa
    anio INT NOT NULL,                      -- Año (2024)
    trimestre INT NOT NULL,                 -- Trimestre (1-4)
    mes INT NOT NULL,                       -- Mes (1-12)
    mes_nombre VARCHAR(20) NOT NULL,        -- Nombre del mes (Enero, Febrero...)
    dia INT NOT NULL,                       -- Día del mes (1-31)
    dia_semana INT NOT NULL,                -- Día de la semana (1=Lunes, 7=Domingo)
    dia_nombre VARCHAR(20) NOT NULL,        -- Nombre del día (Lunes, Martes...)
    dia_anio INT NOT NULL,                  -- Día del año (1-366)
    semana_anio INT NOT NULL,               -- Semana del año (1-53)
    es_fin_semana INT NOT NULL,             -- 1 si es sábado o domingo, 0 si no
    es_dia_laboral INT NOT NULL,            -- 1 si es día laboral (Lun-Vie), 0 si no
    periodo VARCHAR(10) NOT NULL,           -- Formato YYYY-MM
    anio_mes INT NOT NULL,                  -- Formato YYYYMM (útil para agrupaciones)
    fecha_inicio_semana DATE NOT NULL,      -- Primer día de la semana (Lunes)
    fecha_fin_semana DATE NOT NULL,         -- Último día de la semana (Domingo)
    fecha_inicio_mes DATE NOT NULL,         -- Primer día del mes
    fecha_fin_mes DATE NOT NULL,            -- Último día del mes
    fecha_inicio_trimestre DATE NOT NULL,   -- Primer día del trimestre
    fecha_fin_trimestre DATE NOT NULL       -- Último día del trimestre
);

-- =============================================
-- POBLAR LA TABLA CON FECHAS
-- =============================================
-- Este bloque genera fechas desde 2000-01-01 hasta 2030-12-31
-- Ajustar el rango según necesidades

-- Para SQL Server:
WITH fechas_generadas AS (
    SELECT
        DATEADD(DAY, n, '2000-01-01') AS fecha
    FROM (
        SELECT TOP 11323  -- Número de días entre 2000-01-01 y 2030-12-31
            ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
        FROM sys.objects a
        CROSS JOIN sys.objects b
    ) AS numeros
)
INSERT INTO dim_tiempo (
    id_fecha,
    fecha,
    anio,
    trimestre,
    mes,
    mes_nombre,
    dia,
    dia_semana,
    dia_nombre,
    dia_anio,
    semana_anio,
    es_fin_semana,
    es_dia_laboral,
    periodo,
    anio_mes,
    fecha_inicio_semana,
    fecha_fin_semana,
    fecha_inicio_mes,
    fecha_fin_mes,
    fecha_inicio_trimestre,
    fecha_fin_trimestre
)
SELECT
    CAST(FORMAT(fecha, 'yyyyMMdd') AS INT) AS id_fecha,
    fecha,
    YEAR(fecha) AS anio,
    DATEPART(QUARTER, fecha) AS trimestre,
    MONTH(fecha) AS mes,
    DATENAME(MONTH, fecha) AS mes_nombre,
    DAY(fecha) AS dia,
    DATEPART(WEEKDAY, fecha) AS dia_semana,
    DATENAME(WEEKDAY, fecha) AS dia_nombre,
    DATEPART(DAYOFYEAR, fecha) AS dia_anio,
    DATEPART(WEEK, fecha) AS semana_anio,
    CASE WHEN DATEPART(WEEKDAY, fecha) IN (1, 7) THEN 1 ELSE 0 END AS es_fin_semana,
    CASE WHEN DATEPART(WEEKDAY, fecha) BETWEEN 2 AND 6 THEN 1 ELSE 0 END AS es_dia_laboral,
    FORMAT(fecha, 'yyyy-MM') AS periodo,
    YEAR(fecha) * 100 + MONTH(fecha) AS anio_mes,
    DATEADD(DAY, -DATEPART(WEEKDAY, fecha) + 2, fecha) AS fecha_inicio_semana,  -- Lunes
    DATEADD(DAY, -DATEPART(WEEKDAY, fecha) + 8, fecha) AS fecha_fin_semana,      -- Domingo
    DATEADD(DAY, 1, EOMONTH(fecha, -1)) AS fecha_inicio_mes,                     -- Primer día del mes
    EOMONTH(fecha) AS fecha_fin_mes,                                               -- Último día del mes
    DATEADD(QUARTER, DATEDIFF(QUARTER, 0, fecha), 0) AS fecha_inicio_trimestre,  -- Primer día del trimestre
    DATEADD(DAY, -1, DATEADD(QUARTER, DATEDIFF(QUARTER, 0, fecha) + 1, 0)) AS fecha_fin_trimestre  -- Último día del trimestre
FROM fechas_generadas
WHERE fecha <= '2030-12-31';

-- =============================================
-- ÍNDICES RECOMENDADOS
-- =============================================

CREATE INDEX IX_dim_tiempo_anio ON dim_tiempo(anio);
CREATE INDEX IX_dim_tiempo_mes ON dim_tiempo(mes);
CREATE INDEX IX_dim_tiempo_anio_mes ON dim_tiempo(anio, mes);
CREATE INDEX IX_dim_tiempo_periodo ON dim_tiempo(periodo);

-- =============================================
-- CONSULTAS DE EJEMPLO
-- =============================================

-- Verificar datos generados
-- SELECT TOP 10 * FROM dim_tiempo;

-- Contar registros por año
-- SELECT anio, COUNT(*) as total_dias
-- FROM dim_tiempo
-- GROUP BY anio
-- ORDER BY anio;

-- Ver información de un mes específico
-- SELECT * FROM dim_tiempo
-- WHERE anio = 2024 AND mes = 1;
