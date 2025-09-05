# telegram_bot/bot.py
import asyncio
import logging
from typing import Dict
from queue import Queue, Empty

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config.settings import BOT_TOKEN, WEBAPP_URL, notification_queue
from database.db_manager import db

logger = logging.getLogger(__name__)

class RestaurantBot:
    def __init__(self) -> None:
        self.app = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Event handlerek beállítása"""
        app = self.app
        app.add_handler(CommandHandler("start", self.start_cmd))
        app.add_handler(CommandHandler("help", self.help_cmd))
        app.add_handler(CommandHandler("register", self.register_group))
        # csak csoportban figyelünk szövegre
        app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, self.handle_group_message))

        # értesítési queue ürítése időzítővel
        if app.job_queue:
            app.job_queue.run_repeating(self.process_notifications, interval=3)

    async def process_notifications(self, context: ContextTypes.DEFAULT_TYPE):
        """Értesítések feldolgozása a queue-ból"""
        processed_count = 0
        max_per_batch = 5

        while processed_count < max_per_batch:
            try:
                item = notification_queue.get_nowait()
                processed_count += 1
            except Empty:
                break

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await context.bot.send_message(
                        chat_id=item["chat_id"],
                        text=item.get("text", ""),
                        parse_mode="Markdown"
                    )
                    logger.info(f"Notifications sent successfully to {item['chat_id']}")
                    break 

                except Exception as e:
                    logger.error(f"Failed to send notification (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)  # 1 sec várakozás újrapróbálás előtt
                    else:
                        logger.error(f"Final failure sending notification to {item['chat_id']}: {item.get('text', '')[:50]}...")

    def send_notification(self, chat_id: int, text: str):
        """Értesítés hozzáadása a sorhoz megfelelő formázással"""
        try:
            # Ellenőrzi hogy a text nem üres és a chat_id érvényes
            if not text or not chat_id:
                logger.warning(f"Invalid notification: chat_id={chat_id}, text='{text[:50] if text else 'None'}'")
                return
                
            notification_queue.put({
                "chat_id": chat_id, 
                "text": text
            })
            logger.info(f"Notification queued for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error queuing notification: {e}")

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start parancs kezelése"""
        user = update.effective_user
        if update.effective_chat.type == "private":
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚚 Elérhető rendelések", web_app=WebAppInfo(url=f"{WEBAPP_URL}"))],
            ])
            await update.message.reply_text(
                f"Üdv, {user.first_name}!\nNyisd meg a futár felületet:",
                reply_markup=kb
            )
        else:
            await update.message.reply_text(
                "Használd a /register parancsot a csoport regisztrálásához.\n"
                "Rendelés formátum:\n"
                "Cím: ...\nTelefonszám: ...\nMegjegyzés: ..."
            )

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help parancs kezelése"""
        await update.message.reply_text(
            "Rendelés formátum (csoportban):\n"
            "```\nCím: Budapest, Példa utca 1.\nTelefonszám: +36301234567\nMegjegyzés: kp / kártya / megjegyzés\n```",
            parse_mode="Markdown"
        )

    async def register_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Csoport regisztrálása"""
        if update.effective_chat.type not in ("group", "supergroup"):
            await update.message.reply_text("Ezt a parancsot csoportban használd.")
            return
        
        gid = update.effective_chat.id
        gname = update.effective_chat.title or "Ismeretlen csoport"
        db.register_group(gid, gname)
        await update.message.reply_text(f"✅ A '{gname}' csoport regisztrálva.")

    def parse_order_message(self, text: str) -> Dict | None:
        """
        STRICT formátum:
        Cím: <cím>
        Telefonszám: <telefon>
        Megjegyzés: <megjegyzés>
        """
        lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
        info: Dict[str, str] = {}

        def after_colon(s: str) -> str:
            return s.split(":", 1)[1].strip() if ":" in s else ""

        for ln in lines:
            low = ln.lower()
            if low.startswith("cím:") or low.startswith("cim:"):
                info["address"] = after_colon(ln)
            elif low.startswith("telefonszám:") or low.startswith("telefonszam:") or low.startswith("telefon:"):
                info["phone"] = after_colon(ln)
            elif low.startswith("megjegyzés:") or low.startswith("megjegyzes:"):
                info["details"] = after_colon(ln)

        if info.get("address"):
            info.setdefault("phone", "")
            info.setdefault("details", "")
            return info
        return None

    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Csoport üzenetek kezelése"""
        # csak csoportban
        if update.effective_chat.type not in ("group", "supergroup"):
            return
        
        parsed = self.parse_order_message(update.message.text or "")
        if not parsed:
            return
        
        gid = update.effective_chat.id
        gname = update.effective_chat.title or "Ismeretlen"
        
        item = {
            "restaurant_name": gname,                 # étterem = csoport neve
            "restaurant_address": parsed["address"],  # Cím
            "phone_number": parsed.get("phone", ""),
            "order_details": parsed.get("details", ""),
            "group_id": gid,
            "group_name": gname,
            "message_id": update.message.message_id
        }
        
        order_id = db.save_order(item)
        await update.message.reply_text(
            "✅ Rendelés rögzítve.\n\n"
            f"📍 Cím: {item['restaurant_address']}\n"
            f"📞 Telefon: {item['phone_number'] or '—'}\n"
            f"📝 Megjegyzés: {item['order_details']}\n"
            f"ID: #{order_id}"
        )

    def run(self) -> None:
        """Bot indítása"""
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
