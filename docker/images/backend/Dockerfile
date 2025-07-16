# Utiliser une image Python de base légère
FROM python:3.13-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier de dépendances (requirements.txt) dans le conteneur
COPY docker/images/backend/requirements.txt .

# Installer les dépendances Python listées dans requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste de l'application depuis le dossier local vers le répertoire de travail dans le conteneur
COPY docker/images/backend /app/

# Copier les modules d'architecture depuis le dossier src/
COPY src/ /app/

# Rendre le script d'entrée 'start.sh' exécutable
RUN chmod +x start.sh

# Exposer le port 8000 pour permettre l'accès à l'application FastAPI depuis l'extérieur du conteneur
EXPOSE 8000

# Définir la commande par défaut à exécuter lorsque le conteneur démarre
# Cette commande exécute le script 'start.sh' après un délai de 2 secondes
CMD ["sh", "-c", "sleep 2 && ./start.sh"]