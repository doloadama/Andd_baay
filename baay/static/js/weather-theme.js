/**
 * Thèmes visuels pour la météo OpenWeatherMap (codes icône 01d…50n).
 * Utilisé par la fiche projet et le cockpit dashboard.
 */
(function (global) {
    "use strict";

    var DEFAULT_KEY = "02d";

    /** @typedef {{ i: string, c: string }} Deco */
    /** @typedef {{ panelClass: string, cockpitSkin: string, cockpitIcon: string, decos: Deco[] }} Theme */

    /** @type {Record<string, Theme>} */
    var THEMES = {
        "01d": {
            panelClass: "pd-meteo--clear-day",
            cockpitSkin: "cw-skin-clear-day",
            cockpitIcon: "fa-sun",
            decos: [
                { i: "fa-sun", c: "pd-meteo-deco pd-meteo-deco--sun" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-tiny" },
            ],
        },
        "01n": {
            panelClass: "pd-meteo--clear-night",
            cockpitSkin: "cw-skin-clear-night",
            cockpitIcon: "fa-moon",
            decos: [
                { i: "fa-moon", c: "pd-meteo-deco pd-meteo-deco--moon" },
                { i: "fa-star", c: "pd-meteo-deco pd-meteo-deco--star pd-meteo-deco--star-1" },
                { i: "fa-star", c: "pd-meteo-deco pd-meteo-deco--star pd-meteo-deco--star-2" },
            ],
        },
        "02d": {
            panelClass: "pd-meteo--few-clouds-day",
            cockpitSkin: "cw-skin-few-clouds-day",
            cockpitIcon: "fa-cloud-sun",
            decos: [
                { i: "fa-sun", c: "pd-meteo-deco pd-meteo-deco--sun" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
            ],
        },
        "02n": {
            panelClass: "pd-meteo--few-clouds-night",
            cockpitSkin: "cw-skin-few-clouds-night",
            cockpitIcon: "fa-cloud-moon",
            decos: [
                { i: "fa-moon", c: "pd-meteo-deco pd-meteo-deco--moon" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
            ],
        },
        "03d": {
            panelClass: "pd-meteo--cloudy-day",
            cockpitSkin: "cw-skin-cloudy-day",
            cockpitIcon: "fa-cloud",
            decos: [
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-2" },
            ],
        },
        "03n": {
            panelClass: "pd-meteo--cloudy-night",
            cockpitSkin: "cw-skin-cloudy-night",
            cockpitIcon: "fa-cloud",
            decos: [
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
                { i: "fa-moon", c: "pd-meteo-deco pd-meteo-deco--moon-subtle" },
            ],
        },
        "04d": {
            panelClass: "pd-meteo--overcast-day",
            cockpitSkin: "cw-skin-overcast-day",
            cockpitIcon: "fa-cloud",
            decos: [
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-2" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-3" },
            ],
        },
        "04n": {
            panelClass: "pd-meteo--overcast-night",
            cockpitSkin: "cw-skin-overcast-night",
            cockpitIcon: "fa-cloud",
            decos: [
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-2" },
            ],
        },
        "09d": {
            panelClass: "pd-meteo--rain-day",
            cockpitSkin: "cw-skin-rain",
            cockpitIcon: "fa-cloud-rain",
            decos: [
                { i: "fa-cloud-rain", c: "pd-meteo-deco pd-meteo-deco--rain-main" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-back" },
            ],
        },
        "09n": {
            panelClass: "pd-meteo--rain-night",
            cockpitSkin: "cw-skin-rain-night",
            cockpitIcon: "fa-cloud-moon-rain",
            decos: [
                { i: "fa-cloud-moon-rain", c: "pd-meteo-deco pd-meteo-deco--rain-main" },
            ],
        },
        "10d": {
            panelClass: "pd-meteo--rain-day",
            cockpitSkin: "cw-skin-rain",
            cockpitIcon: "fa-cloud-sun-rain",
            decos: [
                { i: "fa-cloud-sun-rain", c: "pd-meteo-deco pd-meteo-deco--rain-main" },
            ],
        },
        "10n": {
            panelClass: "pd-meteo--rain-night",
            cockpitSkin: "cw-skin-rain-night",
            cockpitIcon: "fa-cloud-moon-rain",
            decos: [
                { i: "fa-cloud-moon-rain", c: "pd-meteo-deco pd-meteo-deco--rain-main" },
            ],
        },
        "11d": {
            panelClass: "pd-meteo--storm-day",
            cockpitSkin: "cw-skin-storm",
            cockpitIcon: "fa-bolt",
            decos: [
                { i: "fa-bolt", c: "pd-meteo-deco pd-meteo-deco--bolt" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-dark" },
            ],
        },
        "11n": {
            panelClass: "pd-meteo--storm-night",
            cockpitSkin: "cw-skin-storm-night",
            cockpitIcon: "fa-bolt",
            decos: [
                { i: "fa-bolt", c: "pd-meteo-deco pd-meteo-deco--bolt" },
                { i: "fa-cloud-moon-rain", c: "pd-meteo-deco pd-meteo-deco--rain-main" },
            ],
        },
        "13d": {
            panelClass: "pd-meteo--snow-day",
            cockpitSkin: "cw-skin-snow",
            cockpitIcon: "fa-snowflake",
            decos: [
                { i: "fa-snowflake", c: "pd-meteo-deco pd-meteo-deco--snow-1" },
                { i: "fa-snowflake", c: "pd-meteo-deco pd-meteo-deco--snow-2" },
                { i: "fa-cloud", c: "pd-meteo-deco pd-meteo-deco--cloud-light" },
            ],
        },
        "13n": {
            panelClass: "pd-meteo--snow-night",
            cockpitSkin: "cw-skin-snow-night",
            cockpitIcon: "fa-snowflake",
            decos: [
                { i: "fa-snowflake", c: "pd-meteo-deco pd-meteo-deco--snow-1" },
                { i: "fa-moon", c: "pd-meteo-deco pd-meteo-deco--moon-subtle" },
            ],
        },
        "50d": {
            panelClass: "pd-meteo--fog-day",
            cockpitSkin: "cw-skin-fog",
            cockpitIcon: "fa-smog",
            decos: [
                { i: "fa-smog", c: "pd-meteo-deco pd-meteo-deco--fog" },
                { i: "fa-wind", c: "pd-meteo-deco pd-meteo-deco--wind" },
            ],
        },
        "50n": {
            panelClass: "pd-meteo--fog-night",
            cockpitSkin: "cw-skin-fog-night",
            cockpitIcon: "fa-smog",
            decos: [
                { i: "fa-smog", c: "pd-meteo-deco pd-meteo-deco--fog" },
            ],
        },
    };

    /**
     * @param {string} [icone]
     * @returns {Theme}
     */
    function resolveOpenWeatherTheme(icone) {
        var key =
            icone && String(icone).length >= 3
                ? String(icone).toLowerCase().slice(0, 3)
                : DEFAULT_KEY;
        return THEMES[key] || THEMES[DEFAULT_KEY];
    }

    global.resolveOpenWeatherTheme = resolveOpenWeatherTheme;
})(
    typeof window !== "undefined" ? window : typeof globalThis !== "undefined" ? globalThis : this
);
