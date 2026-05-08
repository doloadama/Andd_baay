from __future__ import annotations

from decimal import Decimal

from django import template

from baay.services import _format_fcfa_montant

register = template.Library()


@register.filter(name="fcfa")
def fcfa(value) -> str:
    """
    Format FCFA integer-like amount with thin-space thousands separator.

    Accepts Decimal/number/None.
    """
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        return _format_fcfa_montant(value)
    try:
        return _format_fcfa_montant(Decimal(str(value)))
    except Exception:
        return "0"

