# Estrategia de Optimización y Escalabilidad: Plataforma SaaS de Reaseguro

Este documento detalla la hoja de ruta técnica para transformar la plataforma actual en una solución competitiva de grado Enterprise, optimizando el rendimiento, la seguridad y la experiencia de usuario.

---

## 1. Análisis de Arquitectura Actual (Histórico)
La plataforma operaba bajo un modelo de **Monolito Modular** con los siguientes riesgos:
- **Bloqueo de Hilos:** Cálculos pesados de Pandas/NumPy bloqueaban la API.
- **Experiencia de Usuario (UX):** Procesamiento síncrono de CSVs generaba timeouts.
- **Seguridad de Datos:** Riesgo de fuga de datos por filtros manuales de `company_id`.
- **Frontend Limitado:** Renderizado puramente en cliente lento con grandes volúmenes de datos.

---

## 2. Implementaciones Realizadas (Estado Final)

### A. Backend & Engine Actuarial
1. **Asincronismo con Celery & Redis:** Implementado. Desacoplamiento total de la recepción de datos y el procesamiento.
2. **Migración a Polars:** Implementado. Sustitución de Pandas por Polars en el motor de cálculo para procesamiento multihilo.
3. **Seguridad de Nivel de Fila (RLS):** Implementado en PostgreSQL para aislamiento total de datos por tenant.

### B. Frontend & Visualización
1. **Migración a Next.js 14 (App Router):** Implementado. Transición de SPA a arquitectura híbrida con Server Components y Client Components.
2. **Sincronización de Datos con TanStack Query:** Implementada caché inteligente y gestión de estados asíncronos para los cálculos actuariales.
3. **Upgrade de Visualización (Apache ECharts):** Migración total de Recharts a ECharts, permitiendo la renderización fluida de miles de puntos de datos en heatmaps y curvas de desarrollo.
4. **Seguridad de Acceso**: Implementación de Middleware de servidor basado en Cookies y JWT para protección de rutas.

### C. Infraestructura y Observabilidad
1. **Orquestación con Kubernetes (K8s):** Implementado. Migración de Docker Compose a un cluster K8s.
2. **Auto-scaling de Workers (HPA)**: Configurado el Horizontal Pod Autoscaler para escalar la capacidad de cálculo actuarial basado en el uso de CPU.
3. **Aislamiento de Capas**: Separación de servicios en capas de Datos, Procesamiento y Presentación mediante Services e Ingress.

---

## 3. Plan de Implementación (Histórico de Ejecución)

### Fase 1: Estabilidad y Asincronismo ✅ COMPLETADO
- Configuración de Redis y Celery Workers.
- Refactorización de endpoints de carga de CSV para que sean asíncronos.
- Implementación de endpoint de "Estado de Tarea" (`/tasks/{id}`).

### Fase 2: Rendimiento y Seguridad Core ✅ COMPLETADO
- Migración de funciones críticas de Pandas $\rightarrow$ Polars.
- Implementación de políticas de RLS en PostgreSQL.
- Implementación de caché de resultados actuariales en Redis.

### Fase la 3: Modernización de Interfaz y Escala ✅ COMPLETADO
- Migración de React $\rightarrow$ Next.js 14 (App Router).
- Sustitución de Recharts $\rightarrow$ Apache ECharts.
- Despliegue en cluster de Kubernetes con HPA para Workers.
- Implementación de Middleware de seguridad y flujo de Cookies/JWT.

---

## 4. Guía de Operación y Escalabilidad

### Escalado del Motor Actuarial
El sistema escala automáticamente los workers de Celery cuando la carga de CPU supera el 70%. 
- **Mínimo de réplicas:** 2
- **Máximo de réplicas:** 10
- **Métrica de disparo:** Average CPU Utilization.

### Flujo de Seguridad
1. El usuario se autentica $\rightarrow$ Backend emite JWT.
2. Frontend guarda JWT en `localStorage` y en una `Cookie`.
3. `middleware.ts` verifica la cookie en cada request al servidor.
4. Si el token expira, el interceptor de Axios redirige al usuario al `/login`.
