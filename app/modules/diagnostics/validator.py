from pydantic import BaseModel, Field
from typing import List
import pandas as pd

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    row_count: int = 0

def validate_insurance_csv(df: pd.DataFrame) -> ValidationResult:
    """
    Valida que el archivo CSV cumpla con los estándares de gobernanza
    requeridos para el procesamiento actuarial.
    """
    required_columns = {
        'id_siniestro', 'fecha_ocurrencia', 'fecha_reporte',
        'monto_pagado', 'monto_reserva', 'ramo', 'id_poliza'
    }

    # 1. Verificar columnas obligatorias
    missing_cols = required_columns - set(df.columns)
    if missing_cols:
        return ValidationResult(
            is_valid=False,
            errors=[f"Faltan columnas requeridas: {', '.join(missing_cols)}"]
        )

    errors = []

    # 2. Validación de fechas ( intentamos convertir para verificar formato)
    try:
        pd.to_datetime(df['fecha_ocurrencia'])
        pd.to_datetime(df['fecha_reporte'])
    except Exception as e:
        errors.append(f"Error en formato de fechas: {str(e)}")

    # 3. Validación de montos (No se permiten valores negativos en reservas o pagos)
    if (df[['monto_pagado', 'monto_reserva']] < 0).any().any():
        errors.append("Se encontraron montos negativos en pagos o reservas, lo cual es actuarialmente inconsistente.")

    # 4. Verificar que no haya valores nulos en campos críticos
    critical_cols = ['id_siniestro', 'fecha_ocurrencia', 'monto_pagado']
    if df[critical_cols].isnull().any().any():
        errors.append("Se detectaron valores nulos en columnas críticas (id_siniestro, fecha_ocurrencia o monto_pagado).")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        row_count=len(df)
    )
