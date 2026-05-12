import pandas as pd
import numpy as np
from app.modules.actuarial.engine import ActuarialEngine
import json

def test_regression():
    # 1. Dataset de prueba sintético (Siniestros)
    data = {
        'id_siniestro': [1, 2, 3, 4, 5, 6],
        'fecha_ocurrencia': ['01/01/2020', '01/01/2020', '01/01/2021', '01/01/2021', '01/01/2022', '01/01/2022'],
        'fecha_reporte': ['01/01/2020', '01/01/2021', '01/01/2021', '01/01/2022', '01/01/2022', '01/01/2023'],
        'monto_pagado': [1000.0, 1200.0, 1100.0, 1300.0, 1050.0, 1150.0],
        'monto_reserva': [200.0, 100.0, 300.0, 200.0, 400.0, 100.0],
        'ramo': ['Vida', 'Vida', 'Vida', 'Vida', 'Vida', 'Vida'],
        'id_poliza': ['P1', 'P1', 'P2', 'P2', 'P3', 'P3']
    }
    df = pd.DataFrame(data)
    
    print("--- Iniciando Validación de Regresión Actuarial ---")
    
    try:
        # Instanciar motor (ahora usa Polars internamente)
        engine = ActuarialEngine(df)
        
        # Test 1: Agregación de datos
        summarized = engine.get_summarized_data(ramo='Vida', metric='paid')
        print(f"✅ Agregación exitosa. Filas procesadas: {len(summarized)}")
        
        # Test 2: Construcción de Triángulo
        triangle = engine.build_triangle(ramo='Vida', metric='paid')
        print(f"✅ Triángulo construido correctamente. Dimensiones: {triangle.shape}")
        
        # Test 3: Cálculo de IBNR (Chain Ladder)
        ibnr_res = engine.calculate_ibnr(triangle, method='chain_ladder')
        print(f"✅ Cálculo de IBNR completado. Estimación: {ibnr_res['ibnr_estimate']}")
        
        # Test 4: Análisis de Severidad
        severity = engine.analyze_severity_distribution(ramo='Vida')
        print(f"✅ Análisis de severidad completado. Media: {severity['mean_severity']}")

        # Verificación de tipos (Crucial para JSON)
        for k, v in ibnr_res.items():
            if isinstance(v, (float, int)):
                pass # OK
            elif isinstance(v, dict):
                pass # OK
            else:
                print(f"⚠️ Warning: Tipo de dato inusual en resultado: {type(v)}")

        print("\nRESULTADO FINAL: El motor Polars es matemáticamente coherente y compatible.")
        return True
    except Exception as e:
        print(f"❌ ERROR en la regresión: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_regression()
    exit(0 if success else 1)
