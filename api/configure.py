from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import os
from lib.slack import verify_slack_request
from lib.database import update_channel_mode, is_admin
from lib.types import ChannelMode


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Get content length to read the body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        # Verify request is from Slack only in production
        if os.getenv('VERCEL_ENV') == 'production':
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
