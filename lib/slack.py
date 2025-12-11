import os
import hmac
import hashlib
import requests
from datetime import datetime

def verify_slack_request(timestamp, body, signature):
    """Verify that the request actually came from Slack"""
    if abs(datetime.now().timestamp() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body}".encode('utf-8')
    my_signature = 'v0=' + hmac.new(
        os.getenv('SLACK_SIGNING_SECRET').encode('utf-8'),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


def send_direct_message(user_id, message):
    """Send a direct message to a Slack user
    
    Args:
        user_id (str): The Slack user ID to send the message to
        message (str): The message content to send
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    try:
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("SLACK_BOT_TOKEN")}'
            },
            json={
                'channel': user_id,
                'text': message
            }
        )
        
        result = response.json()
        return result.get('ok', False)
    except Exception as e:
        print(f"Error sending direct message: {e}")
        return False


def update_message_via_response_url(response_url, text, blocks=None, replace_original=True):
    """Update a Slack message using the response_url
    
    Args:
        response_url (str): The response_url from the Slack payload
        text (str): The new message text
        blocks (list, optional): The new message blocks
        replace_original (bool): Whether to replace the original message
        
    Returns:
        bool: True if message was updated successfully, False otherwise
    """
    try:
        payload = {
            'replace_original': replace_original,
            'text': text
        }
        if blocks:
            payload['blocks'] = blocks
            
        response = requests.post(
            response_url,
            headers={'Content-Type': 'application/json'},
            json=payload
        )
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error updating message via response_url: {e}")
        return False

