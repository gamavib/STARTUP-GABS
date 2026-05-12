# Diccionario de Funcionalidades: Plataforma SaaS de Reaseguro

Este documento detalla la responsabilidad y funcionalidad de cada archivo creado en el proyecto, organizado por capas de la arquitectura.

## 📂 Backend (Python / FastAPI)

### 📁 `app/`
- **`main.py`**: El orquestador de la API. Contiene la configuración de FastAPI, los endpoints públicos y protegidos, la integración del flujo de datos desde la carga hasta el contrato, y la gestión de la sesión de base de datos. Incluye ahora los endpoints de validación estadística y back-testing. Implementa un servidor de WebSockets para notificaciones en tiempo real.
- **`auth.py`**: Módulo de seguridad. Gestiona la creación y validación de tokens JWT, el cifrado de contraseñas con Bcrypt y la dependencia `get_current_user` que asegura la autenticación y el aislamiento multi-tenant.
- **`database.py`**: Capa de persistencia. Define la conexión a PostgreSQL mediante SQLAlchemy y los modelos de datos (`Company`, `User`, `Claim`, `AuditLog` y la nueva tabla `Premium` para gestión de primas).
- **`worker.py`**: Módulo de procesamiento asíncrono. Gestiona la cola de tareas mediante Celery y Redis. Ejecuta la carga masiva de CSVs y los cálculos actuariales complejos en segundo plano para evitar bloqueos de la API.
- **`modules/`**:
    - **`diagnostics/validator.py`**: El "filtro" de calidad. Valida que los CSVs cargados tengan las columnas correctas, fechas válidas y que no existan montos negativos, asegurando la integridad de los datos actuariales.
    - **`actuarial/engine.py`**: El cerebro de la plataforma. Contiene la lógica de ciencia actuarial:
        - Construcción de Triángulos mediante agregaciones SQL.
        - Cálculo de IBNR con soporte multi-modelo: **Chain Ladder**, **Bornhuetter-Ferguson** y **Cape Cod**.
        - Sistema de **Back-testing** mediante simulación de retroceso temporal.
        - Análisis de Severidad y detección de Outliers (IQR).
        - Optimización de Retenciones basada en capital.
        - Ingeniería de selección de contrato (XoL vs QS).
        - Generación de la estructura del borrador de contrato.

## 📂 Frontend (Next.js 14)

### 📁 `app/` (App Router)
- **`layout.tsx`**: Root Layout. Enuelve la aplicación en el `Providers` de TanStack Query y define los metadatos globales.
- **`providers.tsx`**: Configuración del `QueryClientProvider`. Gestiona la caché global de datos actuariales y la estrategia de re-fetch.
- **`middleware.ts`**: Guardián de seguridad. Intercepta peticiones para validar la sesión vía cookies y redirigir al `/login` si no hay token válido.
- **`/(auth)/login/page.tsx`**: Pantalla de acceso. Gestiona la autenticación, la persistencia del token en cookies y la redirección al dashboard.
- **`/(dashboard)/layout.tsx`**: Shell ejecutivo. Contiene la navegación lateral (Sidebar), el header de usuario y la estructura de la zona de contenido.
- **`/(dashboard)/dashboard/page.tsx`**: Panel de Control. Integra la visión global de reservas y optimización de reaseguro.
- **`/(dashboard)/actuarial/page.tsx`**: Página de la Calculadora Actuarial. Gestiona la selección de ramos/métricas y la interacción con el `TriangleViewer`.
- **`/(dashboard)/backtesting/page.tsx`**: Página de Validación Estadística. Orquestra la carga de datos de retroceso y la visualización en el `BacktestingViewer`.

### 📁 `components/` (Client Components)
- **`actuarial/TriangleViewer.js`**: Módulo interactivo de la calculadora. Renderiza el triángulo de siniestralidad y la curva de desarrollo utilizando **Apache ECharts**.
- **`actuarial/ActuarialDashboard.js`**: Centro de visualización ejecutiva. Renderiza KPIs y la comparativa de reservas mediante **Apache ECharts**.
- **`actuarial/ValidationViewer.js`**: Componente de auditoría estadística. Visualiza el error de reserva y comparativas estimado vs real con **Apache ECharts**.
- **`actuarial/BacktestingViewer.js`**: Visualizador de validación. Muestra la precisión del modelo mediante barras agrupadas de ECharts.
- **`shared/`**: Componentes reutilizables de la UI (Botones, Inputs, Modales).

### 📁 `services/`
- **`api.js`**: Capa de comunicación adaptativa. Soporta llamadas tanto desde Server Components como Client Components, gestionando automáticamente los headers de autorización y la redirección por token expirado.

### 📁 `hooks/`
- Custom hooks para la lógica de negocio actuarial y gestión de estados de TanStack Query.

## 📂 Infraestructura y Despliegue (DevOps)

- **`Dockerfile`**: Instrucciones para empaquetar el backend en una imagen ligera de Python 3.12, optimizando la instalación de dependencias actuariales.
- **`frontend/Dockerfile`**: Implementa un build de dos etapas: compila React con Node y sirve el resultado mediante un servidor Nginx de alta eficiencia.
- **`docker-compose.yml`**: Orquestrador local y de servidor. Levanta y conecta la base de datos PostgreSQL, el Backend y el Frontend en una red aislada.
- **`requirements.txt`**: Listado de todas las dependencias de Python necesarias para que el sistema sea reproducible en cualquier entorno.
- **`nginx.conf`**: Configuración del proxy inverso para manejar el tráfico HTTPS, redirigir peticiones al backend y optimizar la entrega del frontend.
- **`.github/workflows/deploy.yml`**: Pipeline de CI/CD que automatiza la construcción de imágenes y el despliegue en el servidor vía SSH cada vez que se sube código a GitHub.

## 📂 Documentación y Datos

- **`ARCHITECTURE.md`**: Documento técnico que describe la visión general, el stack tecnológico y la lógica de diseño de la plataforma.
- **`RESUMEN_CAMBIOS_SISTEMA.md`**: Historial detallado de todas las modificaciones técnicas y estabilizaciones realizadas.
- **`ANALISIS_PLATAFORMA.txt`**: Análisis exhaustivo de la arquitectura y el flujo de trabajo del sistema.
- **`ESTRATEGIA_EVOLUCION_ACTUARIAL.md`**: Hoja de ruta para la evolución del motor actuarial y la gestión de reaseguro.
- **`ejemplo_siniestros.csv`**: Dataset de prueba diseñado para validar la detección de siniestros catastróficos y la selección de contratos XoL.
