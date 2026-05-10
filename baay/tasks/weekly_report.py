"""
Agent IA de rapport hebdomadaire pour Andd Baay
Génère des rapports Excel/PDF avec analyses Gemini
"""
import io
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from celery import shared_task
from weasyprint import HTML, CSS
from google import genai

from baay.models import Projet, Ferme, Investissement, Recette, Message, Utilisateur


@shared_task
def generate_weekly_report():
    """
    Tâche Celery hebdomadaire - génère et envoie le rapport
    S'exécute tous les dimanches à 8h00
    """
    # Période du rapport
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Collecte des données
    data = collect_weekly_data(start_date, end_date)
    
    # Analyse IA avec Gemini
    insights = analyze_with_gemini(data)
    
    # Génération des fichiers
    excel_file = generate_excel_report(data, insights)
    pdf_file = generate_pdf_report(data, insights, start_date, end_date)
    
    # Envoi par email aux administrateurs
    send_report_email(excel_file, pdf_file, start_date, end_date)
    
    return f"Rapport hebdomadaire généré: {data['summary']}"


def collect_weekly_data(start_date, end_date) -> Dict:
    """Collecte toutes les données de la semaine"""
    
    # Nouveaux projets
    new_projects = Projet.objects.filter(
        date_creation__range=(start_date, end_date)
    ).select_related('ferme', 'responsable')
    
    # Nouvelles fermes
    new_farms = Ferme.objects.filter(
        date_creation__range=(start_date, end_date)
    )
    
    # Investissements
    investments = Investissement.objects.filter(
        date_investissement__range=(start_date, end_date)
    ).select_related('projet')
    
    # Recettes
    receipts = Recette.objects.filter(
        date_recolte__range=(start_date, end_date)
    ).select_related('projet')
    
    # Messages échangés
    messages = Message.objects.filter(
        date_envoi__range=(start_date, end_date)
    ).select_related('expediteur', 'conversation')
    
    # Nouveaux utilisateurs
    new_users = Utilisateur.objects.filter(
        date_joined__range=(start_date, end_date)
    )
    
    # Calculs financiers
    total_investissements = sum(inv.montant for inv in investments) if investments else 0
    total_recettes = sum(rec.montant_total for rec in receipts) if receipts else 0
    
    return {
        'period': {'start': start_date, 'end': end_date},
        'new_projects': list(new_projects.values('nom', 'type_culture', 'superficie', 'ferme__nom')),
        'new_farms': list(new_farms.values('nom', 'localisation', 'superficie_total')),
        'investissements': {
            'count': investments.count(),
            'total': float(total_investissements),
            'details': list(investments.values('type_investissement', 'montant', 'projet__nom'))
        },
        'recettes': {
            'count': receipts.count(),
            'total': float(total_recettes),
            'details': list(receipts.values('produit', 'quantite', 'montant_total', 'projet__nom'))
        },
        'messages_count': messages.count(),
        'new_users_count': new_users.count(),
        'financial_summary': {
            'investissements': float(total_investissements),
            'recettes': float(total_recettes),
            'balance': float(total_recettes - total_investissements)
        },
        'summary': f"{new_projects.count()} projets, {new_farms.count()} fermes, {investments.count()} investissements"
    }


def analyze_with_gemini(data: Dict) -> Dict:
    """Utilise Gemini pour analyser les données et générer des insights"""
    
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    Tu es un analyste agricole expert. Analyse ces données hebdomadaires de la plateforme Andd Baay:
    
    PÉRIODE: {data['period']['start'].strftime('%d/%m/%Y')} - {data['period']['end'].strftime('%d/%m/%Y')}
    
    ACTIVITÉS:
    - Nouveaux projets: {len(data['new_projects'])}
    - Nouvelles fermes: {len(data['new_farms'])}
    - Investissements: {data['investissements']['count']} (Total: {data['investissements']['total']:,.0f} FCFA)
    - Recettes: {data['recettes']['count']} (Total: {data['recettes']['total']:,.0f} FCFA)
    - Nouveaux utilisateurs: {data['new_users_count']}
    - Messages échangés: {data['messages_count']}
    
    BILAN FINANCIER:
    - Balance: {data['financial_summary']['balance']:,.0f} FCFA
    
    Fournis une analyse concise en français avec:
    1. Tendance générale (positive/négative/neutre)
    2. 3 observations clés
    3. 2 recommandations pour la semaine prochaine
    4. Alertes éventuelles
    
    Format JSON:
    {{
        "tendance": "positive|negative|neutral",
        "score_activite": "1-10",
        "observations": ["...", "...", "..."],
        "recommandations": ["...", "..."],
        "alertes": ["..."] ou [],
        "summary_ia": "Phrase résumé de l'analyse"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        # Parse la réponse JSON
        import json
        text = response.text
        # Extraction du JSON de la réponse
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        insights = json.loads(text.strip())
        return insights
        
    except Exception as e:
        return {
            "tendance": "neutral",
            "score_activite": "5",
            "observations": ["Données collectées avec succès"],
            "recommandations": ["Continuer le suivi régulier"],
            "alertes": [],
            "summary_ia": f"Rapport hebdomadaire - Activité normale ({str(e)})"
        }


def generate_excel_report(data: Dict, insights: Dict) -> io.BytesIO:
    """Génère un fichier Excel avec plusieurs onglets"""
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # Onglet Résumé
    summary_df = pd.DataFrame({
        'Métrique': [
            'Période',
            'Tendance IA',
            'Score Activité',
            'Nouveaux Projets',
            'Nouvelles Fermes',
            'Investissements (FCFA)',
            'Recettes (FCFA)',
            'Balance (FCFA)',
            'Nouveaux Utilisateurs',
            'Messages Échangés'
        ],
        'Valeur': [
            f"{data['period']['start'].strftime('%d/%m/%Y')} - {data['period']['end'].strftime('%d/%m/%Y')}",
            insights['tendance'],
            insights['score_activite'],
            len(data['new_projects']),
            len(data['new_farms']),
            f"{data['investissements']['total']:,.0f}",
            f"{data['recettes']['total']:,.0f}",
            f"{data['financial_summary']['balance']:,.0f}",
            data['new_users_count'],
            data['messages_count']
        ]
    })
    summary_df.to_excel(writer, sheet_name='Résumé', index=False)
    
    # Onglet Observations IA
    observations_df = pd.DataFrame({
        'Type': ['Observation'] * len(insights['observations']) + 
                ['Recommandation'] * len(insights['recommandations']) +
                ['Alerte'] * len(insights['alertes']),
        'Contenu': insights['observations'] + insights['recommandations'] + insights['alertes']
    })
    if not observations_df.empty:
        observations_df.to_excel(writer, sheet_name='Analyse IA', index=False)
    
    # Onglet Projets
    if data['new_projects']:
        projects_df = pd.DataFrame(data['new_projects'])
        projects_df.to_excel(writer, sheet_name='Nouveaux Projets', index=False)
    
    # Onglet Investissements
    if data['investissements']['details']:
        inv_df = pd.DataFrame(data['investissements']['details'])
        inv_df.to_excel(writer, sheet_name='Investissements', index=False)
    
    # Onglet Recettes
    if data['recettes']['details']:
        rec_df = pd.DataFrame(data['recettes']['details'])
        rec_df.to_excel(writer, sheet_name='Recettes', index=False)
    
    writer.close()
    output.seek(0)
    return output


def generate_pdf_report(data: Dict, insights: Dict, start_date, end_date) -> io.BytesIO:
    """Génère un PDF stylisé avec WeasyPrint"""
    
    context = {
        'data': data,
        'insights': insights,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at': datetime.now(),
        'logo_url': settings.LOGIN_BG_CLOUDINARY_URL  # ou autre logo
    }
    
    html_string = render_to_string('reports/weekly_report.html', context)
    
    pdf_file = io.BytesIO()
    HTML(string=html_string).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file


def send_report_email(excel_file: io.BytesIO, pdf_file: io.BytesIO, start_date, end_date):
    """Envoie le rapport par email aux administrateurs"""
    
    subject = f"📊 Rapport Hebdomadaire Andd Baay - {start_date.strftime('%d/%m/%Y')}"
    
    body = f"""
    Bonjour,
    
    Veuillez trouver ci-joint le rapport hebdomadaire de la plateforme Andd Baay.
    
    Période couverte : {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}
    
    Ce rapport a été généré automatiquement par notre agent IA.
    
    Cordialement,
    L'équipe Andd Baay
    """
    
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['adamadolo30@gmail.com'],  # Admin email
    )
    
    # Attacher Excel
    email.attach(
        f'rapport_hebdomadaire_{start_date.strftime("%Y%m%d")}.xlsx',
        excel_file.getvalue(),
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    # Attacher PDF
    email.attach(
        f'rapport_hebdomadaire_{start_date.strftime("%Y%m%d")}.pdf',
        pdf_file.getvalue(),
        'application/pdf'
    )
    
    email.send()
