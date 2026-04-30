import pandas as pd
import numpy as np
from typing import Dict, Any, List

class ActuarialEngine:
    def __init__(self, df_summarized: pd.DataFrame):
        """
        The engine now expects a summarized DataFrame (origin_year, dev_year, total)
        instead of raw claim data.
        """
        self.df = df_summarized.copy()
        # No longer need to convert dates to datetime because the DB already provides years


    def build_triangle(self, ramo: str = None, metric: str = 'paid') -> pd.DataFrame:
        """
        Transforms the summarized DataFrame into a triangle matrix.
        """
        # The data is already filtered by ramo and aggregated by the DB
        if self.df.empty:
            raise ValueError(f"No hay datos disponibles para el ramo: {ramo if ramo else 'Global'}")

        # Pivot the pre-aggregated data
        triangle = self.df.pivot_table(
            index='origin_year',
            columns='dev_year',
            values='total',
            aggfunc='sum'
        ).fillna(0.0)

        return triangle

    def calculate_ibnr(self, triangle: pd.DataFrame, severity_multiplier: float = 1.0, custom_ldfs: List[float] = None, method: str = 'chain_ladder', expected_loss_ratio: float = None, premiums: Dict[int, float] = None) -> Dict[str, Any]:
        """
        Implements IBNR calculation using different methods.
        Methods: 'chain_ladder', 'bf' (Bornhuetter-Ferguson), 'cape_cod'.
        """
        # Apply severity multiplier to the whole triangle
        adj_tri = triangle * severity_multiplier

        # 1. Calculate Age-to-Age Factors (LDF)
        col_sums = adj_tri.sum(axis=0)
        ldfs = []
        for i in range(len(col_sums) - 1):
            factor = col_sums.iloc[i+1] / col_sums.iloc[i] if col_sums.iloc[i] != 0 else 1.0
            ldfs.append(factor)

        # If custom LDFs are provided, override the calculated ones
        if custom_ldfs is not None:
            while len(custom_ldfs) < len(ldfs):
                custom_ldfs.append(1.0)
            ldfs = custom_ldfs[:len(ldfs)]

        # 2. Calculate Ultimate Losses based on the selected method
        ultimate_losses = []

        # For BF and Cape Cod, we need priors. If premiums are missing, we fallback to CL.
        effective_method = method
        if method in ['bf', 'cape_cod'] and (premiums is None or len(premiums) == 0):
            effective_method = 'chain_ladder'

        for idx in range(len(adj_tri)):
            year_data = adj_tri.iloc[idx]
            origin_year = int(adj_tri.index[idx])
            current_val = year_data.sum()

            # Find development stage
            non_zero_cols = np.where(year_data > 0)[0]
            last_dev_year = non_zero_cols[-1] if len(non_zero_cols) > 0 else 0

            # Development factor from current stage to ultimate
            remaining_factors = ldfs[int(last_dev_year):]
            cumulative_ldf = np.prod(remaining_factors) if remaining_factors else 1.0

            if effective_method == 'chain_ladder':
                # Simple Chain Ladder: Ultimate = Current * Cumulative LDF
                ultimate = current_val * cumulative_ldf

            elif effective_method == 'bf':
                # Bornhuetter-Ferguson: Ultimate = Actual + (Prior * (1 - Development%))
                # Prior = Premium * Expected Loss Ratio
                premium = premiums.get(origin_year, 0) if premiums else 0
                lr = expected_loss_ratio if expected_loss_ratio is not None else 0.6 # Default 60% if not provided
                prior_ultimate = premium * lr

                # Development % is 1 / Cumulative LDF
                dev_pct = 1.0 / cumulative_ldf if cumulative_ldf != 0 else 0
                ultimate = current_val + (prior_ultimate * (1 - dev_pct))

            elif effective_method == 'cape_cod':
                # Cape Cod: Similar to BF but uses historical Loss Ratio for the prior
                premium = premiums.get(origin_year, 0) if premiums else 0
                # Use historical average LDF as a proxy for LR if not provided
                hist_lr = np.mean(ldfs) if ldfs else 0.6
                prior_ultimate = premium * hist_lr

                dev_pct = 1.0 / cumulative_ldf if cumulative_ldf != 0 else 0
                ultimate = current_val + (prior_ultimate * (1 - dev_pct))

            else:
                # Fallback
                ultimate = current_val * cumulative_ldf

            ultimate_losses.append(ultimate)

        ultimate_sum = sum(ultimate_losses)
        actual_sum = adj_tri.sum().sum()
        ibnr = ultimate_sum - actual_sum

        return {
            "actual_losses": float(actual_sum),
            "ultimate_losses": float(ultimate_sum),
            "ibnr_estimate": float(ibnr),
            "development_factors": {f"dev_{i+1}_{i+2}": ldfs[i] for i in range(len(ldfs))},
            "method_used": effective_method
        }

    def compare_reserves(self, ibnr_estimate: float, ramo: str = None) -> Dict[str, Any]:
        # Use self.df but handle the case where it might be summarized
        data = self.df if (ramo is None or ramo == "") else self.df[self.df['ramo'] == ramo] if 'ramo' in self.df.columns else self.df

        if 'monto_reserva' not in data.columns:
            # If data is summarized, we can't sum monto_reserva here.
            # This method should be called with the raw DataFrame.
            return {"error": "Se requieren datos detallados para comparar reservas"}

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
        data = self.df if (ramo is None or ramo == "") else self.df[self.df['ramo'] == ramo]
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
        data = self.df if (ramo is None or ramo == "") else self.df[self.df['ramo'] == ramo]
        severities = data['monto_pagado']

        if severities.empty:
            return {"error": "No hay datos suficientes"}

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

    def optimize_reinsurance(self, ibnr_estimate: float, capital_limit: float, cost_of_capital: float = 0.10) -> Dict[str, Any]:
        """
        Optimizes retention based on cost of capital and solvency limits.
        """
        # Logic: Retention is a trade-off between cost of capital and reinsurance cost.
        # For this model, we use a risk-adjusted retention.
        # If cost of capital is high, we tend to cede more.
        retention_factor = 1.0 - (cost_of_capital * 0.5) # Simplified impact of cost of capital
        suggested_retention = min(capital_limit * 0.4 * retention_factor, ibnr_estimate)
        ceded_amount = max(0, ibnr_estimate - suggested_retention)

        # Solvency Alert: If IBNR is > 30% of capital limit, trigger urgent cession
        solvency_ratio = ibnr_estimate / capital_limit if capital_limit != 0 else 0
        alert_status = "Sugerir Cesión Urgente" if solvency_ratio > 0.30 else "Sostenible"

        return {
            "suggested_retention": float(suggested_retention),
            "ceded_amount": float(ceded_amount),
            "retention_percentage": (suggested_retention / ibnr_estimate * 100) if ibnr_estimate != 0 else 0,
            "solvency_ratio": float(solvency_ratio),
            "alert_status": alert_status,
            "recommendation": f"Estado: {alert_status}. Retención optimizada considerando costo de capital del {cost_of_capital*100}%."
        }

    def analyze_renewal_deltas(self, current_metrics: Dict[str, Any], previous_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares current and previous period metrics to suggest contract adjustments.
        """
        if not current_metrics or not previous_metrics:
            return {"error": "Se requieren métricas de ambos periodos para el análisis"}

        f_curr = current_metrics.get('frecuencia', 0)
        f_prev = previous_metrics.get('frecuencia', 0)
        s_curr = current_metrics.get('severidad', 0)
        s_prev = previous_metrics.get('severidad', 0)

        delta_f = (f_curr - f_prev) / f_prev if f_prev != 0 else 0
        delta_s = (s_curr - s_prev) / s_prev if s_prev != 0 else 0

        suggestions = []
        if delta_s > 0.10:
            suggestions.append("Sugerir aumento de la Prioridad o Límite en XoL debido al incremento en la severidad.")
        if delta_f > 0.10:
            suggestions.append("Sugerir aumento del porcentaje de cesión en Quota Share debido al incremento en la frecuencia.")

        return {
            "delta_frequency": float(delta_f),
            "delta_severity": float(delta_s),
            "suggestions": suggestions,
            "trend": "Volatilidad al Alza" if delta_f > 0 or delta_s > 0 else "Estable/Bajista"
        }

    def engineer_contract(self, ramo: str = None, ibnr_estimate: float = 0, retention: float = 0) -> Dict[str, Any]:
        # Use self.df but handle the case where it might be summarized
        data = self.df if (ramo is None or ramo == "") else self.df[self.df['ramo'] == ramo] if 'ramo' in self.df.columns else self.df

        if 'monto_pagado' not in data.columns:
            return {"error": "Se requieren datos detallados para diseñar el contrato"}

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

    def perform_backtesting(self, method: str = 'chain_ladder', expected_loss_ratio: float = 0.6, premiums: Dict[int, float] = None) -> List[Dict[str, Any]]:
        """
        Performs back-testing by simulating historical data snapshots.
        """
        if self.df.empty:
            return []

        origin_years = sorted(self.df['origin_year'].unique())
        if len(origin_years) < 2:
            return []

        results = []

        for i in range(len(origin_years) - 1):
            snapshot_year = origin_years[i]
            triangle = self.build_triangle()
            snapshot_tri = triangle.copy()
            for r_idx, oy in enumerate(triangle.index):
                for c_idx, dy in enumerate(triangle.columns):
                    if oy + dy > snapshot_year:
                        snapshot_tri.iloc[r_idx, c_idx] = 0.0

            ibnr_res = self.calculate_ibnr(
                snapshot_tri,
                method=method,
                expected_loss_ratio=expected_loss_ratio,
                premiums=premiums
            )

            est = ibnr_res["ibnr_estimate"]
            cur_tot = self.df[self.df['origin_year'] <= snapshot_year]['total'].sum()
            snap_tot = snapshot_tri.sum().sum()
            act = cur_tot - snap_tot

            results.append({
                "year": int(snapshot_year),
                "estimated": float(est),
                "actual": float(act),
                "error": float(act - est),
                "ratio": float(act / est if est != 0 else 0)
            })

        return results

    def generate_contract_draft(self, ramo: str, contract_data: Dict[str, Any], ibnr: float) -> Dict[str, Any]:
        if "error" in contract_data:
            return {"error": contract_data["error"]}

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