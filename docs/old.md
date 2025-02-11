# middts-client
A middts client.

[INSTALLATION GUIDE](docs/installation_guide.md)

1. Frontend (Interface Gráfica)

🔹 Tecnologia: React + TypeScript
🔹 Bibliotecas:

    Shadcn/UI ou Material UI para componentes prontos e estilização moderna
    Cytoscape.js ou React-Flow para visualização gráfica de dados do Neo4j
    D3.js para renderizar gráficos dinâmicos de conexões entre Gêmeos Digitais

📌 Motivos para essa escolha:

    React é altamente modular e permite a fácil integração com APIs REST e WebSockets.
    TypeScript melhora a manutenção e escalabilidade do código.
    Cytoscape.js e React-Flow são ideais para visualizações gráficas, como redes de dependências entre Gêmeos Digitais.
    Shadcn/UI ou Material UI oferecem uma interface moderna e responsiva rapidamente.


Backend (Intermediário entre a API do Middts e a Interface Gráfica)

🔹 Tecnologia: Django com Django Ninja
🔹 Banco de Dados: PostgreSQL (com extensão PostGIS)
🔹 Gerenciamento de Requisições: FastAPI ou Django REST Framework (DRF)
🔹 Autenticação: OAuth 2.0 (Keycloak ou Firebase Auth)

📌 Motivos para essa escolha:

    Django Ninja é leve e rápido para criar APIs eficientes.
    PostgreSQL com PostGIS permite armazenamento e consultas espaciais caso a estrutura do Gêmeo Digital inclua geolocalização.
    FastAPI pode ser uma opção para serviços de eventos assíncronos.
    OAuth 2.0 garante um controle de acesso seguro e escalável.


Banco de Dados para Gêmeos Digitais

🔹 Tecnologia: Neo4j via Docker
🔹 Ferramentas de Visualização: Neo4j Bloom para insights exploratórios, Cytoscape.js para renderização gráfica personalizada.

📌 Motivos para essa escolha:

    Neo4j permite representar de forma natural as relações entre Gêmeos Digitais, sensores e dispositivos.
    O suporte a consultas Cypher facilita a recuperação de informações complexas.
    A visualização via Cytoscape.js ou React-Flow pode integrar diretamente a UI da aplicação cliente.

Arquitetura Geral da Aplicação
```yaml
frontend:
  - React + TypeScript
  - Cytoscape.js (visualização gráfica)
  - API calls para Middts e Neo4j
backend:
  - Django + Django Ninja (API REST)
  - PostgreSQL (armazenamento relacional)
  - Neo4j (representação de relacionamentos)
middleware:
  - Neo4j rodando em Docker
  - Apache Kafka (event-driven updates)
  - Redis (caching de queries frequentes)
```


# Instalação do NODE.JS

Instale a versão mais recente do Node.js
A melhor forma de gerenciar versões do Node.js é usando o NVM (Node Version Manager).

📌 No Linux/macOS:

curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash
source ~/.bashrc  # ou source ~/.zshrc se estiver usando zsh

📌 No Windows:
Baixe o instalador do NVM aqui e instale.

Depois de instalar o NVM, use os comandos abaixo para instalar o Node.js 20:

nvm install 20
nvm use 20

Verifique a instalação:

node -v  # Deve mostrar v20.x.x
npm -v   # Deve mostrar 9.x.x ou mais

Se estiver sem NVM, pode baixar manualmente de:
🔗 https://nodejs.org/en/download

## Atualizar o NPM

Agora que o Node.js está atualizado, atualize o npm:

npm install -g npm

Verifique se tudo está correto:

node -v  # Deve mostrar v20.x.x
npm -v   # Deve mostrar v9.x.x ou mais

Agora tente novamente criar o projeto:

npx create-vite frontend --template react-ts

# Instalar docker e docker-compose e rodar os BDs

```bash
sudo snap install docker
sudo apt  install docker-compose
# Rodar o banco postgres e neo4j
docker-compose up -d
```

# Atualizar pacotes pip e requirements e npm
Cria um venv com python 3.10 ou superior e em seguida instale os pacotes com pip

```bash
pip install -Ur requirements/base.txt
```

## Criando apps Frontend e Backend


```bash
# criando frontend com react-ts
npm create vite@latest frontend -- --template react-ts
# Criando backend com django
django-admin startproject backend .
python manage.py startapp twins
```

📌 Habilitar apps no backend/settings.py

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',
    'twins',
    'corsheaders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]  # React Vite

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'middts_db',
        'USER': 'admin',
        'PASSWORD': 'admin',
        'HOST': 'localhost',
        'PORT': '5434', # porta usada no docker compose
    }
}
```

Depois usa o comando pra criar as tabelas
```bash
python manage.py migrate
```