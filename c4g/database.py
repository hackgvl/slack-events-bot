"""Contains all the functions that interact with the sqlite database"""


def create_tables(conn):
    """Create database tables needed for c4g-events"""
    cur = conn.cursor()

    cur.executescript("""
		CREATE TABLE IF NOT EXISTS channels (
			id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
			slack_channel_id TEXT UNIQUE NOT NULL
		);

		CREATE INDEX IF NOT EXISTS slack_channel_id_index ON channels (slack_channel_id);

		CREATE TABLE IF NOT EXISTS messages (
			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
			event_uuid TEXT NOT NULL,
			message_timestamp TEXT NOT NULL,
            message TEXT NOT NULL,
			channel_id INTEGER NOT NULL,
				CONSTRAINT fk_channel_id
				FOREIGN KEY(channel_id) REFERENCES channels(id)
				ON DELETE CASCADE
		);

		CREATE INDEX IF NOT EXISTS uuid_index ON messages (event_uuid);
	""")

    # saves the change to the database
    conn.commit()


async def create_event_message(conn, event_uuid, message, message_timestamp, channel_id):
    """Create a record of a message sent in slack for an event"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO messages (event_uuid, message, message_timestamp, channel_id)
            VALUES (?, ?, ?, ?)""",
        [event_uuid, message, message_timestamp, channel_id]
    )

    # saves the change to the database
    conn.commit()


async def event_messages_count(conn, event_uuid):
    """Get a count of messages sent in slack for an event"""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(event_uuid) FROM messages WHERE event_uuid = ?",
        [event_uuid]
    )
    return cur.fetchone()[0]


async def get_event_messages(conn, event_uuid):
    """Get all messages sent in slack for an event"""
    cur = conn.cursor()
    cur.execute(
        """SELECT m.message, m.message_timestamp, c.slack_channel_id
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.event_uuid = ?""",
        [event_uuid]
    )
    return [{'message': x[0],
             'message_timestamp': x[1],
             'slack_channel_id': x[2]} for x in cur.fetchall()]


async def get_slack_channel_ids(conn):
    """Get all slack channels that the bot is configured for"""
    cur = conn.cursor()
    cur.execute("SELECT slack_channel_id FROM channels")
    return [x[0] for x in cur.fetchall()]


async def get_slack_channel_id(conn, channel_id):
    """Get Slack's id of a channel from our channel id"""
    cur = conn.cursor()
    cur.execute(
        "SELECT slack_channel_id FROM channels WHERE id = ?", [channel_id])
    return cur.fetchone()[0]


async def get_channel_id(conn, slack_channel_id):
    """Get our id of a channel from Slack's channel id"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM channels WHERE slack_channel_id = ?", [
                slack_channel_id])
    return cur.fetchone()[0]


async def add_channel(conn, slack_channel_id):
    """Add a slack channel to post in for the bot"""
    cur = conn.cursor()
    cur.execute("INSERT INTO channels (slack_channel_id) VALUES (?)", [
                slack_channel_id])

    # saves the change to the database
    conn.commit()


async def remove_channel(conn, channel_id):
    """Remove a slack channel to post in from the bot"""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM channels WHERE slack_channel_id = ?", [channel_id])

    # saves the change to the database
    conn.commit()
