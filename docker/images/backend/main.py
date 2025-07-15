from __future__ import annotations
"""
TW3 Chat Backend – FastAPI + Qwen 7B avec architecture modulaire

Ce module implémente l'API principale du chatbot TW3 avec :
- Intégration du modèle Qwen 7B pour la génération de réponses
- Connexion à NewsAPI pour les actualités en temps réel
- Cache intelligent multi-niveaux
- Patterns de resilience (circuit breaker, retry)
- Monitoring et health checks avancés
- Configuration centralisée

Architecture:
- FastAPI pour l'API REST
- Transformers pour le modèle Qwen
- Modules src/ pour la logique métier
- Docker pour la containerisation

Author: Équipe TW3
Version: 1.0.0
Date: 16 juillet 2025
"""

import logging
import sys
import os
from typing import Dict, Any
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import pipeline, logging as hf_logging  # type: ignore

from dotenv import load_dotenv
import requests
import asyncio

# ───── Imports des modules locaux ────────────────────────────────────
# Ajout du chemin src pour accéder aux modules de l'architecture
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

# ───── Configuration du logging ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tw3.chat")

try:
    from config import config
    from resilience import news_api_circuit_breaker, retry_with_backoff
    from cache import cache_manager
    from monitoring import HealthCheckManager
    logger.info("Modules d'architecture chargés avec succès")
except ImportError as e:
    logger.warning(f"Modules d'architecture non disponibles: {e}")
    # Fallback gracieux si les modules ne sont pas disponibles
    config = None
    news_api_circuit_breaker = None
    cache_manager = None

# Réduit la verbosité des warnings Transformers pour un log plus propre
hf_logging.set_verbosity_error()

# ───── Modèles Pydantic pour l'API ───────────────────────────────────
class AskIn(BaseModel):
    """
    Modèle d'entrée pour l'endpoint /ask
    
    Attributes:
        question: La question de l'utilisateur (min 3 caractères)
        conv_id: ID de conversation optionnel pour la continuité
    """
    question: str = Field(..., min_length=3, description="Question de l'utilisateur")
    conv_id: str | None = Field(None, description="ID de conversation (auto-généré si absent)")

class AskOut(BaseModel):
    """
    Modèle de sortie pour l'endpoint /ask
    
    Attributes:
        conv_id: ID de conversation (pour la continuité)
        answer: Réponse générée par le système
    """
    conv_id: str = Field(..., description="ID de conversation retourné")
    answer: str = Field(..., description="Réponse générée par le système")

# ───── Configuration et initialisation ───────────────────────────────
# Chargement des variables d'environnement
load_dotenv()
API_KEY = os.getenv("NEWSAPI_KEY")
if not API_KEY:
    raise ValueError("NEWSAPI_KEY environment variable is required")

# Création du dossier de logs de conversation
LOG_DIR = Path("/app/volume/conversations")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Répertoire de logs créé: {LOG_DIR}")

# Initialisation du gestionnaire de health checks
health_manager = None
if config:
    try:
        health_manager = HealthCheckManager(API_KEY, lambda: get_pipe())
        logger.info("Health check manager initialisé")
    except Exception as e:
        logger.warning(f"Impossible d'initialiser le health manager: {e}")

# ───── Fonctions utilitaires ─────────────────────────────────────────

def _append_log(conv_id: str, header_dt: str, role: str, text: str) -> None:
    """
    Ajoute une entrée dans le fichier de log de conversation.
    
    Args:
        conv_id: Identifiant unique de la conversation
        header_dt: Timestamp formaté pour le nom de fichier
        role: Rôle de l'émetteur (user, bot, news, prompt)
        text: Contenu du message à logger
    
    Note:
        Crée automatiquement le fichier avec en-tête si première utilisation
    """
    file = LOG_DIR / f"conv-{conv_id}_{header_dt}.txt"
    is_new = not file.exists()
    now = datetime.now(timezone.utc)
    ts = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    
    with file.open("a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# Conversation {conv_id} – démarrée le {header_dt}\n\n")
        f.write(f"[{ts}] {role.upper()}: {text}\n")

# ───── Intégration NewsAPI avec resilience ──────────────────────────

# Décorateur de retry pour les appels réseaux
if retry_with_backoff:
    @retry_with_backoff(max_attempts=3, exceptions=(requests.exceptions.RequestException,))
    def format_news_context(query="Generative AI", from_date="2025-07-01", sort="relevancy", max_results=5):
        """
        Récupère les actualités avec cache, circuit breaker et retry automatique.
        
        Cette fonction implémente plusieurs patterns de resilience :
        - Cache intelligent pour éviter les appels répétitifs
        - Circuit breaker pour protéger contre les pannes d'API
        - Retry avec backoff exponentiel pour les erreurs temporaires
        
        Args:
            query (str): Terme de recherche pour les actualités
            from_date (str): Date de début au format YYYY-MM-DD
            sort (str): Mode de tri ('relevancy', 'popularity', 'publishedAt')
            max_results (int): Nombre maximum d'articles à récupérer
            
        Returns:
            str: Articles formatés en texte ou message d'erreur
            
        Raises:
            Exception: En cas d'erreur non récupérable après tous les retries
        """
        # Étape 1: Vérification du cache intelligent
        if cache_manager and cache_manager.news_cache:
            cached_result = cache_manager.news_cache.get_news(query, from_date, sort, max_results)
            if cached_result is not None:
                logger.info(f"Cache hit pour la requête NewsAPI: {query[:50]}...")
                return cached_result

        # Étape 2: Application du circuit breaker pour protection
        if news_api_circuit_breaker:
            @news_api_circuit_breaker
            def _fetch_news():
                return _fetch_news_api(query, from_date, sort, max_results)
            
            try:
                result = _fetch_news()
                logger.info(f"NewsAPI appelé avec succès pour: {query[:50]}...")
            except Exception as e:
                logger.error(f"Circuit breaker ouvert ou erreur NewsAPI: {e}")
                return "[ERREUR] Service d'actualités temporairement indisponible. Merci de réessayer plus tard."
        else:
            # Fallback sans circuit breaker
            result = _fetch_news_api(query, from_date, sort, max_results)
        
        # Étape 3: Mise en cache du résultat pour éviter futurs appels
        if cache_manager and cache_manager.news_cache and not result.startswith("["):
            cache_manager.news_cache.set_news(query, from_date, sort, max_results, result)
            logger.debug(f"Résultat mis en cache pour: {query[:50]}...")
        
        return result
else:
    # Version simplifiée sans retry si module non disponible
    def format_news_context(query="Generative AI", from_date="2025-07-01", sort="relevancy", max_results=5):
        """Version simplifiée sans patterns de resilience."""
        if cache_manager and cache_manager.news_cache:
            cached_result = cache_manager.news_cache.get_news(query, from_date, sort, max_results)
            if cached_result is not None:
                return cached_result
        
        result = _fetch_news_api(query, from_date, sort, max_results)
        
        if cache_manager and cache_manager.news_cache and not result.startswith("["):
            cache_manager.news_cache.set_news(query, from_date, sort, max_results, result)
        
        return result

def _fetch_news_api(query: str, from_date: str, sort: str, max_results: int) -> str:
    """
    Fonction interne pour récupérer les actualités depuis NewsAPI.
    
    Cette fonction effectue l'appel HTTP réel vers l'API NewsAPI et traite
    la réponse pour la formater en texte utilisable par le modèle IA.
    
    Args:
        query (str): Terme de recherche pour les actualités
        from_date (str): Date de début au format YYYY-MM-DD
        sort (str): Mode de tri ('relevancy', 'popularity', 'publishedAt')
        max_results (int): Nombre maximum d'articles à récupérer
        
    Returns:
        str: Articles formatés en texte ou message d'erreur
        
    Raises:
        requests.exceptions.RequestException: En cas d'erreur réseau
        ValueError: En cas de réponse malformée
    """
    url = (f'https://newsapi.org/v2/everything?'
           f'q={query}&'
           f'from={from_date}&'
           f'sortBy={sort}&'
           f'pageSize={max_results}&'
           f'language=fr&'
           f'apiKey={API_KEY}')
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"NewsAPI connection error: {e}")
        raise Exception("Impossible de se connecter à NewsAPI. Merci de réessayer plus tard.")
    except Exception as e:
        logging.error(f"NewsAPI unknown error: {e}")
        raise Exception("Erreur lors du traitement de la réponse NewsAPI.")

    if data.get("status") != "ok" or "articles" not in data:
        if data.get("code") == "rateLimited":
            logging.warning("NewsAPI rate limit reached")
            return "[RATE LIMIT] Le nombre maximal de requêtes NewsAPI a été atteint pour cette période. Merci de réessayer plus tard."
        logging.warning(f"NewsAPI error: {data.get('message')}")
        return "[ERREUR] NewsAPI n'a pas pu fournir d'articles pour le moment."

    if not data["articles"]:
        return ""
    
    # On extrait un résumé formaté pour chaque article
    return "\n".join(
        f"- {art['title']} ({art.get('source', {}).get('name','')}, {art['publishedAt'][:10]}) — {art.get('description','')}\n  {art['url']}"
        for art in data["articles"][:max_results]
    )

# dossier où l’on écrit les journaux (créé au boot)
LOG_DIR = Path("/app/volume/conversations")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _append_log(conv_id: str, header_dt: str, role: str, text: str) -> None:
    """
    Ajoute une ligne au fichier de conversation.
    Crée le fichier + un en-tête daté si c’est le premier appel.
    """
    file = LOG_DIR / f"conv-{conv_id}_{header_dt}.txt"
    is_new = not file.exists()
    now = datetime.now(timezone.utc)
    ts = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    with file.open("a", encoding="utf-8") as f:
        if is_new:
            f.write(f"# Conversation {conv_id} – démarrée le {header_dt}\n\n")
        f.write(f"[{ts}] {role.upper()}: {text}\n")


# ───── Hugging Face pipeline (lazy‑load + cache) ─────────────────────
@lru_cache(maxsize=1)
def get_pipe():
    """Charge le modèle Qwen 7B une seule fois (GPU si dispo).
    Utilise un cache LRU pour éviter de recharger le modèle à chaque appel.
    Returns:
        pipeline: Instance de pipeline pour la génération de texte.
    """
    logger.info("Loading Qwen pipeline… (first call only)")
    return pipeline(
        "text-generation",
        model="Qwen/Qwen2.5-Coder-7B-Instruct",
        device_map="auto",       # GPU si présent, sinon CPU
        trust_remote_code=True    # nécessaire pour Qwen
    )

def generate_answer(prompt: str,
                    max_new_tokens: int = 4096,
                    temperature: float = 0.7) -> str:
    """
    Appelle le modèle IA et récupère la réponse texte avec cache intelligent.
    
    Cette fonction gère l'interaction avec le modèle Qwen 2.5-Coder-7B-Instruct,
    en gérant différents formats de réponse et en optimisant les performances
    grâce au système de cache.
    
    Args:
        prompt (str): La question ou le prompt à envoyer au modèle
        max_new_tokens (int): Nombre maximum de tokens à générer (défaut: 4096)
        temperature (float): Contrôle la créativité de la génération (0.1-1.0, défaut: 0.7)
        
    Returns:
        str: La réponse générée par le modèle, nettoyée et formatée
        
    Raises:
        Exception: Si le modèle ne peut pas être appelé ou si la réponse est invalide
        RuntimeError: Si le pipeline n'est pas initialisé correctement
        
    Note:
        Les réponses sont automatiquement mises en cache pour optimiser les performances
        sur des requêtes similaires.
    """
    # Vérification du cache pour les réponses du modèle
    if cache_manager and cache_manager.model_cache:
        cached_response = cache_manager.model_cache.get_response(prompt)
        if cached_response is not None:
            logger.info("Cache hit pour la génération de réponse")
            return cached_response
    
    try:
        pipe = get_pipe()
        messages = [{"role": "user", "content": prompt}]
        out = pipe(
            messages,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
        )
        data = out[0]["generated_text"]

        # Format 1 : Qwen renvoie directement une str
        if isinstance(data, str):
            response = data.strip()
        # Format 2 : liste de messages
        elif isinstance(data, list):
            for msg in reversed(data):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    response = str(msg.get("content", "")).strip()
                    break
            else:
                response = " ".join(
                    str(m.get("content", "")) if isinstance(m, dict) else str(m)
                    for m in data
                ).strip()
        else:
            logger.warning("Unexpected generated_text type: %s", type(data))
            response = str(data).strip()
        
        # Mise en cache de la réponse
        if cache_manager and cache_manager.model_cache and response:
            cache_manager.model_cache.set_response(prompt, response)
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération: {e}")
        raise Exception(f"Erreur lors de la génération de la réponse: {str(e)}")

# ───── Lifespan ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pré‑charge le pipeline au démarrage pour éviter la latence du 1ᵉʳ appel.
    Initialise aussi les services de cache et monitoring.
    Yields:
        None: Le contexte de l'application FastAPI.
    """
    logger.info("Initialisation de l'application TW3...")
    
    # Pré-chargement du modèle
    logger.info("Preloading Qwen pipeline for faster responses…")
    get_pipe()  # déclenche le cache LRU
    
    # Démarrage des services de cache
    if cache_manager:
        await cache_manager.start_cleanup_task()
        logger.info("Cache manager started")
    
    # Démarrage du monitoring
    if health_manager:
        await health_manager.start_background_checks()
        logger.info("Health monitoring started")
    
    logger.info("Application TW3 initialisée avec succès")
    
    yield
    
    # Nettoyage lors de l'arrêt
    logger.info("Arrêt de l'application TW3...")
    
    if cache_manager:
        await cache_manager.stop_cleanup_task()
        logger.info("Cache manager stopped")
    
    if health_manager:
        await health_manager.stop_background_checks()
        logger.info("Health monitoring stopped")

# ───── FastAPI app ────────────────────────────────────────────────────
app = FastAPI(title="TW3 Chat Backend", lifespan=lifespan)

# ───── Middleware ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ───── Endpoints ──────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root() -> Dict[str, str]:
    """Simple endpoint de santé.
    Returns:
        Dict[str, str]: Message de bienvenue.
    """
    logger.info("Health check endpoint called")
    return {"data": "Bienvenue sur l'API TW3 Chat 🎉"}


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check détaillé avec métriques système.
    Returns:
        Dict[str, Any]: État de santé complet du système
    """
    if health_manager:
        return await health_manager.get_full_health_report()
    else:
        # Fallback simple si health_manager n'est pas disponible
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "services": {
                "model": "loaded",
                "basic_check": "ok"
            }
        }


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics() -> Dict[str, Any]:
    """
    Endpoint pour consulter les métriques de performance et de santé du système.
    
    Fournit des informations détaillées sur l'état des caches, la santé des services
    externes (NewsAPI, modèle IA) et les statistiques d'utilisation.
    
    Returns:
        Dict[str, Any]: Métriques complètes incluant :
            - timestamp: Horodatage de la collecte
            - cache_stats: Statistiques des caches (hits, misses, évictions)
            - health_summary: État de santé des services externes
            
    Raises:
        HTTPException: 500 en cas d'erreur lors de la collecte des métriques
        
    Example:
        GET /metrics
        {
            "timestamp": "2024-01-15T10:30:00Z",
            "cache_stats": {"total_hits": 150, "total_misses": 23},
            "health_summary": {"newsapi": {"status": "healthy", "response_time_ms": 245}}
        }
    """
    try:
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cache_stats": cache_manager.get_global_stats() if cache_manager else {},
            "health_summary": {}
        }
        
        if health_manager:
            # Ajout des métriques de santé en cache
            for service in ['newsapi', 'model']:
                cached_health = health_manager.get_cached_health(service)
                if cached_health:
                    metrics["health_summary"][service] = {
                        "status": cached_health.status.value,
                        "response_time_ms": cached_health.response_time_ms,
                        "last_check": cached_health.last_check.isoformat() if cached_health.last_check else None
                    }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des métriques")

@app.post("/ask", response_model=AskOut, tags=["Chat"])
async def ask_handler(payload: AskIn) -> AskOut:
    """
    Endpoint principal pour le chat - traite les questions utilisateur avec contexte d'actualités.
    
    Ce endpoint constitue le cœur de l'application TW3. Il récupère automatiquement
    des actualités pertinentes en fonction de la question posée, puis génère une
    réponse contextualisée en utilisant le modèle Qwen 2.5-Coder-7B-Instruct.
    
    Workflow:
    1. Extraction et validation de la question utilisateur
    2. Recherche d'actualités récentes liées au sujet via NewsAPI
    3. Construction d'un prompt enrichi avec le contexte d'actualités
    4. Génération de la réponse par le modèle IA
    5. Logging de la conversation pour traçabilité
    
    Args:
        payload (AskIn): Données de la requête contenant :
            - question: La question posée par l'utilisateur
            - conv_id: ID de conversation optionnel (généré si absent)
            
    Returns:
        AskOut: Réponse structurée contenant :
            - conv_id: Identifiant unique de la conversation
            - answer: Réponse générée par le système
            
    Raises:
        HTTPException: 422 si la question est vide ou invalide
        HTTPException: 500 en cas d'erreur lors du traitement
        
    Example:
        POST /ask
        {
            "question": "Quelles sont les dernières avancées en IA générative ?",
            "conv_id": "optional-conversation-id"
        }
        
        Response:
        {
            "conv_id": "abc123-def456-789",
            "answer": "D'après les dernières actualités, voici les principales avancées..."
        }
    """
    conv_id = payload.conv_id or str(uuid4())
    now = datetime.now(timezone.utc)
    header_dt = now.strftime("%Y-%m-%dT%H%M%S")
    question = payload.question.strip()
    logger.info("Conv %s – question : %s…", conv_id, question)
    _append_log(conv_id, header_dt, "user", question)

    # Recherche d’actualités
    from_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    sort = "relevancy"
    max_results = 5
    news_ctx = format_news_context(
        query=question,
        from_date=from_date,
        sort=sort,
        max_results=max_results
    )
    logger.info("Conv %s – found %d news articles", conv_id, news_ctx.count("- ") if news_ctx and news_ctx.startswith("-") else 0)
    _append_log(conv_id, header_dt, "news", news_ctx or "Aucune information d’actualité trouvée.")

    # --- GESTION ERREUR NEWSAPI / RATE LIMIT ---
    if news_ctx.startswith("[ERREUR]") or news_ctx.startswith("[RATE LIMIT]"):
        answer = (
            f"Erreur lors de la récupération des actualités :\n{news_ctx}\n\n"
            "Je ne peux donc répondre qu'à partir de mes connaissances internes. "
            "Merci de réessayer dans quelques instants si vous souhaitez une réponse basée sur l’actualité."
        )
        _append_log(conv_id, header_dt, "bot", answer)
        return AskOut(conv_id=conv_id, answer=answer)

    if news_ctx:
        prompt = (
            "Réponds à la question suivante uniquement en faisant un résumé des informations fournies et complètes la réponse avec tes connaissances internes si nécessaire."
            "Précise toujours les sources des informations utilisées. Tu dois restituer la source de chaque information que tu utilises dans ta réponse avec sa date de publication.\n\n"
            "Ne commence jamais par une excuse de type ‘en tant qu’IA, je n’ai pas accès au web’.\n\n"
            f"Question : {question}\n\n"
            "Articles d’actualité à exploiter :\n"
            f"{news_ctx}\n"
            "Réponse :"
        )
    else:
        prompt = (
            "Tu vas répondre à une question en utilisant uniquement tes connaissances internes.\n\n"
            "INSTRUCTIONS :\n"
            "- Réponds de manière factuelle et précise.\n"
            "- N'invente jamais de sources, de liens, de dates ou de citations.\n"
            "- Indique clairement que tu t'appuies sur tes connaissances générales, sans accès à l'actualité.\n"
            "- Si la question porte sur des actualités récentes ou des développements très récents, indique que tu ne peux pas fournir de sources d'actualité ou d'exemples récents précis.\n"
            "- Si la question porte sur des actualités récentes, termine ta réponse comme ceci :\n"
            "'Pour obtenir des informations actualisées, veuillez poser votre question sous forme de mots-clés simples comme \"IA générative\", \"technologie\", \"cinéma\".'\n\n"
            "- **IMPORTANT : Termine toujours ta réponse en conseillant à l'utilisateur de reformuler sa question en français avec des mots-clés simples comme 'IA générative', 'technologie', 'cinéma' pour obtenir des informations d'actualité précises.**\n\n"
            f"Question : {question}\n\n"
            "Réponse :"
        )

    logger.info("Conv %s – prompt : %s", conv_id, prompt)
    _append_log(conv_id, header_dt, "prompt", prompt)

    # Génération Qwen dans un thread séparé (gestion d’erreur)
    try:
        loop = asyncio.get_running_loop()
        answer = await loop.run_in_executor(
            None,
            lambda: generate_answer(prompt)
        )
    except Exception as e:
        logger.error(f"Erreur lors de la génération Qwen : {e}")
        answer = (
            "Désolé, une erreur technique est survenue lors de la génération de la réponse. "
            "Merci de réessayer dans quelques instants."
        )

    _append_log(conv_id, header_dt, "bot", answer)
    return AskOut(conv_id=conv_id, answer=answer)