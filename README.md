# ETT Generic Notification Service (GNS)

A highly scalable, asynchronous, and pluggable microservice built in Python (Flask) for routing generic multi-channel notifications (Emails, SMS, Webhooks). Designed for containerized deployments with automatic template discovery and strict rate-limiting.

## 🚀 Features

- **Asynchronous Processing**: Integrated `ThreadPoolExecutor` ensures that API requests return immediately (within ~10ms) while I/O heavy tasks (like SMTP connections) run safely in the background.
- **Auto-Discovering Templates**: Uses Jinja2's AST to automatically parse HTML files dropped into the `templates/` folder. It detects missing variables dynamically—no hardcoding required.
- **Pluggable Channels**: Implements a standard Abstract Base Class (`NotificationChannel`), enabling effortless addition of SMS, WhatsApp, or Push notification strategies.
- **Automatic Retry & Backoff**: Email routines feature robust exponential backoff (retrying 3 times) to guarantee delivery against network hiccups.
- **Enterprise Rate-Limiting**: Powered by `flask-limiter` blocking volumetric spam to active endpoints.
- **Fully White-labeled**: Templates are driven gracefully via runtime payload configuration (Company Name, Action URLs, etc.).
- **Production-Ready**: Hosted securely under an unprivileged `appuser` utilizing `gunicorn` with horizontal thread scaling capabilities instead of standard WSGI.

---

## 🏗 System Architecture

The overarching system utilizes a standard Factory Pattern initialization mapping into multiple worker modules. 

```text
client 
  -> [ Gunicorn WSGI ] 
       -> [ Rate Limiter ]
          -> /send_notification (HTTP 202 Accepted)
             -> [ Thread Pool ] (Background Async)
                  -> NotificationChannel Router
                       -> EmailChannel (Validates Template -> Retries -> Connects SMTP)
                       -> SmsChannel (Stubbed for extension)
                       -> WebhookChannel (Stubbed for extension)
```

---

## 🛠 Prerequisites & Setup

Ensure you have **Podman** (or Docker) installed before proceeding.

### 1. Environment Variables
Create a `.env` file in the root directory (you can copy `sample.env` if present) with the following structure:

```ini
PORT=5000
FLASK_ENV=production

# Email SMTP Credentials
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
SMTP_AUTH_IDENT=your-email@example.com
SMTP_AUTH_PASSWORD=your_secure_password
SMTP_AUTH_NAME=YourCompany Name
```

### 2. Building & Running the Container
The service is containerized securely out of the box using `docker-compose`. 

```bash
# Build the images and start the container in detached mode
podman compose up -d --build

# View real-time container logs (useful for SMTP debugging)
podman logs -f ett_gns
```

The application will start hosting gracefully on `http://localhost:5000` (or whichever port mapping you established).

---

## 📡 API Reference

### 1. Healthcheck
Used for load balancers and container health checks.
```http
GET /health
```
**Response:** `200 OK`
```json
{
    "status": "healthy"
}
```

### 2. View Available Channels
```http
GET /channels
```
**Response:** `200 OK`
```json
{
    "channels": ["email", "sms", "webhook"]
}
```

### 3. Send Notification
Enqueues a message into the background thread pool parser. 
*Note: This route is strictly rate-limited at 10 requests per minute by default.*

```http
POST /send_notification
Content-Type: application/json
```
**Payload Body:**
```json
{
    "channel_name": "email",
    "recipient": "user@example.com",
    "subject": "Securing Your Account",
    "template_name": "password_reset.html",
    "data": {
        "user_name": "John Doe",
        "company_name": "Acme Corp",
        "reset_link": "https://dashboard.acmecorp.com/reset"
    }
}
```
**Responses:**
- `202 Accepted`: Job queued seamlessly (Returns a `notification_id`).
- `400 Bad Request`: Usually due to missing data keys required by the requested HTML template.
- `429 Too Many Requests`: Client surpassed the rate limiter ceiling.

---

## 🎨 Managing Templates

GNS heavily implements **Auto-Discovery**. To add a new email template:
1. Drop your `new_feature.html` file into the `/templates` folder.
2. Inside your HTML, mark dynamic variables with standard Jinja brackets: `{{ signature_name }}`.
3. **No code changes are needed!** GNS will instantly realize that `new_feature.html` requires `signature_name` and will begin validating incoming API payload `data` objects against it immediately. 

---

## 🔌 Extending Channels (e.g. SMS)

GNS adheres to the **Open-Closed Principle (SOLID)**. 

To add an SMS provider (like Twilio, AWS SNS):
1. Open `ett_gns_app/channels/sms_channel.py`.
2. Find the stubbed `def send(...)` function in the `SmsChannel` class.
3. Replace the `NotImplementedError` with your provider API execution code.
4. Restart the container. GNS automatically loops it into the `/channels` directory and route endpoints.
