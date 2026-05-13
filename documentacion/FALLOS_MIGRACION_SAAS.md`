# Registro de Fallos: Migración Estrategia Optimización SaaS

Este documento detalla las regresiones y fallos críticos introducidos durante la implementación de la estrategia de optimización SaaS, los cuales justifican el rollback al commit `fc3959c`.

## 1. Fallos Críticos de Seguridad y Acceso
- **Bucle de Redirección Infinita**: Se implementó un middleware que causaba redirecciones constantes entre `/` $\rightarrow$ `/login` $\rightarrow$ `/dashboard` debido a una validación superficial de la existencia de la cookie `token` sin verificar su validez o expiración.
- **Persistencia Dual Conflictiva**: La coexistencia de tokens en `localStorage` y `Cookies` provocó "resurrecciones" de sesiones inválidas, donde la limpieza de cookies no era efectiva porque el frontend re-inyectaba el token desde el almacenamiento local.
- **Fuga de Acceso**: En el intento de corregir los redireccionamientos, se llegó a un estado donde el Dashboard era accesible sin autenticación real, rompiendo el aislamiento multi-tenant.

## 2. Pérdida de Funcionalidad Core (Regresiones)
- **Eliminación de la UI de Carga de CSV**: A pesar de que el backend mantenía los endpoints, la interfaz de usuario para cargar archivos fue eliminada o no migrada correctamente al App Router de Next.js, dejando la plataforma sin capacidad de ingesta de datos.
- **Errores de Hidratación (Hydration Mismatch)**: La migración a Server Components introdujo conflictos graves entre el renderizado del servidor y el cliente al intentar acceder a `window` o `localStorage` durante el renderizado inicial, provocando la desaparición de componentes críticos de la UI.

## 3. Inestabilidades Técnicas
- **Desajuste de Tipos en la API**: Se introdujeron errores de ejecución como `ramos.map is not a function` debido a que el frontend esperaba un Array mientras que el backend devolvía un Objeto envuelto, evidenciando una falta de sincronización entre la definición de la API y el consumo en el cliente.
- **Inestabilidad en el Entorno Docker**: Problemas de caché en las imágenes y volúmenes que dificultaban la aplicación de parches rápidos en el middleware.

## Conclusión
La migración priorizó la estructura arquitectónica sobre la funcionalidad operativa. El resultado fue una plataforma con una estructura "Enterprise" en papel, pero inoperable en la práctica. Se procede al rollback al commit `fc3959c` para recuperar la funcionalidad base y aplicar las mejoras de forma incremental y validada.
