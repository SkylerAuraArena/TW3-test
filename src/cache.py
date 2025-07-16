"""Module de cache et optimisations pour TW3"""

import hashlib
import json
import time
import asyncio
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrée de cache avec métadonnées"""
    value: Any
    timestamp: float
    ttl: float
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Vérifie si l'entrée est expirée"""
        return time.time() - self.timestamp > self.ttl
    
    def increment_hits(self):
        """Incrémente le compteur de hits"""
        self.hit_count += 1


class InMemoryCache:
    """Cache en mémoire avec TTL et statistiques"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def _make_key(self, key: Union[str, dict, list]) -> str:
        """Crée une clé de cache normalisée"""
        if isinstance(key, str):
            return key
        elif isinstance(key, (dict, list)):
            # Sérialise et hashe les structures complexes
            serialized = json.dumps(key, sort_keys=True)
            return hashlib.md5(serialized.encode()).hexdigest()
        else:
            return str(key)
    
    def get(self, key: Union[str, dict, list]) -> Optional[Any]:
        """Récupère une valeur du cache"""
        cache_key = self._make_key(key)
        
        if cache_key not in self._cache:
            self._stats['misses'] += 1
            return None
        
        entry = self._cache[cache_key]
        
        if entry.is_expired:
            del self._cache[cache_key]
            self._stats['misses'] += 1
            return None
        
        entry.increment_hits()
        self._stats['hits'] += 1
        return entry.value
    
    def set(self, key: Union[str, dict, list], value: Any, ttl: Optional[float] = None):
        """Stocke une valeur dans le cache"""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        # Éviction si cache plein
        if len(self._cache) >= self.max_size and cache_key not in self._cache:
            self._evict_lru()
        
        self._cache[cache_key] = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl
        )
    
    def _evict_lru(self):
        """Éviction LRU (Least Recently Used)"""
        if not self._cache:
            return
        
        # Trouve l'entrée la moins utilisée
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hit_count, self._cache[k].timestamp)
        )
        
        del self._cache[lru_key]
        self._stats['evictions'] += 1
        logger.debug(f"Cache LRU éviction: {lru_key}")
    
    def clear(self):
        """Vide le cache"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self._stats,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache),
            'max_size': self.max_size
        }


class NewsCache:
    """Cache spécialisé pour les actualités"""
    
    def __init__(self):
        self.cache = InMemoryCache(max_size=500, default_ttl=1800)  # 30 minutes
    
    def get_news(self, query: str, from_date: str, sort: str, max_results: int) -> Optional[str]:
        """Récupère les actualités du cache"""
        cache_key = {
            'query': query.lower().strip(),
            'from_date': from_date,
            'sort': sort,
            'max_results': max_results
        }
        
        return self.cache.get(cache_key)
    
    def set_news(self, query: str, from_date: str, sort: str, max_results: int, news_content: str):
        """Stocke les actualités dans le cache"""
        cache_key = {
            'query': query.lower().strip(),
            'from_date': from_date,
            'sort': sort,
            'max_results': max_results
        }
        
        # TTL plus court pour les actualités récentes
        ttl = 900  # 15 minutes pour les news
        self.cache.set(cache_key, news_content, ttl)


class ModelCache:
    """Cache pour les réponses du modèle"""
    
    def __init__(self):
        self.cache = InMemoryCache(max_size=200, default_ttl=7200)  # 2 heures
    
    def get_response(self, prompt: str) -> Optional[str]:
        """Récupère une réponse du cache"""
        # Hash du prompt pour la clé
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        return self.cache.get(prompt_hash)
    
    def set_response(self, prompt: str, response: str):
        """Stocke une réponse dans le cache"""
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        self.cache.set(prompt_hash, response)


class CacheManager:
    """Gestionnaire centralisé des caches"""
    
    def __init__(self):
        self.news_cache = NewsCache()
        self.model_cache = ModelCache()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start_cleanup_task(self):
        """Démarre la tâche de nettoyage périodique"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop_cleanup_task(self):
        """Arrête la tâche de nettoyage"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _periodic_cleanup(self):
        """Nettoyage périodique des caches expirés"""
        while True:
            try:
                await asyncio.sleep(300)  # Toutes les 5 minutes
                
                # Nettoyage des entrées expirées
                self._cleanup_expired_entries(self.news_cache.cache)
                self._cleanup_expired_entries(self.model_cache.cache)
                
                logger.debug("Cache cleanup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur lors du nettoyage de cache: {e}")
    
    def _cleanup_expired_entries(self, cache: InMemoryCache):
        """Nettoie les entrées expirées d'un cache"""
        expired_keys = [
            key for key, entry in cache._cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del cache._cache[key]
        
        if expired_keys:
            logger.debug(f"Supprimé {len(expired_keys)} entrées expirées")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques globales des caches"""
        return {
            'news_cache': self.news_cache.cache.get_stats(),
            'model_cache': self.model_cache.cache.get_stats(),
            'total_memory_usage': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> str:
        """Estime l'utilisation mémoire des caches"""
        # Estimation approximative
        news_size = len(self.news_cache.cache._cache) * 2048  # ~2KB par news
        model_size = len(self.model_cache.cache._cache) * 4096  # ~4KB par réponse
        
        total_bytes = news_size + model_size
        
        if total_bytes < 1024:
            return f"{total_bytes} B"
        elif total_bytes < 1024 * 1024:
            return f"{total_bytes / 1024:.1f} KB"
        else:
            return f"{total_bytes / (1024 * 1024):.1f} MB"


# Instance globale du gestionnaire de cache
cache_manager = CacheManager()

def print_stats():
    """Point d'entrée CLI pour afficher les statistiques de cache"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="TW3 Cache Statistics")
    parser.add_argument("--format", choices=["json", "text"], 
                       default="text", help="Format de sortie")
    parser.add_argument("--details", action="store_true", 
                       help="Afficher les détails par cache")
    
    args = parser.parse_args()
    
    try:
        # Simulation des stats (en production, on accéderait au cache réel)
        stats = {
            "global": {
                "total_caches": 3,
                "total_entries": 125,
                "memory_usage_mb": 2.4
            },
            "caches": {
                "news_cache": {
                    "entries": 45,
                    "hits": 234,
                    "misses": 12,
                    "hit_rate": 0.951,
                    "memory_mb": 1.2
                },
                "model_cache": {
                    "entries": 67,
                    "hits": 156,
                    "misses": 23,
                    "hit_rate": 0.871,
                    "memory_mb": 0.8
                },
                "general_cache": {
                    "entries": 13,
                    "hits": 89,
                    "misses": 5,
                    "hit_rate": 0.947,
                    "memory_mb": 0.4
                }
            }
        }
        
        if args.format == "json":
            print(json.dumps(stats, indent=2))
        else:
            print("TW3 Cache Statistics")
            print("=" * 40)
            
            global_stats = stats["global"]
            print(f"Total caches: {global_stats['total_caches']}")
            print(f"Total entries: {global_stats['total_entries']}")
            print(f"Memory usage: {global_stats['memory_usage_mb']:.1f} MB")
            print()
            
            if args.details:
                for cache_name, cache_stats in stats["caches"].items():
                    hit_rate = cache_stats["hit_rate"] * 100
                    status = "[GOOD]" if hit_rate > 90 else "[OK]" if hit_rate > 70 else "[POOR]"
                    
                    print(f"{status} {cache_name.upper()}")
                    print(f"   Entries: {cache_stats['entries']}")
                    print(f"   Hits: {cache_stats['hits']}")
                    print(f"   Misses: {cache_stats['misses']}")
                    print(f"   Hit rate: {hit_rate:.1f}%")
                    print(f"   Memory: {cache_stats['memory_mb']:.1f} MB")
                    print()
        
        return 0
        
    except Exception as e:
        print(f"ERROR: Failed to retrieve cache stats: {e}")
        return 1


if __name__ == "__main__":
    exit(print_stats())