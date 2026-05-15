import React from 'react';
import ReactECharts from 'echarts-for-react';

const ValidationViewer = ({ data, loading }) => {
    if (loading) return <div style={{ textAlign: 'center', padding: '40px', color: '#3498db' }}>Cargando validaciones...</div>;

    if (!data || data.status === 'insufficient_data') {
        return (
            <div style={{
                backgroundColor: 'white',
                padding: '40px',
                borderRadius: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                textAlign: 'center',
                color: '#7f8c8d'
            }}>
                <div style={{ fontSize: '48px', marginBottom: '20px' }}>📉</div>
                <h3>Datos Históricos Insuficientes</h3>
                <p>Se requieren al menos 3 años de datos de siniestros para generar una simulación de retroceso válida.</p>
            </div>
        );
    }

    const series = data.data;
    const avgError = series.reduce((acc, curr) => acc + Math.abs(curr.error), 0) / series.length;
    const globalRatio = series.reduce((acc, curr) => acc + curr.ratio, 0) / series.length;

    const lineOption = {
        title: { text: 'Evolución del Error de Reserva', left: 'center', textStyle: { fontSize: 14, color: '#2c3e50' } },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: series.map(s => s.year), axisLabel: { color: '#7f8c8d' } },
        yAxis: { type: 'value', axisLabel: { formatter: (v) => `$${v.toLocaleString()}` } },
        series: [{
            data: series.map(s => s.error),
            type: 'line',
            smooth: true,
            symbolSize: 8,
            itemStyle: { color: '#3498db' },
            lineStyle: { width: 3 }
        }]
    };

    const barOption = {
        title: { text: 'Estimados vs Real por Año', left: 'center', textStyle: { fontSize: 14, color: '#2c3e50' } },
        tooltip: { trigger: 'axis' },
        legend: { bottom: '0' },
        xAxis: { type: 'category', data: series.map(s => s.year), axisLabel: { color: '#7f8c8d' } },
        yAxis: { type: 'value', axisLabel: { formatter: (v) => `$${v.toLocaleString()}` } },
        series: [
            { name: 'Estimado', type: 'bar', data: series.map(s => s.estimated), itemStyle: { color: '#3498db' } },
            { name: 'Real', type: 'bar', data: series.map(s => s.actual), itemStyle: { color: '#2ecc71' } }
        ]
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
            {/* KPI Cards */}
            <div style={{ display: 'flex', gap: '20px', justifyContent: 'center' }}>
                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                    textAlign: 'center',
                    minWidth: '200px',
                    borderTop: '4px solid #3498db'
                }}>
                    <span style={{ fontSize: '12px', color: '#7f8c8d', fontWeight: 'bold', textTransform: 'uppercase' }}>Error Medio Absoluto (MAE)</span>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', marginTop: '10px' }}>
                        ${avgError.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                </div>
                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxHadow: '0 4px 6px rgba(0,0,0,0.05)',
                    textAlign: 'center',
                    minWidth: '200px',
                    borderTop: '4px solid #2ecc71'
                }}>
                    <span style={{ fontSize: '12px', color: '#7f8c8d', fontWeight: 'bold', textTransform: 'uppercase' }}>Ratio de Suficiencia Global</span>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', marginTop: '10px' }}>
                        {(globalRatio * 100).toFixed(2)}%
                    </div>
                </div>
                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                    textAlign: 'center',
                    minWidth: '200px',
                    borderTop: '4px solid #f1c40f'
                }}>
                    <span style={{ fontSize: '12px', color: '#7f8c8d', fontWeight: 'bold', textTransform: 'uppercase' }}>Años Analizados</span>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', marginTop: '10px' }}>
                        {series.length}
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                    height: '400px'
                }}>
                    <div style={{ width: '100%', height: '100%' }}>
                        <ReactECharts option={lineOption} style={{ height: '100%', width: '100%' }} />
                    </div>
                </div>

                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                    height: '400px'
                }}>
                    <div style={{ width: '100%', height: '100%' }}>
                        <ReactECharts option={barOption} style={{ height: '100%', width: '100%' }} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ValidationViewer;
