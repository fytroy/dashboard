# Personal Automation Dashboard

## Overview

The Personal Automation Dashboard is a Streamlit-based web application designed to provide a centralized interface for various personal automation tasks and information monitoring. It integrates with multiple APIs and services to offer features like cryptocurrency price tracking, weather updates, news summarization, file backups to Google Drive, PDF document summarization, email sending, and system resource monitoring.

The application is styled with custom CSS for a modern, dark-themed user interface.

## Features

- **Cryptocurrency Tracking:** Displays current prices for Bitcoin (BTC) and Ethereum (ETH) using CoinDesk and CoinGecko APIs.
- **Weather Information:** Fetches and displays current weather conditions for a specified city using the OpenWeatherMap API.
- **Website Uptime Checker:** Checks the status of a given website URL.
- **Google Drive Backup:** Backs up a specified local folder (or the entire project) to a designated folder in Google Drive. Requires initial Google authentication.
- **News Summarization:** Fetches top news headlines for a given query from NewsAPI and uses Google Gemini to summarize the articles.
- **PDF Summarizer:** Allows users to upload a PDF file, extracts its text content, and uses Google Gemini to generate a summary.
- **Quick Email Sender:** Provides a simple interface to send emails via Gmail. Requires Gmail credentials and app password.
- **System Resource Monitor:** Displays current CPU usage, memory usage, disk usage (for the current directory), network interface details, system boot time, and uptime.
- **Customizable UI:** Styled with `style.css` for a modern, dark-themed dashboard experience.

## Prerequisites

- Python 3.7+
- Pip (Python package installer)
- Access to a terminal or command prompt.
- API Keys and Credentials (see Configuration section).
- Web browser for initial Google Drive authentication.

## Setup and Installation

1.  **Clone the repository (or download the source code):**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install required Python libraries:**
    The project relies on several Python packages. While a `requirements.txt` file is not explicitly provided in the initial file listing, common Streamlit apps use one. If it were present, you'd run:
    ```bash
    pip install -r requirements.txt
    ```
    Based on the `app.py` imports, you will likely need to install the following manually if no `requirements.txt` exists:
    ```bash
    pip install streamlit requests google-generativeai pypdf2 psutil pydrive2
    ```

4.  **Configure API Keys and Credentials (Crucial):**
    -   **Streamlit Secrets (`.streamlit/secrets.toml`):**
        Create this file if it doesn't exist. Add the following keys with your actual API credentials:
        ```toml
        OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
        NEWS_API_KEY = "YOUR_NEWS_API_KEY"
        GEMINI_API_KEY = "YOUR_GOOGLE_GEMINI_API_KEY"
        GMAIL_USER = "your_email@gmail.com"
        GMAIL_APP_PASSWORD = "your_gmail_app_password" # Use an App Password if 2FA is enabled
        ```
    -   **Google Drive API (`client_secrets.json` and `creds.json`):**
        -   You need to enable the Google Drive API in your Google Cloud Console.
        -   Create OAuth 2.0 credentials and download the `client_secrets.json` file. Place this file in the root directory of the project.
        -   The `creds.json` file will be automatically generated and saved by PyDrive2 after the first successful authentication via the web browser.
    -   **PyDrive2 Settings (`settings.yaml`):**
        PyDrive2 uses this file for its configuration. A typical `settings.yaml` for PyDrive2 might look like this (though the app seems to imply it might be automatically handled or use defaults if not extensively configured):
        ```yaml
        client_config_backend: "file"
        client_config_file: "client_secrets.json"
        save_credentials: true
        save_credentials_backend: "file"
        save_credentials_file: "creds.json"
        oauth_scope:
          - https://www.googleapis.com/auth/drive
        ```
        Ensure this file is present or that PyDrive2 can operate with its default settings if `client_secrets.json` is in the root. The application code attempts to load credentials using `gauth = GoogleAuth('settings.yaml')`.

5.  **Run the Streamlit application:**
    ```bash
    streamlit run app.py
    ```
    The application should open in your default web browser. For Google Drive backup, the first time you use the feature, it will likely open a browser window for you to authenticate and authorize access.

## Project Structure

-   `app.py`: The main Streamlit application script containing all the logic and UI elements.
-   `style.css`: Custom CSS file for theming the application.
-   `.streamlit/config.toml`: Streamlit configuration file (e.g., for theme settings).
    ```toml
    [theme]
    primaryColor="#0078D4"      # Example: Power BI Blue
    backgroundColor="#1A1A1A"    # Dark background
    secondaryBackgroundColor="#2B2B2B" # Slightly lighter dark
    textColor="#E0E0E0"         # Light text
    font="sans serif"
    ```
-   `.streamlit/secrets.toml`: Stores API keys and sensitive credentials (see setup).
-   `client_secrets.json`: Google API client secrets for OAuth (see setup).
-   `creds.json`: Stores OAuth credentials after successful Google authentication (generated automatically).
-   `settings.yaml`: Configuration file for PyDrive2.
-   `backups/`: Default local directory for storing temporary zip files before uploading to Google Drive (can be configured in the UI).

## Usage

Once the application is running:

-   **Sidebar:** Use the sidebar for quick actions like refreshing crypto prices, getting weather updates, checking website status, and refreshing the machine report.
-   **Main Area:**
    -   **File Backup:** Configure the source folder, temporary local backup path, and Google Drive target folder, then initiate the backup.
    -   **Send Quick Email:** Fill in the recipient, subject, and message to send an email.
    -   **News Summary:** Enter a topic to fetch and summarize related news articles.
    -   **PDF Summarizer:** Upload a PDF to get a concise summary.
    -   **Task Scheduler:** Enter a task name and trigger (currently a placeholder for immediate execution).
-   **Status & System Overview:** View key metrics (crypto, weather, website status) and a detailed machine report.

## Future Enhancements (Potential To-Do)

-   Implement actual background task scheduling (e.g., using APScheduler or a cron job).
-   Add more automation modules (e.g., social media integration, calendar events).
-   User accounts and personalized settings.
-   More robust error handling and logging.
-   Interactive charts for financial data or system metrics.
-   Option to customize the number of news articles or summary length.
-   Direct editing and management of scheduled tasks.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details. (Assuming MIT, a `LICENSE` file would need to be added).
