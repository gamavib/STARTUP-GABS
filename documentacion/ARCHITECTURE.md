# Diseño de Arquitectura: Plataforma SaaS B2B de Optimización de Reaseguro (Versión Enterprise)

## 1. Visión General
La plataforma es una solución de software como servicio (SaaS) diseñada para compañías de seguros. Su objetivo es transformar datos brutos de siniestralidad en estrategias de transferencia de riesgo optimizadas, utilizando ciencia actuarial avanzada, modelos de capital económico y una arquitectura multi-tenant segura.

## 2. Stack Tecnológico
- **Frontend**: React.js + Recharts (Visualización de datos, Dashboards interactivos, Heatmaps de volatilidad y Gráficos de desarrollo Real vs. Proyectado).
- **Backend**: FastAPI (Python 3.12) - Alta performance y soporte nativo de tipado.
- **Motor Actuarial**: Implementación nativa en Pandas + NumPy con modelos de proyección estables y optimización de capital.
- **Persistencia**: PostgreSQL 15 (Aislamiento de clientes y gestión de primas/contratos).
- **Seguridad**: JWT + Passlib/Bcrypt.
- **Infraestructura**: Docker + Docker Compose + Nginx.

## 3. Arquitectura de Módulos (Core)

### A. Módulo de Diagnóstico y Gobernanza
- **Función**: Puerta de entrada de datos y control de calidad.
- **Proceso**: Carga de CSV $\rightarrow$ Validación de tipos $\rightarrow$ Check de coherencia actuarial $\rightarrow$ Registro en Audit Log.
- **Valor**: Asegura la integridad de los datos antes del procesamiento actuarial.

### B. Módulo Actuarial (Enterprise Engine)
- **Triángulos de Siniestralidad**: Construcción de matrices de Origen vs. Desarrollo optimizadas mediante agregaciones SQL.
- **Cálculo de IBNR Avanzado**: 
    - **S-Smoothing**: Implementación de promedio ponderado de LDFs para reducir la volatilidad causada por años atípicos.
    - **Lógica de Proyección**: Implementación de proyección paso a paso (Celdas $j = \text{Celda } j-1 \times \text{LDF}_{j-1}$), asegurando coherencia matemática en el triángulo proyectado.
    - **Tail Factor**: Proyección de pérdidas más allá del horizonte observado para evitar la subestimación de reservas.
    - **Modelos Soportados**: Chain Ladder, Bornhuetter-Ferguson (BF) y Cape Cod.
- **Validación Estadística**: Back-testing mediante simulación de snapshots históricos y medición del error de predicción.
- **Análisis de Severidad**: Detección de siniestros catastróficos mediante el método de Rango Intercuartílico (IQR).

### C. Optimización de Reaseguro y Capital Económico
- **Modelo de Capital Económico (EC)**: 
    - Sustituye heurísticas simples por la minimización del **Costo Total de Riesgo (TCR)**.
    - $\text{TCR} = (\text{Costo de Capital} \times \text{Capital Requerido}) + \text{Costo de Cesión}$.
    - El capital requerido se calcula mediante el VaR al 99.5% (estándar Solvencia II).
- **Análisis de Burn-through**: Medición del agotamiento de la capa de reaseguro para determinar la necesidad de ajustar la prioridad en la renovación.
- **Sugerencia de Contrato**: Recomendación basada en el Índice de Volatilidad (CV) y la optimización de retención.

### D. Gestión de Renovaciones y Contratos
- **Ciclo de Vida**: Gestión de estados de contrato (Active $\rightarrow$ Expired).
- **Renewal Technical Package**: Consolidación de IBNR, Burn-through, Tendencias de Siniestralidad y Optimización de Capital en un formato técnico para negociación con reaseguradores.
- **Generación de Borradores**: Traducción de resultados técnicos en cláusulas contractuales (Prioridad, Límite, Cuotas).

## 4. Diseño de Seguridad y SaaS (Multi-tenancy)
- **Aislamiento de Datos**: Implementación de `company_id` en todas las tablas.
- **Filtrado de Consultas**: Todas las solicitudes son filtradas por el `company_id` extraído del token JWT.

## 5. Diagrama de Flujo de Datos
`CSV Input` $\rightarrow$ `Gobernanza` $\rightarrow$ `DB PostgreSQL` $\rightarrow$ `S-Smoothed Actuarial Engine` $\rightarrow$ `TCR Optimization` $\rightarrow$ `Burn-through Analysis` $\rightarrow$ `Renewal Package` $\rightarrow$ `Executive Dashboard`

## 6. Estrategia de Despliegue
- **Contenerización**: Docker Multi-stage build.
- **CI/CD**: Automatización vía GitHub Actions $\rightarrow$ Docker Hub $\rightarrow$ SSH Deploy.
- **Red**: Nginx como Reverse Proxy manejando HTTPS.
