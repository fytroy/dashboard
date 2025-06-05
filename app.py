from typing import Optional, List, Dict, Any, Union, Callable
import streamlit as st
import datetime
import requests
import zipfile
import os
from datetime import datetime as dt_object
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
import PyPDF2
from io import BytesIO
import psutil
import socket
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from functools import wraps

# Constants
MAX_LLM_INPUT_LENGTH = 5000
MAX_TEXT_LENGTH_PDF = 15000
WEBSITE_CHECK_TIMEOUT = 5
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

# API Endpoints
COINDESK_API_URL = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
OPENWEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

# --- 1. Streamlit Page Configuration (ABSOLUTE FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="Personal Automation Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. Custom CSS Injection for Modern Theme ---
def inject_custom_css(css_file):
    try:
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file not found: {css_file}. Ensure 'style.css' is in the root directory.")

inject_custom_css("style.css")


# --- 3. Configuration & API Key Loading ---
try:
    WEATHER_API_KEY = st.secrets["OPENWEATHERMAP_API_KEY"]
    NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]
except KeyError as e:
    st.error(f"Missing API key or credential in .streamlit/secrets.toml: {e}. Please refer to the setup instructions.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('models/gemini-1.5-flash')


# --- 4. Google Drive Authentication Setup (for PyDrive2) ---
@st.cache_resource
def init_google_drive():
    try:
        gauth = GoogleAuth('settings.yaml')
        gauth.LoadCredentialsFile("creds.json")

        if gauth.credentials is None:
            st.warning("Google Drive authentication required. A browser window will open for initial setup.")
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile("creds.json")
        st.success("Google Drive authenticated successfully!")
        return GoogleDrive(gauth)
    except Exception as e:
        st.error(f"Google Drive authentication failed: {e}. "
                 "Ensure 'client_secrets.json' is in the root directory, "
                 "Google Drive API is enabled in Google Cloud Console, "
                 "and test user is added to OAuth consent screen (if applicable).")
        return None

drive = init_google_drive()


# --- 5. Function Definitions for Automation Modules ---

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry functions on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
            raise last_exception
        return wrapper
    return decorator

class APIError(Exception):
    """Custom exception for API-related errors."""
    pass

@retry_on_failure(max_retries=3)
def get_btc_price() -> Union[float, str]:
    """Get current Bitcoin price from CoinDesk API."""
    try:
        r = requests.get(COINDESK_API_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "bpi" not in data or "USD" not in data["bpi"]:
            raise APIError("Invalid response format from CoinDesk API")
        return float(data["bpi"]["USD"]["rate_float"])
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error fetching Bitcoin price: {e}")
    except (KeyError, ValueError) as e:
        raise APIError(f"Error parsing Bitcoin price data: {e}")

@retry_on_failure(max_retries=3)
def get_eth_price() -> Union[float, str]:
    """Get current Ethereum price from CoinGecko API."""
    try:
        r = requests.get(f"{COINGECKO_API_URL}?ids=ethereum&vs_currencies=usd", timeout=10)
        r.raise_for_status()
        data = r.json()
        if "ethereum" not in data or "usd" not in data["ethereum"]:
            raise APIError("Invalid response format from CoinGecko API")
        return float(data["ethereum"]["usd"])
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error fetching Ethereum price: {e}")
    except (KeyError, ValueError) as e:
        raise APIError(f"Error parsing Ethereum price data: {e}")

def backup_folder_to_drive(folder_path=".", output_dir=".", drive_folder_name="Automated_Backups"):
    if not drive:
        return "Google Drive not authenticated. Please restart the app and ensure credentials are set up."
    if not os.path.exists(folder_path):
        return f"Error: Local folder '{folder_path}' does not exist."
    now = dt_object.now().strftime("%Y%m%d_%H%M%S")
    base_folder_name = os.path.basename(os.path.abspath(folder_path))
    zip_filename_local = os.path.join(output_dir, f"backup_{base_folder_name}_{now}.zip")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        with zipfile.ZipFile(zip_filename_local, "w", zipfile.Z_DEFLATED) as z:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    z.write(file_path, arcname)
        st.info(f"Local zip created: `{zip_filename_local}`. Proceeding to upload to Google Drive...")

        file_list = drive.ListFile(
            {'q': f"'{'root'}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"}
        ).GetList()
        target_folder = None
        for file in file_list:
            if file['title'] == drive_folder_name:
                target_folder = file
                break
        if not target_folder:
            folder_metadata = {'title': drive_folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            target_folder = drive.CreateFile(folder_metadata)
            target_folder.Upload()
            st.info(f"Created new Google Drive folder: '{drive_folder_name}'")

        file_metadata = {'title': os.path.basename(zip_filename_local), 'parents': [{'id': target_folder['id']}]}
        uploaded_file = drive.CreateFile(file_metadata)
        uploaded_file.SetContentFile(zip_filename_local)
        uploaded_file.Upload()

        os.remove(zip_filename_local)
        return (f"Backup of `{folder_path}` successfully uploaded to Google Drive "
                f"as `{uploaded_file['title']}` in folder `{drive_folder_name}`. "
                "Local zip removed.")
    except Exception as e:
        if os.path.exists(zip_filename_local):
            os.remove(zip_filename_local)
        return f"Error during backup to Google Drive: {e}"

@retry_on_failure(max_retries=3)
def get_weather(city: str = "London") -> str:
    """Get weather information for a city."""
    if not WEATHER_API_KEY or WEATHER_API_KEY == 'YOUR_OPENWEATHERMAP_API_KEY':
        return "Please set your OpenWeatherMap API key in .streamlit/secrets.toml."
    
    url = f"{OPENWEATHER_API_URL}?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("cod") != 200:
            raise APIError(f"Weather API error: {data.get('message', 'Unknown error')}")
            
        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]
        return f"**{temp}°C**, {description.capitalize()}. Humidity: {humidity}%, Wind: {wind_speed} m/s."
    except requests.exceptions.RequestException as e:
        raise APIError(f"Network error fetching weather: {e}")
    except (KeyError, ValueError) as e:
        raise APIError(f"Error parsing weather data: {e}")

def get_news_summary(query="general", language="en", num_articles=3):
    if not NEWS_API_KEY or NEWS_API_KEY == 'YOUR_NEWSAPI_ORG_API_KEY':
        return "Please set your NewsAPI.org API key in .streamlit/secrets.toml."
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_GOOGLE_GEMINI_API_KEY':
        return "Please set your Google Gemini API key in .streamlit/secrets.toml for summarization."

    url = f"{NEWS_API_URL}?q={query}&language={language}&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])

        if not articles:
            return f"No news found for '{query}'."

        summary_parts = []
        for i, article in enumerate(articles[:num_articles]):
            title = article.get("title", "No Title")
            description = article.get("description", "No Description")
            content = article.get("content", "")
            article_url = article.get("url", "#")

            text_to_summarize = f"Title: {title}\nDescription: {description}\nContent: {content}"
            if len(text_to_summarize) > MAX_LLM_INPUT_LENGTH:
                text_to_summarize = text_to_summarize[:MAX_LLM_INPUT_LENGTH] + "\n... [Content truncated for summarization]"

            try:
                response_llm = model.generate_content(
                    f"Summarize the following news article briefly (1-2 sentences), "
                    f"highlighting the main topic and outcome: {text_to_summarize}"
                )
                summary_text = response_llm.text.strip()
            except Exception as e:
                if "429 You exceeded your current quota" in str(e):
                    summary_text = f"LLM Quota Exceeded. Please try again later. (Error: {e})"
                elif "blocked" in str(e).lower() or "safety" in str(e).lower():
                    summary_text = "Content blocked by safety settings. Cannot summarize."
                else:
                    summary_text = f"Could not summarize article (LLM Error: {e})"

            summary_parts.append(f"**{i+1}. [{title}]({article_url})**\n   - {summary_text}")

        return "### Top News Headlines:\n" + "\n\n".join(summary_parts)

    except requests.exceptions.RequestException as e:
        return f"Error fetching news from NewsAPI: {e}"
    except Exception as e:
        return f"An unexpected error occurred during news processing: {e}"

def check_website_uptime(url):
    try:
        response = requests.get(url, timeout=WEBSITE_CHECK_TIMEOUT)
        if response.status_code == 200:
            return f"🟢 {url} is UP (Status: {response.status_code})"
        else:
            return f"🟠 {url} is DOWN (Status: {response.status_code})"
    except requests.exceptions.RequestException as e:
        return f"🔴 {url} is DOWN (Error: {e})"

def summarize_pdf_content(uploaded_file):
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'YOUR_GOOGLE_GEMINI_API_KEY':
        return "Please set your Google Gemini API key in .streamlit/secrets.toml for summarization."
    if uploaded_file is None:
        return "Please upload a PDF file to summarize."
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text_content = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            extracted = page.extract_text()
            if extracted:
                text_content += extracted + "\n"
        if not text_content.strip():
            return "Could not extract text from the PDF. It might be an image-based PDF, password-protected, or empty."
        if len(text_content) > MAX_TEXT_LENGTH_PDF:
            st.warning(f"PDF content is very large ({len(text_content)} chars). Truncating for summarization.")
            text_content = text_content[:MAX_TEXT_LENGTH_PDF] + "\n... [Content truncated for summarization]"
        st.info("Sending content to Gemini for summarization. This may take a moment...")
        response_llm = model.generate_content(
            f"Summarize the following document content concisely, highlighting key findings or arguments:\n\n{text_content}"
        )
        summary = response_llm.text.strip()
        return f"**Summary of '{uploaded_file.name}':**\n\n{summary}"
    except PyPDF2.utils.PdfReadError:
        return "Error reading PDF file. It might be corrupted or not a valid PDF."
    except Exception as e:
        if "429 You exceeded your current quota" in str(e):
            return f"LLM Quota Exceeded. Please try again later. (Error: {e})"
        elif "blocked" in str(e).lower() or "safety" in str(e).lower():
            return "Content blocked by safety settings. Cannot summarize."
        else:
            return f"An unexpected error occurred during PDF summarization: {e}"

def run_scheduled_task(task_name):
    st.info(f"Running scheduled task: '{task_name}' now...")
    time.sleep(1)
    return f"Task '{task_name}' executed successfully."

def send_email(to_email, subject, message_body):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return "Please set your GMAIL_USER and GMAIL_APP_PASSWORD in .streamlit/secrets.toml for email sending."
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(message_body, 'plain'))
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return "Email sent successfully!"
    except Exception as e:
        return (f"Error sending email: {e}. "
                "Please check your Gmail credentials and 'App passwords' settings "
                "(if using 2FA) or ensure Less Secure App Access is enabled (for older setups).")

def get_machine_report():
    """Gathers and formats detailed system information."""
    report = []
    report.append(f"**System Information ({dt_object.now().strftime('%Y-%m-%d %H:%M:%S')})**")
    report.append("---")

    cpu_percent = psutil.cpu_percent(interval=1)
    report.append(f"CPU Usage: {cpu_percent:.1f}%")

    svmem = psutil.virtual_memory()
    mem_total_gb = svmem.total / (1024**3)
    mem_used_gb = svmem.used / (1024**3)
    mem_percent = svmem.percent
    report.append(f"Memory Usage: {mem_used_gb:.2f} GB / {mem_total_gb:.2f} GB ({mem_percent:.1f}%)")

    disk_usage = psutil.disk_usage(os.getcwd())
    disk_total_gb = disk_usage.total / (1024**3)
    disk_used_gb = disk_usage.used / (1024**3)
    disk_percent = disk_usage.percent
    report.append(f"Disk Usage ({os.getcwd()}): {disk_used_gb:.2f} GB / {disk_total_gb:.2f} GB ({disk_percent:.1f}%)")

    report.append("\n**Network Interfaces:**")
    net_if_addrs = psutil.net_if_addrs()
    if not net_if_addrs:
        report.append("  No network interfaces found.")
    else:
        for interface_name, interface_addresses in net_if_addrs.items():
            report.append(f"  - **{interface_name}:**")
            found_ip = False
            for addr in interface_addresses:
                # IMPORTANT: Use socket module constants as a fallback or primary for AF_INET/AF_INET6
                # And use hasattr checks for AF_LINK/AF_PACKET as they are OS-dependent or not always present.
                if addr.family == socket.AF_INET: # IPv4 address
                    report.append(f"    - IP Address: {addr.address}")
                    report.append(f"    - Netmask: {addr.netmask}")
                    if addr.broadcast: report.append(f"    - Broadcast: {addr.broadcast}")
                    found_ip = True
                elif addr.family == socket.AF_INET6: # IPv6 address
                    report.append(f"    - IPv6 Address: {addr.address}")
                # Check for platform-specific MAC address constants
                elif hasattr(socket, 'AF_LINK') and addr.family == socket.AF_LINK: # Often macOS, BSD
                    report.append(f"    - MAC Address: {addr.address}")
                elif hasattr(socket, 'AF_PACKET') and addr.family == socket.AF_PACKET: # Often Linux
                    report.append(f"    - MAC Address: {addr.address}")
                # Fallback for systems where MAC address family might not be explicitly AF_LINK/AF_PACKET,
                # but might appear as another family with a MAC-like address string.
                elif not found_ip and addr.address and len(addr.address.replace(':', '')) == 12 and all(c in '0123456789abcdefABCDEF' for c in addr.address.replace(':', '')):
                    report.append(f"    - MAC Address (heuristic): {addr.address}")

            if not found_ip and not interface_addresses: # If no IP address found for interface
                report.append("    - No address details.")

    boot_time_timestamp = psutil.boot_time()
    boot_time_dt = dt_object.fromtimestamp(boot_time_timestamp)
    current_time_dt = dt_object.now()
    uptime_duration = current_time_dt - boot_time_dt
    report.append(f"\nSystem Boot Time: {boot_time_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"System Uptime: {uptime_duration}")

    return "\n".join(report)


# --- 6. Dashboard Layout ---

st.title("🛠️ Personal Automation Dashboard")
st.markdown("---")

if 'btc_price' not in st.session_state:
    st.session_state['btc_price'] = "N/A"
if 'eth_price' not in st.session_state:
    st.session_state['eth_price'] = "N/A"
if 'weather_report' not in st.session_state:
    st.session_state['weather_report'] = "No weather fetched yet."
if 'website_status' not in st.session_state:
    st.session_state['website_status'] = "No website checked yet."
if 'machine_report' not in st.session_state:
    st.session_state['machine_report'] = "Click 'Refresh Machine Report' to view."


with st.sidebar:
    st.header("⚙️ Quick Actions")
    st.markdown("---")

    with st.container(border=True):
        st.subheader("📊 Crypto Price Refresh")
        if st.button("🔄 Refresh Crypto Prices", use_container_width=True):
            with st.spinner("Fetching crypto prices..."):
                btc_price_val = get_btc_price()
                eth_price_val = get_eth_price()
                st.session_state['btc_price'] = f"${btc_price_val:,.2f}" if isinstance(btc_price_val, float) else btc_price_val
                st.session_state['eth_price'] = f"${eth_price_val:,.2f}" if isinstance(eth_price_val, float) else eth_price_val
            st.success("Prices updated!")

    st.markdown("---")

    with st.container(border=True):
        st.subheader("☁️ Weather Location")
        weather_city_input = st.text_input("Enter City for Weather:", value="Nairobi", key="weather_city")
        if st.button("Get Weather", use_container_width=True):
            with st.spinner("Fetching weather..."):
                weather_report = get_weather(weather_city_input)
            st.session_state['weather_report'] = weather_report
            st.success("Weather updated!")

    st.markdown("---")

    with st.container(border=True):
        st.subheader("🌐 Website Monitor")
        website_url = st.text_input("Website URL to Check:", value="https://www.google.com", key="website_url_input")
        if st.button("Check Website", use_container_width=True):
            with st.spinner("Checking website..."):
                website_status = check_website_uptime(website_url)
            st.session_state['website_status'] = website_status
            st.success("Website status updated!")

    st.markdown("---")

    with st.container(border=True):
        st.subheader("🖥️ Machine Report")
        if st.button("Refresh Machine Report", use_container_width=True):
            with st.spinner("Gathering system information..."):
                machine_report = get_machine_report()
            st.session_state['machine_report'] = machine_report
            st.success("Machine report updated!")

    st.markdown("---")
    st.markdown("For continuous scheduling, consider a separate script running with `schedule` or `APScheduler`.")


st.header("⚡ Core Automation Modules")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("📁 File Backup (to Google Drive)")
        st.caption("First time backup requires browser authentication for Google Drive via 'client_secrets.json'.")
        backup_source_folder = st.text_input("Local Folder to Backup (e.g., '.' for current):", value=".", key="backup_source_folder")
        backup_output_folder_local = st.text_input("Local Temp Folder for Zip:", value="temp_backups", key="backup_output_folder_local_zip")
        drive_folder_name_input = st.text_input("Google Drive Target Folder:", value="Automated_Backups", key="drive_folder_name_input")

        if st.button("▶️ Start Google Drive Backup", use_container_width=True):
            if not drive:
                st.warning("Google Drive not initialized. Please ensure setup and try again.")
            else:
                with st.spinner(f"Backing up '{backup_source_folder}' to Google Drive..."):
                    backup_result = backup_folder_to_drive(backup_source_folder, backup_output_folder_local, drive_folder_name_input)
                st.info(backup_result)

    with st.container(border=True):
        st.subheader("📧 Send Quick Email")
        email_to = st.text_input("Recipient Email:", key="email_to_input")
        email_subject = st.text_input("Subject:", key="email_subject_input")
        email_message = st.text_area("Message:", key="email_message_input")
        if st.button("🚀 Send Email", use_container_width=True):
            if email_to and email_message:
                with st.spinner("Sending email..."):
                    email_status = send_email(email_to, email_subject, email_message)
                st.success(email_status)
            else:
                st.warning("Please fill in recipient and message for the email.")

with col2:
    with st.container(border=True):
        st.subheader("🗞️ News Summary")
        news_query = st.text_input("News Topic (e.g., 'technology', 'finance'):", value="AI", key="news_query_input")
        if st.button("📰 Fetch & Summarize News", use_container_width=True):
            with st.spinner(f"Fetching and summarizing news about '{news_query}'..."):
                news_summary = get_news_summary(query=news_query)
            st.markdown(news_summary)

    with st.container(border=True):
        st.subheader("📝 PDF/Note Summarizer")
        uploaded_file = st.file_uploader("Upload a PDF file", type="pdf", key="pdf_uploader")
        if st.button("🧠 Summarize Document", use_container_width=True):
            if uploaded_file is not None:
                with st.spinner("Summarizing document..."):
                    summary_output = summarize_pdf_content(uploaded_file)
                st.info(summary_output)
            else:
                st.warning("Please upload a PDF file first.")

    with st.container(border=True):
        st.subheader("🕒 Task Scheduler (Trigger Now)")
        task_name_input = st.text_input("Task to Trigger (e.g., 'Daily Report Generation'):", key="task_name_input")
        if st.button("⚡ Trigger Task", use_container_width=True):
            if task_name_input:
                st.info(run_scheduled_task(task_name_input))
            else:
                st.warning("Please enter a task name to trigger.")

st.markdown("---")
st.header("📊 Current Status & System Overview")

col_status_1, col_status_2 = st.columns([1, 2])

with col_status_1:
    with st.container(border=True):
        st.subheader("Key Metrics")
        st.metric(label="Bitcoin Price (USD)", value=st.session_state['btc_price'])
        st.metric(label="Ethereum Price (USD)", value=st.session_state['eth_price'])
        st.info(f"**Current Weather:** {st.session_state['weather_report']}")
        st.info(f"**Website Uptime:** {st.session_state['website_status']}")

with col_status_2:
    with st.expander("Detailed Machine Report", expanded=True):
        st.code(st.session_state['machine_report'], language='text')

st.markdown("---")
st.markdown(f"Last updated: {dt_object.now().strftime('%Y-%m-%d %H:%M:%S')}")