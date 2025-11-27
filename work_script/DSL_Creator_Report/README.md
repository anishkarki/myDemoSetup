# DSL Creator & Log Reporter UI

A Flask-based web interface to generate OpenSearch DSL queries and fetch logs with a beautiful HTML report.

## 🚀 Getting Started

1.  **Run the UI:**
    ```bash
    ./run_ui.sh
    ```
    Or manually:
    ```bash
    python3 app.py
    ```

2.  **Access the Interface:**
    Open your browser and go to: `http://localhost:5002`

## ✨ Features

*   **Generate DSL:** Input hostname, keywords, and time range to see the exact OpenSearch DSL query generated.
*   **Fetch & Report:** Execute the query against OpenSearch and generate a downloadable HTML report.
*   **Dynamic Filtering:** Supports wildcards (e.g., `error*`) and multiple keywords.

## 📂 Files

*   `app.py`: The Flask application logic.
*   `templates/index.html`: The frontend UI.
*   `fetch_and_report.py`: The core logic for DSL generation and fetching (reused from CLI tool).
*   `run_ui.sh`: Helper script to launch the app.
