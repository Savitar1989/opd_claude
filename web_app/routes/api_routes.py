# web_app/routes/api_routes.py
import json
import sqlite3
import logging
from typing import Dict, Optional
from flask import Blueprint, request, jsonify
from urllib.parse import unquote

from config.settings import notification_queue, DB_NAME
from database.db_manager import db
from utils.geocoding import optimize_route

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

def validate_telegram_data(init_data: str) -> Optional[Dict]:
    """Egyszerű dekódolás (HMAC ellenőrzés nélkül)."""
    try:
        data = {}
        for part in (init_data or "").split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                data[k] = v
        if "user" in data:
            return json.loads(unquote(data["user"]))
    except Exception as e:
        logger.error(f"validate_telegram_data error: {e}")
    return None

@api_bp.route("/orders")
def get_orders():
    """Összes aktív rendelés lekérése"""
    try:
        return jsonify(db.get_open_orders())
    except Exception as e:
        logger.error(f"api_orders error: {e}")
        return jsonify([])

@api_bp.route("/accept_order", methods=["POST"])
def accept_order():
    """Rendelés elfogadása"""
    try:
        data = request.json or {}
        order_id = int(data.get("order_id"))
        eta = int(data.get("estimated_time", 20))
        user = validate_telegram_data(data.get("initData", ""))
        
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        
        order = db.get_order_by_id(order_id)
        if not order or order["status"] != "pending":
            return jsonify({"ok": False, "error": "not_available"}), 400

        partner_name = ((user.get("first_name", "") + " " + user.get("last_name", ""))).strip()
        if not partner_name.strip():
            partner_name = str(user.get("id"))
        partner_username = user.get("username")

        db.update_order_status(order_id, "accepted",
                               partner_id=user.get("id"),
                               partner_name=partner_name,
                               partner_username=partner_username,
                               estimated_time=eta)

        # Értesítés az éttermi csoportnak
        try:
            partner_contact = f"@{partner_username}" if partner_username else partner_name
            text = (
                "🚚 **FUTÁR JELENTKEZETT!**\n\n"
                f"👤 **Futár:** {partner_name}\n"
                f"📱 **Kontakt:** {partner_contact}\n"
                f"⏱️ **Becsült érkezés:** {eta} perc\n"
                f"📋 **Rendelés ID:** #{order_id}\n"
            )
            notification_queue.put({"chat_id": order["group_id"], "text": text})
            logger.info(f"Accept notification queued for group {order['group_id']}")

        except Exception as e:
            logger.error(f"group notify fail (accept): {e}")

        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"api_accept_order error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.route("/pickup_order", methods=["POST"])
def pickup_order():
    """Rendelés felvétele"""
    try:
        data = request.json or {}
        order_id = int(data.get("order_id"))
        user = validate_telegram_data(data.get("initData", ""))
        
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        
        order = db.get_order_by_id(order_id)
        if not order or order["status"] != "accepted":
            return jsonify({"ok": False, "error": "not_accepted"}), 400

        db.update_order_status(order_id, "picked_up", partner_id=user.get("id"))
        
        # Értesítés a csoportnak
        try:
            partner_name = ((user.get("first_name", "") + " " + user.get("last_name", ""))).strip() or str(user.get("id"))
            partner_username = user.get("username")
            partner_contact = f"@{partner_username}" if partner_username else partner_name
            text = (
                "📦 **RENDELÉS FELVÉVE!**\n\n"
                f"👤 **Futár:** {partner_name}\n"
                f"📱 **Kontakt:** {partner_contact}\n"
                f"📋 **Rendelés ID:** #{order_id}\n"
            )
            notification_queue.put({"chat_id": order["group_id"], "text": text})
        except Exception as e:
            logger.error(f"group notify fail (pickup): {e}")

        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"api_pickup_order error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.route("/mark_delivered", methods=["POST"])
def mark_delivered():
    """Rendelés kiszállítottként jelölése"""
    try:
        data = request.json or {}
        order_id = int(data.get("order_id"))
        user = validate_telegram_data(data.get("initData", ""))
        
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        
        order = db.get_order_by_id(order_id)
        if not order or order["status"] != "picked_up":
            return jsonify({"ok": False, "error": "not_pickup"}), 400

        db.update_order_status(order_id, "delivered")

        # Értesítés csoportnak
        try:
            partner_name = ((user.get("first_name", "") + " " + user.get("last_name", ""))).strip() or str(user.get("id"))
            partner_username = user.get("username")
            partner_contact = f"@{partner_username}" if partner_username else partner_name
            text = (
                "✅ **RENDELÉS KISZÁLLÍTVA!**\n\n"
                f"👤 **Futár:** {partner_name}\n"
                f"📱 **Kontakt:** {partner_contact}\n"
                f"📋 **Rendelés ID:** #{order_id}\n"
            )
            notification_queue.put({"chat_id": order["group_id"], "text": text})
        except Exception as e:
            logger.error(f"group notify fail (delivered): {e}")

        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"api_mark_delivered error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.route("/orders_by_status")
def orders_by_status():
    """Rendelések státusz szerint"""
    try:
        status = (request.args.get("status") or "").strip()
        courier_id = request.args.get("courier_id", type=int)
        
        if not status:
            return jsonify([])
            
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        if status == "pending":
            cur.execute("""
                SELECT id, restaurant_name, restaurant_address, phone_number, order_details,
                       group_id, group_name, created_at, status
                FROM orders WHERE status='pending' ORDER BY created_at DESC
            """)
            rows = [dict(r) for r in cur.fetchall()]
        elif status in ("accepted", "picked_up", "delivered"):
            if not courier_id:
                conn.close()
                return jsonify({"ok": False, "error": "missing_courier"}), 400
            cur.execute("""
                SELECT id, restaurant_name, restaurant_address, phone_number, order_details,
                       group_id, group_name, created_at, status, estimated_time
                FROM orders
                WHERE status=? AND delivery_partner_id=?
                ORDER BY created_at DESC
            """, (status, courier_id))
            rows = [dict(r) for r in cur.fetchall()]
        else:
            rows = []
            
        conn.close()
        return jsonify(rows)
    except Exception as e:
        logger.error(f"api_orders_by_status error: {e}")
        return jsonify([]), 500

@api_bp.route("/my_orders", methods=["POST"])
def my_orders():
    """Saját rendelések lekérése"""
    try:
        data = request.json or {}
        user = validate_telegram_data(data.get("initData", ""))
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        
        status = data.get("status", "").strip()
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        if status not in ("accepted", "picked_up", "delivered"):
            return jsonify({"ok": True, "orders": []})
        
        cur.execute("""
            SELECT id, restaurant_name, restaurant_address, phone_number, order_details,
                   group_id, group_name, created_at, status, estimated_time
            FROM orders
            WHERE status=? AND delivery_partner_id=?
            ORDER BY created_at DESC
        """, (status, user["id"]))
        
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"ok": True, "orders": rows})
    except Exception as e:
        logger.error(f"api_my_orders error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@api_bp.route("/optimize_route", methods=["POST"])
def optimize_route_api():
    """Útvonal optimalizálás"""
    try:
        data = request.json or {}
        user = validate_telegram_data(data.get("initData", ""))
        if not user:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        
        # Felvett rendelések lekérése
        rows = db.get_partner_addresses(partner_id=user["id"], status="picked_up")
        addresses = [r["restaurant_address"] for r in rows if r.get("restaurant_address") and r["restaurant_address"].strip()]
        
        if not addresses:
            return jsonify({"ok": False, "error": "no_addresses"})
        
        # Útvonal optimalizálás
        optimized_addresses = optimize_route(addresses)

        return jsonify({
            "ok": True,
            "addresses": optimized_addresses,
            "count": len(optimized_addresses)
        })
        
    except Exception as e:
        logger.error(f"api_optimize_route error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
