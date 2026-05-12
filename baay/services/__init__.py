"""
Package services : sous-modules (carte, ROI, RAG, …) + API historique
réexportée depuis ``core_services`` (anciennement ``baay.services`` en module).
"""

from baay.core_services import *  # noqa: F401,F403
from baay.core_services import _format_fcfa_montant  # noqa: F401 — hors import *
