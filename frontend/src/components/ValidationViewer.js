import React from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

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

    const prepareErrorLineOption = () => {
        return {
            title: {
                text: 'Evolución del Error de Reserva',
                left: 'center',
                textStyle: { color: '#2c3e50', fontSize: 16 }
            },
            tooltip: {
                trigger: 'axis',
                formatter: (params) => {
                    const p = params[0];
                    return `Año ${p.name}<br/><b style="color:#3498db">Error: $${p.value?.toLocaleString()}</b>`;
                }
            },
            grid: {
                top: '20%',
                bottom: '10%',
                left: '10%',
                right: '5%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: series.map(d => d.year),
                axisLine: { lineStyle: { color: '#7f8c8d' } }
            },
            yAxis: {
                type: 'value',
                axisLabel: { formatter: (value) => `$${value.toLocaleString()}` },
                axisLine: { show: true, lineStyle: { color: '#7f8c8d' } }
            },
            series: [
                {
                    name: 'Error',
                    type: 'line',
                    data: series.map(d => d.error),
                    smooth: true,
                    symbolSize: 8,
                    itemStyle: { color: '#3498db' },
                    lineStyle: { width: 3 },
                    emphasis: { focus: 'series' }
                }
            ]
        };
    };

    const prepareComparisonBarOption = () => {
        return {
            title: {
                text: 'Estimado vs Real por Año',
                left: 'center',
                textStyle: { color: '#2c3e50', fontSize: 16 }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: (params) => {
                    let res = `Año ${params[0].name}<br/>`;
                    params.forEach(p => {
                        res += `${p.marker} ${p.seriesName}: <b>$${p.value?.toLocaleString()}</b><br/>`;
                    });
                    return res;
                }
            },
            legend: {
                bottom: 0,
                data: ['Estimado', 'Real']
            },
            grid: {
                top: '20%',
                bottom: '10%',
                left: '10%',
                right: '5%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: series.map(d => d.year),
                axisLine: { lineStyle: { color: '#7f8c8d' } }
            },
            yAxis: {
                type: 'value',
                axisLabel: { formatter: (value) => `$${value.toLocaleString()}` },
                axisLine: { show: true, lineStyle: { color: '#7f8c8d' } }
            },
            series: [
                {
                    name: 'Estimado',
                    type: 'bar',
                    data: series.map(d => d.estimated),
                    itemStyle: { color: '#3498db' },
                    emphasis: { focus: 'series' }
                },
                {
                    name: 'Real',
                    type: 'bar',
                    data: series.map(d => d.actual),
                    itemStyle: { color: '#2ecc71' },
                    emphasis: { focus: 'series' }
                }
            ]
        };
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
                    <h3 style={{ color: '#2c3e50', fontSize: '16px', marginBottom: '20px', textAlign: 'center' }}>Evolución del Error de Reserva</h3>
                    <ResponsiveContainer width="100%" height="80%">
                        <LineChart data={series}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="year" label={{ value: 'Año', position: 'insideBottom', offset: -5 }} />
                            <YAxis label={{ value: 'Error ($)', angle: -90, position: 'insideLeft' }} />
                            <Tooltip />
                            <Line type="monotone" dataKey="error" stroke="#3498db" strokeWidth={3} dot={{ r: 6 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                <div style={{
                    backgroundColor: 'white',
                    padding: '20px',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                    height: '400px'
                }}>
                    <h3 style={{ color: '#2c3e50', fontSize: '16px', marginBottom: '20px', textAlign: 'center' }}>Estimado vs Real por Año</h3>
                    <ResponsiveContainer width="100%" height="80%">
                        <BarChart data={series}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="year" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="estimated" name="Estimado" fill="#3498db" />
                            <Bar dataKey="actual" name="Real" fill="#2ecc71" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default ValidationViewer;
