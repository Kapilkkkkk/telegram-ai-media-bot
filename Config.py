import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file for local development
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Telegram Bot Token (Required)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")

# Admin User IDs (Required - Comma-separated string)
ADMIN_USER_IDS_STR = os.environ.get("ADMIN_USER_IDS", "")
try:
    # Split string by comma and convert each part to an integer
    ADMIN_USER_IDS = {int(admin_id.strip()) for admin_id in ADMIN_USER_IDS_STR.split(',') if admin_id.strip()}
    if not ADMIN_USER_IDS:
        raise ValueError("ADMIN_USER_IDS cannot be empty.")
except ValueError as e:
    raise ValueError(f"Invalid ADMIN_USER_IDS format in environment variables. Expected comma-separated integers. Error: {e}")

# --- Optional Configuration ---

# AI Service API Key (Example - replace if needed)
AI_API_KEY = os.environ.get("AI_API_KEY")

# Placeholder for other configs (e.g., D-ID key if re-enabled)
# D_ID_API_KEY = os.environ.get("D_ID_API_KEY")

# Logging level
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Webhook URL (if using webhooks instead of polling)
# RENDER_WEBHOOK_URL = os.environ.get("RENDER_WEBHOOK_URL") # e.g., https://your-app-name.onrender.com/

# --- Configuration Validation ---
# Add more checks here if necessary

# --- Setup Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=LOG_LEVEL
)
# Set higher logging level for httpx to avoid verbose messages
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

logger.info("Configuration loaded.")
logger.info(f"Admin User IDs: {ADMIN_USER_IDS}")
# Avoid logging sensitive keys directly
logger.info(f"AI API Key Loaded: {'Yes' if AI_API_KEY else 'No'}")

