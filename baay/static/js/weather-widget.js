/**
 * Widget météo unifié (OpenWeather) — rendu, thèmes adaptatifs, fetch API.
 * Dépend de weather-theme.js (resolveOpenWeatherTheme).
 */
(function (global) {
    "use strict";

    var PANEL_PREFIX = "pd-meteo--";
    var COCKPIT_SKIN_PREFIX = "cw-skin-";

    function resolveTheme(icone) {
        return (
            global.resolveOpenWeatherTheme ||
            function () {
                return { panelClass: "", cockpitSkin: "", cockpitIcon: "fa-cloud-sun", decos: [] };
            }
        )(icone);
    }

    function stripWeatherClasses(el) {
        if (!el || !el.classList) return;
        Array.from(el.classList).forEach(function (cls) {
            if (
                cls.indexOf(PANEL_PREFIX) === 0 ||
                cls.indexOf(COCKPIT_SKIN_PREFIX) === 0
            ) {
                el.classList.remove(cls);
            }
        });
    }

    function renderSkyDecos(skyEl, decos) {
        if (!skyEl) return;
        skyEl.innerHTML = "";
        (decos || []).forEach(function (deco) {
            var icon = document.createElement("i");
            icon.className = "fas " + deco.i + " " + deco.c;
            icon.setAttribute("aria-hidden", "true");
            skyEl.appendChild(icon);
        });
    }

    function capitalizeDescription(text) {
        var s = (text || "").trim();
        if (!s) return "";
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    /**
     * Applique le thème visuel (dégradé + décors).
     * @param {HTMLElement} root
     * @param {string} [icone]
     * @param {{ cockpit?: boolean }} [opts]
     */
    function applyTheme(root, icone, opts) {
        opts = opts || {};
        var theme = resolveTheme(icone);
        stripWeatherClasses(root);
        if (theme.panelClass) root.classList.add(theme.panelClass);
        if (opts.cockpit && theme.cockpitSkin) root.classList.add(theme.cockpitSkin);
        renderSkyDecos(root.querySelector("[data-weather-sky]"), theme.decos);
        return theme;
    }

    function setText(el, text) {
        if (el) el.textContent = text;
    }

    function setIconImg(wrapEl, icone, description) {
        if (!wrapEl) return;
        if (icone) {
            wrapEl.innerHTML =
                '<img class="pd-meteo-owm-img" data-weather-icon src="https://openweathermap.org/img/wn/' +
                encodeURIComponent(icone) +
                '@2x.png" alt="' +
                (description || "Météo").replace(/"/g, "&quot;") +
                '" width="64" height="64" loading="lazy">';
        } else {
            var theme = resolveTheme(null);
            wrapEl.innerHTML =
                '<i class="fas ' +
                (theme.cockpitIcon || "fa-cloud-sun") +
                ' pd-meteo-fa-fallback" data-weather-fa aria-hidden="true"></i>';
        }
    }

    /**
     * Met à jour le contenu d’un widget [data-weather-widget].
     * @param {HTMLElement} root
     * @param {{ temperature?: number, description?: string, icone?: string, humidite?: number, vent?: number }} data
     * @param {{ cockpit?: boolean }} [opts]
     */
    function update(root, data, opts) {
        if (!root || !data) return;
        opts = opts || {};
        var theme = applyTheme(root, data.icone, opts);

        var temp =
            data.temperature != null && !Number.isNaN(Number(data.temperature))
                ? Math.round(Number(data.temperature)) + "°C"
                : "--°C";
        setText(root.querySelector("[data-weather-temp]"), temp);
        setText(
            root.querySelector("[data-weather-desc]"),
            capitalizeDescription(data.description || "")
        );

        var metaEl = root.querySelector("[data-weather-meta]");
        if (metaEl) {
            var parts = [];
            if (data.humidite != null) parts.push("Humidité " + data.humidite + "%");
            if (data.vent != null) parts.push("Vent " + data.vent + " km/h");
            metaEl.textContent = parts.join(" · ");
            metaEl.hidden = parts.length === 0;
        }

        var wrapEl = root.querySelector("[data-weather-icon-wrap]");
        if (wrapEl) {
            setIconImg(wrapEl, data.icone, data.description);
        }

        var faEl = root.querySelector("[data-weather-fa]");
        if (faEl) {
            faEl.className = "fas " + (theme.cockpitIcon || "fa-cloud-sun") + " cw-weather-icon";
        }

        root.classList.remove("pd-meteo-widget--loading");
        root.setAttribute("aria-busy", "false");
    }

    function setError(root, message, opts) {
        if (!root) return;
        opts = opts || {};
        stripWeatherClasses(root);
        root.classList.remove("pd-meteo-widget--loading");
        root.setAttribute("aria-busy", "false");
        setText(root.querySelector("[data-weather-temp]"), "");
        setText(root.querySelector("[data-weather-desc]"), message || "Météo indisponible");
        var wrapEl = root.querySelector("[data-weather-icon-wrap]");
        if (wrapEl) {
            wrapEl.innerHTML =
                '<i class="fas fa-cloud-sun cw-weather-icon" aria-hidden="true"></i>';
        }
    }

    function setLoading(root) {
        if (!root) return;
        root.classList.add("pd-meteo-widget--loading");
        root.setAttribute("aria-busy", "true");
        setText(root.querySelector("[data-weather-desc]"), "Chargement météo…");
    }

    /**
     * Charge la météo depuis une URL JSON { ok, data }.
     */
    function load(root, url, opts) {
        if (!root || !url) return Promise.resolve();
        opts = opts || {};
        setLoading(root);
        return fetch(url)
            .then(function (res) {
                return res.json();
            })
            .then(function (payload) {
                if (payload && payload.ok && payload.data) {
                    update(root, payload.data, opts);
                    return payload.data;
                }
                var msg =
                    payload && payload.error === "coords_absentes"
                        ? "GPS ferme à renseigner"
                        : payload && payload.error === "api_key_absente"
                          ? "Météo : clé API absente"
                          : payload && payload.error === "coords_manquantes"
                            ? "Coordonnées GPS manquantes"
                            : "Météo indisponible";
                setError(root, msg, opts);
                return null;
            })
            .catch(function () {
                setError(root, "Erreur réseau météo", opts);
                return null;
            });
    }

    /**
     * Monte tous les widgets [data-weather-fetch] sur la page.
     */
    function initAll() {
        document.querySelectorAll("[data-weather-fetch]").forEach(function (root) {
            var url = root.getAttribute("data-weather-fetch");
            var cockpit = root.classList.contains("cockpit-weather");
            if (url) load(root, url, { cockpit: cockpit });
        });
    }

    /**
     * @param {HTMLElement} root
     * @param {{ fetchUrl?: string, data?: object, cockpit?: boolean }} options
     */
    function mount(root, options) {
        options = options || {};
        if (!root) return Promise.resolve();
        if (options.data) {
            update(root, options.data, { cockpit: options.cockpit });
            return Promise.resolve(options.data);
        }
        if (options.fetchUrl) {
            return load(root, options.fetchUrl, { cockpit: options.cockpit });
        }
        return Promise.resolve();
    }

    global.WeatherWidget = {
        applyTheme: applyTheme,
        update: update,
        load: load,
        mount: mount,
        initAll: initAll,
        setError: setError,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }

    document.body.addEventListener("htmx:afterSwap", function (evt) {
        if (!evt.detail || !evt.detail.target) return;
        evt.detail.target.querySelectorAll("[data-weather-fetch]").forEach(function (root) {
            var url = root.getAttribute("data-weather-fetch");
            if (url) load(root, url, { cockpit: root.classList.contains("cockpit-weather") });
        });
    });
})(typeof window !== "undefined" ? window : globalThis);
