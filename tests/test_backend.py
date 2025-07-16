"""Tests unitaires pour le backend TW3"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

# Import de l'application
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../docker/images/backend'))

from main import app, format_news_context, generate_answer


@pytest.fixture
def client():
    """Client de test FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_news_response():
    """Mock de réponse NewsAPI"""
    return {
        "status": "ok",
        "articles": [
            {
                "title": "Test Article 1",
                "description": "Description test 1",
                "url": "https://test1.com",
                "publishedAt": "2025-07-15T10:00:00Z",
                "source": {"name": "Test Source 1"}
            },
            {
                "title": "Test Article 2", 
                "description": "Description test 2",
                "url": "https://test2.com",
                "publishedAt": "2025-07-14T15:30:00Z",
                "source": {"name": "Test Source 2"}
            }
        ]
    }


class TestHealthEndpoint:
    """Tests pour l'endpoint de santé"""
    
    def test_root_endpoint(self, client):
        """Test de l'endpoint racine"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Bienvenue" in response.json()["data"]


class TestNewsAPIIntegration:
    """Tests pour l'intégration NewsAPI"""
    
    @patch('main.requests.get')
    def test_format_news_context_success(self, mock_get, mock_news_response):
        """Test de récupération d'actualités réussie"""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_news_response
        mock_get.return_value.raise_for_status = Mock()
        
        result = format_news_context("test query")
        
        assert "Test Article 1" in result
        assert "Test Article 2" in result
        assert "Test Source 1" in result
        assert "https://test1.com" in result
    
    @patch('main.requests.get')
    def test_format_news_context_rate_limit(self, mock_get):
        """Test de gestion du rate limit NewsAPI"""
        mock_response = {
            "status": "error",
            "code": "rateLimited",
            "message": "Rate limit exceeded"
        }
        mock_get.return_value.status_code = 429
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.raise_for_status = Mock()
        
        result = format_news_context("test query")
        
        assert "[RATE LIMIT]" in result
    
    @patch('main.requests.get')
    def test_format_news_context_connection_error(self, mock_get):
        """Test de gestion d'erreur de connexion"""
        mock_get.side_effect = ConnectionError("Connection failed")
        
        result = format_news_context("test query")
        
        assert "[ERREUR]" in result
        assert "Impossible de se connecter" in result


class TestAskEndpoint:
    """Tests pour l'endpoint /ask"""
    
    @patch('main.format_news_context')
    @patch('main.generate_answer')
    def test_ask_with_news_context(self, mock_generate, mock_news, client):
        """Test de question avec contexte d'actualités"""
        mock_news.return_value = "- Article test (Source, 2025-07-15) — Description\n  https://test.com"
        mock_generate.return_value = "Réponse générée par le modèle"
        
        payload = {"question": "Que se passe-t-il en IA ?"}
        response = client.post("/ask", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "conv_id" in data
        assert "answer" in data
        assert data["answer"] == "Réponse générée par le modèle"
    
    @patch('main.format_news_context')
    @patch('main.generate_answer')
    def test_ask_without_news_context(self, mock_generate, mock_news, client):
        """Test de question sans contexte d'actualités"""
        mock_news.return_value = ""
        mock_generate.return_value = "Réponse basée sur connaissances internes"
        
        payload = {"question": "Question générale"}
        response = client.post("/ask", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "conv_id" in data
        assert "answer" in data
    
    def test_ask_invalid_question(self, client):
        """Test avec question trop courte"""
        payload = {"question": "Hi"}  # Moins de 3 caractères
        response = client.post("/ask", json=payload)
        
        assert response.status_code == 422  # Validation error
    
    @patch('main.format_news_context')
    def test_ask_news_api_error_handling(self, mock_news, client):
        """Test de gestion d'erreur NewsAPI"""
        mock_news.return_value = "[ERREUR] Impossible de se connecter à NewsAPI"
        
        payload = {"question": "Question test"}
        response = client.post("/ask", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "Erreur lors de la récupération" in data["answer"]


class TestModelGeneration:
    """Tests pour la génération de réponses"""
    
    @patch('main.get_pipe')
    def test_generate_answer_string_response(self, mock_pipe):
        """Test génération avec réponse string"""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [{"generated_text": "Réponse directe"}]
        mock_pipe.return_value = mock_pipeline
        
        result = generate_answer("Test prompt")
        
        assert result == "Réponse directe"
    
    @patch('main.get_pipe')
    def test_generate_answer_list_response(self, mock_pipe):
        """Test génération avec réponse liste de messages"""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [{
            "generated_text": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Réponse assistant"}
            ]
        }]
        mock_pipe.return_value = mock_pipeline
        
        result = generate_answer("Test prompt")
        
        assert result == "Réponse assistant"


class TestConversationLogging:
    """Tests pour le logging des conversations"""
    
    @patch('main._append_log')
    @patch('main.format_news_context')
    @patch('main.generate_answer')
    def test_conversation_logging(self, mock_generate, mock_news, mock_log, client):
        """Test du logging des conversations"""
        mock_news.return_value = "Contexte news"
        mock_generate.return_value = "Réponse"
        
        payload = {"question": "Test question"}
        response = client.post("/ask", json=payload)
        
        assert response.status_code == 200
        # Vérifier que _append_log a été appelé pour user, news, prompt et bot
        assert mock_log.call_count >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
