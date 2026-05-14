import React, { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from "chart.js";

// Реєструємо необхідні модулі Chart.js
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const SensorCharts = ({ bellId }) => {
    const [sensorData, setSensorData] = useState(null);

    useEffect(() => {
        setSensorData(null); // Очищення попередніх даних перед новим запитом
        fetch(`http://10.0.60.208:8080/site/get_sensor_data/${bellId}`)
            .then((response) => response.json())
            .then((data) => setSensorData(data))
            .catch((error) => console.error("Помилка завантаження даних:", error));
    }, [bellId]); // bellId у залежностях

    if (!sensorData) return <p>Дані відсутні або завантажуються...</p>;

    const chartsConfig = [
        { id: "tempChart", label: "Температура (°C)", data: sensorData.temperature, color: "rgba(255, 99, 132, 1)" },
        { id: "airQualityChart", label: "Якість повітря", data: sensorData.airQuality, color: "rgba(54, 162, 235, 1)" },
        { id: "noiseChart", label: "Шум (dB)", data: sensorData.noise, color: "rgba(255, 206, 86, 1)" },
        { id: "humidityChart", label: "Вологість (%)", data: sensorData.humidity, color: "rgba(75, 192, 192, 1)" }
    ];

    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            {chartsConfig.map((config) => (
                <div key={config.id} className="sensors">
                    <h3 style={{ textAlign: "center" }}>{config.label}</h3>
                    <Line
                        data={{
                            labels: sensorData.labels,
                            datasets: [
                                {
                                    label: config.label,
                                    data: config.data,
                                    borderColor: config.color,
                                    backgroundColor: config.color.replace("1)", "0.2)"),
                                    borderWidth: 2
                                }
                            ]
                        }}
                        options={{
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }}
                    />
                </div>
            ))}
        </div>
    );
};

export default SensorCharts;
