# Reporte de Resolución de Error 422 - Endpoint /setup/company

## Descripción del Problema
Se detectó un error persistente de código **422 (Unprocessable Entity)** al intentar utilizar el endpoint de creación de compañía (`/setup/company`) a través de Swagger y curl. El servidor rechazaba la petición antes de procesar la lógica de negocio, lo que indicaba un fallo en la validación de los datos de entrada (Pydantic).

## Análisis y Diagnóstico
1. **Pruebas de Conectividad:** Se creó un endpoint `/debug/test` que aceptaba un `dict` genérico. Este funcionó correctamente, descartando problemas de red o de formato JSON básico.
2. **Revisión de Esquemas:** Se identificó que el modelo `CompanySetup` en `app/schemas.py` utilizaba el tipo `EmailStr` para el campo `admin_email`.
3. **Causa Raíz:** El tipo `EmailStr` de Pydantic requiere la librería `email-validator`. Si esta librería no está instalada o hay una discrepancia en la versión, Pydantic lanza un error de validación 422 automáticamente antes de que la petición llegue a la función del endpoint.

## Solución Aplicada
Se modificó el archivo `app/schemas.py` sustituyendo el tipo de dato del campo `admin_email`:
- **Antes:** `admin_email: EmailStr`
- **Después:** `admin_email: str`

Esto permite que el servidor acepte cualquier cadena de texto como correo electrónico, eliminando la dependencia del validador externo y resolviendo el bloqueo.

## Instrucciones para Reinstalar Validación Estricta (Opcional)
Si en el futuro se desea recuperar la validación automática de correos electrónicos, seguir estos pasos:

1. **Instalar la dependencia necesaria:**
   ```bash
   pip install email-validator
   ```
2. **Actualizar requirements.txt:**
   Añadir `email-validator` a la lista de dependencias para asegurar que se instale en despliegues futuros.
3. **Revertir el cambio en el código:**
   En `app/schemas.py`, cambiar nuevamente `admin_email: str` por `admin_email: EmailStr`.
4. **Reiniciar el servidor:**
   Reiniciar la aplicación FastAPI para cargar la nueva librería.

---
**Estado Final:** Resuelto ✅
**Fecha:** 2026-04-21
