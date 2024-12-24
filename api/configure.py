from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import os
import psycopg2
from datetime import datetime
import hmac
import hashlib
from enum import Enum


class ChannelMode(Enum):
    RESTRICTED = "RESTRICTED"
    FREE = "FREE"


def get_db_connection():
    """Get a PostgreSQL database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))


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


def is_admin(user_id):
    """Check if a user is an admin"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT EXISTS(SELECT 1 FROM admin_users WHERE user_id = %s)', (user_id,))
    is_admin = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return is_admin


def update_channel_mode(channel_id, mode):
    """Update or insert channel configuration"""
    if not isinstance(mode, ChannelMode):
        raise ValueError("Mode must be a ChannelMode enum value")

    conn = get_db_connection()
    cur = conn.cursor()

    # Using upsert (INSERT ... ON CONFLICT DO UPDATE)
    cur.execute('''
        INSERT INTO channel_configs (channel_id, mode, updated_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (channel_id) 
        DO UPDATE SET mode = EXCLUDED.mode, updated_at = EXCLUDED.updated_at
    ''', (channel_id, mode.value, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Get content length to read the body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        # Verify request is from Slack
        timestamp = self.headers.get('X-Slack-Request-Timestamp')
        signature = self.headers.get('X-Slack-Signature')

        if not timestamp or not signature or not verify_slack_request(timestamp, post_data, signature):
            self.send_response(401)
            self.end_headers()
            return

        # Parse form data
        params = parse_qs(post_data)
        slack_params = {
            'command': params.get('command', [''])[0],
            'text': params.get('text', [''])[0].upper(),  # Convert mode to uppercase
            'response_url': params.get('response_url', [''])[0],
            'channel_id': params.get('channel_id', [''])[0],
            'channel_name': params.get('channel_name', [''])[0],
            'user_id': params.get('user_id', [''])[0],
        }

        # Check if user is admin
        if not is_admin(slack_params['user_id']):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'response_type': 'ephemeral',
                'text': "Sorry, only administrators can configure channel modes."
            }
            self.wfile.write(bytes(str(response), 'utf-8'))
            return

        # Validate the mode
        try:
            mode = ChannelMode(slack_params['text'])
        except ValueError:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'response_type': 'ephemeral',
                'text': f"Invalid mode. Please use one of: {', '.join([mode.value for mode in ChannelMode])}"
            }
            self.wfile.write(bytes(str(response), 'utf-8'))
            return

        # Update channel configuration
        try:
            update_channel_mode(slack_params['channel_id'], mode)
        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'response_type': 'ephemeral',
                'text': f"Error updating channel mode: {str(e)}"
            }
            self.wfile.write(bytes(str(response), 'utf-8'))
            return

        # Send success response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'response_type': 'in_channel',
            'text': f"Channel mode has been set to: {mode.value}"
        }
        self.wfile.write(bytes(str(response), 'utf-8'))
