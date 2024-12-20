from http.server import BaseHTTPRequestHandler
import json
import requests
from urllib.parse import parse_qs
from db import store_message, init_db

# Initialize database on module load
init_db()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Get content length to read the body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Parse form data
        params = parse_qs(post_data)
        
        # Extract Slack command parameters
        slack_params = {
            'command': params.get('command', [''])[0],
            'text': params.get('text', [''])[0],
            'response_url': params.get('response_url', [''])[0],
            'trigger_id': params.get('trigger_id', [''])[0],
            'user_id': params.get('user_id', [''])[0],
            'user_name': params.get('user_name', ['']),
            'team_id': params.get('team_id', [''])[0],
            'enterprise_id': params.get('enterprise_id', [''])[0],
            'channel_id': params.get('channel_id', [''])[0],
            'channel_name': params.get('channel_name', [''])[0],
            'api_app_id': params.get('api_app_id', [''])[0]
        }

        # Send immediate empty 200 response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'')

        # Store message in database
        store_message(
            slack_params['text'],
            slack_params['user_id'],
            slack_params['user_name'][0],  # user_name is a list
            slack_params['channel_id'],
            slack_params['channel_name']
        )

        # Send delayed response to response_url
        delayed_response = {
            'response_type': 'in_channel',
            'text': slack_params['text']
        }
        requests.post(
            slack_params['response_url'],
            json=delayed_response
        )
        return
