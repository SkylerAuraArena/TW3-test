#!/bin/bash
set -e

echo "Démarrage de l'application FastAPI backend..."
uvicorn main:app --host 0.0.0.0 --port 8000

echo "Toutes les applications ont été démarrées avec succès."