import pandas as pd
import numpy as np
import polars as pl
import datetime
from typing import Dict, Any, List
from app.modules.diagnostics.validator import winsorize_data

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
        Uses Polars for high-performance aggregation.
        """
        if self.is_summarized:
            return self.df

        # Convert to polars if necessary
        pl_df = pl.from_pandas(self.df) if isinstance(self.df, pd.DataFrame) else self.df

        if ramo and 'ramo' in pl_df.columns:
            pl_df = pl_df.filter(pl.col('ramo') == ramo)

        # Calculate origin_year and dev_year from dates
        if 'origin_year' not in pl_df.columns:
            # Solo convertir si no son ya tipos fecha (date/datetime)
            occ_col = pl.col('fecha_ocurrencia')
            rep_col = pl.col('fecha_reporte')

            # Usamos casting condicional o detectamos el tipo
            # En Polars, si ya es Date, .dt.year() funciona directo.
            # Si es String, requiere str.to_datetime().

            def ensure_date(col_name):
                # Intentar obtener el tipo actual del dataframe
                dtype = pl_df.schema.get(col_name)
                if dtype is not None and (dtype == pl.Date or dtype == pl.Datetime):
                    return pl.col(col_name)
                return pl.col(col_name).cast(pl.String).str.to_datetime()

            pl_df = pl_df.with_columns([
                ensure_date('fecha_ocurrencia').dt.year().alias('origin_year'),
                (ensure_date('fecha_reporte').dt.year() -
                 ensure_date('fecha_ocurrencia').dt.year()).alias('dev_year')
            ])

        metric_col = 'monto_pagado' if metric == 'paid' else 'monto_reserva' if metric == 'reserve' else 'total'

        if metric_col not in pl_df.columns:
            return pd.DataFrame(columns=['origin_year', 'dev_year', 'total'])

        summarized = (
            pl_df.group_by(['origin_year', 'dev_year'])
            .agg(pl.col(metric_col).sum().alias('total'))
            .sort(['origin_year', 'dev_year'])
            .to_pandas()
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

    def derive_tail_factor(self, ldfs: List[float]) -> float:
        """
        Derives a tail factor using exponential decay of the last 3-5 factors.
        If no decay is detected or insufficient data, returns 1.0.
        """
        if len(ldfs) < 3:
            return 1.0

        # Take the last 3-5 factors that are > 1.0
        candidates = [f for f in ldfs[-5:] if f > 1.0]
        if len(candidates) < 3:
            return 1.0

        try:
            # Fit ln(f-1) = alpha + beta * i
            x = np.arange(len(candidates))
            y = np.log(np.array(candidates) - 1.0)

            beta, alpha = np.polyfit(x, y, 1)

            if beta >= 0:  # No decay detected
                return 1.0

            # The last observed excess is exp(alpha + beta * (len-1))
            # The tail is the sum of the remaining geometric series:
            # Sum_{i=1}^inf exp(alpha + beta * (len-1 + i))
            # = exp(alpha + beta*len) * (1 / (1 - exp(beta)))

            last_excess = candidates[-1] - 1.0
            decay_rate = np.exp(beta)
            tail_excess = last_excess * decay_rate / (1 - decay_rate)

            return 1.0 + tail_excess
        except Exception:
            return 1.0

    def calculate_ibnr(self, triangle: pd.DataFrame, severity_multiplier: float = 1.0, custom_ldfs: List[float] = None, method: str = 'chain_ladder', expected_loss_ratio: float = None, premiums: Dict[int, float] = None, tail_factor: float = None) -> Dict[str, Any]:
        """
        Implements IBNR calculation using vectorized NumPy operations.
        Incorporates S-Smoothing and automated tail derivation.
        """
        adj_tri = triangle * severity_multiplier
        data_mat = adj_tri.values
        num_rows, num_cols = data_mat.shape

        # 1. LDF Calculation with S-Smoothing (Volume-Weighted)
        ldfs = []
        for i in range(num_cols - 1):
            curr_col = data_mat[:, i]
            next_col = data_mat[:, i+1]

            mask = next_col > 0
            sum_curr = np.sum(curr_col[mask])
            sum_next = np.sum(next_col[mask])

            # Volume Weighted Average is the baseline for S-Smoothing in this context
            factor = sum_next / sum_curr if sum_curr != 0 else 1.0
            ldfs.append(max(1.0, factor))

        if custom_ldfs is not None:
            ldfs = (custom_ldfs + [1.0] * (len(ldfs) - len(custom_ldfs)))[:len(ldfs)]

        # 2. Tail Factor Automation
        if tail_factor is None:
            tail_factor = self.derive_tail_factor(ldfs)

        # 3. Ultimate Losses Calculation
        ultimate_losses = []
        projected_triangle = {}

        effective_method = method
        if method in ['bf', 'cape_cod'] and (premiums is None or len(premiums) == 0):
            effective_method = 'chain_ladder'

        for idx in range(num_rows):
            row = data_mat[idx]
            origin_year = int(adj_tri.index[idx])
            current_val = np.sum(row)

            non_zero = np.where(row > 0)[0]
            last_dev = non_zero[-1] if len(non_zero) > 0 else 0

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
            "tail_factor": float(tail_factor),
            "method_used": effective_method,
            "projected_triangle": projected_triangle
        }

    def process_stable_reserves(self, ramo: str = None, metric: str = 'paid', winsorize_limit: float = 0.05, severity_multiplier: float = 1.0, method: str = 'chain_ladder', expected_loss_ratio: float = None, premiums: Dict[int, float] = None) -> Dict[str, Any]:
        """
 la estabilidad de la reserva mediante la tubería:
        Winsorización -> S-Smoothing -> Tail Factor -> Ultimate Loss.
        """
        # 1. Winsorization (Cleaning)
        if not self.is_summarized:
            metric_col = 'monto_pagado' if metric == 'paid' else 'monto_reserva' if metric == 'reserve' else 'total'
            # We apply winsorization to the raw data before summarization
            self.df = winsorize_data(self.df, columns=[metric_col], limits=winsorize_limit)

        # 2. Build Triangle (S-Smoothing is inside calculate_ibnr via VWA)
        triangle = self.build_triangle(ramo=ramo, metric=metric)

        # 3. Calculate IBNR (incorporates automated Tail Factor and S-Smoothing)
        ibnr_res = self.calculate_ibnr(
            triangle=triangle,
            severity_multiplier=severity_multiplier,
            method=method,
            expected_loss_ratio=expected_loss_ratio,
            premiums=premiums
        )

        return {
            "status": "Stable Pipeline Applied",
            "winsorize_limit": winsorize_limit,
            "ibnr_results": ibnr_res
        }

    def get_ldf_matrix(self, ramo: str = None, metric: str = 'paid') -> pd.DataFrame:
        """
        Calculates the raw age-to-age factors for each origin year.
        Returns a DataFrame where index=origin_year and columns=dev_periods.
        """
        triangle = self.build_triangle(ramo=ramo, metric=metric)
        ldf_mat = pd.DataFrame(index=triangle.index)

        for i in range(triangle.shape[1] - 1):
            curr_col = triangle.iloc[:, i]
            next_col = triangle.iloc[:, i+1]

            # Factor = Next / Curr
            ldf_mat[f'dev_{i+1}_{i+2}'] = next_col / curr_col

        return ldf_mat

    def simulate_ibnr_monte_carlo(self, iterations: int = 10000, ramo: str = None, metric: str = 'paid') -> Dict[str, Any]:
        """
        Generates a distribution of IBNR using Monte Carlo simulations.
        LDFs are sampled from a Log-normal distribution based on historical volatility.
        """
        triangle = self.build_triangle(ramo=ramo, metric=metric)
        ldf_mat = self.get_ldf_matrix(ramo=ramo, metric=metric)

        # 1. Calculate means and std devs for each LDF (log-space)
        # Filter out zeros/NaNs to avoid log issues
        log_ldfs = np.log(ldf_mat.replace(0, np.nan))
        means = log_ldfs.mean()
        stds = log_ldfs.std().fillna(0.1) # Default 10% volatility if not available

        # 2. Run Simulations
        simulated_ultimates = []

        # Current cumulative losses per origin year
        current_losses = triangle.sum(axis=1).values

        # Tail factor from the current logic
        ldf_means = ldf_mat.mean().values
        tail_factor = self.derive_tail_factor(ldf_means.tolist())

        for _ in range(iterations):
            # Sample LDFs for this iteration
            sampled_ldfs = []
            for mean, std in zip(means, stds):
                sampled_ldfs.append(np.random.lognormal(mean, std))

            # Calculate cumulative LDF for each origin year
            # This is a simplification: we use the same sampled LDFs for all years
            # but weighted by their maturity.

            # For each origin year, identify its last development period
            # and apply the sampled LDFs from that point onwards.

            total_ultimate = 0
            for idx in range(len(current_losses)):
                row = triangle.values[idx]
                non_zero = np.where(row > 0)[0]
                last_dev = non_zero[-1] if len(non_zero) > 0 else 0

                # Apply sampled factors from last_dev to the end
                remaining_factors = sampled_ldfs[int(last_dev):]
                cumulative_ldf = np.prod(remaining_factors) * tail_factor if remaining_factors else tail_factor

                total_ultimate += current_losses[idx] * cumulative_ldf

            simulated_ultimates.append(total_ultimate)

        sim_array = np.array(simulated_ultimates)
        actual_sum = np.sum(triangle.values)

        return {
            "mean_ibnr": float(np.mean(sim_array) - actual_sum),
            "p50_ibnr": float(np.percentile(sim_array, 50) - actual_sum),
            "p95_ibnr": float(np.percentile(sim_array, 95) - actual_sum),
            "p995_ibnr": float(np.percentile(sim_array, 99.5) - actual_sum),
            "std_dev": float(np.std(sim_array)),
            "distribution": simulated_ultimates # To be used by frontend for histogram
        }

    def generate_full_technical_package(self, ramo: str = None, metric: str = 'paid', winsorize_limit: float = 0.05, method: str = 'chain_ladder', expected_loss_ratio: float = 0.6, premiums: Dict[int, float] = None, capital_limit: float = 1000000.0, cost_of_capital: float = 0.10, priority: float = 0, limit: float = 0) -> Dict[str, Any]:
        """
        Consolidates ALL actuarial analyses into a single technical package for renewals.
        Cubre: Estabilidad -> Capital -> Justificación Técnica.
        """
        # 1. Reserve Stability Pipeline
        stable_res = self.process_stable_reserves(
            ramo=ramo, metric=metric, winsorize_limit=winsorize_limit,
            method=method, expected_loss_ratio=expected_loss_ratio, premiums=premiums
        )
        ibnr_res = stable_res["ibnr_results"]

        # 2. Risk & Uncertainty (Monte Carlo)
        monte_carlo = self.simulate_ibnr_monte_carlo(ramo=ramo, metric=metric)

        # 3. Capital Optimization
        optimization = self.optimize_reinsurance(
            ibnr_estimate=ibnr_res["ibnr_estimate"],
            capital_limit=capital_limit,
            cost_of_capital=cost_of_capital
        )

        # 4. Burn-through Analysis
        burn_through = self.analyze_burn_through(priority=priority, limit=limit, ramo=ramo)

        # 5. Projected Loss Ratio
        plr = self.calculate_projected_loss_ratio(ramo=ramo, premiums=premiums, expected_lr=expected_loss_ratio)

        # 6. Contract Engineering
        contract = self.engineer_contract(
            ramo=ramo,
            ibnr_estimate=ibnr_res["ibnr_estimate"],
            retention=optimization["suggested_retention"]
        )

        return {
            "header": {
                "title": "Renewal Technical Package",
                "ramo": ramo if ramo else "Global",
                "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                "status": "Technical Proposal - Final"
            },
            "reserve_stability": {
                "ibnr_estimate": ibnr_res["ibnr_estimate"],
                "actual_losses": ibnr_res["actual_losses"],
                "ultimate_losses": ibnr_res["ultimate_losses"],
                "method": ibnr_res["method_used"],
                "tail_factor": ibnr_res["tail_factor"],
                "winsorization_applied": winsorize_limit > 0
            },
            "risk_distribution": monte_carlo,
            "capital_efficiency": optimization,
            "burn_through_analysis": burn_through,
            "pricing_projection": plr,
            "proposed_structure": contract
        }

    def benchmark_performance(self, ramo: str = None, metric: str = 'paid') -> Dict[str, Any]:
        """
        Benchmarks the performance of Pandas vs Polars for the summarization step.
        """
        import time

        # Pandas baseline
        start_pd = time.time()
        # Mock the old logic
        df = self.df.copy()
        if ramo and 'ramo' in df.columns:
            df = df[df['ramo'] == ramo]
        if 'origin_year' not in df.columns:
            df['occurrence_date_dt'] = pd.to_datetime(df['fecha_ocurrencia'])
            df['report_date_dt'] = pd.to_datetime(df['fecha_reporte'])
            df['origin_year'] = df['occurrence_date_dt'].dt.year
            df['dev_year'] = df['report_date_dt'].dt.year - df['occurrence_date_dt'].dt.year
        metric_col = 'monto_pagado' if metric == 'paid' else 'monto_reserva' if metric == 'reserve' else 'total'
        if metric_col in df.columns:
            _ = df.groupby(['origin_year', 'dev_year'])[metric_col].sum()
        end_pd = time.time()

        # Polars optimization
        start_pl = time.time()
        self.get_summarized_data(ramo=ramo, metric=metric)
        end_pl = time.time()

        pd_time = end_pd - start_pd
        pl_time = end_pl - start_pl

        return {
            "pandas_time_sec": float(pd_time),
            "polars_time_sec": float(pl_time),
            "speedup_factor": float(pd_time / pl_time) if pl_time > 0 else 0,
            "rows_processed": len(self.df)
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

    def calculate_projected_loss_ratio(self, ramo: str = None, premiums: Dict[int, float] = None, expected_lr: float = None) -> Dict[str, Any]:
        """
        Calculates the Projected Loss Ratio (PLR).
        PLR = Projected Ultimate Losses / Earned Premiums.
        """
        # Use a default method (Chain Ladder) to get projected ultimates
        ibnr_res = self.calculate_ibnr(
            triangle=self.build_triangle(ramo=ramo),
            method='chain_ladder',
            premiums=premiums,
            expected_loss_ratio=expected_lr
        )

        ultimate_losses = ibnr_res["ultimate_losses"]
        total_premium = sum(premiums.values()) if premiums else 0

        if total_premium == 0:
            return {"error": "Se requieren datos de primas para calcular el Loss Ratio."}

        plr = ultimate_losses / total_premium

        return {
            "projected_ultimate": float(ultimate_losses),
            "total_premium": float(total_premium),
            "projected_loss_ratio": float(plr),
            "status": "Sostenible" if plr < 0.75 else "Alerta" if plr < 0.90 else "Crítico"
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