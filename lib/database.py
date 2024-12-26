import os
import psycopg2
from datetime import datetime
from .types import ChannelMode


def get_db_connection():
    """Get a PostgreSQL database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))


def update_channel_mode(channel_id, mode):
    """Update or insert channel configuration"""
    if not isinstance(mode, ChannelMode):
        raise ValueError("Mode must be a ChannelMode enum value")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO channel_configs (channel_id, mode, updated_at)
        VALUES (%s, %s, %s)
        ON CONFLICT (channel_id) 
        DO UPDATE SET mode = EXCLUDED.mode, updated_at = EXCLUDED.updated_at
    ''', (channel_id, mode.value, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()


def store_message(text, user_id, channel_id, channel_name):
    """Store a new message in the database"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO messages (text, user_id, channel_id, channel_name, created_at)
        VALUES (%s, %s, %s, %s, %s)
    ''', (text, user_id, channel_id, channel_name, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()


def is_admin(user_id):
    """Check if a user is an admin"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT EXISTS(SELECT 1 FROM admin_users WHERE user_id = %s)', (user_id,))
    is_admin = cur.fetchone()[0]

    cur.close()
    conn.close()

    return is_admin


def get_channel_mode(channel_id):
    """Get the mode for a channel, defaults to FREE if not configured
    
    Args:
        channel_id (str): The Slack channel ID
        
    Returns:
        ChannelMode: The channel's mode (FREE if not configured)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT mode FROM channel_configs WHERE channel_id = %s', (channel_id,))
    result = cur.fetchone()
    channel_mode = ChannelMode(result[0]) if result else ChannelMode.FREE
    
    cur.close()
    conn.close()
    
    return channel_mode


def store_inappropriate_message(text, channel_id, channel_name):
    """Store an inappropriate message in the dedicated table
    
    Args:
        text (str): The message content
        channel_id (str): The Slack channel ID
        channel_name (str): The Slack channel name
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO inappropriate_messages (message_text, channel_id, channel_name, created_at)
        VALUES (%s, %s, %s, %s)
    ''', (text, channel_id, channel_name, datetime.now()))

    conn.commit()
    cur.close()
    conn.close()
