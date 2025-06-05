# Personal Automation Dashboard

This Streamlit application provides a personal dashboard with various automation tools and information widgets. It integrates with several APIs and local system utilities to offer functionalities like cryptocurrency price tracking, weather updates, website monitoring, system resource display, Google Drive backups, email sending, and AI-powered news and document summarization.

## Key Features

*   **Crypto Price Tracking**: Displays current prices for Bitcoin (BTC) and Ethereum (ETH) using CoinDesk and CoinGecko APIs.
*   **Weather Information**: Fetches and shows current weather conditions for a specified city using the OpenWeatherMap API.
*   **Website Uptime Monitoring**: Checks and reports the status (up/down) of a given website URL.
*   **System Resource Monitoring**: Provides a detailed report of system resources including CPU usage, memory usage, disk space, network interface details, and system uptime, utilizing the `psutil` library.
*   **Google Drive Backup**: Backs up a specified local folder (or the entire project) as a ZIP file to a designated folder in Google Drive. Requires Google Drive API setup and authentication.
*   **Email Sending**: Allows sending emails via Gmail. Requires Gmail credentials and app password setup.
*   **News Summarization**: Fetches top news headlines for a given query using NewsAPI and then uses Google Gemini to provide a concise summary of selected articles.
*   **PDF Document Summarization**: Upload a PDF file and get an AI-generated summary of its content using Google Gemini.
*   **Task Triggering**: A simple interface to simulate triggering predefined tasks (note: actual background scheduling is not implemented within this app).
*   **Customizable Interface**: Styled with custom CSS for a modern look and feel.

## Technologies Used

*   **Frontend**: Streamlit
*   **Programming Language**: Python
*   **Core Libraries**:
    *   `requests`: For making HTTP requests to external APIs.
    *   `google-generativeai`: For interacting with the Google Gemini API for summarization.
    *   `pydrive2`: For Google Drive integration (authentication and file uploads).
    *   `PyPDF2`: For extracting text from PDF files.
    *   `psutil`: For accessing system details and process utilities.
    *   `smtplib`, `email.mime.text`, `email.mime.multipart`: For sending emails.
*   **External APIs**:
    *   CoinDesk API (Bitcoin prices)
    *   CoinGecko API (Ethereum prices)
    *   OpenWeatherMap API (Weather information)
    *   NewsAPI (News headlines)
*   **Styling**: Custom CSS

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file (if not already present in the repository) with the following content:
    ```txt
    streamlit
    requests
    google-generativeai
    pydrive2
    PyPDF2
    psutil
    # Add any other specific versions if known e.g., streamlit==1.20.0
    ```
    Then install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The `requirements.txt` will be created in a subsequent step if it doesn't exist.)*

4.  **Set Up API Keys and Credentials:**
    Navigate to the `.streamlit` directory (create it if it doesn't exist at the root of your project).
    ```bash
    mkdir -p .streamlit
    cd .streamlit
    ```
    Create a file named `secrets.toml` inside the `.streamlit` directory and add your API keys and credentials. **Do not commit `secrets.toml` if it contains sensitive information.**
    ```toml
    # .streamlit/secrets.toml

    OPENWEATHERMAP_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
    NEWS_API_KEY = "YOUR_NEWSAPI_ORG_API_KEY"
    GEMINI_API_KEY = "YOUR_GOOGLE_GEMINI_API_KEY"

    # For Gmail integration (ensure you use an App Password if 2FA is enabled)
    GMAIL_USER = "your_email@gmail.com"
    GMAIL_APP_PASSWORD = "your_gmail_app_password"
    ```

5.  **Google Drive API Setup:**
    *   **Enable Google Drive API:**
        *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
        *   Create a new project or select an existing one.
        *   Navigate to "APIs & Services" > "Library".
        *   Search for "Google Drive API" and enable it.
    *   **Create OAuth 2.0 Credentials:**
        *   Go to "APIs & Services" > "Credentials".
        *   Click "Create Credentials" > "OAuth client ID".
        *   Configure the OAuth consent screen if you haven't already. For "User type", you can select "External" and add your email as a test user during development/testing if your app is not yet published.
        *   Choose "Desktop app" as the Application type.
        *   Name your OAuth client ID.
        *   Click "Create". A dialog will show your client ID and client secret.
        *   Click "DOWNLOAD JSON" to download the client secret file.
    *   **Place `client_secrets.json`:**
        *   Rename the downloaded JSON file to `client_secrets.json`.
        *   Place this `client_secrets.json` file in the **root directory** of the project.
    *   **PyDrive2 Authentication Settings (`settings.yaml`):**
        *   Ensure you have a `settings.yaml` file in the root directory with the following content (PyDrive2 uses this to specify the client secrets file):
          ```yaml
          client_config_backend: file
          client_config_file: client_secrets.json
          save_credentials: true
          save_credentials_backend: file
          save_credentials_file: creds.json
          oauth_scope:
            - https://www.googleapis.com/auth/drive
          ```
    *   **First-time Authentication:**
        *   When you run the application for the first time, PyDrive2 will attempt to authenticate. It will likely open a web browser page asking you to log in with your Google account and authorize the application to access your Google Drive.
        *   After successful authentication, a `creds.json` file will be created in your project's root directory (or as specified in `settings.yaml`). This file stores your OAuth 2.0 credentials. **It's recommended to add `creds.json` to your `.gitignore` file to avoid committing it.**

6.  **Verify `style.css`:**
    *   Ensure the `style.css` file is present in the root directory of the project for custom styling to be applied.

## Usage

1.  **Ensure all setup steps are completed**, especially the installation of dependencies and the configuration of API keys in `.streamlit/secrets.toml` and Google Drive credentials (`client_secrets.json`, `settings.yaml`, and subsequent `creds.json`).

2.  **Run the Streamlit Application:**
    Open your terminal, navigate to the project's root directory, and run:
    ```bash
    streamlit run app.py
    ```

3.  **Interact with the Dashboard:**
    *   The application will open in your web browser.
    *   Use the **sidebar** for quick actions like refreshing crypto prices, getting weather updates for a city, checking website uptime, or refreshing the machine report.
    *   The **main area** contains modules for:
        *   **File Backup**: Specify the local folder to back up, a temporary local path for the zip file, and the target Google Drive folder name, then click "Start Google Drive Backup". Authenticate with Google if it's the first time.
        *   **Send Quick Email**: Fill in the recipient's email, subject, and message, then click "Send Email".
        *   **News Summary**: Enter a news topic and click "Fetch & Summarize News".
        *   **PDF/Note Summarizer**: Upload a PDF file and click "Summarize Document".
        *   **Task Scheduler**: Enter a task name and click "Trigger Task" to simulate task execution.
    *   The **Status & System Overview** section displays key metrics and a detailed machine report.
