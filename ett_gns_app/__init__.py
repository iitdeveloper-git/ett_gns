from flask import Flask, jsonify
from ett_gns_app.gns_routes import register_blueprints
from ett_gns_app.utils.helpers.logger import setup_logger
from ett_gns_app.config import load_config
from ett_gns_app.gns_controller import GnsController
from ett_gns_app.limit import limiter
from flasgger import Swagger
import logging

def create_app():
    # Load configuration
    config = load_config()

    app = Flask(__name__)
    
    # Store config
    app.config['GNS_CONFIG'] = config

    # Set up logging
    logger = setup_logger()
    flask_logger = logging.getLogger('flask')
    flask_logger.handlers = logger.handlers
    flask_logger.setLevel(logger.level)
    
    # Initialize Rate Limiter
    limiter.init_app(app)

    # Initialize Controller and attach to extensions
    if not hasattr(app, 'extensions'):
        app.extensions = {}
    app.extensions['gns_controller'] = GnsController(config)
    
    # Register blueprints
    register_blueprints(app)

    # Swagger / API docs configuration
    swagger_config = {
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
    }

    swagger_template = {
        "info": {
            "title": "ETT GNS API",
            "description": "ETT Generic Notification Service - API Documentation",
            "version": "1.0.0",
        }
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        logger.warning("404 error: %s", e)
        return jsonify({"error": "Not Found", "message": "The requested resource could not be found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        logger.warning("405 error: %s", e)
        return jsonify({"error": "Method Not Allowed", "message": "The method is not allowed for the requested URL."}), 405

    @app.errorhandler(429)
    def ratelimit_handler(e):
        logger.warning("429 error: Too many requests")
        return jsonify({"error": "Too Many Requests", "message": str(e.description)}), 429

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("An unexpected error occurred: %s", str(e))
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

    return app
