from django import template

register = template.Library()


@register.simple_tag
def weather_theme(icone=None):
    """{% weather_theme weather.icone as wx %} → panel_class, cockpit_skin, decos…"""
    from baay.weather_theme import resolve_weather_theme
    return resolve_weather_theme(icone)
