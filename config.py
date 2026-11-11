import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)      # Telegram ID of the studio owner (main admin)
DB_PATH = os.getenv("DB_PATH", "data/bot.db")          # on Railway/Render point this to a persistent volume, e.g. /data/bot.db
PORT = int(os.getenv("PORT", "0") or 0)                # if set, a tiny health-check web server is started (Render web service)
LOGO_PATH = os.getenv("LOGO_PATH", "assets/logo.jpg")  # optional welcome picture
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://www.instagram.com/alina_cosmo__")
