# Diseño de Arquitectura: Plataforma SaaS B2B de Optimización de Reaseguro

## 1. Visión General
La plataforma es una solución de software como servicio (SaaS) diseñada para compañías de seguros. Su objetivo es transformar datos brutos de siniestralidad en estrategias de transferencia de riesgo optimizadas, utilizando ciencia actuarial avanzada, modelos de capital económico y una arquitectura multi-tenant segura.

## 2. Stack Tecnológico (Versión Estable)
- **Frontend**: React.js + Recharts (En proceso de migración gradual a Next.js 14 App Router).
- **Backend**: FastAPI (Python 3.12) - Alta performance y soporte nativo de tipado.
- **Motor Actuarial**: Implementación en Pandas + NumPy (Con hoja de ruta hacia la migración a Polars para Big Data).
- **Persistencia**: PostgreSQL 15 (Aislamiento de clientes mediante `company_id` y Row Level Security - RLS).
- **Seguridad**: JWT (JSON Web Tokens) + Passlib/Bcrypt.
- **Infraestructura**: Docker + Docker Compose + Nginx.

## 3. Arquitectura de Módulos (Core)

### A. Módulo de Diagnóstico y Gobernanza
- **Función**: Puerta de entrada de datos y control de calidad.
- **Proceso**: Carga de CSV $\rightarrow$ Validación de tipos $\rightarrow$ Check de coherencia actuarial $\rightarrow$ Registro en Audit Log.
- **Valor**: Asegura la integridad de los datos antes del procesamiento actuarial.

### B. Módulo Actuarial (Enterprise Engine)
- **Triángulos de Siniestralidad**: Construcción de matrices de Origen vs. Desarrollo optimizadas mediante agregaciones SQL.
- **Cálculo de IBNR Avanzado**: 
    - **S-Smoothing**: Implementación de promedio ponderado de LDFs para reducir la volatilidad.
    - **Lógica de Proyección**: Proyección paso a paso asegurando coherencia matemática.
    - **Tail Factor**: Proyección de pérdidas más allá del horizonte observado.
    - **Modelos Soportados**: Chain Ladder, Bornhuetter-Ferguson (BF) y Cape Cod.
- **Validación Estadística**: Back-testing mediante simulación de snapshots históricos.
- **Análisis de Severidad**: Detección de siniestros catastróficos mediante el método de Rango Intercuartílico (IQR).

### C. Optimización de Reaseguro y Capital Económico
- **Modelo de Capital Económico (EC)**: Minimización del **Costo Total de Riesgo (TCR)** basada en VaR al 99.5% (Estándar Solvencia II).
- **Análisis de Burn-through**: Medición del agotamiento de la capa de reaseguro.
- **Sugerencia de Contrato**: Recomendación basada en la optimización de retención y volatilidad.

### D. Gestión de Renovaciones y Contratos
- **Ciclo de Vida**: Gestión de estados de contrato (Active $\rightarrow$ Expired).
- **Renewal Technical Package**: Consolidación de IBNR, Burn-through y Tendencias para negociación.

## 4. Diseño de Seguridad y SaaS (Multi-tenancy)
- **Aislamiento de Datos**: Implementación estricta de `company_id` en todas las tablas.
- **Sincronización de Sesión**: Validación de tokens en el servidor (Middleware) y persistencia coordinada en cliente para evitar bucles de redirección.
- **Filtrado de Consultas**: Todas las solicitudes son filtradas por el `company_id` extraído del token JWT.

## 5. Diagrama de Flujo de Datos
`CSV Input` $\rightarrow$ `Gobernanza` $\rightarrow$ `DB PostgreSQL` $\rightarrow$ `S-Smoothed Actuarial Engine` $\rightarrow$ `TCR Optimization` $\rightarrow$ `Burn-through Analysis` $\rightarrow$ `Renewal Package` $\rightarrow$ `Executive Dashboard`

## 6. Estrategia de Despliegue y Gobernanza
- **Contenerización**: Docker Multi-stage build.
- **Despliegue**: Docker Compose con orquestación de servicios (Frontend, Backend, DB).
- **Evolución Controlada**: Sigue la `ESTRATEGIA_OPTIMIZACION_SaaS.md` para evitar regresiones funcionales, priorizando la estabilidad operativa sobre las optimizaciones arquitectónicas.
