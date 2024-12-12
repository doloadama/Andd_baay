import datetime
import jwt
from django.contrib.auth.hashers import make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from Andd_Baayi import settings
from .models import Utilisateur
from .serializers import UtilisateurSerializer
from utils import authenticate_user

class UtilisateurListCreateAPIView(APIView):
    def get(self, request):
        utilisateurs = Utilisateur.objects.all()
        serializer = UtilisateurSerializer(utilisateurs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UtilisateurSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            if 'mot_de_passe' in request.data:
                serializer.instance.set_password(request.data['mot_de_passe'])
                serializer.instance.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UtilisateurDetailAPIView(APIView):
    def put(self, request, pk):
        try:
            utilisateur = Utilisateur.objects.get(pk=pk)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur introuvable"}, status=status.HTTP_404_NOT_FOUND)

        new_password = request.data.get('new_password')
        if new_password:
            utilisateur.set_password(new_password)
            utilisateur.save()

        serializer = UtilisateurSerializer(utilisateur, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            utilisateur = Utilisateur.objects.get(pk=pk)
            utilisateur.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Utilisateur.DoesNotExist:
            return Response({"error": "Utilisateur introuvable"}, status=status.HTTP_404_NOT_FOUND)



@csrf_exempt
def reset_password_view(request):
    if request.method == 'POST':
        # Extraire les données du corps de la requête
        email = request.POST.get('email')
        new_password = request.POST.get('mot_de_passe')

        if not email or not new_password:
            return JsonResponse({'error': 'Email and new password are both required.'}, status=400)

        try:
            # Chercher l'utilisateur par email
            user = Utilisateur.objects.get(email=email)
            # Mettre à jour le mot de passe
            user.mot_de_passe = make_password(new_password)
            user.save()
            return JsonResponse({'message': 'Mot de passe réinitialisé avec succès'}, status=200)
        except Utilisateur.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur introuvable.'}, status=404)
    else:
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@csrf_exempt
@require_POST
def login_view(request):
    if request.method == 'POST':
        # Récupération des données envoyées
        nom = request.POST.get('nom')
        mot_de_passe = request.POST.get('mot_de_passe')

        # Validation des champs
        if not nom or not mot_de_passe:
            return JsonResponse({"status": "error", "message": "Nom et mot de passe requis"}, status=400)

        # Authentification utilisateur
        user = authenticate_user(nom, mot_de_passe)  # Remplacez par votre fonction d'authentification
        if user:
            # Création du JWT
            payload = {
                "nom": user.nom,
                "exp": datetime.datetime.now() + datetime.timedelta(hours=1)  # Expire dans 1 heure
            }
            try:
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Erreur lors de la création du toke: {str(e)}"},
                                    status=500)

            return JsonResponse({
                "status": "success",
                "user": {"id": user.id, "nom": user.nom},
                "token": token
            })
        else:
            return JsonResponse({"status": "error", "message": "Identifiants invalides"}, status=401)

    return JsonResponse({"status": "error", "message": "Méthode non autorisée"}, status=405)

























"""
# Create your views here.
import streamlit as st
#from baay.models import FruitLegume
# Importer le modèle Django

# Liste statique des fruits et légumes cultivés au Sénégal
fruits_et_legumes_senegal = [
    "Manguier (Mangue)", "Papaye", "Banane", "Orange", "Citrons et Agrumes", "Goyave", 
    "Pomme de terre douce (patate douce)", "Oignon", "Tomate", "Carotte", "Chou", "Aubergine", 
    "Poivron", "Concombre", "Haricot", "Piment", "Moringa", "Baobab", "Citrouille", "Gombo", "Tamarin"
]

# Fonction pour afficher les fruits et légumes avec suggestions dynamiques
def afficher_fruits_et_legumes():
    st.title("Liste des fruits et légumes cultivés au Sénégal")
    
    # Champ de texte pour rechercher par lettre
    st.write(f"Si ce que vous cherchez n'est pas dans la liste veuillez l'écrire")
    search_term = st.text_input("Rechercher un fruit ou légume (ex : carotte, tomate)")

    # Filtrer les fruits et légumes qui contiennent le terme de recherche
    if search_term:
        filtered_items = [item for item in fruits_et_legumes_senegal if search_term.lower() in item.lower()]
    else:
        filtered_items = fruits_et_legumes_senegal  # Récupérer toutes les suggestions si aucune recherche n'est effectuée

    # Afficher les suggestions sous forme de selectbox
    if filtered_items:
        selected_item = st.selectbox("Choisir un fruit ou légume", filtered_items)
        
        # Afficher un message avec l'élément sélectionné
        st.write(f"Vous avez sélectionné : {selected_item}")
    else:
        st.write("Aucun fruit ou légume trouvé.")

# Fonction principale pour choisir l'option
def main():
    menu = ["Ajouter un fruit ou légume", "Voir les fruits et légumes"]
    choix = st.sidebar.selectbox("Choisir une option", menu)

    if choix == "Ajouter un fruit ou légume":
        # Vous pouvez ajouter une fonction pour ajouter un fruit ou légume ici
        st.write("Fonction pour ajouter un fruit ou légume.")
    elif choix == "Voir les fruits et légumes":
        afficher_fruits_et_legumes()

if __name__ == "__main__":
    main()
"""