# Middts Client

Middts Client é uma ferramenta para visualização e gerenciamento de Gêmeos Digitais. A aplicação permite visualizar instâncias de Gêmeos Digitais, suas propriedades e relações, além de editar propriedades causais diretamente na interface.

## Instalação

### Pré-requisitos

- Python 3.8+
- Django 3.2+
- Node.js (para gerenciamento de dependências front-end, se necessário)

### Passos para Instalação

1. Clone o repositório:

    ```sh
    git clone https://github.com/seu-usuario/middts-client.git
    cd middts-client
    ```

2. Crie e ative um ambiente virtual:

    ```sh
    python -m venv venv
    source venv/bin/activate  # No Windows use `venv\Scripts\activate`
    ```

3. Instale as dependências do projeto:

    ```sh
    pip install -r requirements.txt
    ```

4. Configure o banco de dados no arquivo `settings.py`:

    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    ```

5. Aplique as migrações do banco de dados:

    ```sh
    python manage.py migrate
    ```

6. Inicie o servidor de desenvolvimento:

    ```sh
    python manage.py runserver
    ```

## Configurações Extras

Para o funcionamento correto do Middts Client, algumas configurações adicionais são necessárias no arquivo [settings_base.py](http://_vscodecontentref_/1):

- [SITE_URL](http://_vscodecontentref_/2): Define a URL base do site onde o cliente está rodando.
- [MIDDTS_API_URL](http://_vscodecontentref_/3): Define a URL base da API do Middts.
- [CORS_ALLOWED_ORIGINS](http://_vscodecontentref_/4): Define as origens permitidas para requisições CORS.

Exemplo de configuração:

```python
SITE_URL = "http://localhost:8004"
MIDDTS_API_URL = "http://localhost:8000/api"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # "http://seu-servidor-middts.com"
]
```
### Explicação das Configurações

* SITE_URL: Esta configuração define a URL base do cliente Middts. No exemplo, o cliente está rodando em http://localhost:8004.
* MIDDTS_API_URL: Esta configuração define a URL base da API do Middts. No exemplo, a API está disponível em http://localhost:8000/api.
* CORS_ALLOWED_ORIGINS: Esta configuração permite que o cliente Middts faça requisições para a API do Middts. No exemplo, as origens permitidas são http://localhost:8000 e http://127.0.0.1:8000.


## Uso
### Passo a Passo
1. Acessar a aplicação: Abra o navegador e acesse http://127.0.0.1:8000.

2. Filtrar por Sistema: Utilize o filtro no topo da página para selecionar o sistema desejado. Isso atualizará a visualização para mostrar apenas as instâncias do sistema selecionado.

3. Visualizar Gêmeos Digitais: No gráfico, clique em qualquer nó para visualizar as informações detalhadas do Gêmeo Digital no painel lateral.

4. Editar Propriedades: No painel lateral, edite as propriedades causais conforme necessário. Após realizar as alterações, clique no botão "Salvar Alterações" para atualizar as propriedades no banco de dados.

5. Atualizar Visualização: As alterações feitas nas propriedades serão refletidas imediatamente na interface. Para garantir que os dados estão atualizados, clique novamente no nó do Gêmeo Digital.

### Funcionalidades Adicionais
* Arrastar e Soltar: Você pode arrastar os nós no gráfico para reorganizar a visualização conforme necessário.
* Zoom e Pan: Utilize o scroll do mouse para aplicar zoom e arraste o gráfico para navegar pela visualização.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests no repositório.
