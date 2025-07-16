"""Module de monitoring et health checks pour TW3"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """États de santé des services"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceHealth:
    """État de santé d'un service"""
    name: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON"""
        result = asdict(self)
        result['status'] = self.status.value
        if self.last_check:
            result['last_check'] = self.last_check.isoformat()
        return result


class SystemMetrics:
    """Collecteur de métriques système"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Retourne l'utilisation mémoire"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percentage': memory.percent
        }
    
    @staticmethod
    def get_cpu_usage() -> Dict[str, float]:
        """Retourne l'utilisation CPU"""
        return {
            'percentage': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        }
    
    @staticmethod
    def get_disk_usage() -> Dict[str, float]:
        """Retourne l'utilisation disque"""
        disk = psutil.disk_usage('/')
        return {
            'total_gb': disk.total / (1024**3),
            'used_gb': disk.used / (1024**3),
            'free_gb': disk.free / (1024**3),
            'percentage': (disk.used / disk.total) * 100
        }


class NewsAPIHealthChecker:
    """Vérificateur de santé pour NewsAPI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def check_health(self) -> ServiceHealth:
        """Vérifie la santé de NewsAPI"""
        start_time = time.time()
        
        try:
            import aiohttp
            
            # Test simple avec une requête légère
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'country': 'fr',
                'pageSize': 1,
                'apiKey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'ok':
                            return ServiceHealth(
                                name="NewsAPI",
                                status=HealthStatus.HEALTHY,
                                response_time_ms=response_time,
                                last_check=datetime.now(timezone.utc),
                                metadata={'articles_available': len(data.get('articles', []))}
                            )
                        else:
                            return ServiceHealth(
                                name="NewsAPI",
                                status=HealthStatus.DEGRADED,
                                response_time_ms=response_time,
                                error_message=data.get('message', 'Unknown API error'),
                                last_check=datetime.now(timezone.utc)
                            )
                    else:
                        return ServiceHealth(
                            name="NewsAPI",
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=response_time,
                            error_message=f"HTTP {response.status}",
                            last_check=datetime.now(timezone.utc)
                        )
                        
        except asyncio.TimeoutError:
            return ServiceHealth(
                name="NewsAPI",
                status=HealthStatus.UNHEALTHY,
                error_message="Timeout après 5 secondes",
                last_check=datetime.now(timezone.utc)
            )
        except Exception as e:
            return ServiceHealth(
                name="NewsAPI",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                last_check=datetime.now(timezone.utc)
            )


class ModelHealthChecker:
    """Vérificateur de santé pour le modèle Qwen"""
    
    def __init__(self, get_pipe_func):
        self.get_pipe_func = get_pipe_func
    
    async def check_health(self) -> ServiceHealth:
        """Vérifie la santé du modèle"""
        start_time = time.time()
        
        try:
            # Test simple de génération
            pipe = self.get_pipe_func()
            
            # Prompt de test minimal
            test_messages = [{"role": "user", "content": "Test"}]
            
            # Génération avec paramètres minimaux
            result = pipe(
                test_messages,
                max_new_tokens=10,
                do_sample=False,
                temperature=0.1
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result and len(result) > 0:
                return ServiceHealth(
                    name="QwenModel",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    last_check=datetime.now(timezone.utc),
                    metadata={'test_generation': 'success'}
                )
            else:
                return ServiceHealth(
                    name="QwenModel",
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    error_message="Empty model response",
                    last_check=datetime.now(timezone.utc)
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name="QwenModel",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error_message=str(e),
                last_check=datetime.now(timezone.utc)
            )


class HealthCheckManager:
    """Gestionnaire centralisé des health checks"""
    
    def __init__(self, api_key: str, get_pipe_func):
        self.news_checker = NewsAPIHealthChecker(api_key)
        self.model_checker = ModelHealthChecker(get_pipe_func)
        self.system_metrics = SystemMetrics()
        
        # Cache des dernières vérifications
        self._last_checks: Dict[str, ServiceHealth] = {}
        self._check_interval = 60  # 1 minute
        self._background_task: Optional[asyncio.Task] = None
    
    async def get_full_health_report(self) -> Dict[str, Any]:
        """Retourne un rapport de santé complet"""
        
        # Vérifications des services
        news_health = await self.news_checker.check_health()
        model_health = await self.model_checker.check_health()
        
        # Métriques système
        memory = self.system_metrics.get_memory_usage()
        cpu = self.system_metrics.get_cpu_usage()
        disk = self.system_metrics.get_disk_usage()
        
        # État global
        overall_status = self._determine_overall_status([news_health, model_health], memory, cpu)
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '1.0.0',
            'services': {
                'newsapi': news_health.to_dict(),
                'model': model_health.to_dict()
            },
            'system': {
                'memory': memory,
                'cpu': cpu,
                'disk': disk
            },
            'cache_stats': self._get_cache_stats()
        }
    
    def _determine_overall_status(
        self, 
        service_healths: List[ServiceHealth], 
        memory: Dict[str, float], 
        cpu: Dict[str, float]
    ) -> HealthStatus:
        """Détermine l'état global du système"""
        
        # Vérification des services critiques
        unhealthy_services = [s for s in service_healths if s.status == HealthStatus.UNHEALTHY]
        if unhealthy_services:
            return HealthStatus.UNHEALTHY
        
        degraded_services = [s for s in service_healths if s.status == HealthStatus.DEGRADED]
        
        # Vérification des ressources système
        if memory['percentage'] > 95 or cpu['percentage'] > 95:
            return HealthStatus.UNHEALTHY
        elif memory['percentage'] > 85 or cpu['percentage'] > 85 or degraded_services:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques de cache"""
        try:
            from .cache import cache_manager
            return cache_manager.get_global_stats()
        except ImportError:
            return {'error': 'Cache manager not available'}
    
    async def start_background_checks(self):
        """Démarre les vérifications en arrière-plan"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._background_health_checks())
    
    async def stop_background_checks(self):
        """Arrête les vérifications en arrière-plan"""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
    
    async def _background_health_checks(self):
        """Vérifications périodiques en arrière-plan"""
        while True:
            try:
                await asyncio.sleep(self._check_interval)
                
                # Vérifications asynchrones
                news_task = asyncio.create_task(self.news_checker.check_health())
                model_task = asyncio.create_task(self.model_checker.check_health())
                
                news_health, model_health = await asyncio.gather(news_task, model_task)
                
                # Mise à jour du cache
                self._last_checks['newsapi'] = news_health
                self._last_checks['model'] = model_health
                
                # Log des problèmes
                if news_health.status != HealthStatus.HEALTHY:
                    logger.warning(f"NewsAPI health issue: {news_health.error_message}")
                if model_health.status != HealthStatus.HEALTHY:
                    logger.warning(f"Model health issue: {model_health.error_message}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur lors des health checks: {e}")
    
    def get_cached_health(self, service_name: str) -> Optional[ServiceHealth]:
        """Retourne le dernier état de santé en cache"""
        return self._last_checks.get(service_name)


def main():
    """Point d'entrée CLI pour les health checks"""
    import argparse
    import json
    import os
    
    parser = argparse.ArgumentParser(description="TW3 Health Check Tool")
    parser.add_argument("--service", choices=["newsapi", "model", "all"], 
                       default="all", help="Service à vérifier")
    parser.add_argument("--format", choices=["json", "text"], 
                       default="text", help="Format de sortie")
    
    args = parser.parse_args()
    
    # Configuration de base
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        print("❌ NEWSAPI_KEY non configurée")
        return 1
    
    # Création du health manager
    try:
        health_manager = HealthCheckManager(api_key, lambda: None)
        
        if args.service == "all":
            results = {}
            for service in ["newsapi", "model"]:
                try:
                    health = asyncio.run(health_manager.check_service_health(service))
                    results[service] = health.to_dict()
                except Exception as e:
                    results[service] = {"status": "unhealthy", "error": str(e)}
        else:
            health = asyncio.run(health_manager.check_service_health(args.service))
            results = {args.service: health.to_dict()}
        
        # Affichage
        if args.format == "json":
            print(json.dumps(results, indent=2))
        else:
            for service, health in results.items():
                status = health.get("status", "unknown")
                emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
                print(f"{emoji} {service.upper()}: {status}")
                if health.get("response_time_ms"):
                    print(f"   Temps de réponse: {health['response_time_ms']:.1f}ms")
                if health.get("error_message"):
                    print(f"   Erreur: {health['error_message']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erreur lors du health check: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
