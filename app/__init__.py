import os

from flask import Flask, jsonify, request

from app.db import close_db, init_db


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "centro_culturale_aurora.sqlite3"),
        SEED_DEMO=True,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    from app.routes import api

    app.register_blueprint(api)

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Risorsa non trovata."}), 404
        return "Pagina non trovata.", 404

    with app.app_context():
        init_db()

    return app
