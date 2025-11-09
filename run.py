# run.py
from ett_gns_app import create_app

# Create the Flask application
app = create_app()
if __name__ == "__main__":
    # Run the application
    app.run(debug=True)  # Set debug to True for development; change to False in production
