# web_app/routes/admin_routes.py
import logging
from flask import Blueprint, request, render_template_string, jsonify

from config.settings import ADMIN_USER_IDS
from database.db_manager import db
from web_app.templates.templates import ADMIN_HTML
from web_app.routes.api_routes import validate_telegram_data

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin")
def admin_page():
    """Admin statisztika oldal"""
    init_data = request.args.get('init_data', '')
    user = validate_telegram_data(init_data)
    
    if not user or user.get("id") not in ADMIN_USER_IDS:
        return "🚫 Hozzáférés megtagadva", 403
    
    try:
        weekly_courier = db.get_weekly_courier_stats()
        weekly_restaurant = db.get_weekly_restaurant_stats()
        deliveries = db.get_recent_deliveries(500)

        return render_template_string(ADMIN_HTML,
                                      weekly_courier=weekly_courier,
                                      weekly_restaurant=weekly_restaurant,
                                      deliveries=deliveries)
    except Exception as e:
        logger.error(f"admin_page error: {e}")
        return "admin error", 500

@admin_bp.route("/api/is_admin", methods=["POST"])
def is_admin():
    """Admin jogosultság ellenőrzése"""
    try:
        data = request.json or {}
        user = validate_telegram_data(data.get("initData", ""))
        if not user:
            return jsonify({"ok": False, "admin": False}), 401
        
        return jsonify({
            "ok": True,
            "admin": user.get("id") in ADMIN_USER_IDS
        })
    except Exception as e:
        logger.error(f"api_is_admin error: {e}")
        return jsonify({"ok": False, "admin": False}), 500
