#!/usr/bin/env python3
"""
Example usage of the ETT GNS API for sending notifications.
"""
import json
import requests
import time
import sys


class ETTGNSClient:
    """Simple client for ETT GNS API."""
    
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
        
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ETT-GNS-Client/1.0'
        })
    
    def send_notification(self, channel_name, recipient, subject, template_name, data=None):
        """Send a notification."""
        payload = {
            'channel_name': channel_name,
            'recipient': recipient,
            'subject': subject,
            'template_name': template_name,
            'data': data or {}
        }
        
        response = self.session.post(
            f'{self.base_url}/api/v1/send_notification',
            json=payload
        )
        
        return response
    
    def get_templates(self):
        """Get available templates."""
        response = self.session.get(f'{self.base_url}/api/v1/templates')
        return response
    
    def health_check(self):
        """Check service health."""
        response = self.session.get(f'{self.base_url}/health')
        return response


def example_welcome_email():
    """Example: Send a welcome email."""
    print("📧 Example: Sending Welcome Email")
    
    # Initialize client
    client = ETTGNSClient('http://localhost:5000')
    
    # Send welcome email
    response = client.send_notification(
        channel_name='email',
        recipient='user@example.com',
        subject='Welcome to Our Platform!',
        template_name='welcome_email.html',
        data={
            'user_name': 'John Doe',
            'welcome_message': 'Thank you for joining our amazing platform! We\'re excited to have you aboard.'
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Request ID: {result.get('request_id')}")
        print(f"   Processing time: {result.get('processing_time_ms')}ms")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   Error: {response.json()}")


def example_password_reset():
    """Example: Send a password reset email."""
    print("🔐 Example: Sending Password Reset Email")
    
    client = ETTGNSClient('http://localhost:5000')
    
    response = client.send_notification(
        channel_name='email',
        recipient='user@example.com',
        subject='Password Reset Request',
        template_name='password_reset.html',
        data={
            'user_name': 'Jane Smith',
            'reset_link': 'https://yourapp.com/reset-password?token=abc123xyz789'
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Request ID: {result.get('request_id')}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   Error: {response.json()}")


def example_batch_notifications():
    """Example: Send multiple notifications."""
    print("📬 Example: Sending Batch Notifications")
    
    client = ETTGNSClient('http://localhost:5000')
    
    users = [
        {'email': 'user1@example.com', 'name': 'Alice Johnson'},
        {'email': 'user2@example.com', 'name': 'Bob Wilson'},
        {'email': 'user3@example.com', 'name': 'Carol Davis'},
    ]
    
    success_count = 0
    
    for user in users:
        try:
            response = client.send_notification(
                channel_name='email',
                recipient=user['email'],
                subject='Monthly Newsletter',
                template_name='welcome_email.html',
                data={
                    'user_name': user['name'],
                    'welcome_message': 'Check out our latest updates and features!'
                }
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"  ✅ Sent to {user['name']}")
            else:
                print(f"  ❌ Failed for {user['name']}: {response.json().get('message')}")
            
            # Be nice to the rate limiter
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  ❌ Error for {user['name']}: {e}")
    
    print(f"📊 Batch complete: {success_count}/{len(users)} notifications sent")


def example_error_handling():
    """Example: Error handling and validation."""
    print("⚠️  Example: Error Handling")
    
    client = ETTGNSClient('http://localhost:5000')
    
    # Test cases with different types of errors
    test_cases = [
        {
            'name': 'Invalid Email',
            'payload': {
                'channel_name': 'email',
                'recipient': 'invalid-email',  # Invalid format
                'subject': 'Test',
                'template_name': 'welcome_email.html',
                'data': {'user_name': 'Test User', 'welcome_message': 'Hello'}
            }
        },
        {
            'name': 'Missing Required Field',
            'payload': {
                'channel_name': 'email',
                'recipient': 'test@example.com',
                # Missing subject
                'template_name': 'welcome_email.html',
                'data': {'user_name': 'Test User', 'welcome_message': 'Hello'}
            }
        },
        {
            'name': 'Invalid Template',
            'payload': {
                'channel_name': 'email',
                'recipient': 'test@example.com',
                'subject': 'Test',
                'template_name': 'nonexistent.html',  # Doesn't exist
                'data': {'user_name': 'Test User'}
            }
        }
    ]
    
    for test_case in test_cases:
        try:
            response = client.session.post(
                f'{client.base_url}/api/v1/send_notification',
                json=test_case['payload']
            )
            
            print(f"  Test: {test_case['name']}")
            if response.status_code == 400:
                error_data = response.json()
                print(f"    ✅ Expected error: {error_data.get('error')}")
                print(f"    Message: {error_data.get('message')}")
            else:
                print(f"    ❓ Unexpected response: {response.status_code}")
            
        except Exception as e:
            print(f"    ❌ Exception: {e}")


def example_health_and_templates():
    """Example: Health check and template listing."""
    print("🏥 Example: Health Check and Templates")
    
    client = ETTGNSClient('http://localhost:5000')
    
    # Health check
    health_response = client.health_check()
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"  ✅ Service Status: {health_data.get('status')}")
        print(f"  📊 Response Time: {health_data.get('response_time_ms')}ms")
        
        # Show individual checks
        checks = health_data.get('checks', {})
        for check_name, check_data in checks.items():
            status = check_data.get('status', 'unknown')
            emoji = '✅' if status == 'healthy' else '⚠️' if status == 'degraded' else '❌'
            print(f"    {emoji} {check_name}: {status}")
    else:
        print(f"  ❌ Health check failed: {health_response.status_code}")
    
    # List templates
    templates_response = client.get_templates()
    if templates_response.status_code == 200:
        templates_data = templates_response.json()
        print(f"  📋 Available Templates ({templates_data.get('total_count', 0)}):")
        
        for template in templates_data.get('templates', []):
            print(f"    • {template['name']}")
            print(f"      Required: {', '.join(template['required_variables'])}")
    else:
        print(f"  ❌ Templates request failed: {templates_response.status_code}")


def example_rate_limiting():
    """Example: Rate limiting demonstration."""
    print("🚦 Example: Rate Limiting")
    
    client = ETTGNSClient('http://localhost:5000')
    
    print("  Sending requests rapidly to test rate limiting...")
    
    for i in range(5):
        try:
            response = client.send_notification(
                channel_name='email',
                recipient='test@example.com',
                subject=f'Test Email #{i+1}',
                template_name='welcome_email.html',
                data={
                    'user_name': f'Test User {i+1}',
                    'welcome_message': 'This is a rate limit test'
                }
            )
            
            if response.status_code == 200:
                print(f"    ✅ Request {i+1}: Success")
            elif response.status_code == 429:
                print(f"    🚦 Request {i+1}: Rate limited")
                # Check rate limit headers
                headers = response.headers
                print(f"       Remaining: {headers.get('X-RateLimit-Remaining', 'N/A')}")
                print(f"       Reset: {headers.get('X-RateLimit-Reset', 'N/A')}")
                print(f"       Retry After: {headers.get('Retry-After', 'N/A')}s")
                break
            else:
                print(f"    ❌ Request {i+1}: Error {response.status_code}")
            
            # Small delay between requests
            time.sleep(0.1)
            
        except Exception as e:
            print(f"    ❌ Request {i+1}: Exception - {e}")


def main():
    """Run all examples."""
    print("🚀 ETT GNS API Examples")
    print("=" * 50)
    
    try:
        # Check if service is running
        client = ETTGNSClient('http://localhost:5000')
        health_response = client.health_check()
        
        if health_response.status_code not in [200, 503]:
            print("❌ Service appears to be down. Please start the ETT GNS service first.")
            print("   Run: docker-compose up -d")
            sys.exit(1)
        
        # Run examples
        examples = [
            example_health_and_templates,
            example_welcome_email,
            example_password_reset,
            example_error_handling,
            example_batch_notifications,
            example_rate_limiting,
        ]
        
        for i, example_func in enumerate(examples, 1):
            print(f"\n{i}. Running {example_func.__name__}...")
            try:
                example_func()
            except Exception as e:
                print(f"   ❌ Example failed: {e}")
            
            if i < len(examples):
                print("   Waiting 2 seconds before next example...")
                time.sleep(2)
        
        print("\n🎉 All examples completed!")
        print("\nNext steps:")
        print("- Modify the examples for your use case")
        print("- Check the logs: docker-compose logs ett_gns_service")
        print("- View API docs: http://localhost:5000/api/v1/docs")
        
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Failed to run examples: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()