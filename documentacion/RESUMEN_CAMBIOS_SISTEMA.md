# Resumen de Cambios del Sistema - Plataforma de Optimización de Reaseguro

Este documento es la fuente de verdad sobre la evolución técnica de la plataforma, desde la estabilización inicial hasta la culminación de la Estrategia de Optimización en 4 etapas.

## 🛠️ Historial de Estabilización y Recuperación (Mayo 2026)
Antes de iniciar las etapas de optimización, el sistema pasó por un proceso de blindaje:
- **Rollback Estratégico:** Regreso al commit estable tras detectar fallos masivos de hidratación y seguridad en intentos de migración global.
- **Blindaje de Seguridad:** Implementación de validación real de JWT y limpieza de sesiones para eliminar bucles de redirección.
- **Optimización de Herramientas:** Migración de `npm` $\rightarrow$ `pnpm` para garantizar determinismo en dependencias y velocidad de build.
- **Saneamiento de UI:** Implementación del patrón `isMounted` para resolver conflictos de hidratación entre servidor y cliente.

---

## 🚀 Implementación de la Estrategia de Optimización (4 Etapas)

### Etapa 1: Seguridad y Gestión de Usuarios
**Objetivo:** Aislamiento total de datos y control de acceso profesional.
- **Multi-Tenancy:** Implementación de aislamiento basado en `company_id` en todas las capas (DB $\rightarrow$ API $\rightarrow$ UI).
- **RBAC (Role-Based Access Control):** Creación de roles `admin` y `user` con permisos diferenciados (ej. solo admins pueden crear usuarios).
- **Autenticación:** Flujo completo con JWT, incluyendo endpoints de `/token` y validación de sesión `/auth/me`.
- **Auditoría:** Sistema de `AuditLog` para trazabilidad de acciones críticas.

### Etapa 2: Ingesta de Datos y Gobernanza
**Objetivo:** Asegurar que los datos actuariales cargados sean íntegros y normalizados.
- **Carga Robusta:** Implementación de detección automática de encoding (UTF-8/Latin-1) y separadores (`,` o `;`).
- **Validación Rigurosa:** Módulo de diagnóstico (`validate_insurance_csv`) que verifica la integridad de columnas obligatorias y coherencia de fechas.
- **Normalización:** Saneamiento de montos numéricos y fechas para evitar errores de parsing en el motor.

### Etapa 3: Modernización de Visualización y Performance
**Objetivo:** Escalabilidad de UI y eficiencia de despliegue.
- **Gestión de Estado:** Integración de `@tanstack/react-query` para caché eficiente e invalidación de datos, eliminando llamadas redundantes a la API.
- **Gráficos Avanzados:** Implementación de Apache ECharts para la representación dinámica de triángulos y distribuciones de severidad.
- **Migración de Gestor de Paquetes:** Cambio de `npm` $\rightarrow$ `pnpm` para optimizar el uso de disco y acelerar los tiempos de instalación en Docker.
- **Infraestructura Docker:** Optimización de imágenes Alpine y uso de `pnpm` mediante `corepack` para reducir tiempos de CI/CD.

### Etapa 4: Optimización del Motor Actuarial
**Objetivo:** Maximizar la precisión numérica y el rendimiento de los cálculos de IBNR.
- **Vectorización con NumPy:** Sustitución de bucles Python por operaciones vectorizadas en el cálculo de LDFs y pérdidas ultimate.
- **Cálculos Avanzados:** Implementación de métodos Bornhuetter-Ferguson y Cape Cod integrados con datos de primas.
- **Análisis de Contratos:** Lógica de diseño de contratos basada en el Coeficiente de Variación (CV) para recomendar **Excess of Loss (XoL)** o **Quota Share (QS)**.

---

## ⚠️ Excepciones Críticas y Decisiones de Diseño

### 1. El "Caso Polars": Rollback por Inestabilidad Numérica
Se realizó un intento de migración total del motor a Polars para ganar velocidad de procesamiento.
- **El Problema:** Se detectó que el pivoteo de datos y la agregación de factores en Polars introducía micro-corrupciones numéricas que alteraban los resultados de los triángulos y el IBNR.
- **La Solución:** Reversión inmediata al núcleo de **Pandas** para el procesamiento de estructuras y pivoteo, manteniendo **NumPy** exclusivamente para las operaciones matemáticas pesadas.
- **Lección:** En actuaría, la precisión del centavo es prioritaria sobre la velocidad de milisegundos.

### 2. Estrategia de Carga Híbrida (SQL $\leftrightarrow$ RAM)
Para evitar la saturación de memoria RAM al procesar millones de filas (Big Data) sin perder la capacidad de análisis detallado:
- **Agregación en SQL:** El cálculo de triángulos y el IBNR se basan en `get_summarized_claims`, que realiza la suma y el agrupamiento directamente en PostgreSQL.
- **Extracción Quirúrgica:** Para análisis que requieren datos crudos (como la distribución de severidad o el cálculo de reservas contables), el sistema no carga el DataFrame completo, sino que ejecuta queries SQL específicas para traer únicamente la columna necesaria (`amount_paid` o `amount_reserve`).
- **Resultado:** Rendimiento de base de datos con flexibilidad de análisis de memoria.

---
*Última actualización: 2026-05-14*
