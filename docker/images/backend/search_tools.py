import os
from dotenv import load_dotenv
import requests
import asyncio

load_dotenv()
API_KEY = os.getenv("NEWSAPI_KEY")
if not API_KEY:
    raise ValueError("NEWSAPI_KEY manquante.")

def format_news_context(query="Generative AI", from_date="2025-07-10", sort="relevancy", max_results=5):
    url = (f'https://newsapi.org/v2/everything?'
           f'q={query}&'
           f'from={from_date}&'
           f'sortBy={sort}&'
           f'pageSize={max_results}&'
           f'language=fr&'
           f'apiKey={API_KEY}')
    resp = requests.get(url)
    data = resp.json()
    if data.get("status") != "ok" or "articles" not in data:
        return ""
    # On extrait un résumé formaté pour chaque article
    return "\n".join(
        f"- {art['title']} ({art.get('source', {}).get('name','')}, {art['publishedAt'][:10]}) — {art.get('description','')}\n  {art['url']}"
        for art in data["articles"][:max_results]
    )

async def search_news_async(query, from_date, sort, max_results=5):
    # Adapter pour être async : run format_news_context dans un thread
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: format_news_context(query, from_date, sort, max_results)
    )

if __name__ == "__main__":
    import argparse
    from datetime import datetime, timedelta

    parser = argparse.ArgumentParser(description="Recherche d'actualités via NewsAPI")
    parser.add_argument("query", nargs="+", help="Texte à chercher (ex: 'générative AI')")
    parser.add_argument("--from-date", default=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                        help="Date de début (YYYY-MM-DD, défaut = il y a 7 jours)")
    parser.add_argument("--sort", default="relevancy", choices=["relevancy", "popularity", "publishedAt"],
                        help="Mode de tri (défaut: relevancy)")
    parser.add_argument("--max-results", type=int, default=5, help="Nombre d'articles (défaut: 5)")

    args = parser.parse_args()
    query_str = " ".join(args.query)

    # Appel synchrone pour la ligne de commande
    print(f"Recherche actualités pour : {query_str}\n")
    context = format_news_context(
        query=query_str,
        from_date=args.from_date,
        sort=args.sort,
        max_results=args.max_results
    )

    if context:
        print(context)
    else:
        print("[Aucun résultat trouvé]")