from __future__ import annotations
"""TW3 Chat Backend – FastAPI + Qwen 7B"""

import logging
from typing import Dict
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import pipeline, logging as hf_logging  # type: ignore

import os
from dotenv import load_dotenv
import requests
import asyncio

# ───── Logger ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tw3.chat")

# Réduit la verbosité des warnings Transformers
hf_logging.set_verbosity_error()

# ───── Pydantic DTO ───────────────────────────────────────────────────
class AskIn(BaseModel):
    question: str = Field(..., min_length=3)
    conv_id: str | None = None  # ID de conversation, None pour le 1er tour

class AskOut(BaseModel):
    conv_id: str                      # renvoyé au front
    answer: str

# --------------------------------------------------------
load_dotenv()
API_KEY = os.getenv("NEWSAPI_KEY")
if not API_KEY:
    raise ValueError("NEWSAPI_KEY manquante.")

def format_news_context(query="Generative AI", from_date="2025-07-01", sort="relevancy", max_results=5):
    url = (f'https://newsapi.org/v2/everything?'
           f'q={query}&'
           f'from={from_date}&'
           f'sortBy={sort}&'
           f'pageSize={max_results}&'
           f'language=fr&'
           f'apiKey={API_KEY}')
    resp = requests.get(url)
    data = resp.json()
    logging.info(f"NewsAPI response: {data}")
    if data.get("status") != "ok" or "articles" not in data:
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
    """Appelle le modèle et récupère la réponse texte.
    Args:
        prompt (str): La question ou le prompt à envoyer au modèle.
        max_new_tokens (int): Nombre maximum de tokens à générer.
        temperature (float): Contrôle la créativité de la génération.
    Returns:
        str: La réponse générée par le modèle.
    Raises:
        Exception: Si le modèle ne peut pas être appelé ou si la réponse est invalide.
    """
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
        return data.strip()

    # Format 2 : liste de messages
    if isinstance(data, list):
        for msg in reversed(data):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return str(msg.get("content", "")).strip()
        return " ".join(
            str(m.get("content", "")) if isinstance(m, dict) else str(m)
            for m in data
        ).strip()

    logger.warning("Unexpected generated_text type: %s", type(data))
    return str(data).strip()

# ───── Lifespan ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pré‑charge le pipeline au démarrage pour éviter la latence du 1ᵉʳ appel.
    Utilise un cache LRU pour garder une seule instance en mémoire.
    Yields:
        None: Le contexte de l'application FastAPI.
    """
    logger.info("Preloading Qwen pipeline for faster responses…")
    get_pipe()  # déclenche le cache LRU
    yield

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

@app.post("/ask", response_model=AskOut, tags=["Chat"])
async def ask_handler(payload: AskIn) -> AskOut:
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
    logger.info("Conv %s – found %d news articles", conv_id, news_ctx.count("- ") if news_ctx else 0)
    _append_log(conv_id, header_dt, "news", news_ctx or "Aucune information d’actualité trouvée.")

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
            "Réponds à la question suivante en t’appuyant sur tes connaissances propres. N’invente jamais de sources, de liens, de dates ou de citations.\n"
            "Commence par identifier le thème principal de la question (par exemple : “les derniers développements en IA générative”) et donne une réponse basée uniquement sur tes connaissances internes.\n"
            "Précise alors que tu t’appuies sur tes connaissances générales, sans inventer ni supposer d’actualité précise ou de sources.\n"
            "Dans ce cas, indique aussi à l’utilisateur que pour obtenir des informations récentes, il est préférable de poser sa question sous la forme de mots-clés simples correspondant à un thème, comme “IA générative”, “cinéma”, “technologie”, etc., plutôt que sous forme de question complexe ou d’exemple.\n\n"
            f"Question : {question}\n\n"
            "Réponse :"
        ).replace("{question}", question)

    logger.info("Conv %s – prompt : %s", conv_id, prompt)
    _append_log(conv_id, header_dt, "prompt", prompt)

    # Génération Qwen dans un thread séparé
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(
        None,
        lambda: generate_answer(prompt)
    )

    _append_log(conv_id, header_dt, "bot", answer)
    return AskOut(conv_id=conv_id, answer=answer)