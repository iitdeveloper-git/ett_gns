# run.py
from ett_gns_app import create_app

# Create the Flask application
app = create_app()
if __name__ == "__main__":
    import os
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    # Run the application locally
    app.run(debug=debug_mode, host="0.0.0.0")
