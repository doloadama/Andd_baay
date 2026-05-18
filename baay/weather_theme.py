"""Thèmes météo OpenWeather (miroir de weather-theme.js) pour le rendu serveur."""

from __future__ import annotations

from typing import Any, TypedDict

DEFAULT_KEY = "02d"


class WeatherDeco(TypedDict):
    i: str
    c: str


class WeatherTheme(TypedDict):
    panel_class: str
    cockpit_skin: str
    cockpit_icon: str
    decos: list[WeatherDeco]


def _deco(icon: str, classes: str) -> WeatherDeco:
    return {"i": icon, "c": classes}


THEMES: dict[str, WeatherTheme] = {
    "01d": {
        "panel_class": "pd-meteo--clear-day",
        "cockpit_skin": "cw-skin-clear-day",
        "cockpit_icon": "fa-sun",
        "decos": [
            _deco("fa-sun", "pd-meteo-deco pd-meteo-deco--sun"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-tiny"),
        ],
    },
    "01n": {
        "panel_class": "pd-meteo--clear-night",
        "cockpit_skin": "cw-skin-clear-night",
        "cockpit_icon": "fa-moon",
        "decos": [
            _deco("fa-moon", "pd-meteo-deco pd-meteo-deco--moon"),
            _deco("fa-star", "pd-meteo-deco pd-meteo-deco--star pd-meteo-deco--star-1"),
            _deco("fa-star", "pd-meteo-deco pd-meteo-deco--star pd-meteo-deco--star-2"),
        ],
    },
    "02d": {
        "panel_class": "pd-meteo--few-clouds-day",
        "cockpit_skin": "cw-skin-few-clouds-day",
        "cockpit_icon": "fa-cloud-sun",
        "decos": [
            _deco("fa-sun", "pd-meteo-deco pd-meteo-deco--sun"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
        ],
    },
    "02n": {
        "panel_class": "pd-meteo--few-clouds-night",
        "cockpit_skin": "cw-skin-few-clouds-night",
        "cockpit_icon": "fa-cloud-moon",
        "decos": [
            _deco("fa-moon", "pd-meteo-deco pd-meteo-deco--moon"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
        ],
    },
    "03d": {
        "panel_class": "pd-meteo--cloudy-day",
        "cockpit_skin": "cw-skin-cloudy-day",
        "cockpit_icon": "fa-cloud",
        "decos": [
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-2"),
        ],
    },
    "03n": {
        "panel_class": "pd-meteo--cloudy-night",
        "cockpit_skin": "cw-skin-cloudy-night",
        "cockpit_icon": "fa-cloud",
        "decos": [
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
            _deco("fa-moon", "pd-meteo-deco pd-meteo-deco--moon-subtle"),
        ],
    },
    "04d": {
        "panel_class": "pd-meteo--overcast-day",
        "cockpit_skin": "cw-skin-overcast-day",
        "cockpit_icon": "fa-cloud",
        "decos": [
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-2"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-3"),
        ],
    },
    "04n": {
        "panel_class": "pd-meteo--overcast-night",
        "cockpit_skin": "cw-skin-overcast-night",
        "cockpit_icon": "fa-cloud",
        "decos": [
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-2"),
        ],
    },
    "09d": {
        "panel_class": "pd-meteo--rain-day",
        "cockpit_skin": "cw-skin-rain",
        "cockpit_icon": "fa-cloud-rain",
        "decos": [
            _deco("fa-cloud-rain", "pd-meteo-deco pd-meteo-deco--rain-main"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-back"),
        ],
    },
    "09n": {
        "panel_class": "pd-meteo--rain-night",
        "cockpit_skin": "cw-skin-rain-night",
        "cockpit_icon": "fa-cloud-moon-rain",
        "decos": [_deco("fa-cloud-moon-rain", "pd-meteo-deco pd-meteo-deco--rain-main")],
    },
    "10d": {
        "panel_class": "pd-meteo--rain-day",
        "cockpit_skin": "cw-skin-rain",
        "cockpit_icon": "fa-cloud-sun-rain",
        "decos": [_deco("fa-cloud-sun-rain", "pd-meteo-deco pd-meteo-deco--rain-main")],
    },
    "10n": {
        "panel_class": "pd-meteo--rain-night",
        "cockpit_skin": "cw-skin-rain-night",
        "cockpit_icon": "fa-cloud-moon-rain",
        "decos": [_deco("fa-cloud-moon-rain", "pd-meteo-deco pd-meteo-deco--rain-main")],
    },
    "11d": {
        "panel_class": "pd-meteo--storm-day",
        "cockpit_skin": "cw-skin-storm",
        "cockpit_icon": "fa-bolt",
        "decos": [
            _deco("fa-bolt", "pd-meteo-deco pd-meteo-deco--bolt"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-dark"),
        ],
    },
    "11n": {
        "panel_class": "pd-meteo--storm-night",
        "cockpit_skin": "cw-skin-storm-night",
        "cockpit_icon": "fa-bolt",
        "decos": [
            _deco("fa-bolt", "pd-meteo-deco pd-meteo-deco--bolt"),
            _deco("fa-cloud-moon-rain", "pd-meteo-deco pd-meteo-deco--rain-main"),
        ],
    },
    "13d": {
        "panel_class": "pd-meteo--snow-day",
        "cockpit_skin": "cw-skin-snow",
        "cockpit_icon": "fa-snowflake",
        "decos": [
            _deco("fa-snowflake", "pd-meteo-deco pd-meteo-deco--snow-1"),
            _deco("fa-snowflake", "pd-meteo-deco pd-meteo-deco--snow-2"),
            _deco("fa-cloud", "pd-meteo-deco pd-meteo-deco--cloud-light"),
        ],
    },
    "13n": {
        "panel_class": "pd-meteo--snow-night",
        "cockpit_skin": "cw-skin-snow-night",
        "cockpit_icon": "fa-snowflake",
        "decos": [
            _deco("fa-snowflake", "pd-meteo-deco pd-meteo-deco--snow-1"),
            _deco("fa-moon", "pd-meteo-deco pd-meteo-deco--moon-subtle"),
        ],
    },
    "50d": {
        "panel_class": "pd-meteo--fog-day",
        "cockpit_skin": "cw-skin-fog",
        "cockpit_icon": "fa-smog",
        "decos": [
            _deco("fa-smog", "pd-meteo-deco pd-meteo-deco--fog"),
            _deco("fa-wind", "pd-meteo-deco pd-meteo-deco--wind"),
        ],
    },
    "50n": {
        "panel_class": "pd-meteo--fog-night",
        "cockpit_skin": "cw-skin-fog-night",
        "cockpit_icon": "fa-smog",
        "decos": [_deco("fa-smog", "pd-meteo-deco pd-meteo-deco--fog")],
    },
}

PANEL_THEME_CLASSES = frozenset(t["panel_class"] for t in THEMES.values())
COCKPIT_SKIN_CLASSES = frozenset(t["cockpit_skin"] for t in THEMES.values())


def resolve_weather_theme(icone: str | None = None) -> WeatherTheme:
    key = DEFAULT_KEY
    if icone and len(str(icone)) >= 3:
        key = str(icone).lower()[:3]
    return THEMES.get(key, THEMES[DEFAULT_KEY])


def weather_theme_as_context(icone: str | None = None) -> dict[str, Any]:
    """Dict utilisable dans les templates / vues."""
    theme = resolve_weather_theme(icone)
    return {
        "panel_class": theme["panel_class"],
        "cockpit_skin": theme["cockpit_skin"],
        "cockpit_icon": theme["cockpit_icon"],
        "decos": theme["decos"],
    }
