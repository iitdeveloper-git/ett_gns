from flask import Flask, jsonify
from ett_gns_app.gns_routes import register_blueprints  # Adjust import as necessary
from ett_gns_app.utils.helpers.logger import setup_logger
import logging


def create_app():
    app = Flask(__name__)
    
    # Set up logging
    logger = setup_logger()
    # Set Flask's logger to use your logger
    flask_logger = logging.getLogger('flask')
    flask_logger.handlers = logger.handlers  # Share handlers
    flask_logger.setLevel(logger.level)  # Set level
    
    # Register blueprints
    register_blueprints(app)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        logger.warning("404 error: %s", e)
        return jsonify({"error": "Not Found", "message": "The requested resource could not be found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        logger.warning("405 error: %s", e)
        return jsonify({"error": "Method Not Allowed", "message": "The method is not allowed for the requested URL."}), 405

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("An unexpected error occurred: %s", str(e))
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

    return app
