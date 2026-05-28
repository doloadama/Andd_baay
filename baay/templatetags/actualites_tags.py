"""
Template tags pour les actualités agro-météo.
"""
from django import template

register = template.Library()


@register.filter
def emoji_source(source):
    """
    Retourne un emoji correspondant à la source d'actualité.
    
    Args:
        source: str - Le nom de la source (anacim, ministere, etc.)
    
    Returns:
        str: Un emoji représentatif de la source
    """
    if not source:
        return "🌿"
    
    source_lower = str(source).lower()
    
    # Correspondance exacte avec ArticleActualite.SOURCE_* constants
    emoji_map = {
        "anacim":    "☁️",   # météo
        "mae":       "🌾",   # Ministère Agriculture
        "fao":       "🌍",   # FAO
        "ansd":      "📊",   # statistiques
        "autre":     "📰",   # autre source
        # Alias larges pour rétro-compatibilité
        "ministere": "🏛️",
        "ministère": "🏛️",
        "agriculture": "🌾",
        "senegal":   "🇸🇳",
        "sénégal":   "🇸🇳",
        "cnra":      "🔬",
        "isra":      "🔬",
        "cse":       "🌡️",
        "default":   "📰",
    }
    
    for key, emoji in emoji_map.items():
        if key in source_lower:
            return emoji
    
    return emoji_map["default"]


@register.filter
def source_label(source):
    """
    Retourne un libellé lisible pour la source.
    
    Args:
        source: str - Le nom de la source
    
    Returns:
        str: Un libellé formaté
    """
    if not source:
        return "Source inconnue"
    
    source_lower = str(source).lower()
    
    labels = {
        "anacim": "ANACIM",
        "ministere": "Ministère de l'Agriculture",
        "ministère": "Ministère de l'Agriculture",
        "aibd": "AIBD",
        "fasel": "FASEL",
        "cnra": "CNRA",
        "isra": "ISRA",
        "cse": "CSE",
        "cms": "CMS",
    }
    
    for key, label in labels.items():
        if key in source_lower:
            return label
    
    return source.capitalize()
