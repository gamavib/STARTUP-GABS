import pandas as pd
import chainladder as cl
import numpy as np
from typing import Dict, Any, List

class ActuarialEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.df['fecha_ocurrencia'] = pd.to_datetime(self.df['fecha_ocurrencia'])
        self.df['fecha_reporte'] = pd.to_datetime(self.df['fecha_reporte'])

    def build_triangle(self, ramo: str = None) -> cl.Triangle:
        data = self.df if ramo is None else self.df[self.df['ramo'] == ramo]
        triangle = cl.Triangle(data,
                              origin='fecha_ocurrencia',
                              development='fecha_reporte',
                              value='monto_pagado')
        return triangle

    def calculate_ibnr(self, triangle: cl.Triangle, severity_multiplier: float = 1.0) -> Dict[str, Any]:
        adjusted_triangle = triangle * severity_multiplier
        ld = cl.ChainladderFit(adjusted_triangle)
        ultimate = ld.ultimate_losses
        actual = adjusted_triangle.sum()
        ibnr = ultimate.sum() - actual

        return {
            "actual_losses": float(actual),
            "ultimate_losses": float(ultimate.sum()),
            "ibnr_estimate": float(ibnr),
            "development_factors": ld.development_factors.to_dict()
        }

    def compare_reserves(self, ibnr_estimate: float, ramo: str = None) -> Dict[str, Any]:
        data = self.df if ramo is None else self.df[self.df['ramo'] == ramo]
        reserva_contable = data['monto_reserva'].sum()
        diff = ibnr_estimate - reserva_contable
        ratio = (ibnr_estimate / reserva_contable) if reserva_contable != 0 else 0

        return {
            "reserva_contable": float(reserva_contable),
            "reserva_tecnica_actuarial": float(ibnr_estimate),
            "diferencia": float(diff),
            "ratio_insuficiencia": float(ratio),
            "status": "Suficiente" if diff <= 0 else "Insuficiente"
        }

    def analyze_frequency_severity(self, ramo: str = None) -> Dict[str, Any]:
        data = self.df if ramo is None else self.df[self.df['ramo'] == ramo]
        num_siniestros = len(data)
        num_polizas = data['id_poliza'].nunique()
        total_pagado = data['monto_pagado'].sum()
        frecuencia = num_siniestros / num_polizas if num_polizas > 0 else 0
        severidad = total_pagado / num_siniestros if num_siniestros > 0 else 0

        return {
            "frecuencia": frecuencia,
            "severidad": severidad,
            "total_siniestros": num_siniestros,
            "total_polizas": num_polizas
        }

    def analyze_severity_distribution(self, ramo: str = None) -> Dict[str, Any]:
        """
        Análisis avanzado de severidad para detección de Outliers (Siniestros Catastróficos).
        """
        data = self.df if ramo is None else self.df[self.df['ramo'] == ramo]
        severities = data['monto_pagado']

        if severities.empty:
            return {"error": "No hay datos suficientes"}

        # Cálculo de Outliers usando el método de Interquartile Range (IQR)
        q1 = severities.quantile(0.25)
        q3 = severities.quantile(0.75)
        iqr = q3 - q1
        upper_bound = q3 + 1.5 * iqr

        outliers = severities[severities > upper_bound]

        return {
            "mean_severity": float(severities.mean()),
            "median_severity": float(severities.median()),
            "max_severity": float(severities.max()),
            "outlier_count": int(len(outliers)),
            "outlier_sum": float(outliers.sum()),
            "outlier_percentage": (len(outliers) / len(severities)) * 100,
            "upper_bound_threshold": float(upper_bound)
        }

    def optimize_reinsurance(self, ibnr_estimate: float, capital_available: float) -> Dict[str, Any]:
        suggested_retention = min(capital_available * 0.5, ibnr_estimate)
        ceded_amount = max(0, ibnr_estimate - suggested_retention)

        return {
            "suggested_retention": float(suggested_retention),
            "ceded_amount": float(ceded_amount),
            "retention_percentage": (suggested_retention / ibnr_estimate * 100) if ibnr_estimate != 0 else 0,
            "recommendation": "Transferir excedente al reasegurador para proteger solvencia" if ceded_amount > 0 else "Retención sostenible con capital actual"
        }

    def engineer_contract(self, ramo: str = None, ibnr_estimate: float = 0, retention: float = 0) -> Dict[str, Any]:
        data = self.df if ramo is None else self.df[self.df['ramo'] == ramo]
        severities = data['monto_pagado']
        std_dev = severities.std()
        mean_sev = severities.mean()
        cv = std_dev / mean_sev if mean_sev != 0 else 0
        contract_type = "Excess of Loss (XoL)" if cv > 1.0 else "Quota Share (QS)"

        contract_details = {}
        if contract_type == "Excess of Loss (XoL)":
            contract_details = {
                "priority": retention,
                "limit": ibnr_estimate - retention,
                "structure": "Protección contra siniestros severos"
            }
        else:
            retention_pct = (retention / ibnr_estimate * 100) if ibnr_estimate != 0 else 0
            contract_details = {
                "retention_percentage": retention_pct,
                "cession_percentage": 100 - retention_pct,
                "structure": "Distribución proporcional del riesgo"
            }

        return {
            "suggested_type": contract_type,
            "volatility_index": float(cv),
            "details": contract_details,
            "draft_summary": f"Contrato de {contract_type} basado en volatilidad {cv:.2f}. Retención optimizada en ${retention:,.2f}"
        }

    def generate_contract_draft(self, ramo: str, contract_data: Dict[str, Any], ibnr: float) -> Dict[str, Any]:
        type_name = contract_data["suggested_type"]
        details = contract_data["details"]

        draft = {
            "header": {
                "document_type": "Borrador de Contrato de Reaseguro",
                "ramo": ramo,
                "currency": "USD",
                "version": "1.0-AutoGenerated"
            },
            "technical_basis": {
                "projected_ibnr": ibnr,
                "volatility_index": contract_data["volatility_index"]
            },
            "clauses": []
        }

        if type_name == "Excess of Loss (XoL)":
            draft["clauses"].append({
                "clause": "Prioridad de Retención",
                "value": f"${details['priority']:,.2f}",
                "description": "La aseguradora retiene los primeros siniestros hasta este monto."
            })
            draft["clauses"].append({
                "clause": "Límite de Responsabilidad del Reasegurador",
                "value": f"${details['limit']:,.2f}",
                "description": "El reasegurador cubre el excedente sobre la prioridad hasta este límite."
            })
        else:
            draft["clauses"].append({
                "clause": "Cuota de Retención",
                "value": f"{details['retention_percentage']:.2f}%",
                "description": "La aseguradora retiene el porcentaje indicado de cada siniestro."
            })
            draft["clauses"].append({
                "clause": "Cuota de Cesión",
                "value": f"{details['cession_percentage']:.2f}%",
                "description": "El reasegurador asume el porcentaje indicado del riesgo total."
            })

        return draft
