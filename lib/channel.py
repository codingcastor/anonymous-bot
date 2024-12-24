from datetime import datetime
from .database import get_db_connection
from .types import ChannelMode

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
