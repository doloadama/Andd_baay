from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from baay.models import Commentaire, Ferme, Profile, Tache
from baay.permissions import peut_voir_ferme, peut_voir_tache


def _get_profile(user):
    return get_object_or_404(Profile, user=user)


def _commentaires_ctx(obj):
    ct = ContentType.objects.get_for_model(obj)
    qs = Commentaire.objects.filter(content_type=ct, object_id=obj.pk).select_related("auteur__user")
    return {"commentaires": qs, "ct_id": ct.pk, "object_id": obj.pk}


@login_required
@require_POST
def ajouter_commentaire(request, ct_id, object_id):
    ct = get_object_or_404(ContentType, pk=ct_id)
    model_class = ct.model_class()

    if model_class == Ferme:
        obj = get_object_or_404(Ferme, pk=object_id)
        profile = _get_profile(request.user)
        if not peut_voir_ferme(profile, obj):
            return HttpResponse("Accès refusé", status=403)
    elif model_class == Tache:
        obj = get_object_or_404(Tache.objects.select_related("ferme"), pk=object_id)
        profile = _get_profile(request.user)
        if not peut_voir_tache(profile, obj):
            return HttpResponse("Accès refusé", status=403)
    else:
        return HttpResponse("Type non supporté", status=400)

    texte = request.POST.get("texte", "").strip()
    if not texte:
        return HttpResponse("Commentaire vide", status=400)
    if len(texte) > 2000:
        return HttpResponse("Commentaire trop long (max 2000 caractères)", status=400)

    c = Commentaire.objects.create(
        content_type=ct,
        object_id=object_id,
        auteur=_get_profile(request.user),
        texte=texte,
    )
    return render(request, "commentaires/_commentaire.html", {"c": c})
