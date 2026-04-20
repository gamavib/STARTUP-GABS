# Diseño de Arquitectura: Plataforma SaaS B2B de Optimización de Reaseguro

## 1. Visión General
La plataforma es una solución de software como servicio (SaaS) diseñada para compañías de seguros. Su objetivo es transformar datos brutos de siniestralidad en estrategias de transferencia de riesgo optimizadas, utilizando ciencia actuarial avanzada y una arquitectura multi-tenant segura.

## 2. Stack Tecnológico
- **Frontend**: React.js + Recharts (Visualización de datos y Dashboard interactivo).
- **Backend**: FastAPI (Python 3.12) - Elegido por su alta performance y soporte nativo de tipado.
- **Motor Actuarial**: `chainladder` + `Pandas` + `NumPy` (Estándar industrial para cálculos de IBNR).
- **Persistencia**: PostgreSQL 15 (Soporte para datos relacionales y aislamiento de clientes).
- **Seguridad**: JWT (JSON Web Tokens) + Passlib/Bcrypt (Cifrado de contraseñas).
- **Infraestructura**: Docker + Docker Compose + Nginx (Proxy Inverso y SSL).

## 3. Arquitectura de Módulos (Core)

### A. Módulo de Diagnóstico y Gobernanza
- **Función**: Puerta de entrada de datos.
- **Proceso**: Carga de CSV $\rightarrow$ Validación de tipos $\rightarrow$ Check de coherencia actuarial $\rightarrow$ Registro en Audit Log.
- **Valor**: Asegura que el motor actuarial no procese "datos basura", evitando errores de proyección.

### B. Módulo Actuarial (El Núcleo)
- **Triángulos de Siniestralidad**: Construcción de matrices de Origen vs. Desarrollo.
- **Cálculo de IBNR**: Aplicación de la técnica *Chain Ladder* para estimar la reserva técnica necesaria.
- **Análisis de Severidad**: Detección de siniestros catastróficos mediante el método de Rango Intercuartílico (IQR).
- **Métricas de Cartera**: Cálculo dinámico de Frecuencia y Severidad promedio por ramo.

### C. Módulo de Proyecciones y Optimización
- **Simulador de Estrés**: Permite ajustar multiplicadores de severidad para analizar escenarios adversos.
- **Optimización de Retención**: Sugiere la cantidad óptima de capital a retener basándose en la solvencia de la compañía.
- **Sugerencia de Contrato**: Basado en el Índice de Volatilidad (CV), recomienda el tipo de contrato:
    - **Quota Share (QS)**: Para riesgos estables y predecibles.
    - **Excess of Loss (XoL)**: Para riesgos volátiles con picos de severidad.

### D. Módulo de Ingeniería de Contratos
- **Generación de Borradores**: Traduce los resultados técnicos en cláusulas contractuales (Prioridad, Límite, Cuotas de Cesión).
- **Formato**: Genera estructuras JSON listas para exportación a documentos legales.

## 4. Diseño de Seguridad y SaaS (Multi-tenancy)
- **Aislamiento de Datos**: Cada tabla en la base de datos contiene un `company_id`. Todas las consultas se filtran por este ID basándose en el token JWT del usuario.
- **Flujo de Autenticación**:
    1. Usuario $\rightarrow$ `/token` $\rightarrow$ Recibe JWT.
    2. Usuario $\rightarrow$ Endpoint Actuarial $\rightarrow$ Envía JWT en Header.
    3. Backend $\rightarrow$ Valida JWT $\rightarrow$ Extrae `company_id` $\rightarrow$ Consulta solo datos de esa compañía.

## 5. Diagrama de Flujo de Datos
`CSV Input` $\rightarrow$ `Gobernanza` $\rightarrow$ `DB PostgreSQL` $\rightarrow$ `Actuarial Engine` $\rightarrow$ `Simulador de Escenarios` $\rightarrow$ `Ingeniería de Contratos` $\rightarrow$ `Dashboard Ejecutivo`

## 6. Estrategia de Despliegue
- **Contenerización**: Docker Multi-stage build para optimizar el tamaño de la imagen de React (via Nginx).
- **CI/CD**: Automatización vía GitHub Actions $\rightarrow$ Docker Hub $\rightarrow$ SSH Deploy.
- **Red**: Nginx como Reverse Proxy manejando HTTPS (SSL Let's Encrypt).
