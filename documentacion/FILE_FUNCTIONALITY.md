# Diccionario de Funcionalidades: Plataforma SaaS de Reaseguro

Este documento detalla la responsabilidad y funcionalidad de cada archivo creado en el proyecto, organizado por capas de la arquitectura.

## 📂 Backend (Python / FastAPI)

### 📁 `app/`
- **`main.py`**: El orquestador de la API. Contiene la configuración de FastAPI, los endpoints públicos y protegidos, la integración del flujo de datos desde la carga hasta el contrato, y la gestión de la sesión de base de datos.
- **`auth.py`**: Módulo de seguridad. Gestiona la creación y validación de tokens JWT, el cifrado de contraseñas con Bcrypt y la dependencia `get_current_user` que asegura la autenticación y el aislamiento multi-tenant.
- **`database.py`**: Capa de persistencia. Define la conexión a PostgreSQL mediante SQLAlchemy y los modelos de datos (`Company`, `User`, `Claim`, `AuditLog`).
- **`modules/`**:
    - **`diagnostics/validator.py`**: El "filtro" de calidad. Valida que los CSVs cargados tengan las columnas correctas, fechas válidas y que no existan montos negativos, asegurando la integridad de los datos actuariales.
    - **`actuarial/engine.py`**: El cerebro de la plataforma. Contiene la lógica de ciencia actuarial:
        - Construcción de Triángulos.
        - Cálculo de IBNR (Chain Ladder).
        - Análisis de Severidad y detección de Outliers (IQR).
        - Optimización de Retenciones basada en capital.
        - Ingeniería de selección de contrato (XoL vs QS).
        - Generación de la estructura del borrador de contrato.

## 📂 Frontend (React.js)

### 📁 `frontend/src/`
- **`App.js`**: Componente principal y orquestador de la UI. Gestiona el estado global (autenticación, archivos cargados, filtros de ramo), el formulario de login y la navegación entre la carga de datos y el dashboard.
- **`components/ActuarialDashboard.js`**: El centro de visualización. Renderiza los KPIs ejecutivos, el gráfico de comparativa de reservas (Recharts) y la previsualización del borrador de contrato optimizado.
- **`services/api.js`**: Capa de comunicación. Centraliza todas las peticiones Axios al backend, gestionando el envío de tokens JWT en los encabezados de autorización.

## 📂 Infraestructura y Despliegue (DevOps)

- **`Dockerfile`**: Instrucciones para empaquetar el backend en una imagen ligera de Python 3.12, optimizando la instalación de dependencias actuariales.
- **`frontend/Dockerfile`**: Implementa un build de dos etapas: compila React con Node y sirve el resultado mediante un servidor Nginx de alta eficiencia.
- **`docker-compose.yml`**: Orquestrador local y de servidor. Levanta y conecta la base de datos PostgreSQL, el Backend y el Frontend en una red aislada.
- **`requirements.txt`**: Listado de todas las dependencias de Python necesarias para que el sistema sea reproducible en cualquier entorno.
- **`nginx.conf`**: Configuración del proxy inverso para manejar el tráfico HTTPS, redirigir peticiones al backend y optimizar la entrega del frontend.
- **`.github/workflows/deploy.yml`**: Pipeline de CI/CD que automatiza la construcción de imágenes y el despliegue en el servidor vía SSH cada vez que se sube código a GitHub.

## 📂 Documentación y Datos

- **`ARCHITECTURE.md`**: Documento técnico que describe la visión general, el stack tecnológico y la lógica de diseño de la plataforma.
- **`ejemplo_siniestros.csv`**: Dataset de prueba diseñado para validar la detección de siniestros catastróficos y la selección de contratos XoL.
