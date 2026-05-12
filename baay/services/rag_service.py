"""
Service de Retrieval Augmented Generation (RAG) pour Andd Baay.
Interface abstraite pour requêtage LLM sur base de connaissances agronomiques.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Protocol
from dataclasses import dataclass

from django.db.models import Q

from baay.models import DocumentConnaissance

logger = logging.getLogger(__name__)


@dataclass
class RAGQueryResult:
    """Résultat d'une requête RAG avec contexte et réponse."""
    reponse: str
    sources: list[dict]  # Documents utilisés avec métadonnées
    confidence: float
    query_time_ms: int


@dataclass  
class RetrievedDocument:
    """Document récupéré par le retriever avec score."""
    document: DocumentConnaissance
    score: float
    excerpt: str  # Extrait pertinent


class BaseRAGProvider(ABC):
    """
    Interface abstraite pour les fournisseurs RAG.
    Permet de brancher différentes implémentations (simulé, embeddings, API externe).
    """
    
    @abstractmethod
    def index_documents(self, documents: list[DocumentConnaissance]) -> bool:
        """Indexe les documents pour recherche vectorielle."""
        pass
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedDocument]:
        """Récupère les documents les plus pertinents pour une requête."""
        pass
    
    @abstractmethod
    def query(self, user_question: str, context_documents: Optional[list[RetrievedDocument]] = None) -> RAGQueryResult:
        """Exécute une requête complète: retrieval + génération réponse."""
        pass


class SimulatedRAGProvider(BaseRAGProvider):
    """
    Implémentation simulée du RAG pour développement et tests.
    Utilise recherche par mots-clés simple plutôt qu'embeddings.
    """
    
    # Corpus de connaissances agronomiques pour simulation
    KNOWLEDGE_SNIPPETS = {
        'fertilisation': [
            {
                'titre': 'Fertilisation Azotée - Arachide',
                'contenu': 'L\'arachide nécessite 20-40 ppm d\'azote. Appliquer en 2 fois: 1/3 au semis, 2/3 au stade floraison. Privilégier l\'urée couverte pour limiter volatilisation.',
                'mots_cles': ['arachide', 'azote', 'urée', 'fertilisation', 'floraison'],
            },
            {
                'titre': 'Fertilisation Phosphatée',
                'contenu': 'Le phosphore est essentiel au développement racinaire. Appliquer au moment du semis (localisé), pas en surface. Doser 20-30 ppm selon culture.',
                'mots_cles': ['phosphore', 'racines', 'semis', 'fertilisation'],
            },
            {
                'titre': 'Compost et Matière Organique',
                'contenu': 'Apport de 5-10 tonnes/ha de compost bien décomposé améliore structure sol et biodisponibilité nutriments. À apporter 3-4 semaines avant semis.',
                'mots_cles': ['compost', 'organique', 'matière', 'sol', 'structure'],
            },
        ],
        'irrigation': [
            {
                'titre': 'Irrigation Goutte-à-Goutte',
                'contenu': 'Système efficace pour cultures maraîchères. Débit 2-4L/h, espacement 20-30cm. Fertilisation possible par irrigation (fertigation).',
                'mots_cles': ['goutte', 'irrigation', 'fertigation', 'eau', 'débit'],
            },
            {
                'titre': 'Gestion Stress Hydrique',
                'contenu': 'Périodes critiques: floraison et remplissage grain. Réduire stress hydrique à ces stades peut augmenter rendement de 30%.',
                'mots_cles': ['stress', 'hydrique', 'eau', 'floraison', 'rendement'],
            },
        ],
        'ravageurs': [
            {
                'titre': 'Criquets Pèlerins - Prévention',
                'contenu': 'Surveillance précoce essentielle. Créer couloirs dégagés autour champs. Traitement biologique possible avec Metarhizium.',
                'mots_cles': ['criquet', 'pèlerin', 'ravageur', 'biologique', 'prévention'],
            },
            {
                'titre': 'Chenilles Légionnaires',
                'contenu': 'Maraudage nocturne. Pièges à lumière pour détection. Bacillus thuringiensis efficace si traitement précoce.',
                'mots_cles': ['chenille', 'légionnaire', 'nuit', 'biologique'],
            },
        ],
        'culture': [
            {
                'titre': 'Rotation Céréales-Légumineuses',
                'contenu': 'Alterner mil/sorgho avec niébé/arachide améliore azote du sol et réduit maladies. Cycle recommandé: 2 ans céréale, 1 an légumineuse.',
                'mots_cles': ['rotation', 'céréale', 'légumineuse', 'niébé', 'arachide', 'mil'],
            },
            {
                'titre': 'Densité Semis Mil',
                'contenu': 'Densité optimale: 15000-20000 plants/ha (variétés améliorées) vs 10000-12000 (variétés locales). Espacement 80x40cm ou 100x50cm.',
                'mots_cles': ['mil', 'densité', 'semis', 'plants', 'espacement'],
            },
        ],
    }
    
    def __init__(self):
        self._indexed = False
    
    def index_documents(self, documents: list[DocumentConnaissance]) -> bool:
        """
        Simule l'indexation. En production, créerait les embeddings.
        """
        logger.info("Indexation simulée de %d documents", len(documents))
        
        # Mettre à jour statut
        for doc in documents:
            doc.embedding_status = 'indexed'
            doc.date_indexation = __import__('django.utils.timezone').utils.timezone.now()
            doc.save(update_fields=['embedding_status', 'date_indexation'])
        
        self._indexed = True
        return True
    
    def _score_document(self, query: str, doc: dict) -> float:
        """Score simple basé sur mots-clés communs."""
        query_words = set(query.lower().split())
        doc_words = set(doc.get('mots_cles', []))
        
        # Score basé sur mots-clés
        keyword_matches = len(query_words & doc_words)
        
        # Score titre
        titre_matches = sum(1 for w in query_words if w in doc.get('titre', '').lower())
        
        # Score contenu
        contenu_lower = doc.get('contenu', '').lower()
        contenu_matches = sum(1 for w in query_words if w in contenu_lower)
        
        total_score = keyword_matches * 3 + titre_matches * 2 + contenu_matches * 0.5
        return total_score
    
    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedDocument]:
        """
        Recherche par mots-clés dans le corpus simulé.
        """
        all_docs = []
        for category, docs in self.KNOWLEDGE_SNIPPETS.items():
            for doc_dict in docs:
                score = self._score_document(query, doc_dict)
                if score > 0:
                    # Créer mock DocumentConnaissance
                    mock_doc = DocumentConnaissance(
                        id=f"sim-{category}-{len(all_docs)}",
                        titre=doc_dict['titre'],
                        contenu=doc_dict['contenu'],
                        categorie=category,
                        mots_cles=doc_dict['mots_cles'],
                    )
                    all_docs.append((score, mock_doc, doc_dict['contenu'][:200]))
        
        # Trier par score
        all_docs.sort(key=lambda x: -x[0])
        
        # Convertir en RetrievedDocument
        results = []
        for score, doc, excerpt in all_docs[:top_k]:
            results.append(RetrievedDocument(
                document=doc,
                score=score,
                excerpt=excerpt + "..." if len(doc.contenu) > 200 else excerpt,
            ))
        
        return results
    
    def query(self, user_question: str, context_documents: Optional[list[RetrievedDocument]] = None) -> RAGQueryResult:
        """
        Pipeline complet: retrieve + génération réponse simulée.
        """
        import time
        start_time = __import__('time').time()
        
        # Retrieval si pas de contexte fourni
        if context_documents is None:
            context_documents = self.retrieve(user_question)
        
        # Génération réponse (simulée)
        if not context_documents:
            reponse = (
                "Je n'ai pas trouvé d'informations spécifiques dans ma base de connaissances. "
                "Pour les questions techniques urgentes, je recommande de consulter un agronome "
                "ou les services de vulgarisation agricole de votre région."
            )
            sources = []
            confidence = 0.3
        else:
            # Construire réponse avec contexte
            context_parts = []
            sources = []
            
            for i, retrieved in enumerate(context_documents, 1):
                context_parts.append(f"{i}. {retrieved.excerpt}")
                sources.append({
                    'id': str(retrieved.document.id),
                    'titre': retrieved.document.titre,
                    'categorie': retrieved.document.categorie,
                    'score': round(retrieved.score, 2),
                    'excerpt': retrieved.excerpt,
                })
            
            # Réponse formatée
            reponse = (
                f"Voici les informations disponibles sur votre question:\n\n"
                f"{'\n'.join(context_parts)}\n\n"
                f"Ces données proviennent de notre base de connaissances agronomiques. "
                f"Pour une recommandation personnalisée selon votre contexte spécifique, "
                f"n'hésitez pas à contacter un technicien agricole."
            )
            confidence = min(0.85, 0.5 + len(context_documents) * 0.1)
        
        elapsed_ms = int((__import__('time').time() - start_time) * 1000)
        
        return RAGQueryResult(
            reponse=reponse,
            sources=sources,
            confidence=confidence,
            query_time_ms=elapsed_ms,
        )


class RAGService:
    """
    Service façade pour l'utilisation du RAG dans l'application.
    Gère le provider actif et expose une API simple.
    """
    
    _provider: Optional[BaseRAGProvider] = None
    
    @classmethod
    def get_provider(cls) -> BaseRAGProvider:
        """Retourne le provider RAG actif (lazy init)."""
        if cls._provider is None:
            # Pour l'instant, utiliser le provider simulé
            # En production, injecter via settings ou config
            cls._provider = SimulatedRAGProvider()
            logger.info("RAG Provider initialisé: %s", type(cls._provider).__name__)
        return cls._provider
    
    @classmethod
    def set_provider(cls, provider: BaseRAGProvider):
        """Permet de changer le provider (pour tests ou upgrade)."""
        cls._provider = provider
        logger.info("RAG Provider changé: %s", type(provider).__name__)
    
    @classmethod
    def repondre_question(cls, question: str, locale: str = "fr") -> RAGQueryResult:
        """
        Répond à une question agricole en utilisant le RAG.
        
        Args:
            question: Question de l'utilisateur
            locale: Langue (fr, wo, ff) - pour futur support multilingue
        
        Returns:
            RAGQueryResult avec réponse et sources
        """
        provider = cls.get_provider()
        
        # TODO: Traduction question si locale != fr
        # Pour l'instant, traitement direct
        
        result = provider.query(question)
        
        logger.info(
            "RAG Query: question='%s...', sources=%d, confidence=%.2f, time=%dms",
            question[:50],
            len(result.sources),
            result.confidence,
            result.query_time_ms,
        )
        
        return result
    
    @classmethod
    def indexer_documents_actifs(cls) -> int:
        """
        Indexe tous les documents de connaissance actifs.
        Retourne le nombre de documents indexés.
        """
        provider = cls.get_provider()
        
        docs = DocumentConnaissance.objects.filter(
            is_actif=True,
            embedding_status__in=['pending', 'failed'],
        )
        
        if not docs.exists():
            logger.info("Aucun document à indexer")
            return 0
        
        success = provider.index_documents(list(docs))
        
        if success:
            count = docs.count()
            logger.info("%d documents indexés avec succès", count)
            return count
        else:
            logger.error("Échec de l'indexation")
            return 0
    
    @classmethod
    def rechercher_documents(cls, query: str, categorie: Optional[str] = None) -> list[RetrievedDocument]:
        """
        Recherche simple de documents par mots-clés (fallback sans embeddings).
        """
        qs = DocumentConnaissance.objects.filter(is_actif=True)
        
        if categorie:
            qs = qs.filter(categorie=categorie)
        
        # Recherche simple sur titre et contenu
        qs = qs.filter(
            Q(titre__icontains=query) | Q(contenu__icontains=query) | Q(mots_cles__icontains=query)
        )
        
        results = []
        for doc in qs[:5]:
            results.append(RetrievedDocument(
                document=doc,
                score=1.0,  # Score arbitraire pour compatibilité
                excerpt=doc.contenu[:200] + "..." if len(doc.contenu) > 200 else doc.contenu,
            ))
        
        return results


# Fonction helper pour les vues
def repondre_question_agricole(question: str, user_profile=None) -> dict:
    """
    Helper simple pour les vues Django.
    Retourne un dict JSON-sérialisable.
    """
    result = RAGService.repondre_question(question)
    
    return {
        'question': question,
        'reponse': result.reponse,
        'sources': result.sources,
        'confidence': round(result.confidence, 2),
        'query_time_ms': result.query_time_ms,
        'status': 'success',
    }


def generer_recommandation_expert_agronome(
    contexte,
    sol_data,
    superficie_ha: float = 1.0,
) -> dict:
    """
    Génère une recommandation agronomique personnalisée via RAG.
    
    Args:
        contexte: Instance ContexteExploitation (localite, culture, etc.)
        sol_data: Instance DonneesSol ou dict avec N, P, K, pH
        superficie_ha: Superficie cultivée
        
    Returns:
        Dict avec recommandation formatée et métadonnées
    """
    from .prompts_agronomiques import (
        generer_prompt_expert,
        analyser_carences,
        recommander_solutions_budget,
        ContexteExploitation,
        DonneesSol,
    )
    
    import time
    start_time = time.time()
    
    # Convertir sol_data si nécessaire
    if isinstance(sol_data, dict):
        sol = DonneesSol(
            n_mg_kg=sol_data.get('n', 0),
            p_mg_kg=sol_data.get('p', 0),
            k_mg_kg=sol_data.get('k', 0),
            ph=sol_data.get('ph', 7.0),
            matieres_organiques_pourcent=sol_data.get('mo'),
            texture=sol_data.get('texture'),
            date_analyse=sol_data.get('date_analyse'),
        )
    else:
        sol = sol_data
    
    # Générer le prompt expert
    prompt = generer_prompt_expert(contexte, sol, superficie_ha)
    
    # Analyser les carences localement
    carences = analyser_carences(sol, contexte.produit_nom)
    
    # Recommander solutions selon budget
    solutions = recommander_solutions_budget(
        carences,
        contexte.budget_disponible,
        superficie_ha,
    )
    
    # Appeler le service RAG avec le prompt expert
    result = RAGService.repondre_question(prompt)
    
    query_time = int((time.time() - start_time) * 1000)
    
    return {
        'recommandation': result.reponse,
        'prompt_genere': prompt[:500] + '...',  # Tronqué pour debug
        'analyse_sol': {
            'n_status': carences['N']['statut'],
            'n_message': carences['N']['message'],
            'p_status': carences['P']['statut'],
            'p_message': carences['P']['message'],
            'k_status': carences['K']['statut'],
            'k_message': carences['K']['message'],
            'ph_status': carences['pH']['statut'],
            'ph_message': carences['pH']['message'],
        },
        'solutions_budget': {
            'option_economique': solutions['economique'],
            'option_rapide': solutions['rapide'],
            'cout_estime_economique': solutions['cout_total_estime']['economique'],
            'cout_estime_rapide': solutions['cout_total_estime']['rapide'],
            'budget_suffisant': solutions['cout_total_estime']['budget_suffisant_economique'],
        },
        'sources': result.sources,
        'confidence': round(result.confidence, 2),
        'query_time_ms': query_time,
        'culture': contexte.produit_nom,
        'stade': f"{contexte.age_plant}j / {contexte.cycle_estime}j",
    }
