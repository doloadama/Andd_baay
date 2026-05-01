"""Petites CBV génériques (hors urls dédiées métier).

La page hors-ligne n’envoie pas de messages contrib : évite une dépendance
inutile au framework messages lorsque le navigateur est déjà offline.
"""

from django.views.generic import TemplateView


class OfflineView(TemplateView):
    template_name = "offline.html"
