from flask import Blueprint, request, jsonify
from ett_gns_app.gns_controller import GnsController

# Create a Blueprint for the notification routes
notification_bp = Blueprint('notifications', __name__)

# Initialize the notification service
gns_controller = GnsController()

@notification_bp.route("/", methods=["GET"])
def home():
    """
    Home endpoint for the service.
    """
    return jsonify({
        "message": "Welcome to the ETT Service!",
        "version": "v1.0.0"
    }), 200

@notification_bp.route("/send_notification", methods=["POST"])
def send_notification():
    """
    Endpoint to send a notification through a specified channel.
    """
    try:
        # Get JSON payload from request
        payload = request.get_json()
        # Extract required fields from payload
        channel_name = payload.get("channel_name")
        recipient = payload.get("recipient")
        subject = payload.get("subject")
        template_name = payload.get("template_name")
        data = payload.get("data", {})  # Optional dynamic data for templates

        # Send the notification
        gns_controller.send_notification(
            channel_name=channel_name,
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            data=data
        )

        # Return success response
        return jsonify({"message": "Notification sent successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@notification_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return jsonify({"status": "healthy"}), 200


@notification_bp.route("/send_universal_notification", methods=["POST"])
def send_notificationv1():
    """
    Universal endpoint to send email/notification using a template.
    
    Expected Payload:
    {
        "recipient": "user@example.com",
        "subject": "Welcome!",
        "template_name": "universal_template.html",
        "sender_name": "Oryne Notifications",
        "sender_email": "no-reply@oryne.com",
        "channel_name": "email",  # Optional
        "data": {
            "heading": "...",
            "user_name": "...",
            "body_message": "...",
            "dynamic_block": "<p>...</p>",
            "cta_url": "...",
            "cta_label": "...",
            "year": 2025
        }
    }
    """
    try:
        payload = request.get_json()

        # Required fields
        recipient = payload.get("recipient")
        subject = payload.get("subject")
        template_name = payload.get("template_name")

        if not recipient or not subject or not template_name:
            return jsonify({
                "error": "recipient, subject, and template_name are required"
            }), 400

        # Optional
        channel_name = payload.get("channel_name", "email")
        sender_name = payload.get("sender_name", "Oryne")
        sender_email = payload.get("sender_email", "no-reply@oryne.com")

        # Data block
        data = payload.get("data", {})
        data["sender_name"] = sender_name

        # Always allow template to know sender email if needed
        data["sender_email"] = sender_email

        # Send notification through controller
        gns_controller.send_notification(

            channel_name=channel_name, 
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            data=data,
        )

        return jsonify({
            "success": True,
            "detail": "Notification enqueued"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Error handlers
@notification_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": "The requested resource could not be found."}), 404

@notification_bp.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method Not Allowed", "message": "The method is not allowed for the requested URL."}), 405

def register_blueprints(app):
    app.register_blueprint(notification_bp, url_prefix='/v1')
