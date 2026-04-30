# Diseño de Arquitectura: Plataforma SaaS B2B de Optimización de Reaseguro

## 1. Visión General
La plataforma es una solución de software como servicio (SaaS) diseñada para compañías de seguros. Su objetivo es transformar datos brutos de siniestralidad en estrategias de transferencia la de riesgo optimizadas, utilizando ciencia actuarial avanzada y una arquitectura multi-tenant segura.

## 2. Stack Tecnológico
- **Frontend**: React.js + Recharts (Visualización de datos, Dashboards interactivos y gráficos de validación estadística).
- **Backend**: FastAPI (Python 3.12) - Elegido por su alta performance y soporte nativo de tipado.
- **Motor Actuarial**: Implementación nativa en Pandas + NumPy (Sustituyendo dependencias externas para mayor estabilidad y control).
- **Persistencia**: PostgreSQL 15 (Soporte para datos relacionales, aislamiento de clientes y gestión de primas).
- **Seguridad**: JWT (JSON Web Tokens) + Passlib/Bcrypt (Cifrado de contraseñas).
- **Infraestructura**: Docker + Docker Compose + Nginx (Proxy Inverso y SSL).

## 3. Arquitectura de Módulos (Core)

### A. Módulo de Diagnóstico y Gobernanza
- **Función**: Puerta de entrada de datos.
- **Proceso**: Carga de CSV $\rightarrow$ Validación de tipos $\rightarrow$ Check de coherencia actuarial $\rightarrow$ Registro en Audit Log.
- **Valor**: Asegura que el motor actuarial no procese "datos basura", evitando errores de proyección.

## 3. Arquitectura de Módulos (Core)

### A. Módulo de Diagnóstico y Gobernanza
- **Función**: Puerta de entrada de datos.
- **Proceso**: Carga de CSV $\rightarrow$ Validación de tipos $\rightarrow$ Check de coherencia actuarial $\rightarrow$ Registro en Audit Log.
- **Valor**: Asegura que el motor actuarial no procese "datos basura", evitando errores de proyección.

### B. Módulo Actuarial (El Núcleo)
- **Triángulos de Siniestralidad**: Construcción de matrices de Origen vs. Desarrollo basadas en agregaciones SQL eficientes (SUM/GROUP BY) para soportar millones de registros.
- **Cálculo de IBNR (Modelos Avanzados)**: 
    - **Chain Ladder Interactivo**: Proyección basada en experiencia histórica con soporte para ajuste manual de LDFs en tiempo real.
    - **Bornhuetter-Ferguson (BF)**: Combina experiencia histórica con expectativa *a priori* basada en primas y Loss Ratio.
    - **Cape Cod**: Proyección basada en el Loss Ratio histórico y primas emitidas.
- **Validación Estadística (Back-testing)**: Simulación de retroceso temporal para comparar reservas estimadas en el pasado contra pagos reales actuales, midiendo el MAE (Error Medio Absoluto).
- **Análisis de Severidad**: Detección de siniestros catastróficos mediante el método de Rango Intercuartílico (IQR).
- **Métricas de Cartera**: Cálculo dinámico de Frecuencia y Severidad promedio por ramo.

### C. Módulo de Proyecciones y Optimización de Reaseguro
- **Simulador de Estrés**: Ajuste de multiplicadores de severidad para analizar escenarios adversos.
- **Optimización de Retención**: Sugerencia de capital a retener basándose en la solvencia y el costo de capital de la compañía.
- **Sugerencia de Contrato**: Basado en el Índice de Volatilidad (CV) y deltas de frecuencia/severidad, recomienda:
    - **Quota Share (QS)**: Para riesgos estables y predecibles.
    - **Excess of Loss (XoL)**: Para riesgos volátiles con picos de severidad.

### D. Módulo de Gestión de Renovaciones y Contratos
- **Ciclo de Vida del Contrato**: Gestión de estados de contrato (Active $\rightarrow$ Expired) y activación de nuevas pólizas de reaseguro.
- **Generación de Borradores**: Traduce resultados técnicos en cláusulas contractuales (Prioridad, Límite, Cuotas de Cesión) con un sistema de fallback robusto para asegurar la generación del documento.
- **Formato**: Genera estructuras JSON listas para exportación a documentos legales y visualización en el dashboard de renovación.

## 4. Diseño de Seguridad y SaaS (Multi-tenancy)
- **Aislamiento de Datos**: Cada tabla en la base de datos contiene un `company_id`. Todas las consultas se filtran por este ID basándose en el token JWT del usuario.
- **Flujo de Autenticación**:
    1. Usuario $\rightarrow$ `/token` $\rightarrow$ Recibe JWT.
    2. Usuario $\rightarrow$ Endpoint Actuarial $\rightarrow$ Envía JWT en Header.
    3. Backend $\rightarrow$ Valida JWT $\rightarrow$ Extrae `company_id` $\rightarrow$ Consulta solo datos de esa compañía.

## 5. Diagrama de Flujo de Datos
`CSV Input` $\rightarrow$ `Gobernanza` $\rightarrow$ `DB PostgreSQL` $\rightarrow$ `Actuarial Engine` $\rightarrow$ `Simulador de Escenarios` $\rightarrow$ `Ingeniería de Contratos` $\rightarrow$ `Dashboard Ejecutivo` $\rightarrow$ `Validación Estadística`

## 6. Estrategia de Despliegue
- **Contenerización**: Docker Multi-stage build para optimizar el tamaño de la imagen de React (via Nginx).
- **CI/CD**: Automatización vía GitHub Actions $\rightarrow$ Docker Hub $\rightarrow$ SSH Deploy.
- **Red**: Nginx como Reverse Proxy manejando HTTPS (SSL Let's Encrypt).
