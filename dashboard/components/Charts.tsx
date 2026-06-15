"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface BarChartProps {
  labels: string[];
  datasets: { label: string; data: number[]; backgroundColor?: string }[];
  title?: string;
}

export function BarChart({ labels, datasets, title }: BarChartProps) {
  return (
    <Bar
      data={{ labels, datasets }}
      options={{
        responsive: true,
        plugins: {
          title: { display: !!title, text: title, font: { size: 13, weight: "normal" }, color: "#6b7280" },
          legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      }}
    />
  );
}

interface LineChartProps {
  labels: string[];
  datasets: { label: string; data: number[]; borderColor?: string; backgroundColor?: string }[];
  title?: string;
}

export function LineChart({ labels, datasets, title }: LineChartProps) {
  return (
    <Line
      data={{
        labels,
        datasets: datasets.map((ds) => ({
          ...ds,
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          tension: 0.3,
          fill: true,
        })),
      }}
      options={{
        responsive: true,
        plugins: {
          title: { display: !!title, text: title, font: { size: 13, weight: "normal" }, color: "#6b7280" },
          legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
        },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      }}
    />
  );
}
