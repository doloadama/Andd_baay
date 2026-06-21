/**
 * Fiche projet — onglets Alpine, carte Leaflet, graphique Chart.js
 */
(function () {
    'use strict';

    function projetDetailTabsData() {
        var root = document.querySelector('.pd-page');
        var order = ['dashboard', 'products'];
        if (root && root.dataset.canFinance === '1') {
            order.push('finance');
        }
        order.push('expertise', 'accompagnement', 'management');

        var base = { activeTab: 'dashboard' };
        var mixin = typeof tabRouletteMixin === 'function'
            ? tabRouletteMixin({
                order: order,
                select: function (tab) { this.activeTab = tab; }
            })
            : {};
        return Object.assign(base, mixin, {
            init: function () {
                if (typeof this.initTabRoulette === 'function') {
                    this.initTabRoulette();
                }
                if (typeof this.initTabRouletteScrollSync === 'function') {
                    this.initTabRouletteScrollSync();
                }
            }
        });
    }

    window.projetDetailTabsData = projetDetailTabsData;

    function initProjectMap() {
        var el = document.getElementById('projectMap');
        if (!el || typeof L === 'undefined') {
            return;
        }
        var lat = parseFloat(el.dataset.lat, 10);
        var lon = parseFloat(el.dataset.lon, 10);
        if (Number.isNaN(lat) || Number.isNaN(lon)) {
            return;
        }

        var map = L.map(el, {
            zoomControl: false,
            attributionControl: false
        }).setView([lat, lon], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '\u00a9 OpenStreetMap'
        }).addTo(map);

        var ferme = el.dataset.ferme || '';
        var projet = el.dataset.projet || '';
        L.marker([lat, lon]).addTo(map)
            .bindPopup('<strong>' + ferme + '</strong><br>' + projet)
            .openPopup();
    }

    function initGrowthChart() {
        var canvas = document.getElementById('growthCurveChart');
        if (!canvas || typeof Chart === 'undefined') {
            return;
        }

        var brandColor = '#1D9E75';
        new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Semaine 1', 'Semaine 3', 'Semaine 5', 'Semaine 7', 'Semaine 9', 'Semaine 12'],
                datasets: [{
                    label: 'Volume de biomasse',
                    data: [5, 12, 35, 68, 85, 95],
                    borderColor: brandColor,
                    backgroundColor: 'rgba(29, 158, 117, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointBackgroundColor: brandColor
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { display: false } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initProjectMap();
        initGrowthChart();
    });
})();
