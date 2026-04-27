import React, { useState } from 'react';
import { api } from '../services/api';

const TriangleViewer = ({ initialTriangleData, initialRamo, token, onRamoChange }) => {
    const [triangleData, setTriangleData] = useState(initialTriangleData);
    const [ramo, setRamo] = useState(initialRamo || '');
    const [metric, setMetric] = useState(initialTriangleData?.metric || 'paid');
    const [loading, setLoading] = useState(false);
    const [ibnrResults, setIbnrResults] = useState(null);
    const [customLdfs, setCustomLdfs] = useState([]);
    const [method, setMethod] = useState('chain_ladder');
    const [expectedLossRatio, setExpectedLossRatio] = useState(0.6);

    const fetchTriangle = async (selectedRamo, selectedMetric) => {
        if (!token) {
            console.error("Auth token is missing in TriangleViewer");
            alert('Error: Sesión no autenticada');
            return;
        }
        setLoading(true);
        try {
            const data = await api.getTriangleData({
                ramo: selectedRamo,
                metric: selectedMetric,
                token: token
            });
            setTriangleData(data);

            // Calcular IBNR inicial basándonos en los datos del triángulo
            await calculateIBNR(selectedRamo, selectedMetric, [], method, expectedLossRatio);
        } catch (error) {
            alert('Error al actualizar los datos del triángulo');
        } finally {
            setLoading(false);
        }
    };

    const calculateIBNR = async (selectedRamo, selectedMetric, ldfs, selectedMethod = method, lr = expectedLossRatio) => {
        setLoading(true);
        try {
            const results = await api.calculateCustomIBNR({
                ramo: selectedRamo,
                metric: selectedMetric,
                customLdfs: ldfs,
                severityAdj: 1.0,
                method: selectedMethod,
                expected_loss_ratio: lr,
                token: token
            });
            setIbnrResults(results);
        } catch (error) {
            console.error("Error calculating IBNR:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleRamoChange = (e) => {
        const newRamo = e.target.value;
        setRamo(newRamo);
        if (onRamoChange) {
            onRamoChange(newRamo);
        }
        fetchTriangle(newRamo, metric);
    };

    const handleMetricChange = (e) => {
        const newMetric = e.target.value;
        setMetric(newMetric);
        fetchTriangle(ramo, newMetric);
    };

    const handleLdfChange = (index, value) => {
        const newLdfs = [...customLdfs];
        newLdfs[index] = parseFloat(value) || 0;
        setCustomLdfs(newLdfs);
        calculateIBNR(ramo, metric, newLdfs, method, expectedLossRatio);
    };

    const handleMethodChange = (e) => {
        const newMethod = e.target.value;
        setMethod(newMethod);
        calculateIBNR(ramo, metric, customLdfs, newMethod, expectedLossRatio);
    };

    const handleLRChange = (e) => {
        const newLR = parseFloat(e.target.value) || 0;
        setExpectedLossRatio(newLR);
        calculateIBNR(ramo, metric, customLdfs, method, newLR);
    };

    if (!triangleData) return (
        <div style={{ padding: '40px', textAlign: 'center', color: '#7f8c8d' }}>
            Cargando datos del triángulo...
        </div>
    );

    const { ramo: currentRamo, triangle_data, triangle_shape, metric: currentMetric } = triangleData;
    const years = Object.keys(triangle_data);
    const devYears = years.length > 0 ? Object.keys(triangle_data[years[0]]) : [];

    const metricLabels = {
        paid: 'Pagados',
        reserve: 'Reservas',
        total: 'Total (Pagado + Reserva)'
    };

    // Calcular totales por fila
    const rowTotals = {};
    years.forEach(year => {
        rowTotals[year] = Object.values(triangle_data[year]).reduce((a, b) => a + b, 0);
    });

    // Calcular totales por columna
    const colTotals = {};
    devYears.forEach(devYear => {
        colTotals[devYear] = years.reduce((sum, year) => sum + triangle_data[year][devYear], 0);
    });

    const grandTotal = Object.values(rowTotals).reduce((a, b) => a + b, 0);

    // Generar LDFs sugeridos basados en los datos actuales para los inputs
    const suggestedLdfs = [];
    if (devYears.length > 1) {
        for (let i = 0; i < devYears.length - 1; i++) {
            const colCurrent = colTotals[devYears[i]];
            const colNext = colTotals[devYears[i+1]];
            suggestedLdfs.push(colNext / colCurrent || 1.0);
        }
    }

    return (
        <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            width: '100%',
            maxWidth: '1200px',
            margin: '0 auto',
            overflow: 'auto'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <h2 style={{ margin: 0, color: '#2c3e50', fontSize: '24px' }}>Calculadora Actuarial - Matriz de Desarrollo</h2>
                <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Ramo</label>
                        <input
                            type="text"
                            value={ramo}
                            onChange={handleRamoChange}
                            placeholder="Ej: Autos..."
                            style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
                        />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Métrica</label>
                        <select
                            value={metric}
                            onChange={handleMetricChange}
                            style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
                        >
                            <option value="paid">Pagados</option>
                            <option value="reserve">Reservas</option>
                            <option value="total">Total</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Método</label>
                        <select
                            value={method}
                            onChange={handleMethodChange}
                            style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
                        >
                            <option value="chain_ladder">Chain Ladder</option>
                            <option value="bf">Bornhuetter-Ferguson</option>
                            <option value="cape_cod">Cape Cod</option>
                        </select>
                    </div>
                    {method === 'bf' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                            <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Loss Ratio Esperado</label>
                            <input
                                type="number"
                                step="0.01"
                                value={expectedLossRatio}
                                onChange={handleLRChange}
                                style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc', width: '80px' }}
                            />
                        </div>
                    )}
                    {loading && <div style={{ color: '#3498db', fontSize: '14px', fontWeight: 'bold' }}>Actualizando...</div>}
                </div>
            </div>

            <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
                <div style={{ flex: 1, padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '8px', borderLeft: '4px solid #3498db' }}>
                    <p style={{ color: '#2c3e50', fontSize: '16px', margin: 0 }}>
                        <strong style={{ color: '#3498db' }}>Análisis Actual:</strong> {metricLabels[currentMetric]} |
                        <strong style={{ color: '#3498db', marginLeft: '10px' }}>Ramo:</strong> {currentRamo || 'Global'}
                    </p>
                    <p style={{ fontSize: '14px', color: '#7f8c8d', margin: '5px 0 0 0' }}>
                        Dimensiones: {triangle_shape.rows} años de origen × {triangle_shape.columns} años de desarrollo
                    </p>
                </div>

                {ibnrResults && (
                    <div style={{ flex: 1, padding: '15px', backgroundColor: '#eefafb', borderRadius: '8px', borderLeft: '4px solid #2ecc71', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <p style={{ color: '#2c3e50', fontSize: '14px', margin: 0 }}>Estimación IBNR ({ibnrResults.method_used === 'chain_ladder' ? 'Chain Ladder' : ibnrResults.method_used === 'bf' ? 'Bornhuetter-Ferguson' : 'Cape Cod'})</p>
                        <p style={{ color: '#27ae60', fontSize: '22px', fontWeight: 'bold', margin: '5px 0 0 0' }}>
                            ${ibnrResults.ibnr_estimate.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                    </div>
                )}
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table style={{
                    borderCollapse: 'collapse',
                    width: '100%',
                    fontSize: '13px',
                    border: '1px solid #ddd'
                }}>
                    <thead style={{ backgroundColor: '#f8f9fa' }}>
                        <tr style={{ backgroundColor: '#f1f3f5' }}>
                            <th style={{ border: '1px solid #ddd', padding: '10px', fontWeight: 'bold', textAlign: 'left' }}>Año Origen</th>
                            {devYears.map(devYear => (
                                <th key={devYear} style={{ border: '1px solid #ddd', padding: '10px', fontWeight: 'bold', textAlign: 'center' }}>
                                    Año {devYear}
                                </th>
                            ))}
                            <th style={{ border: '1px solid #ddd', padding: '10px', fontWeight: 'bold', backgroundColor: '#e9ecef', color: '#2c3e50' }}>Total Fila</th>
                        </tr>
                    </thead>
                    <tbody>
                        {years.map(year => (
                            <tr key={year}>
                                <td style={{ border: '1px solid #ddd', padding: '10px', fontWeight: 'bold', backgroundColor: '#fbfbfb', textAlign: 'left' }}>{year}</td>
                                {devYears.map(devYear => (
                                    <td
                                        key={`${year}-${devYear}`}
                                        style={{
                                            border: '1px solid #ddd',
                                            padding: '10px',
                                            textAlign: 'right',
                                            backgroundColor: triangle_data[year][devYear] === 0 ? '#ffeaea' : 'white'
                                        }}
                                    >
                                        {triangle_data[year][devYear].toLocaleString(undefined, {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        })}
                                    </td>
                                ))}
                                <td style={{
                                    border: '1px solid #ddd',
                                    padding: '10px',
                                    textAlign: 'right',
                                    fontWeight: 'bold',
                                    backgroundColor: '#f1f3f5',
                                    color: '#2c3e50'
                                }}>
                                    {rowTotals[year].toLocaleString(undefined, {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    })}
                                </td>
                            </tr>
                        ))}
                        <tr style={{ backgroundColor: '#f1f3f5', fontWeight: 'bold' }}>
                            <td style={{ border: '1px solid #ddd', padding: '10px', textAlign: 'left', color: '#2c3e50' }}>Total Columna</td>
                            {devYears.map((devYear, idx) => (
                                <td key={`total-${devYear}`} style={{
                                    border: '1px solid #ddd',
                                    padding: '10px',
                                    textAlign: 'right',
                                    color: '#2c3e50',
                                    backgroundColor: idx < devYears.length - 1 ? 'white' : '#f8f9fa'
                                }}>
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                                        <span>{colTotals[devYear].toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                                        {idx < devYears.length - 1 && (
                                            <input
                                                type="number"
                                                step="0.01"
                                                value={customLdfs[idx] || suggestedLdfs[idx] || ''}
                                                onChange={(e) => handleLdfChange(idx, e.target.value)}
                                                style={{
                                                    width: '60px',
                                                    fontSize: '10px',
                                                    marginTop: '4px',
                                                    textAlign: 'center',
                                                    border: '1px solid #3498db',
                                                }}
                                                placeholder="LDF"
                                            />
                                        )}
                                    </div>
                                </td>
                            ))}
                            <td style={{
                                border: '1px solid #ddd',
                                padding: '10px',
                                textAlign: 'right',
                                backgroundColor: '#d1d8e0',
                                color: '#2c3e50',
                                fontSize: '14px'
                            }}>
                                {grandTotal.toLocaleString(undefined, {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2
                                })}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div style={{ marginTop: '20px', fontSize: '12px', color: '#7f8c8d', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span style={{ color: '#e74c3c', fontWeight: 'bold' }}>●</span> Las celdas en rojo indican períodos sin datos (valor 0).
                <span style={{ marginLeft: '20px', color: '#3498db', fontWeight: 'bold' }}>⚙️</span> Modifica los LDFs en la fila de totales para ajustar la reserva técnica.
            </div>
        </div>
    );
};

export default TriangleViewer;