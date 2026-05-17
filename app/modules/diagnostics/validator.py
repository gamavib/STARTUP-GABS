from pydantic import BaseModel, Field
from typing import List
import pandas as pd

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    row_count: int = 0

def winsorize_data(df: pd.DataFrame, columns: List[str], limits: float = 0.05) -> pd.DataFrame:
    """
    Limpia outliers mediante Winsorización: reemplaza los valores extremos
    por los percentiles definidos en limits (ej. 0.05 para 5% y 95%).
    """
    df_win = df.copy()
    for col in columns:
        if col in df_win.columns:
            lower_limit = df_win[col].quantile(limits)
            upper_limit = df_win[col].quantile(1 - limits)
            df_win[col] = df_win[col].clip(lower=lower_limit, upper=upper_limit)
    return df_win


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
        pd.to_datetime(df['fecha_ocurrencia'], dayfirst=True)
        pd.to_datetime(df['fecha_reporte'], dayfirst=True)
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
