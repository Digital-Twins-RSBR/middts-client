# Middts Client

Middts Client is a tool for visualization and management of Digital Twins. The application allows you to view Digital Twin instances, their properties, and relationships, as well as edit causal properties directly in the interface.

## Installation

### Prerequisites

- Python 3.8+
- Django 3.2+

### Installation Steps

1. Clone the repository:

    ```sh
    git clone https://github.com/your-username/middts-client.git
    cd middts-client
    ```

2. Create and activate a virtual environment:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install project dependencies:

    ```sh
    pip install -r requirements.txt
    ```

4. Configure the database in the `settings.py` file:

    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    ```

5. Apply database migrations:

    ```sh
    python manage.py migrate
    ```

6. Start the development server:

    ```sh
    python manage.py runserver
    ```

## Additional Configurations

For the correct functioning of Middts Client, some additional configurations are required in the `settings_base.py` file:

- `SITE_URL`: Defines the base URL of the site where the client is running.
- `MIDDTS_API_URL`: Defines the base URL of the Middts API.
- `CORS_ALLOWED_ORIGINS`: Defines the allowed origins for CORS requests.

Example configuration:

```python
SITE_URL = "http://localhost:8004"
MIDDTS_API_URL = "http://localhost:8000/api"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    # "http://your-middts-server.com"
]
```

### Configuration Explanation

* `SITE_URL`: This setting defines the base URL of the Middts client. In the example, the client is running at `http://localhost:8004`.
* `MIDDTS_API_URL`: This setting defines the base URL of the Middts API. In the example, the API is available at `http://localhost:8000/api`.
* `CORS_ALLOWED_ORIGINS`: This setting allows the Middts client to make requests to the Middts API. In the example, the allowed origins are `http://localhost:8000` and `http://127.0.0.1:8000`.

## Usage

### Step-by-Step

1. Access the application: Open your browser and go to `http://127.0.0.1:8000`.

2. Filter by System: Use the filter at the top of the page to select the desired system. This will update the view to show only the instances of the selected system.

3. View Digital Twins: In the graph, click on any node to view detailed information about the Digital Twin in the side panel.

4. Edit Properties: In the side panel, edit the causal properties as needed. After making changes, click the "Save Changes" button to update the properties in the database.

5. Update View: The changes made to the properties will be immediately reflected in the interface. To ensure the data is up-to-date, click on the Digital Twin node again.

### Additional Features

* Drag and Drop: You can drag nodes in the graph to rearrange the view as needed.
* Zoom and Pan: Use the mouse scroll to zoom in and out, and drag the graph to navigate the view.
* Left Sidebar: Provides options to switch between different views (Graph, Text, JSON) of the query results.
* Right Sidebar: Displays detailed information about the selected Digital Twin, including non-editable and editable properties.

## Contribution

Contributions are welcome! Feel free to open issues and pull requests in the repository.
