# web_app/app.py
from flask import Flask, render_template_string
from flask_cors import CORS

from web_app.routes.api_routes import api_bp
from web_app.routes.admin_routes import admin_bp
from web_app.templates.templates import HTML_TEMPLATE
from database.db_manager import db

def create_app():
    """Flask alkalmazás létrehozása és konfigurálása"""
    app = Flask(__name__)
    CORS(app)
    
    # Blueprint-ek regisztrálása
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    @app.route("/")
    def index():
        """Főoldal - futár felület"""
        try:
            orders = db.get_open_orders()
            return render_template_string(HTML_TEMPLATE, orders=orders)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"index error: {e}")
            return "error", 500
    
    return app

def run_flask():
    """Flask alkalmazás futtatása"""
    from werkzeug.serving import WSGIRequestHandler
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
