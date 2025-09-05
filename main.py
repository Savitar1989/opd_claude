# main.py
import threading
from config.settings import setup_logging
from telegram_bot.bot import RestaurantBot
from web_app.app import run_flask

def main():
    """Alkalmazás főbelépési pontja"""
    # Logging beállítása
    logger = setup_logging()
    logger.info("Application starting...")
    
    # Flask háttérszálon
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server started in background")
    
    # Bot főszálon (stabil)
    logger.info("Starting Telegram bot...")
    bot = RestaurantBot()
    bot.run()

if __name__ == "__main__":
    main()