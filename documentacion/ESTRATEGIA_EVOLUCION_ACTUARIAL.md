# Hoja de Ruta Actuarial: Evolución hacia el Estándar de Industria
**Documento: Estrategia de Mejora de Reservas y Reaseguro Automático**
**Rol: Actuario Senior**

## 1. Visión General
Tras analizar el estado actual de la plataforma y compararla con los estándares de `asegurao.es` y la metodología de `chainladder-python`, el sistema ha logrado una base sólida en la construcción de triángulos y cálculo de IBNR. Sin embargo, para evolucionar de una "calculadora" a un "ecosistema de gestión de riesgos", debemos implementar capacidades de análisis predictivo, validación estadística y automatización de la renovación de contratos.

---

## 2. Mejoras en el Core Actuarial (Metodología)

### 2.1. Modelos de Proyección Avanzados
Actualmente usamos el método *Chain Ladder* simple. Para mejorar la precisión, implementaremos:
- **Bornhuetter-Ferguson (BF):** Combinar el método Chain Ladder con una expectativa de pérdida (*a priori*). Esto evita la volatilidad en los años más recientes donde un solo siniestro grande puede distorsionar el LDF.
- **Cape Cod:** Útil para carteras nuevas donde no hay suficiente historia para generar LDFs confiables, basándose en la relación siniestros/primas.
- **SSmoothing de LDFs:** Implementar promedios móviles o ajustes de "Tail Factor" para evitar que la curva de desarrollo sea demasiado errática al final del periodo.

### 2.2. Validación Estadística (Back-testing)
No basta con proyectar; hay que validar la proyección:
- **Análisis de Error de Predicción:** Comparar la reserva técnica estimada el año pasado contra lo que realmente se pagó este año.
- **Pruebas de Estrés (Siniestros Catastróficos):** Simular el impacto de un siniestro "Black Swan" (extremo) en la solvencia de la compañía basándose en la distribución de severidad actual.

---

## 3. Automatización de Reaseguro y Renovaciones

El objetivo es transformar la generación de borradores de contratos en un **Sistema de Renovación Automática**.

### 3.1. Motor de Análisis de Retención Óptima
Implementar un algoritmo que sugiera la retención basándose en:
- **Costo de Capital:** Calcular el costo de retener el riesgo vs. el costo de la prima de reaseguro.
- **Límite de Solvencia:** Si el IBNR proyectado supera el 30% del capital disponible, el sistema debe disparar una alerta de "Necesidad de Cesión" y sugerir un aumento del límite del contrato XoL.

### 3.2. Flujo de Renovación Automática (Automatic Renewal Workflow)
Crear un módulo que ejecute el siguiente flujo al cierre del año técnico:
1. **Evaluación de Siniestralidad:** El sistema analiza la pérdida real vs. la proyectada el año anterior.
2. **Cálculo de la Nueva Prima de Reaseguro:** Basado en el *Loss Ratio* del contrato actual, el sistema sugiere el ajuste de la prima para el nuevo periodo.
3. **Sugerencia de Estructura:** 
    - Si la severidad aumentó $\rightarrow$ Sugerir aumento de la prioridad en el contrato **Excess of Loss**.
    - Si la frecuencia aumentó $\rightarrow$ Sugerir aumento del porcentaje de cesión en el contrato **Quota Share**.
4. **Generación de "Renewal Package":** Crear automáticamente el PDF con el historial de siniestros, la proyección de IBNR y la propuesta de contrato renovado para enviar al reasegurador.

---

## 4. Mejoras en la Experiencia de Usuario (UX Actuarial)

### 4.1. Visualizaciones Avanzadas (Inspiración `asegurao.es`)
- **Gráfico de Desarrollo de Pérdidas:** Curvas de desarrollo acumuladas comparando el "estimado" vs el "real" a través del tiempo.
- **Heatmap de Triángulos:** Colores dinámicos en las celdas del triángulo para identificar rápidamente anomalías o picos de siniestralidad.

### 4.2. Análisis de Sensibilidad "What-if"
Permitir que el usuario mueva un *slider* de severidad y vea en tiempo real cómo cambia la necesidad de reaseguro y la solvencia de la empresa sin necesidad de recargar la página.

---

## 5. Prioridades de Implementación (Roadmap)

| Prioridad | Módulo | Funcionalidad | Impacto |
| :--- | :--- | :--- | :--- |
| **Alta** | Core | Método Bornhuetter-Ferguson | Precisión de Reservas |
| **Alta** | Reaseguro | Análisis de Retención basada en Capital | Solvencia Financiera |
| **Media** | UI | Gráficos de Curvas de Desarrollo | Análisis Visual |
| **Media** | Renovación | Generador de Renewal Package (PDF) | Eficiencia Operativa |
| **Baja** | Core | Back-testing de Reservas | Auditoría Técnica |
