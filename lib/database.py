import os
import psycopg2
import random
from datetime import datetime, timedelta
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


def store_message(text, user_id, channel_id, channel_name, response_url):
    """Store a new message in the database"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO messages (text, user_id, channel_id, channel_name, response_url, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (text, user_id, channel_id, channel_name, response_url, datetime.now()))

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
    """Get the mode for a channel, defaults to DISABLED if not configured
    
    Args:
        channel_id (str): The Slack channel ID
        
    Returns:
        ChannelMode: The channel's mode (DISABLED if not configured)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT mode FROM channel_configs WHERE channel_id = %s', (channel_id,))
    result = cur.fetchone()
    channel_mode = ChannelMode(result[0]) if result else ChannelMode.DISABLED
    
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
    
    

PSEUDOS = [
    # Animaux
    "Lynx", "Orca", "Puma", "Manta", "Heron", "Renne", "Grue", "Dingo", "Carpe", "Gecko",
    "Cobra", "Bison", "Fennec", "Condor", "Triton", "Moray", "Panda", "Tanuki", "Otarie", "Grizzly",
    "Loris", "Guppy", "Caiman", "Koala", "Ibex", "Tapir", "Makaki", "Loutre", "Narval",
    "Vison", "Dauri", "Aiglon", "Gibbon", "Hyene", "Jaguar", "Pigeon", "Faucon", "Souris", "Phoque",
    "Falcon", "Lynette", "Onca", "Harfang", "Corbeau", "Mergan", "Arowana", "Toucan", "Okapi",
    "Mako", "Otter", "Varan", "Hocco", "Saki", "Dhole", "Civette", "Yak", "Albatros", "Bulbul",
    "Sarcelle", "Draco", "Kestrel", "Puffin", "Beluga", "Python", "Cobrax", "Moloch", "Ratel",
    "Manakin", "Osprey",

    # Plantes / arbres
    "Saule", "Cypres", "Noyer", "Erable", "Lotus", "Iris", "Yucca", "Tamarin", "Cendre", "Aulne",
    "Myrte", "Orme", "Balsa", "Sureau", "Acacia", "Lauro", "Canna", "Myrica", "Bambou", "Baobab",
    "Figuier", "Zelkova", "Tamaris", "Persil", "Lavandin", "Cycas", "Epicea", "Genet", "Chene",
    "Aroeira", "Gingko", "Pinson", "Cedro", "Olmo", "Mangue", "Ruscus", "Aralia", "Nerium",
    "Linum", "Tilleul", "Chara", "Cassia", "Kauri", "Argan", "Tisa", "Sabal", "Pitya", "Croton",
    "Salvia", "Musgo", "Aloe", "Agave", "Cedrela", "Abelia", "Celosia", "Lantana", "Erica",
    "Verbena", "Oxalis", "Hetre", "Cardon", "Pruche", "Tamaru", "Arundo", "Riparia", "Celtis",
    "Acorus", "Lupin",

    # Codes / abstraits
    "Nova", "Vector", "Prisma", "Sigma", "Echo", "Orbit", "Nexus", "Flux", "Delta", "Vortex",
    "Axion", "Tempo", "Atlas", "Photon", "Crypto", "Helix", "Optix", "Quant", "Neon", "Plexus",
    "Vertex", "Pulsar", "Byte", "Cipher", "Kilo", "Tango", "Lambda", "Gamma", "Zenith", "Orion",
    "Parsec", "Proton", "Hexa", "Mono", "Quark", "Unity", "Astro", "Pulse", "Spectra", "Optima",
    "Modulo", "Voxel", "Turbo", "Synchro", "Kappa", "Orbiton", "Pixel", "Numa", "Ionix", "Scalar",
    "Kronos", "Solis", "Lumen", "Holo", "Aero", "Ionis"
] 
def get_or_assign_pseudo(user_id, channel_id, validity_hours=1) -> str:
    """Get or assign a pseudo for a user in a channel"""
    conn = get_db_connection()
    cur = conn.cursor()

    now = datetime.now()
    expiry = now - timedelta(hours=validity_hours)

    # Check existing record
    cur.execute('SELECT pseudo, last_used FROM pseudos WHERE user_id = %s AND channel_id = %s', (user_id, channel_id))
    result = cur.fetchone()

    # Case 1: user already has a pseudo AND it's still valid
    if result:
        pseudo, last_used = result
        if last_used and last_used > expiry:
            cur.execute('UPDATE pseudos SET last_used = %s WHERE user_id = %s AND channel_id = %s', 
                       (now, user_id, channel_id))
            conn.commit()
            cur.close()
            conn.close()
            return pseudo

    # Case 2: user needs a new pseudo
    # Get used pseudos in this channel that are still valid
    cur.execute('SELECT pseudo FROM pseudos WHERE channel_id = %s AND last_used > %s', (channel_id, expiry))
    used_pseudos = {row[0] for row in cur.fetchall()}

    available = [p for p in PSEUDOS if p not in used_pseudos]

    # fallback if everyone is using a pseudo (rare)
    if not available:
        available = list(PSEUDOS)

    new_pseudo = random.choice(available)

    if result:
        # Update existing expired record
        cur.execute('UPDATE pseudos SET pseudo = %s, last_used = %s WHERE user_id = %s AND channel_id = %s',
                   (new_pseudo, now, user_id, channel_id))
    else:
        # Create new record
        cur.execute('INSERT INTO pseudos (user_id, channel_id, pseudo, last_used) VALUES (%s, %s, %s, %s)',
                   (user_id, channel_id, new_pseudo, now))

    conn.commit()
    cur.close()
    conn.close()

    return new_pseudo


def get_user_by_pseudo(pseudo, channel_id, validity_hours=1) -> str | None:
    """Get user_id by pseudo in a channel if the pseudo is still valid
    
    Args:
        pseudo (str): The pseudo to look up
        channel_id (str): The Slack channel ID
        validity_hours (int): How long a pseudo remains valid
        
    Returns:
        str | None: The user_id if found and valid, None otherwise
    """
    conn = get_db_connection()
    cur = conn.cursor()

    expiry = datetime.now() - timedelta(hours=validity_hours)

    cur.execute(
        'SELECT user_id FROM pseudos WHERE pseudo = %s AND channel_id = %s AND last_used > %s',
        (pseudo, channel_id, expiry)
    )
    result = cur.fetchone()

    cur.close()
    conn.close()

    return result[0] if result else None


def get_known_pseudos() -> list:
    """Get the list of all known pseudos
    
    Returns:
        list: The list of pseudos
    """
    return PSEUDOS