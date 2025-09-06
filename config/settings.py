# config/settings.py
import logging
from queue import Queue
from typing import Dict

# =============== KONFIGURÁCIÓS BEÁLLÍTÁSOK ===============
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
WEBAPP_URL = "https://e1d404acf189.ngrok-free.app"  # ha iPad/ngrok: "https://<valami>.ngrok-free.app"
DB_NAME = "restaurant_orders.db"

# Admin jogosultottak listája (Telegram user ID-k)
ADMIN_USER_IDS = [7553912440]  # Itt add meg a saját Telegram user ID-d

# =============== LOGGING KONFIGURÁCIÓ ===============
def setup_logging():
    """Logging beállítása"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)

# =============== GLOBÁLIS VÁLTOZÓK ===============
# Értesítések sorban (pl. éttermi csoportnak visszaírás)
notification_queue: "Queue[Dict]" = Queue()
