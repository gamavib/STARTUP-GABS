# Resumen de Cambios Técnicos y Estabilización del Sistema - SaaS Actuarial

Este documento detalla las modificaciones críticas realizadas para estabilizar el sistema, resolver errores de conexión, autenticación y fallos en el motor actuarial.

## 1. Capa de Infraestructura y Conectividad (Docker)
- **Resolución de Socket:** Se corrigió la conexión al motor de Docker en macOS cambiando el contexto de Docker a `desktop-linux` y asegurando que el enlace simbólico `/var/run/docker.sock` apuntara correctamente al socket de Docker Desktop.
- **Sincronización de Código:** Se implementó un flujo de limpieza total (`docker-compose down -v`, `docker rmi`, `docker builder prune`) para eliminar la caché de capas y asegurar que el código editado en el host se refleje exactamente en el contenedor.

## 2. Autenticación y Seguridad
- **CORS (Cross-Origin Resource Sharing):** Se implementó `CORSMiddleware` en `app/main.py` permitiendo todos los orígenes (`*`). Sin esto, el navegador bloqueaba las peticiones del frontend al backend.
- **Formato de Login:** Se corrigió la llamada al endpoint `/token`.
    - **Problema:** El frontend enviaba datos como JSON/URLSearchParams, pero la librería `OAuth2PasswordRequestForm` de FastAPI requiere estrictamente `application/x-www-form-urlencoded`.
    - **Solución:** Se cambió en `frontend/src/services/api.js` el uso de `URLSearchParams` por un objeto `FormData` con la cabecera de contenido explícita.

## 3. Motor Actuarial y Manejo de Datos
- **Eliminación de la librería `chainladder`:**
    - **Causa:** La librería presentaba incompatibilidades críticas con la versión de Pandas en el contenedor, lanzando errores persistentes de `KeyError: None` y `TypeError: Chainladder() takes no arguments`.
    - **Sustitución:** Se implementó la lógica de **Chain Ladder nativa** usando Pandas y Numpy.
    - **Lógica implementada:**
        - `build_triangle`: Genera la matriz de desarrollo mediante `pivot_table` (Año de Origen vs Año de Desarrollo).
        - `calculate_ibnr`: Calcula los Factores de Desarrollo (LDF) mediante la razón de sumas de columnas y proyecta la pérdida final (Ultimate) multiplicando la última diagonal por los factores restantes.
- **Saneamiento de CSV:**
    - Implementación de detección de encoding (`utf-8` $\rightarrow$ `latin-1`).
    - Limpieza de espacios en blanco en encabezados de columnas (`.strip()`).
    - Conversión forzada de montos a numéricos eliminando caracteres no deseados para evitar errores de comparación `str` vs `int`.

---

## 🚀 PROMPT DE RESTAURACIÓN (Para IA)

Si necesitas aplicar estos cambios sobre una versión inicial del código, utiliza el siguiente prompt:

> "Actúa como un experto en FastAPI, React y Actuaría. Necesito actualizar el proyecto con las siguientes correcciones críticas de estabilidad:
> 
> 1. **CORS:** En `app/main.py`, añade `CORSMiddleware` permitiendo todos los orígenes, métodos y cabeceras inmediatamente después de instanciar `FastAPI()`.
> 2. **Auth Frontend:** En `frontend/src/services/api.js`, modifica la función `login` para que envíe los datos usando un objeto `FormData` y la cabecera `'Content-Type': 'application/x-www-form-urlencoded'`.
> 3. **Motor Actuarial Nativo:** En `app/modules/actuarial/engine.py`, elimina totalmente la dependencia de la librería `chainladder`. Implementa el cálculo de IBNR manualmente:
>    - Crea el triángulo usando `df.pivot_table` con `origin_year` y `dev_year`.
>    - Calcula los LDFs como el ratio de la suma de la columna n+1 sobre la columna n.
>    - Calcula el IBNR como la diferencia entre la suma de las pérdidas proyectadas (Ultimate) y las pérdidas actuales.
> 4. **Carga de CSV Robusta:** En `app/main.py`, el endpoint `/upload-csv` debe:
>    - Intentar decodificar el archivo en `utf-8` y fallback a `latin-1`.
>    - Hacer `.strip()` a los nombres de las columnas.
>    - Convertir `monto_pagado` y `monto_reserva` a float usando `pd.to_numeric` con `errors='coerce'`.
> 
> Asegúrate de que el código sea compatible con Python 3.12 y Pandas 2.0+."
