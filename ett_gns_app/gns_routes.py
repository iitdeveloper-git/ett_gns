from flask import Blueprint, request, jsonify, current_app
from ett_gns_app.limit import limiter

# Create a Blueprint for the notification routes
notification_bp = Blueprint('notifications', __name__)

@notification_bp.route("/", methods=["GET"])
def home():
    """
    Home - Welcome endpoint
    Returns service info and version.
    ---
    tags:
      - General
    responses:
      200:
        description: Service info
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Welcome to the ETT Service!"
            version:
              type: string
              example: "v1.0.0"
    """
    return jsonify({
        "message": "Welcome to the ETT Service!",
        "version": "v1.0.0"
    }), 200

@notification_bp.route("/channels", methods=["GET"])
def get_channels():
    """
    List available channels
    ---
    tags:
      - General
    responses:
      200:
        description: List of supported channels
        schema:
          type: object
          properties:
            channels:
              type: array
              items:
                type: string
    """
    gns_controller = current_app.extensions.get('gns_controller')
    channels = list(gns_controller.channels.keys()) if gns_controller else []
    return jsonify({"channels": channels}), 200


@notification_bp.route("/send_notification", methods=["POST"])
@limiter.limit("10 per minute")
def send_notification():
    """
    Send Notification
    Enqueues a notification through a specified channel.
    ---
    tags:
      - Notifications
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - channel_name
            - recipient
            - subject
            - template_name
          properties:
            channel_name:
              type: string
              description: "Channel to send through (e.g. 'email')"
              example: "email"
            recipient:
              type: string
              description: "Recipient email or contact info"
              example: "user@example.com"
            subject:
              type: string
              description: "Notification subject"
              example: "Welcome!"
            template_name:
              type: string
              description: "HTML template filename"
              example: "welcome_email.html"
            sync:
              type: boolean
              description: "Wait until execution finishes (true) or drop into async queue (false)."
              example: false
            data:
              type: object
              description: "Dynamic data for template rendering"
              example:
                user_name: "Ravi"
                welcome_message: "Welcome to the platform!"
                company_name: "Acme Corp"
                action_url: "https://dashboard.example.com"
    responses:
      200:
        description: Notification delivered successfully (if sync=true)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Notification delivered successfully"
            notification_id:
              type: string
      202:
        description: Notification queued successfully (if sync=false)
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Notification queued successfully"
            notification_id:
              type: string
      400:
        description: Bad request or validation error
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Internal Server Error
    """
    gns_controller = current_app.extensions.get('gns_controller')
    if not gns_controller:
        return jsonify({"error": "Controller not initialized"}), 500

    try:
        # Get JSON payload from request
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Invalid or missing JSON payload"}), 400
            
        # Extract required fields from payload
        channel_name = payload.get("channel_name")
        recipient = payload.get("recipient")
        subject = payload.get("subject")
        template_name = payload.get("template_name")
        data = payload.get("data", {})

        # Check if client wants synchronous delivery
        is_sync = payload.get("sync", True)  # Defaulting to True as requested to confirm delivery

        # Queue or send the notification
        notification_id = gns_controller.send_notification(
            channel_name=channel_name,
            recipient=recipient,
            subject=subject,
            template_name=template_name,
            data=data,
            sync=is_sync
        )

        if is_sync:
            return jsonify({
                "message": "Notification delivered successfully",
                "notification_id": notification_id
            }), 200
        else:
            return jsonify({
                "message": "Notification queued successfully",
                "notification_id": notification_id
            }), 202

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except NotImplementedError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

@notification_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health Check
    Verify the service is running.
    ---
    tags:
      - General
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: "healthy"
    """
    return jsonify({"status": "healthy"}), 200


def register_blueprints(app):
    app.register_blueprint(notification_bp)
