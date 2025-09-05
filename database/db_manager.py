# database/db_manager.py
import sqlite3
import logging
from typing import Dict, List, Optional
from config.settings import DB_NAME

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self) -> None:
        self.init_db()
    
    def init_db(self) -> None:
        """Adatbázis inicializálása és táblák létrehozása"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_name TEXT NOT NULL,            -- csoport neve
                restaurant_address TEXT NOT NULL,         -- Cím
                phone_number TEXT,                        -- Telefonszám
                order_details TEXT NOT NULL,              -- Megjegyzés
                group_id INTEGER NOT NULL,
                group_name TEXT,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',            -- pending|accepted|picked_up|delivered
                delivery_partner_id INTEGER,
                delivery_partner_name TEXT,
                delivery_partner_username TEXT,
                estimated_time INTEGER,
                accepted_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS groups(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        try:
            cur.execute("PRAGMA table_info(orders)")
            cols = [r[1] for r in cur.fetchall()]

            if "picked_up_at" not in cols:
                cur.execute("ALTER TABLE orders ADD COLUMN picked_up_at TIMESTAMP")
            if "delivered_at" not in cols:
                cur.execute("ALTER TABLE orders ADD COLUMN delivered_at TIMESTAMP")

            # opcionális, de hasznos indexek:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_delivered_at ON orders(delivered_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_partner ON orders(delivery_partner_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_group ON orders(group_name)")
            
        except Exception as e:
            logger.error(f'DB migrate error: {e}')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")

    def register_group(self, group_id: int, group_name: str) -> None:
        """Csoport regisztrálása"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO groups(id, name) VALUES (?,?)", (group_id, group_name))
        conn.commit()
        conn.close()

    def save_order(self, item: Dict) -> int:
        """Új rendelés mentése"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders
            (restaurant_name, restaurant_address, phone_number, order_details, group_id, group_name, message_id)
            VALUES (?,?,?,?,?,?,?)
        """, (
            item.get("restaurant_name",""),
            item.get("restaurant_address",""),
            item.get("phone_number",""),
            item.get("order_details",""),
            item.get("group_id"),
            item.get("group_name"),
            item.get("message_id"),
        ))
        oid = cur.lastrowid
        conn.commit()
        conn.close()
        return oid

    def get_open_orders(self) -> List[Dict]:
        """Aktív listához: pending + accepted + picked_up (hogy felvétel után is lehessen 'Kiszállítva'-ra zárni)"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, restaurant_name, restaurant_address, phone_number, order_details,
                   group_id, group_name, created_at, status,
                   delivery_partner_id, estimated_time
            FROM orders
            WHERE status IN ('pending','accepted','picked_up')
            ORDER BY created_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_order_by_id(self, order_id: int) -> Optional[Dict]:
        """Rendelés lekérése ID alapján"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_order_status(self, order_id: int, status: str,
                            partner_id: int | None = None,
                            partner_name: str | None = None,
                            partner_username: str | None = None,
                            estimated_time: int | None = None) -> None:
        """Rendelés státusz frissítése"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            UPDATE orders
               SET status = ?,
                   delivery_partner_id = COALESCE(?, delivery_partner_id),
                   delivery_partner_name = COALESCE(?, delivery_partner_name),
                   delivery_partner_username = COALESCE(?, delivery_partner_username),
                   estimated_time = COALESCE(?, estimated_time),
                   accepted_at = CASE WHEN ?='accepted' THEN CURRENT_TIMESTAMP ELSE accepted_at END,
                   picked_up_at = CASE WHEN ?='picked_up' THEN CURRENT_TIMESTAMP ELSE picked_up_at END,
                   delivered_at = CASE WHEN ?='delivered' THEN CURRENT_TIMESTAMP ELSE delivered_at END
             WHERE id = ?
        """, (
            status,
            partner_id, partner_name, partner_username, estimated_time,
            status,  # accepted
            status,  # picked_up
            status,  # delivered
            order_id
        ))
        conn.commit()
        conn.close()

    def get_partner_addresses(self, partner_id: int, status: str) -> List[Dict]:
        """Futár adott státuszú rendeléseinek címeit adja vissza"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, restaurant_address, group_name
            FROM orders
            WHERE delivery_partner_id = ? AND status = ?
            ORDER BY created_at
        """, (partner_id, status))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_partner_order_count(self, partner_id: int, status: str = None) -> int:
        """Futár rendeléseinek számát adja vissza (opcionálisan státusz szerint szűrve)"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        
        if status:
            cur.execute("SELECT COUNT(*) FROM orders WHERE delivery_partner_id = ? AND status = ?", 
                       (partner_id, status))
        else:
            cur.execute("SELECT COUNT(*) FROM orders WHERE delivery_partner_id = ?", 
                       (partner_id,))
        
        count = cur.fetchone()[0]
        conn.close()
        return count

    def get_weekly_courier_stats(self) -> List[Dict]:
        """Heti futár statisztikák"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT
              strftime('%Y-%W', delivered_at) AS week,
              delivery_partner_id,
              COALESCE(delivery_partner_name, '') AS courier_name,
              COUNT(*) AS cnt,
              ROUND(AVG((julianday(delivered_at) - julianday(accepted_at)) * 24 * 60), 1) AS avg_min
            FROM orders
            WHERE delivered_at IS NOT NULL AND accepted_at IS NOT NULL
            GROUP BY delivery_partner_id, week
            ORDER BY week DESC, cnt DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_weekly_restaurant_stats(self) -> List[Dict]:
        """Heti étterem statisztikák"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT
              strftime('%Y-%W', delivered_at) AS week,
              group_name,
              COUNT(*) AS cnt,
              ROUND(AVG((julianday(delivered_at) - julianday(accepted_at)) * 24 * 60), 1) AS avg_min
            FROM orders
            WHERE delivered_at IS NOT NULL AND accepted_at IS NOT NULL
            GROUP BY group_name, week
            ORDER BY week DESC, cnt DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_recent_deliveries(self, limit: int = 500) -> List[Dict]:
        """Legutóbbi kézbesítések részletes listája"""
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT
              delivered_at,
              delivery_partner_id,
              COALESCE(delivery_partner_name, '') AS courier_name,
              group_name,
              restaurant_address,
              ROUND((julianday(delivered_at) - julianday(accepted_at)) * 24 * 60, 1) AS min
            FROM orders
            WHERE delivered_at IS NOT NULL AND accepted_at IS NOT NULL
            ORDER BY delivered_at DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

# Globális adatbázis példány
db = DatabaseManager()
