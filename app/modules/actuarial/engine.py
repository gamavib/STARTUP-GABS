import pandas as pd
import numpy as np
import polars as pl
import datetime
from typing import Dict, Any, List

class ActuarialEngine:
    def __init__(self, df: pd.DataFrame):
        """
        The engine accepts a DataFrame. It can be either raw claim data
        or summarized data (origin_year, dev_year, total).
        """
        self.df = df

        # Determine if the provided df is already summarized or raw
        self.is_summarized = all(col in df.columns for col in ['origin_year', 'dev_year', 'total']) and \
                             len(df.columns) <= 5

        if self.is_summarized:
            self.summarized_df = self.df
        else:
            self.summarized_df = None

    def get_summarized_data(self, ramo: str = None, metric: str = 'paid') -> pd.DataFrame:
        """
        Returns the summarized version of the data as a Pandas DataFrame.
        """
        if self.is_summarized:
            return self.df

        df = self.df.copy()
        if ramo and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]

        # Calculate origin_year and dev_year from dates
        if 'origin_year' not in df.columns:
            df['occurrence_date_dt'] = pd.to_datetime(df['fecha_ocurrencia'])
            df['report_date_dt'] = pd.to_datetime(df['fecha_reporte'])

            df['origin_year'] = df['occurrence_date_dt'].dt.year
            df['dev_year'] = df['report_date_dt'].dt.year - df['occurrence_date_dt'].dt.year

            df = df.drop(['occurrence_date_dt', 'report_date_dt'], axis=1)

        metric_col = 'monto_pagado' if metric == 'paid' else 'monto_reserva' if metric == 'reserve' else 'total'

        if metric_col not in df.columns:
            return pd.DataFrame(columns=['origin_year', 'dev_year', 'total'])

        summarized = (
            df.groupby(['origin_year', 'dev_year'])[metric_col]
            .sum()
            .reset_index()
            .rename(columns={metric_col: 'total'})
            .sort_values(['origin_year', 'dev_year'])
        )

        return summarized


    def build_triangle(self, ramo: str = None, metric: str = 'paid') -> pd.DataFrame:
        """
        Transforms the summarized DataFrame into a triangle matrix.
        """
        df_sum = self.get_summarized_data(ramo=ramo, metric=metric)

        if df_sum.empty:
            raise ValueError(f"No hay datos disponibles para el ramo: {ramo if ramo else 'Global'}")

        # Pivot to triangle
        triangle = df_sum.pivot(
            index='origin_year',
            columns='dev_year',
            values='total'
        ).fillna(0.0)

        return triangle

    def calculate_ibnr(self, triangle: pd.DataFrame, severity_multiplier: float = 1.0, custom_ldfs: List[float] = None, method: str = 'chain_ladder', expected_loss_ratio: float = None, premiums: Dict[int, float] = None, tail_factor: float = 1.0) -> Dict[str, Any]:
        """
        Implements IBNR calculation using vectorized NumPy operations.
        """
        adj_tri = triangle * severity_multiplier
        data_mat = adj_tri.values
        num_rows, num_cols = data_mat.shape

        # 1. Vectorized LDF Calculation (S-Smoothed / Weighted)
        ldfs = []
        for i in range(num_cols - 1):
            curr_col = data_mat[:, i]
            next_col = data_mat[:, i+1]

            # Mask: only rows that have reached the next development stage
            mask = next_col > 0
            sum_curr = np.sum(curr_col[mask])
            sum_next = np.sum(next_col[mask])

            factor = sum_next / sum_curr if sum_curr != 0 else 1.0
            ldfs.append(max(1.0, factor))

        if custom_ldfs is not None:
            ldfs = (custom_ldfs + [1.0] * (len(ldfs) - len(custom_ldfs)))[:len(ldfs)]

        # 2. Ultimate Losses Calculation
        ultimate_losses = []
        projected_triangle = {}

        effective_method = method
        if method in ['bf', 'cape_cod'] and (premiums is None or len(premiums) == 0):
            effective_method = 'chain_ladder'

        for idx in range(num_rows):
            row = data_mat[idx]
            origin_year = int(adj_tri.index[idx])
            current_val = np.sum(row)

            # Find last development stage with data
            non_zero = np.where(row > 0)[0]
            last_dev = non_zero[-1] if len(non_zero) > 0 else 0

            # Cumulative factor to ultimate
            remaining_factors = ldfs[int(last_dev):]
            cumulative_ldf = np.prod(remaining_factors) * tail_factor if remaining_factors else tail_factor

            if effective_method == 'chain_ladder':
                ultimate = current_val * cumulative_ldf
            elif effective_method == 'bf':
                premium = premiums.get(origin_year, 0) if premiums else 0
                lr = expected_loss_ratio if expected_loss_ratio is not None else 0.6
                prior_ultimate = premium * lr
                dev_pct = 1.0 / cumulative_ldf if cumulative_ldf != 0 else 0
                ultimate = current_val + (prior_ultimate * (1 - dev_pct))
            elif effective_method == 'cape_cod':
                premium = premiums.get(origin_year, 0) if premiums else 0
                hist_lr = np.mean(ldfs) if ldfs else 0.6
                prior_ultimate = premium * hist_lr
                dev_pct = 1.0 / cumulative_ldf if cumulative_ldf != 0 else 0
                ultimate = current_val + (prior_ultimate * (1 - dev_pct))
            else:
                ultimate = current_val * cumulative_ldf

            ultimate = max(current_val, ultimate)
            ultimate_losses.append(ultimate)

            # Vectorized projection for the triangle
            proj_row = row.copy()
            if len(non_zero) > 0:
                last_val = row[last_dev]
                for next_idx in range(last_dev + 1, num_cols):
                    factor = ldfs[next_idx - 1] if (next_idx - 1) < len(ldfs) else 1.0
                    last_val *= factor
                    proj_row[next_idx] = last_val

            projected_triangle[origin_year] = {i: float(val) for i, val in enumerate(proj_row)}
            projected_triangle[origin_year][num_cols] = float(ultimate)

        ultimate_sum = sum(ultimate_losses)
        actual_sum = np.sum(data_mat)
        ibnr = ultimate_sum - actual_sum

        return {
            "actual_losses": float(actual_sum),
            "ultimate_losses": float(ultimate_sum),
            "ibnr_estimate": float(ibnr),
            "development_factors": {f"dev_{i+1}_{i+2}": ldfs[i] for i in range(len(ldfs))},
            "method_used": effective_method,
            "projected_triangle": projected_triangle
        }

    def compare_reserves(self, ibnr_estimate: float, ramo: str = None, current_reserves: float = None) -> Dict[str, Any]:
        # If current_reserves is provided, use it directly to avoid needing raw data
        if current_reserves is not None:
            reserva_contable = current_reserves
        else:
            # Check if we have raw data for this analysis
            if self.is_summarized or 'monto_reserva' not in self.df.columns:
                return {"error": "Se requieren datos detallados (monto_reserva) para comparar reservas. Use la carga de datos crudos."}

            df = self.df
            if ramo and ramo != "" and 'ramo' in df.columns:
                df = df[df['ramo'] == ramo]
            reserva_contable = df['monto_reserva'].sum() or 0.0

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
        if self.is_summarized or 'id_poliza' not in self.df.columns or 'monto_pagado' not in self.df.columns:
            return {"error": "Se requieren datos detallados (id_poliza, monto_pagado) para este análisis"}

        df = self.df
        if ramo and ramo != "" and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]

        num_siniestros = len(df)
        num_polizas = df['id_poliza'].nunique()
        total_pagado = df['monto_pagado'].sum() or 0.0

        frecuencia = num_siniestros / num_polizas if num_polizas > 0 else 0
        severidad = total_pagado / num_siniestros if num_siniestros > 0 else 0

        return {
            "frecuencia": frecuencia,
            "severidad": severidad,
            "total_siniestros": num_siniestros,
            "total_polizas": num_polizas
        }

    def analyze_severity_distribution(self, ramo: str = None) -> Dict[str, Any]:
        if self.is_summarized or 'monto_pagado' not in self.df.columns:
            return {"error": "Se requieren datos detallados (monto_pagado) para este análisis"}

        df = self.df
        if ramo and ramo != "" and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]

        severities = df['monto_pagado']

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
        Optimizes retention based on Economic Capital (EC) model.
        Minimizes Total Cost of Risk (TCR) = Capital Charge + Ceding Cost.
        """
        # Calculate portfolio volatility (Std Dev of paid claims)
        if not self.is_summarized and 'monto_pagado' in self.df.columns:
            volatility = self.df['monto_pagado'].std() or 0.0
        else:
            volatility = ibnr_estimate * 0.2  # Baseline 20% volatility fallback

        # Constants for EC Model
        z_score = 2.58  # 99.5% Confidence Level (Standard for Solvency II)
        reinsurance_loading = 0.15  # Reinsurers charge a premium above the expected loss

        # TCR Optimization: Iterate through potential retention levels to find minimum cost
        best_retention = 0.0
        min_tcr = float('inf')

        # Test retentions from 0 to 100% of IBNR in 1% increments
        for pct in np.linspace(0, 1, 101):
            retention = ibnr_estimate * pct
            ceded = ibnr_estimate - retention

            # 1. Required Capital for retained risk
            retention_ratio = pct if ibnr_estimate > 0 else 0
            required_capital = (ibnr_estimate * retention_ratio) + (z_score * volatility * np.sqrt(retention_ratio))
            capital_charge = required_capital * cost_of_capital

            # 2. Cost of Ceding
            ceding_cost = ceded * reinsurance_loading

            tcr = capital_charge + ceding_cost

            if tcr < min_tcr:
                min_tcr = tcr
                best_retention = retention

        # Solvency Alert: If IBNR is > 30% of capital limit, trigger urgent cession
        solvency_ratio = ibnr_estimate / capital_limit if capital_limit != 0 else 0
        alert_status = "Sugerir Cesión Urgente" if solvency_ratio > 0.30 else "Sostenible"

        return {
            "suggested_retention": float(best_retention),
            "ceded_amount": float(max(0, ibnr_estimate - best_retention)),
            "retention_percentage": (best_retention / ibnr_estimate * 100) if ibnr_estimate != 0 else 0,
            "solvency_ratio": float(solvency_ratio),
            "alert_status": alert_status,
            "recommendation": f"Optimización EC: Retención de ${best_retention:,.2f} minimiza el Costo Total de Riesgo considerando volatilidad y costo de capital del {cost_of_capital*100}%."
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
        df = self.df
        if ramo and ramo != "" and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]

        if 'monto_pagado' not in df.columns:
            return {"error": "Se requieren datos detallados para diseñar el contrato"}

        severities = df['monto_pagado']
        std_dev = severities.std() or 0.0
        mean_sev = severities.mean() or 0.0
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
        df_sum = self.get_summarized_data()
        if df_sum.empty:
            return []

        origin_years = sorted(df_sum['origin_year'].unique())
        if len(origin_years) < 2:
            return []

        results = []
        full_triangle = self.build_triangle()
        triangle_mat = full_triangle.values
        years = full_triangle.index.values

        for i in range(len(origin_years) - 1):
            snapshot_year = origin_years[i]

            # Create a mask for the snapshot: oy + dy <= snapshot_year
            # triangle_mat[r, c] is for origin_year=years[r] and dev_year=c
            mask = (years[:, None] + np.arange(triangle_mat.shape[1])) <= snapshot_year
            snapshot_mat = np.where(mask, triangle_mat, 0.0)

            # Convert back to DataFrame for calculate_ibnr compatibility
            snapshot_tri = pd.DataFrame(snapshot_mat, index=years, columns=full_triangle.columns)

            ibnr_res = self.calculate_ibnr(
                snapshot_tri,
                method=method,
                expected_loss_ratio=expected_loss_ratio,
                premiums=premiums
            )

            est = ibnr_res["ibnr_estimate"]
            cur_tot = df_sum[df_sum['origin_year'] <= snapshot_year]['total'].sum()
            snap_tot = np.sum(snapshot_mat)
            act = cur_tot - snap_tot

            results.append({
                "year": int(snapshot_year),
                "estimated": float(est),
                "actual": float(act),
                "error": float(act - est),
                "ratio": float(act / est if est != 0 else 0)
            })

        return results

    def analyze_burn_through(self, priority: float, limit: float, ramo: str = None) -> Dict[str, Any]:
        """
        Analyzes how much of the reinsurance layer was 'burned through' by actual claims.
        Essential for determining if the priority needs to be increased in the renewal.
        """
        df = self.df
        if ramo and ramo != "" and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]

        if 'monto_pagado' not in df.columns:
            return {"error": "Se requieren datos detallados para el análisis de burn-through"}

        severities = df['monto_pagado']

        # Only claims that exceed the priority contribute to the burn-through
        excess_claims = severities[severities > priority]

        total_burn = excess_claims.sum() or 0.0
        burn_percentage = (total_burn / limit * 100) if limit > 0 else 0

        # Count how many claims actually hit the reinsurance layer
        hit_count = len(excess_claims)

        return {
            "total_burn_amount": float(total_burn),
            "burn_percentage": float(burn_percentage),
            "claims_hitting_layer": int(hit_count),
            "status": "Agotamiento Alto" if burn_percentage > 70 else "Agotamiento Medio" if burn_percentage > 30 else "Capa Estable",
            "recommendation": "Aumentar Prioridad" if burn_percentage > 50 else "Mantener Estructura"
        }

    def generate_renewal_package_data(self, ramo: str, ibnr_res: Dict[str, Any], optimization: Dict[str, Any], deltas: Dict[str, Any], burn_through: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolidates all technical data into a structured format for the Renewal PDF.
        """
        return {
            "report_header": {
                "title": "Renewal Technical Package",
                "ramo": ramo,
                "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                "status": "Technical Proposal"
            },
            "ibnr_section": {
                "actual_losses": ibnr_res["actual_losses"],
                "ultimate_losses": ibnr_res["ultimate_losses"],
                "ibnr_estimate": ibnr_res["ibnr_estimate"],
                "method": ibnr_res["method_used"]
            },
            "reinsurance_section": {
                "suggested_retention": optimization["suggested_retention"],
                "ceded_amount": optimization["ceded_amount"],
                "solvency_ratio": optimization["solvency_ratio"],
                "burn_through_pct": burn_through["burn_percentage"],
                "burn_status": burn_through["status"]
            },
            "trend_analysis": {
                "delta_freq": deltas["delta_frequency"],
                "delta_sev": deltas["delta_severity"],
                "trend": deltas["trend"],
                "suggestions": deltas["suggestions"]
            }
        }

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