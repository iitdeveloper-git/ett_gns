"""ETT Generic Notification Service.

The production entry point is :mod:`ett_gns_app.main`. ``create_legacy_app`` keeps
the historical Flask prototype importable during the migration without making
Flask a prerequisite for the FastAPI application.
"""

from typing import Any


def create_legacy_app() -> Any:
    from flask import Flask, jsonify
    from flasgger import Swagger

    from ett_gns_app.config import load_config
    from ett_gns_app.gns_controller import GnsController
    from ett_gns_app.gns_routes import register_blueprints
    from ett_gns_app.limit import limiter
    from ett_gns_app.utils.helpers.logger import setup_logger

    config = load_config()
    app = Flask(__name__)
    app.config["GNS_CONFIG"] = config
    setup_logger()
    limiter.init_app(app)
    app.extensions["gns_controller"] = GnsController(config)
    register_blueprints(app)
    Swagger(
        app,
        config={
            "headers": [],
            "specs": [
                {
                    "endpoint": "apispec",
                    "route": "/apispec.json",
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/docs",
        },
        template={"info": {"title": "ETT GNS Legacy API", "version": "1.0.0"}},
    )

    @app.errorhandler(404)
    def not_found(error: Exception):
        return jsonify({"error": "Not Found", "message": str(error)}), 404

    return app


# Backward-compatible name for callers that explicitly use the Flask prototype.
create_app = create_legacy_app
