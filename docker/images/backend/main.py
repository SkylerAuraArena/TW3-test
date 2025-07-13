from __future__ import annotations
"""TW3 Chat Backend – FastAPI + Qwen 7B"""

import logging
import asyncio
from typing import Dict
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel, Field
from transformers import pipeline, logging as hf_logging # type: ignore

# ───── Logger ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tw3.chat")

# Réduit la verbosité des warnings Transformers
hf_logging.set_verbosity_error()

# ───── Pydantic DTO ───────────────────────────────────────────────────
class AskIn(BaseModel):
    question: str = Field(..., min_length=3)

class AskOut(BaseModel):
    answer: str

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

def generate_answer(question: str,
                    max_new_tokens: int = 128,
                    temperature: float = 0.2) -> str:
    """Génère une réponse à *question* via le modèle Qwen.
    Gère les deux formats de sortie possibles :
    1. `generated_text` est une **str**  – cas habituel.
    2. `generated_text` est une **liste de messages** (dict) – certains templates récents renvoient toute la conversation.
    Args:
        question (str): La question à laquelle répondre.
        max_new_tokens (int): Nombre maximum de tokens à générer.
        temperature (float): Contrôle la créativité de la réponse.
    Returns:
        str: La réponse générée par le modèle.
    """
    logger.info(f"Generating answer for question: {question}")
    pipe = get_pipe()
    messages = [{"role": "user", "content": question}]
    out = pipe(
        messages,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
    )
    data = out[0]["generated_text"]

    # Format 1 : chaîne de caractères directe
    if isinstance(data, str):
        return data.strip()

    # Format 2 : liste de messages (dict)
    if isinstance(data, list):
        # On cherche le dernier message de rôle 'assistant'
        for msg in reversed(data):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return str(msg.get("content", "")).strip()
        # Fallback : tout convertir en texte
        return " ".join(str(m.get("content", "")) if isinstance(m, dict) else str(m) for m in data).strip()

    # Inattendu : on cast en str
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
    """Retourne la réponse générée localement par Qwen.
    Args:
        payload (AskIn): Contient la question à poser.
    Returns:
        AskOut: Contient la réponse générée par le modèle.
    """
    logger.info(f"Received question: {payload.question}")
    question = payload.question.strip()

    # Exécution bloquante déportée dans un thread pour ne pas bloquer l'event‑loop
    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(
        None,
        lambda: generate_answer(question, max_new_tokens=256, temperature=0.7)
    )

    return AskOut(answer=answer)