/* global Chart */

function parseJsonAttr(el, attrName) {
  const raw = el?.getAttribute(attrName) || "";
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (_e) {
    return null;
  }
}

function initFarmUtilizationChart() {
  const farmCanvas = document.getElementById("farmUtilizationChart");
  if (!farmCanvas || typeof Chart === "undefined") return;

  const farmChartData =
    parseJsonAttr(farmCanvas, "data-farms-chart") || [];

  if (!Array.isArray(farmChartData) || farmChartData.length === 0) return;

  const farmLabels = farmChartData.map((farm) => farm.nom);
  const farmUtilData = farmChartData.map((farm) => farm.utilisation_pct);
  const farmSuperficie = farmChartData.map((farm) => farm.superficie_ferme);
  const fermeIds = farmChartData.map((farm) => farm.id);

  const isDark = document.body.classList.contains("dark-mode");
  const textColor = isDark ? "#e0e0e0" : "#333333";
  const gridColor = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";

  // eslint-disable-next-line no-undef
  window.farmUtilizationChart = new Chart(farmCanvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: farmLabels,
      datasets: [
        {
          label: "Taux utilisation (%)",
          data: farmUtilData,
          backgroundColor: farmUtilData.map((v) =>
            v > 90
              ? "rgba(226, 114, 91, 0.8)"
              : v > 50
                ? "rgba(57, 255, 20, 0.6)"
                : "rgba(14, 165, 233, 0.6)",
          ),
          borderColor: farmUtilData.map((v) =>
            v > 90 ? "#E2725B" : v > 50 ? "#39FF14" : "#0ea5e9",
          ),
          borderWidth: 2,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          ticks: { color: textColor },
          grid: { color: gridColor },
        },
        y: {
          ticks: { color: textColor },
          grid: { display: false },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(22, 27, 19, 0.95)",
          titleColor: "#e0e0e0",
          bodyColor: "#39FF14",
          callbacks: {
            label: function (ctx) {
              const idx = ctx.dataIndex;
              return `Utilisation: ${ctx.raw}% (${farmSuperficie[idx]} ha total)`;
            },
          },
        },
      },
      onClick: function (_event, elements) {
        if (!elements || elements.length === 0) return;
        const idx = elements[0].index;
        const fermeId = String(fermeIds[idx]);
        const fermeSelect = document.getElementById("filterFerme");
        if (fermeSelect) fermeSelect.value = fermeId;
        if (typeof window.applyFarmFilter === "function") {
          window.applyFarmFilter(fermeId);
        } else {
          window.location.href = "?ferme=" + encodeURIComponent(fermeId);
        }
      },
    },
  });

  window.addEventListener("themeChanged", function () {
    if (!window.farmUtilizationChart) return;
    const newDark = document.body.classList.contains("dark-mode");
    const newText = newDark ? "#e0e0e0" : "#333333";
    const newGrid = newDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)";
    window.farmUtilizationChart.options.scales.x.ticks.color = newText;
    window.farmUtilizationChart.options.scales.x.grid.color = newGrid;
    window.farmUtilizationChart.options.scales.y.ticks.color = newText;
    window.farmUtilizationChart.update("none");
  });
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".farm-utilization-bar").forEach(function (bar) {
    const value = Math.min(Number(bar.dataset.utilization || 0), 100);
    bar.style.width = `${value}%`;
  });

  initFarmUtilizationChart();
});

