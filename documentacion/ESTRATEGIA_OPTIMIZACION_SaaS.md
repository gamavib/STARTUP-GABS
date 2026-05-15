# Estrategia de Optimización SaaS: Blueprint de Ingeniería y Evolución Estable

## 1. Análisis de la Base Operativa (Estado Actual)
El sistema se encuentra en el commit `fc3959c`, el cual es la última versión con **estabilidad funcional comprobada**.

### Flujo Core (The Golden Path):
`CSV Ingestion` $\rightarrow$ `FastAPI/Pandas` $\rightarrow$ `PostgreSQL (Multi-tenant)` $\rightarrow$ `Actuarial Engine` $\rightarrow$ `Frontend (React/Next.js)`.

### Análisis de Dependencias y Riesgos:
- **Frontend (Next.js)**: La transición al App Router es la zona de mayor riesgo. El uso de `localStorage` y `cookies` en componentes de servidor provoca errores de hidratación.
- **Backend (FastAPI/Python 3.12)**: Estabilidad alta. La dependencia de Pandas es robusta pero presenta cuellos de botella en datasets masivos.
- **Infraestructura (Docker/K8s)**: La orquestación es correcta, pero el manejo de volúmenes y caché de imágenes puede causar que cambios en el código no se reflejen inmediatamente.
- **Seguridad (JWT/RLS)**: El aislamiento por `company_id` es la piedra angular. Cualquier cambio en la gestión de tokens debe garantizar que el `company_id` se mantenga íntegro.

---

## 2. Matriz de Prioridades de Implementación

La evolución se divide en etapas estrictas. **No se avanzará a la siguiente etapa hasta que la anterior haya sido validada en el entorno de despliegue.**

### Etapa 1: Estabilización de Acceso y Gestión de Usuarios (Prioridad: CRÍTICA)
*Objetivo: Garantizar que el usuario pueda entrar, salir y gestionar su equipo sin bucles de redirección.*
- **Implementación de `POST /users`**: Permitir la creación de usuarios adicionales por el administrador.
- **Middleware de Seguridad Robusto**: Implementar validación de expiración de JWT en el servidor (Edge) sin depender la redirección solo de la existencia de la cookie.
- **Sincronización de Sesión**: Unificar el manejo de tokens evitando la "resurrección" desde `localStorage`.

### Etapa 2: Restauración y Blindaje de Ingesta de Datos (Prioridad: ALTA)
*Objetivo: Asegurar que la carga de datos sea infalible y visible.*
- **UI de Carga de CSV**: Implementar el componente de carga en la Calculadora Actuarial con feedback de estado (Subiendo $\rightarrow$ Procesando $\rightarrow$ Completado).
- **Validación de Datos**: Reforzar la detección de encodings y separadores en el backend para evitar fallos en la carga de archivos reales.
- **Sincronización Reactiva**: Usar TanStack Query para refrescar los ramos automáticamente tras la carga.

### Etapa 3: Modernización de Visualización y Performance (Prioridad: MEDIA)
*Objetivo: Pasar de tablas estáticas a dashboards ejecutivos de alta performance.*
- **Migración a Apache ECharts**: Sustituir Recharts por ECharts para manejar la renderización de miles de puntos de datos sin lag.
- **Sincronización de Estado**: Implementar la gestión de caché inteligente con TanStack Query para evitar peticiones redundantes al backend.
- **Solución de Hidratación**: Implementar el patrón `isMounted` en todos los componentes que consuman datos del cliente.

### Etapa 4: Optimización del Motor Actuarial (Prioridad: OPTIMIZACIÓN)
*Objetivo: Escalar la capacidad de cálculo para millones de filas.*
- **Migración Pandas $\rightarrow$ Polars**: Sustituir el procesamiento de DataFrames para aprovechar el multithreading.
- **Agregaciones SQL**: Mover la construcción de triángulos directamente a queries de PostgreSQL (`SUM`, `GROUP BY`) para reducir la carga de RAM en el servidor.
- **HPA (Horizontal Pod Autoscaler)**: Configurar el escalado de Workers de Celery basado en la carga de CPU.

---

## 3. Guía de Implementación (Prompts Técnicos)

Para evitar regresiones, cada tarea debe ejecutarse siguiendo estos prompts detallados:

### Prompt para la Etapa 1 (Seguridad)
> "Implementar la creación de usuarios adicionales en `app/main.py` mediante un endpoint `POST /users` protegido por `get_current_user`. Validar que solo el rol 'admin' pueda crear usuarios y que el nuevo usuario herede el `company_id` del administrador. Actualizar `app/schemas.py` con `UserCreate`. Asegurar que la contraseña se cifre con `get_password_hash`. No modificar la lógica de redirección del middleware hasta que esta funcionalidad esté validada."

### Prompt para la Etapa 2 (Carga de CSV)
> "Implementar la interfaz de carga de CSV en `frontend/app/(dashboard)/actuarial/page.tsx`. Crear un botón de carga que utilice `useMutation` de TanStack Query para llamar a `api.uploadCsv`. El componente debe manejar tres estados: IDLE, PENDING (desactivar botón), y SUCCESS (mostrar alerta y ejecutar `invalidateQueries` para los ramos). Implementar la carga mediante `FormData` y asegurar que el token de sesión se envíe en los headers."

### Prompt para la Etapa 3 (Hidratación y UI)
> "Refactorizar el componente `ActuarialPage` para eliminar errores de `Hydration Mismatch`. Implementar un estado `isMounted` mediante `useEffect`. Mover la lectura de `localStorage` dentro del `useEffect` y evitar renderizar cualquier contenido dependiente del token antes de que `isMounted` sea true. Sustituir la renderización de la sesión no autenticada por un loader neutro durante el montaje."

---

## 4. Protocolo de Validación (Anti-Regresión)

Antes de dar por finalizada cualquier etapa, se debe ejecutar el siguiente checklist:
- [ ] **Prueba de Humo**: ¿El usuario puede loguearse y llegar al dashboard?
- [ ] **Prueba de Ingesta**: ¿Un CSV válido se carga y los ramos aparecen en el selector?
- [ ] **Prueba de Aislamiento**: ¿El usuario A puede ver datos de la Empresa A pero NO de la Empresa B?
- [ ] **Prueba de Consola**: ¿La consola del navegador está libre de errores de `Hydration` y `TypeError`?
