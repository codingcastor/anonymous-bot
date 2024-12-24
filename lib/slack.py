import os
import hmac
import hashlib
from datetime import datetime
from .database import get_db_connection

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
