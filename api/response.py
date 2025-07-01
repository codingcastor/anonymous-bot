from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
import os
import json
from lib.slack import verify_slack_request, send_direct_message


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Get content length to read the body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        # Handle interactive component interactions (button clicks)
        self.handle_interactive_component(post_data)

    def handle_interactive_component(self, post_data):
        """Handle interactive component interactions (button clicks)"""
        # Parse the payload
        params = parse_qs(post_data)
        payload_str = params.get('payload', [''])[0]
        
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        # Verify request is from Slack only in production
        if os.getenv('VERCEL_ENV') == 'production':
            timestamp = self.headers.get('X-Slack-Request-Timestamp')
            signature = self.headers.get('X-Slack-Signature')

            if not timestamp or not signature or not verify_slack_request(timestamp, post_data, signature):
                self.send_response(401)
                self.end_headers()
                return

        # Handle the "Go" button click
        if (payload.get('type') == 'block_actions' and 
            len(payload.get('actions', [])) > 0 and 
            payload['actions'][0].get('action_id') == 'go_button'):
            
            # Get the original poster's user ID from the button value
            original_poster_id = payload['actions'][0].get('value')
            # Get the user who clicked the button
            button_clicker_id = payload.get('user', {}).get('id')
            
            if original_poster_id and button_clicker_id:
                # Send direct message to the original poster
                message = f"Hey! Someone wants you to come play! 🎮"
                send_direct_message(original_poster_id, message)
                
                # Send confirmation to the button clicker
                response = {
                    'response_type': 'ephemeral',
                    'text': "✅ Message envoyé !"
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(response), 'utf-8'))
                return

        # Default response for unhandled interactions
        self.send_response(200)
        self.end_headers() 