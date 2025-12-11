from http.server import BaseHTTPRequestHandler
import requests
import re
from urllib.parse import parse_qs
import os
import json
from datetime import datetime
from lib.database import store_message, get_channel_mode, store_inappropriate_message, get_or_assign_pseudo, get_user_by_pseudo, get_known_pseudos
from lib.slack import verify_slack_request, send_direct_message
from lib.openai import generate_response
from lib.types import ChannelMode


def is_april_fools():
    """Check if today is April 1st"""
    today = datetime.now()
    return today.month == 4 and today.day == 1

# Special channel ID for BMT
# It's a WIP feature that add a button to notify the original poster of a "BMT ?" or "+1" message
# It doesn't work because the `send_direct_message` seems to fail in this case
# BMT channel
#SPECIAL_CHANNEL_ID = "C040N4UB458"
# raph's channel
SPECIAL_CHANNEL_ID = "D06TJMZ7N7N"

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
        # Extract Slack command parameters
        slack_params = {
            'command': params.get('command', [''])[0],
            'text': params.get('text', [''])[0],
            'response_url': params.get('response_url', [''])[0],
            'trigger_id': params.get('trigger_id', [''])[0],
            'user_id': params.get('user_id', [''])[0],
            'user_name': params.get('user_name', [''])[0],
            'team_id': params.get('team_id', [''])[0],
            'enterprise_id': params.get('enterprise_id', [''])[0],
            'channel_id': params.get('channel_id', [''])[0],
            'channel_name': params.get('channel_name', [''])[0],
            'api_app_id': params.get('api_app_id', [''])[0]
        }

        # Special handling for the BMT channel
        if slack_params['channel_id'] == SPECIAL_CHANNEL_ID:
            self.handle_special_channel(slack_params)
            return

        # Get channel mode and prepare message text
        channel_mode = get_channel_mode(slack_params['channel_id'])
        
        # Check if channel mode is enabled
        if channel_mode not in (ChannelMode.FREE, ChannelMode.RESTRICTED):
            response = {
                'response_type': 'ephemeral',
                'text': "❌ Ce bot n'est pas activé dans ce canal. Veuillez contacter l'administrateur de votre espace de travail si vous pensez qu'il s'agit d'une erreur."
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(str(response), 'utf-8'))
            return

        message_text = slack_params['text']
        stored_message_text = message_text
        if slack_params['channel_name'] == 'directmessage':
            stored_message_text = '<REDACTED>'

        # For restricted channels, check message appropriateness
        if channel_mode == ChannelMode.RESTRICTED:
            result = generate_response(message_text)
            if result.strip() == "1":  # Message is inappropriate
                # Store the inappropriate message
                store_inappropriate_message(
                    message_text,
                    slack_params['channel_id'],
                    slack_params['channel_name']
                )
                
                delayed_response = {
                    'response_type': 'ephemeral',
                    'text': "Désolé, ce canal est en mode restreint et ton message a été identifié comme inapproprié, il ne sera pas posté."
                }
                # Send immediate empty 200 response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(str(delayed_response), 'utf-8'))
                return

        # Store message in database
        store_message(
            stored_message_text,
            slack_params['user_id'],
            slack_params['channel_id'],
            slack_params['channel_name'],
            slack_params['response_url']
        )

        # Get pseudo for the user
        pseudo = get_or_assign_pseudo(slack_params['user_id'], slack_params['channel_id'])

        # April Fools' Day easter egg: use real username and add fish emoji
        april_fools = is_april_fools()
        display_name = slack_params['user_name'] if april_fools else pseudo
        message_suffix = " 🐟" if april_fools else ""

        # Detect @Pseudo mentions and notify users
        mentioned_pseudos = re.findall(r'@(\w+)', message_text)
        for mentioned_pseudo in mentioned_pseudos:
            # Look up the user who owns this pseudo (case-insensitive match)
            for known_pseudo in get_known_pseudos():
                if known_pseudo.lower() == mentioned_pseudo.lower():
                    target_user_id = get_user_by_pseudo(known_pseudo, slack_params['channel_id'])
                    if target_user_id and target_user_id != slack_params['user_id']:
                        res = send_direct_message(
                            target_user_id,
                            f"🔔 *{display_name}* t'a mentionné dans un message anonyme dans le canal <#{slack_params['channel_id']}> !\n\n> {message_text}"
                        )
                    break

        # Send delayed response to response_url
        delayed_response = {
            'response_type': 'in_channel',
            'text': f"*{display_name}* : {message_text}{message_suffix}"
        }
        requests.post(
            slack_params['response_url'],
            json=delayed_response
        )

        # Send immediate empty 200 response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'')

        return

    def handle_special_channel(self, slack_params):
        """Handle messages for the special BMT channel"""
        message_text = slack_params['text'].strip()
        
        # Check if message content is allowed
        if message_text not in ["BMT ?", "+1"]:
            response = {
                'response_type': 'ephemeral',
                'text': "❌ Dans ce canal, seuls les messages 'BMT ?' et '+1' sont autorisés."
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(bytes(json.dumps(response), 'utf-8'))
            return

        # Store message in database
        store_message(
            message_text,
            slack_params['user_id'],
            slack_params['channel_id'],
            slack_params['channel_name'],
            slack_params['response_url']
        )

        # Add button for +1 messages
        delayed_response = {
            'response_type': 'in_channel',
            'text': message_text,
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': message_text
                    }
                },
                {
                    'type': 'actions',
                    'elements': [
                        {
                            'type': 'button',
                            'text': {
                                'type': 'plain_text',
                                'text': 'Go'
                            },
                            'style': 'primary',
                            'action_id': 'go_button',
                            'value': slack_params['user_id']  # Store the original poster's user ID
                        }
                    ]
                }
            ]
        }

        # Send the response
        requests.post(
            slack_params['response_url'],
            json=delayed_response
        )

        # Send immediate empty 200 response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'')


