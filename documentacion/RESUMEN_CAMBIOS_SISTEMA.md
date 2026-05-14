# Resumen de Cambios Técnicos y Estabilización del Sistema - SaaS Actuarial

Este documento detalla las modificaciones críticas realizadas para estabilizar el sistema, resolver errores de conexión, autenticación y la implementación del módulo interactivo de cálculo actuarial.

## 1. Capa de Infraestructura y Conectividad (Docker)
- **Resolución de Socket:** Se corrigió la conexión al motor de Docker en macOS cambiando el contexto de Docker a `desktop-linux` y asegurando que el enlace simbólico `/var/run/docker.sock` apuntara correctamente al socket de Docker Desktop.
- **Sincronización de Código:** Se implementó un flujo de limpieza total (`docker-compose down -v`, `docker rmi`, `docker builder prune`) para eliminar la caché de capas y asegurar que el código editado en el host se refleje exactamente en el contenedor.

## 2. Autenticación y Seguridad
- **CORS (Cross-Origin Resource Sharing):** Se implementó `CORSMiddleware` en `app/main.py` permitiendo todos los orígenes (`*`).
- **Formato de Login:** Se corrigió la llamada al endpoint `/token` usando `FormData` y la cabecera `application/x-www-form-urlencoded`.
- **Gestión de Tokens en Frontend:** Se migró la comunicación de la API en el frontend a un modelo de **Objetos de Configuración** en lugar de argumentos posicionales, eliminando errores de `undefined` en los headers de autorización y resolviendo fallos de 401 Unauthorized.

## 3. Motor Actuarial y Calculadora Interactiva
- **Eliminación de la librería `chainladder`:** Se sustituyó por una implementación nativa en Pandas y Numpy para evitar incompatibilidades de versiones.
- **Saneamiento de CSV:** Implementación de detección de encoding (`utf-8` $\rightarrow$ `latin-1`), limpieza de columnas y conversión robusta de tipos numéricos. Soporte para separadores `,` y `;`.
- **Optimización de Big Data (5M+ filas):** 
    - Migración de la agregación de datos desde la memoria RAM de Python hacia el motor de la base de datos PostgreSQL utilizando `SUM` y `GROUP BY` mediante SQLAlchemy.
    - Implementación de `get_summarized_claims` para reducir la carga de datos antes de procesar los triángulos.
    - Adición de índices en la tabla `claims` (`company_id`, `ramo`, `occurrence_date`, `report_date`) para optimizar la velocidad de respuesta.
- **Modelos de Proyección Avanzados:**
    - **Soporte Multi-Modelo:** El motor ahora soporta **Chain Ladder**, **Bornhuetter-Ferguson (BF)** y **Cape Cod**, permitiendo al actuario elegir el modelo más adecuado según la volatilidad de la cartera.
    - **Lógica BF y Cape Cod:** Implementación de la expectativa *a priori* basada en primas emitidas y Loss Ratios esperados.
    - **Soporte de Primas:** Creación de la tabla `Premium` en la base de datos para almacenar la prima emitida por año y ramo.
- **Módulo de Calculadora Actuarial (SaaS v2):**
    - **Navegación por Pestañas:** Se implementó un sistema de vistas (`activeTab`) en `App.js` para separar el "Análisis Ejecutivo" de la "Calculadora Actuarial", el módulo de "Validación Estadística" y el de "Renovación de Contrato".
    - **Visualización de Triángulos Expandida:** El visor de triángulos pasó de ser un modal a una vista de página completa optimizada.
    - **Métricas Dinámicas:** El sistema ahora permite alternar entre métricas de **Pagados**, **Reservas** y **Total (Pagados + Reservas)** en tiempo real.
    - **Sincronización de Contexto:** El estado del `ramo` seleccionado se sincroniza globalmente entre todas las pestañas. Se implementó la recuperación dinámica de ramos desde la API para alimentar un menú desplegable (`<select>`) en el filtro, eliminando la entrada de texto manual.
    - **Interacción LDF (Chain Ladder Interactivo):**
        - Implementación de un nuevo endpoint `POST /actuarial/calculate-ibnr`.
        - Capacidad de editar los **Factores de Desarrollo (LDF)** directamente en la tabla de totales.
        - Recálculo instantáneo de la estimación de **IBNR y Reserva Técnica** basado en los ajustes manuales del actuario.
- **Validación Estadística y Back-testing:**
    - **Simulación de Retroceso:** Implementación de la lógica de reconstrucción histórica para comparar reservas estimadas en el pasado contra pagos reales actuales.
    - **Visualización de Auditoría:** Integración de `Recharts` en el frontend para mostrar la evolución del error de reserva y comparativas Estimado vs Real.
    - **KPIs de Precisión:** Cálculo de Error Medio Absoluto (MAE) y Ratio de Suficiencia Global.
- **Renovación de Contratos de Reaseguro:**
    - **Flujo Automatizado:** Implementación de `/actuarial/renew` y `/actuarial/contracts/activate` para gestionar la transición de contratos.
    - **Sugerencia de Contrato:** Lógica basada en la volatilidad (CV) para recomendar contratos **Excess of Loss (XoL)** o **Quota Share (QS)**.
    - **Generación de Borradores:** Implementación de la generación de borradores técnicos con cláusulas automáticas, incluyendo un sistema de *fallback* para asegurar la generación del documento incluso con datos limitados.
- **Estabilización de Endpoints:** Corrección de errores `KeyError` y `404 Not Found` asegurando que los análisis de volatilidad y severidad utilicen datos brutos mientras que los cálculos de triángulos utilicen datos resumidos. Se eliminaron decoradores de ruta duplicados en la API.

---

## 🚀 PROMPT DE RESTAURACIÓN (Para IA)

Si necesitas aplicar estos cambios sobre una versión inicial del código, utiliza el siguiente prompt:

> "Actúa como un experto en FastAPI, React y Actuaría. Necesito actualizar el proyecto con las siguientes correcciones y funcionalidades:
> 
> 1. **CORS & Auth:** En `app/main.py`, añade `CORSMiddleware` (*). En `frontend/src/services/api.js`, modifica las funciones de API para que reciban un objeto de configuración `{ ramo, metric, token }` y envíen el token estrictamente en la cabecera `Authorization: Bearer`.
> 2. **Optimización Big Data & Motor Actuarial:** 
>    - Implementa la agregación de datos directamente en SQL (PostgreSQL) mediante `SUM` y `GROUP BY` en un helper `get_summarized_claims` para soportar millones de filas sin colapsar la RAM.
>    - Elimina la librería `chainladder` en `app/modules/actuarial/engine.py`. Implementa la lógica de Chain Ladder nativa en Pandas/Numpy, permitiendo el uso de `custom_ldfs` para el cálculo del Ultimate y el IBNR.
>    - Añade soporte para los modelos **Bornhuetter-Ferguson** y **Cape Cod**, integrando una tabla de primas en la DB y permitiendo la selección del método vía API.
>    - Implementa la lógica de **Back-testing** (Simulación de Retroceso) en el motor para comparar estimaciones pasadas vs reales.
>    - Asegura que los métodos de análisis de severidad y volatilidad utilicen el DataFrame bruto, mientras que la construcción de triángulos use el resumido.
> 3. **Carga de CSV Robusta:** En `app/main.py`, el endpoint `/upload-csv` debe soportar fallback de encoding (`utf-8` $\rightarrow$ `latin-1`), detección automática de separadores (`,` o `;`), hacer `.strip()` a columnas y usar `pd.to_numeric` para los montos.
> 4. **Sistema de Pestañas y Calculadora:**
>    - En `App.js`, implementa un estado `activeTab` para alternar entre 'executive', 'actuarial' y 'validation'.
>    - Convierte `TriangleViewer.js` en una vista de página completa (no modal) que permita cambiar la métrica (paid, reserve, total) y el método de proyección (CL, BF, CC).
>    - Integra inputs numéricos en la fila de totales del triángulo para editar los LDFs y conectar esto al endpoint `POST /actuarial/calculate-ibnr` para mostrar el IBNR ajustado en tiempo real.
>    - Crea un componente de validación con `recharts` para visualizar el error de reserva y los KPIs de precisión.
> 
> Asegúrate de que la base de datos sea compatible con PostgreSQL 15 y el código compatible con Python 3.12 y Pandas 2.0+".

---

## 🔄 Historial de Estabilización y Recuperación (Mayo 2026)

Se detectaron regresiones críticas durante el intento de implementar la "Estrategia de Optimización SaaS", lo que llevó a un proceso de rollback y re-estabilización.

### 1. Rollback a Versión Estable
- **Acción**: Regreso al commit `fc3959c` tras detectar fallos inaceptables en la funcionalidad core.
- **Motivación**: Pérdida de la interfaz de carga de CSV, errores de hidratación masivos en el frontend y bucles de redirección infinitos en la seguridad.
- **Documentación**: Se creó `documentacion/FALLOS_MIGRACION_SAAS.md` para registrar las lecciones aprendidas.

### 2. Reestructuración Estratégica
- **Nuevo Plan de Evolución**: Creación de `ESTRATEGIA_OPTIMIZACION_SaaS.md`, cambiando la migración masiva por un enfoque **Incremental y Validado**.
- **Soporte Actuarial**: Unificación de la hoja de ruta técnica en `ESTRATEGIA_EVOLUCION_ACTUARIAL.md`, alineando la plataforma con los estándares de Swiss Re y Patria Re (Solvencia II, TCR, Burn-through).
- **Actualización de Arquitectura**: El archivo `ARCHITECTURE.md` fue actualizado para reflejar la base estable actual y la ruta de migración gradual.

### 3. Blindaje de Seguridad y Dependencias
- **Migración a pnpm**: Eliminación total de la dependencia de `npm` para evitar vulnerabilidades asociadas a hacks de la plataforma. Implementación de `pnpm` mediante `corepack` en el `Dockerfile`.
- **Corrección de Middleware**: Implementación de validación real de JWT (decodificación de payload y chequeo de expiración) en el servidor, eliminando la dependencia de la simple existencia de la cookie.
- **Solución de Hidratación**: Implementación del patrón de montaje (`isMounted`) en componentes críticos para evitar conflictos entre el renderizado del servidor y el cliente.
- **Saneamiento de Sesiones**: Implementación de limpieza agresiva de tokens en el `LoginPage` para romper bucles de "resurrección de sesión" desde el `localStorage`.
 y el código compatible con Python 3.12 y Pandas 2.0+."
