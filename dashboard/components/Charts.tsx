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
          title: { display: !!title, text: title },
          legend: { position: "bottom" },
        },
        scales: { y: { beginAtZero: true } },
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
      data={{ labels, datasets }}
      options={{
        responsive: true,
        plugins: {
          title: { display: !!title, text: title },
          legend: { position: "bottom" },
        },
        scales: { y: { beginAtZero: true } },
      }}
    />
  );
}
