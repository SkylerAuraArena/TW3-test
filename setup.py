from setuptools import find_packages, setup

# Lecture du README pour la description longue
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Lecture des dépendances depuis requirements.txt
with open("docker/images/backend/requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name='tw3-chat-system',
    packages=find_packages(),
    version='1.0.0',
    description="TW3 Chat System - AI-powered conversational interface with news context integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='SkylerAuraArena',
    license='MIT',
    url="https://github.com/SkylerAuraArena/TW3-test",
    
    # Classification du projet
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    
    # Versions Python supportées
    python_requires=">=3.9",
    
    # Dépendances du projet
    install_requires=requirements,
    
    # Dépendances optionnelles pour le développement
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0", 
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
        ],
        "azure": [
            "azure-identity>=1.12.0",
            "azure-keyvault-secrets>=4.7.0",
            "azure-monitor-opentelemetry-exporter>=1.0.0",
        ]
    },
    
    # Points d'entrée pour scripts CLI
    entry_points={
        "console_scripts": [
            "tw3-health=src.monitoring:main",
            "tw3-cache-stats=src.cache:print_stats",
        ],
    },
    
    # Fichiers de données à inclure
    include_package_data=True,
    
    # Mots-clés pour la recherche
    keywords="ai chatbot news api fastapi transformers qwen azure",
    
    # Informations du projet
    project_urls={
        "Bug Reports": "https://github.com/SkylerAuraArena/TW3-test/issues",
        "Source": "https://github.com/SkylerAuraArena/TW3-test",
        "Documentation": "https://github.com/SkylerAuraArena/TW3-test/blob/main/README.md",
    },
)