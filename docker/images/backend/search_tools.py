# search_tools.py
import os, logging, httpx
from dotenv import load_dotenv
load_dotenv()

SERP_API_KEY = os.getenv("SERPAPI_KEY")
logger = logging.getLogger("tw3.search")

async def search_web(query: str, max_results: int = 5) -> str:
    """
    Interroge SerpAPI et renvoie un petit contexte texte (titres + snippets).
    Retourne une chaîne vide si aucun résultat ou si l'API est KO.
    Args:
        query (str): La requête de recherche.
        max_results (int): Nombre maximum de résultats à renvoyer.
    Returns:
        str: Contexte formaté ou chaîne vide si échec.
    Raises:
        Exception: Si l'API est inaccessible ou si la requête échoue.
    Note:
        - Utilise SerpAPI pour interroger Google Search.
        - Limite les résultats à `max_results` (par défaut 5).
        - Retourne une chaîne formatée avec chaque résultat sur une ligne.
    """
    if not SERP_API_KEY:
        logger.warning("SERPAPI_KEY manquant ; recherche désactivée")
        return ""

    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "hl": "fr",
        "num": max_results,
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return ""

    results = data.get("organic_results", [])[:max_results]
    if not results:
        return ""

    print(f"Web search for '{query}' returned {len(results)} results")
    # On formate chaque résultat sur une ligne : « - Titre — extrait »
    lines = [
        f"- {res.get('title', '⟂ Sans titre')} — "
        f"{res.get('snippet', res.get('snippet_highlighted', ''))}"
        for res in results
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    """
    Point d'entrée pour tester la recherche Web en ligne de commande.
    Usage : python search_tools.py "votre requête"
    Exemple : python search_tools.py "Python async programming"
    Note : Nécessite la variable d'environnement SERPAPI_KEY définie.
    """
    import asyncio
    import sys

    if len(sys.argv) < 2:
        print("Usage : python search_tools.py 'votre requête'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    result = asyncio.run(search_web(query))
    print("\nRésultats Web :\n")
    print(result or "[Aucun résultat]")