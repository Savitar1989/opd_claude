# utils/url_shortener.py
import requests
import logging

logger = logging.getLogger(__name__)

def shorten_url(url: str) -> str:
    """
    Rövidíti a kapott URL-t TinyURL API-val.
    Ha nem sikerül, visszaadja az eredeti URL-t.
    """
    try:
        r = requests.get("https://tinyurl.com/api-create.php", params={"url": url}, timeout=5)
        if r.status_code == 200 and r.text.startswith("http"):
            return r.text.strip()
    except Exception as e:
        logger.error(f"URL rövidítés hiba: {e}")
    
    return url
