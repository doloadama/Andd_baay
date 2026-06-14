/**
 * Andd Baay — Dashboard unifié V4
 * Cartes Chart.js, carte Leaflet, onglets Alpine.
 */
(function () {
    'use strict';

    var CHART_COLORS = {
        brand: '#1D9E75',
        deep: '#085041',
        accent: '#EF9F27',
        palette: ['#1D9E75', '#085041', '#EF9F27', '#D4AF37', '#795548'],
    };

    function readJson(id) {
        var el = document.getElementById(id);
        if (!el || !el.textContent) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function chartDefaults() {
        if (!window.Chart) return;
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = getComputedStyle(document.documentElement)
            .getPropertyValue('--db-muted').trim() || '#64748b';
    }

    function initMap() {
        if (!window.L) return;
        var markersEl = document.getElementById('dashboard-map-markers');
        var mapEl = document.getElementById('dashboardMap');
        var emptyEl = document.getElementById('dashboardMapEmpty');
        if (!markersEl || !mapEl) return;

        var markers = readJson('dashboard-map-markers') || [];
        if (!markers.length) {
            mapEl.classList.add('d-none');
            if (emptyEl) emptyEl.classList.remove('d-none');
            return;
        }

        var map = L.map('dashboardMap', { zoomControl: false, attributionControl: false })
            .setView([markers[0].lat, markers[0].lng], 10);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

        var leafletMarkers = markers.map(function (m) {
            return L.marker([m.lat, m.lng]).addTo(map).bindPopup(m.title);
        });
        if (leafletMarkers.length > 1) {
            map.fitBounds(L.featureGroup(leafletMarkers).getBounds().pad(0.1));
        }
    }

    function initWeather() {
        var w = document.getElementById('atWeatherWidget');
        if (!w || !window.WeatherWidget) return;
        var fermeId = w.getAttribute('data-weather-ferme') || '';
        if (!fermeId && !w.getAttribute('data-weather-fetch')) {
            WeatherWidget.setError(w, 'Aucune ferme geolocalisee');
        }
    }

    function doughnutOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: { legend: { display: false } },
        };
    }

    function initCharts(config) {
        if (!window.Chart) return;
        chartDefaults();

        var yieldCtx = document.getElementById('yieldChart');
        if (yieldCtx && config.cultures.length) {
            new Chart(yieldCtx, {
                type: 'bar',
                data: {
                    labels: config.cultures.map(function (c) { return c.nom; }),
                    datasets: [{
                        label: 'Production (kg)',
                        data: config.cultures.map(function (c) { return c.rendement; }),
                        backgroundColor: CHART_COLORS.brand,
                        borderRadius: 8,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                },
            });
        }

        var cultureCtx = document.getElementById('cultureChart');
        if (cultureCtx && config.cultures.length) {
            new Chart(cultureCtx, {
                type: 'doughnut',
                data: {
                    labels: config.cultures.map(function (c) { return c.nom; }),
                    datasets: [{
                        data: config.cultures.map(function (c) { return c.superficie; }),
                        backgroundColor: CHART_COLORS.palette,
                        borderWidth: 0,
                    }],
                },
                options: doughnutOptions(),
            });
        }

        var statusCtx = document.getElementById('statusChart');
        if (statusCtx) {
            new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: ['En cours', 'Termines', 'En pause'],
                    datasets: [{
                        data: [config.status.en_cours, config.status.finis, config.status.en_pause],
                        backgroundColor: [CHART_COLORS.brand, CHART_COLORS.deep, CHART_COLORS.accent],
                        borderWidth: 0,
                    }],
                },
                options: doughnutOptions(),
            });
        }

        if (!config.finance.enabled) return;

        var cashflowCtx = document.getElementById('cashflowChart');
        var financeData = readJson('cockpit-finance-monthly');
        if (cashflowCtx && financeData) {
            new Chart(cashflowCtx, {
                type: 'line',
                data: {
                    labels: financeData.labels,
                    datasets: [
                        {
                            label: 'Recettes',
                            data: financeData.recettes,
                            borderColor: CHART_COLORS.brand,
                            tension: 0.4,
                            fill: true,
                            backgroundColor: 'rgba(29, 158, 117, 0.06)',
                            borderWidth: 3,
                        },
                        {
                            label: 'Sorties',
                            data: financeData.depenses,
                            borderColor: CHART_COLORS.accent,
                            tension: 0.4,
                            fill: true,
                            backgroundColor: 'rgba(239, 159, 39, 0.06)',
                            borderWidth: 3,
                            borderDash: [5, 5],
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: 'index' },
                    plugins: { legend: { position: 'top', align: 'end' } },
                },
            });
        }

        var investCtx = document.getElementById('investCatChart');
        var investData = readJson('cockpit-invest-by-category');
        if (investCtx && investData) {
            new Chart(investCtx, {
                type: 'doughnut',
                data: {
                    labels: investData.labels,
                    datasets: [{
                        data: investData.values,
                        backgroundColor: CHART_COLORS.palette,
                        borderWidth: 0,
                    }],
                },
                options: doughnutOptions(),
            });
        }
    }

    window.dashboardUnifiedTabsData = function () {
        var params = new URLSearchParams(window.location.search);
        var initial = params.get('tab') || 'overview';
        var order = ['overview', 'performance', 'activities'];
        var base = {
            activeTab: order.indexOf(initial) >= 0 ? initial : 'overview',
            fabActive: false,
            updateTab: function (tab) {
                this.activeTab = tab;
                var url = new URL(window.location.href);
                url.searchParams.set('tab', tab);
                window.history.pushState({}, '', url);
            },
        };
        var mixin = typeof tabRouletteMixin === 'function'
            ? tabRouletteMixin({
                order: order,
                select: function (tab) { this.updateTab(tab); },
            })
            : {};
        return Object.assign(base, mixin, {
            init: function () {
                if (typeof this.initTabRoulette === 'function') this.initTabRoulette();
                if (typeof this.initTabRouletteScrollSync === 'function') this.initTabRouletteScrollSync();
            },
        });
    };

    document.addEventListener('DOMContentLoaded', function () {
        initMap();
        initWeather();

        var chartConfigEl = document.getElementById('db-chart-config');
        if (chartConfigEl) {
            initCharts(readJson('db-chart-config') || {});
        }
    });
})();
