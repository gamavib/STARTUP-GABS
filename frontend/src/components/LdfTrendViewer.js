import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';

const LdfTrendViewer = ({ ramo }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchLdfs = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`/actuarial/ldf-matrix?ramo=${ramo || ''}`);
                setData(response.data);
            } catch (err) {
                setError('Error cargando la matriz de factores');
            } finally {
                setLoading(false);
            }
        };
        fetchLdfs();
    }, [ramo]);

    if (loading) return <div style={{ textAlign: 'center', padding: '20px' }}>Cargando tendencias de LDF...</div>;
    if (error) return <div style={{ textAlign: 'center', padding: '20px', color: 'red' }}>{error}</div>;
    if (!data) return null;

    const ldfMatrix = data.ldf_matrix;
    const periods = Object.keys(ldfMatrix[Object.keys(ldfMatrix)[0]] || {});
    const originYears = Object.keys(ldfMatrix);

    const series = originYears.map(year => ({
        name: `Año ${year}`,
        type: 'line',
        smooth: true,
        data: periods.map(p => ldfMatrix[year][p]),
        symbolSize: 8,
        lineStyle: { width: 2 }
    }));

    const option = {
        title: { text: 'Tendencia de Factores de Desarrollo (LDF)', left: 'center', textStyle: { fontSize: 16, color: '#2c3e50' } },
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, type: 'scroll' },
        grid: { left: '5%', right: '5%', bottom: '15%', containLabel: true },
        xAxis: {
            type: 'category',
            data: periods,
            name: 'Periodo Desarrollo',
            axisLabel: { color: '#7f8c8d' }
        },
        yAxis: {
            type: 'value',
            name: 'Factor',
            axisLabel: { formatter: (value) => value.toFixed(2) },
            min: (value) => Math.floor(value.min * 100) / 100
        },
        series: series
    };

    return (
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '30px' }}>
            <div style={{ width: '100%', height: 400 }}>
                <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
            </div>
        </div>
    );
};

export default LdfTrendViewer;
