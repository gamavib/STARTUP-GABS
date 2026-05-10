# Roadmap de Mejoras Técnicas - Core Actuarial (engine.py)

Este documento detalla las optimizaciones y mejoras arquitectónicas identificadas en el motor actuarial para elevar su robustez a un nivel de producción enterprise.

## 1. Refactorización y Limpieza (Prioridad: Alta)
- [ ] **Eliminación de Redundancia**: Eliminar la definición duplicada del diccionario `draft` en la función `generate_contract_draft` (líneas 450-476).
- [ ] **Estandarización de Entrada de Datos**: 
    - Actualmente, el motor espera datos resumidos, pero algunos métodos (`analyze_frequency_severity`, `compare_reserves`) requieren datos detallados (crudos).
    - **Propuesta**: Modificar `ActuarialEngine` para que acepte el DataFrame crudo y gestione internamente las versiones resumidas mediante propiedades `@property` o caché, evitando errores de `KeyError` al buscar columnas como `id_poliza` o `monto_reserva`.

## 2. Robustez Actuarial (Prioridad: Media)
- [ ] **Parametrización de Ratios**: Sustituir los valores hardcodeados (ej. `expected_loss_ratio = 0.6`) por un sistema de configuración por ramo.
- [ ] **Ampliación de Métodos de Proyección**:
 idea de implementar el método de *Bornhuetter-Ferguson* con ratios variables por año de desarrollo.
- [ ] **Manejo de Outliers**: Implementar una función de "Winsorización" o limpieza de datos extremos antes de calcular los LDFs para evitar que un solo siniestro masivo distorsione toda la proyección del triángulo.

## 3. Análisis y Validación (Prioridad: Media)
- [ ] **Métricas de Backtesting**: Añadir indicadores de precisión al método `perform_backtesting`:
    - MAPE (Mean Absolute Percentage Error).
    - RMSE (Root Mean Square Error).
    - Gráficos de "Actual vs Estimated".
- [ ] **Validación de Consistencia**: Implementar checks automáticos para asegurar que la suma de los triangulos proyectados sea coherente con la suma de los ultimate losses.

## 4. Optimización de Reaseguro (Prioridad: Baja)
- [ ] **Simulaciones Monte Carlo**: Evolucionar el modelo de Capital Económico (EC) de una fórmula determinista a una simulación estocástica para modelar la volatilidad de la severidad.
- [ ] **Sugerencias de Capas (Layering)**: Automatizar la sugerencia de múltiples capas de reaseguro (ej. 1era capa XoL, 2da capa XoL) en lugar de una sola retención.

## 5. Rendimiento y Escalabilidad (Prioridad: Baja)
- [ ] **Tipado Estricto**: Migrar las firmas de los métodos a usar `Pandas.DataFrame` y `Pandas.Series` específicamente en lugar de `Any` para mejorar la detección de errores en tiempo de desarrollo.
- [ ] **Vectorización**: Revisar los bucles `for` en el cálculo de LDFs y sustituirlos por operaciones vectorizadas de NumPy para mejorar el rendimiento con triángulos de gran volumen.
