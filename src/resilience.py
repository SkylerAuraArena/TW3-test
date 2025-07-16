"""Module de gestion des erreurs et resilience pour TW3"""

import functools
import time
import logging
from typing import Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """États du circuit breaker"""
    CLOSED = "closed"      # Circuit fermé, tout passe
    OPEN = "open"          # Circuit ouvert, tout échoue
    HALF_OPEN = "half_open"  # Test si le service est revenu


class CircuitBreaker:
    """Implémentation d'un circuit breaker pour protéger les appels externes"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED
    
    def __call__(self, func: Callable) -> Callable:
        """Décorateur pour appliquer le circuit breaker"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self._call(func, *args, **kwargs)
        return wrapper
    
    def _call(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute la fonction avec protection circuit breaker"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker: tentative de reset (HALF_OPEN)")
            else:
                raise Exception("Circuit breaker OPEN - service indisponible")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Vérifie si on doit tenter de remettre le circuit en service"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Réinitialise le circuit breaker en cas de succès"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit breaker: reset réussi (CLOSED)")
    
    def _on_failure(self):
        """Gère les échecs et ouvre le circuit si nécessaire"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker: OUVERT après {self.failure_count} échecs"
            )


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Décorateur pour retry avec backoff exponentiel
    
    Args:
        max_attempts: Nombre maximum de tentatives
        base_delay: Délai de base en secondes
        max_delay: Délai maximum en secondes
        exponential_base: Base pour le calcul exponentiel
        exceptions: Types d'exceptions à retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Dernière tentative, on lève l'exception
                        logger.error(
                            f"Échec définitif après {max_attempts} tentatives: {e}"
                        )
                        raise e
                    
                    # Calcul du délai avec backoff exponentiel
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Tentative {attempt + 1}/{max_attempts} échouée: {e}. "
                        f"Retry dans {delay:.1f}s"
                    )
                    
                    time.sleep(delay)
            
            # Ne devrait jamais arriver, mais au cas où
            raise last_exception
            
        return wrapper
    return decorator


class RateLimiter:
    """Limiteur de débit pour protéger les APIs externes"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Nombre maximum d'appels
            time_window: Fenêtre de temps en secondes
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self._can_make_call():
                raise Exception(
                    f"Rate limit atteint: {self.max_calls} appels par {self.time_window}s"
                )
            
            self._register_call()
            return func(*args, **kwargs)
        return wrapper
    
    def _can_make_call(self) -> bool:
        """Vérifie si on peut faire un appel"""
        now = time.time()
        # Nettoie les anciens appels
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < self.time_window]
        
        return len(self.calls) < self.max_calls
    
    def _register_call(self):
        """Enregistre un nouvel appel"""
        self.calls.append(time.time())


# Instances globales configurées pour TW3
news_api_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

news_api_rate_limiter = RateLimiter(
    max_calls=100,  # 100 appels max par heure (NewsAPI gratuit)
    time_window=3600  # 1 heure
)
