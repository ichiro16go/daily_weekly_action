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
import { Bar, Chart, Line } from "react-chartjs-2";

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

interface BarDataset {
  label: string;
  data: number[];
  backgroundColor?: string;
}

interface LineOverlayDataset {
  label: string;
  data: number[];
  borderColor?: string;
  backgroundColor?: string;
  yAxisID?: string;
}

interface BarChartProps {
  labels: string[];
  datasets: BarDataset[];
  title?: string;
  /** Optional line datasets overlaid on the same chart (combo bar+line). */
  lineDatasets?: LineOverlayDataset[];
}

export function BarChart({ labels, datasets, title, lineDatasets }: BarChartProps) {
  if (lineDatasets && lineDatasets.length > 0) {
    const hasSecondaryAxis = lineDatasets.some((d) => d.yAxisID === "y1");
    const data = {
      labels,
      datasets: [
        ...datasets.map((d) => ({
          type: "bar" as const,
          label: d.label,
          data: d.data,
          backgroundColor: d.backgroundColor,
          order: 2,
        })),
        ...lineDatasets.map((d) => ({
          type: "line" as const,
          label: d.label,
          data: d.data,
          borderColor: d.borderColor,
          backgroundColor: d.backgroundColor,
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          tension: 0.3,
          fill: false,
          order: 1,
          yAxisID: d.yAxisID,
        })),
      ],
    };
    return (
      <Chart
        type="bar"
        data={data}
        options={{
          responsive: true,
          // デフォルト aspectRatio=2 だと縦長すぎるため 4 に（高さ約 1/2）
          aspectRatio: 4,
          plugins: {
            title: { display: !!title, text: title, font: { size: 13, weight: "normal" }, color: "#6b7280" },
            legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } },
          },
          scales: {
            y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
            ...(hasSecondaryAxis
              ? {
                  y1: {
                    beginAtZero: true,
                    position: "right" as const,
                    grid: { display: false },
                    ticks: {
                      font: { size: 11 },
                      callback: (v: number | string) => `${v}%`,
                    },
                    title: { display: true, text: "閉じ率", font: { size: 10 }, color: "#6b7280" },
                  },
                }
              : {}),
            x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          },
        }}
      />
    );
  }
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
