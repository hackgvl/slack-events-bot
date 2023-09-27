"""Contains all the functions that interact with the sqlite database"""


def create_tables(conn):
    """Create database tables needed for slack events bot"""
    cur = conn.cursor()

    cur.executescript(
        """
		CREATE TABLE IF NOT EXISTS channels (
			id integer PRIMARY KEY AUTOINCREMENT NOT NULL,
			slack_channel_id TEXT UNIQUE NOT NULL
		);

		CREATE INDEX IF NOT EXISTS slack_channel_id_index ON channels (slack_channel_id);

		CREATE TABLE IF NOT EXISTS messages (
			id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
			week DATE NOT NULL,
			message_timestamp TEXT NOT NULL,
            message TEXT NOT NULL,
			channel_id INTEGER NOT NULL,
				CONSTRAINT fk_channel_id
				FOREIGN KEY(channel_id) REFERENCES channels(id)
				ON DELETE CASCADE
		);

		CREATE INDEX IF NOT EXISTS week_index ON messages (week);
	"""
    )

    # saves the change to the database
    conn.commit()


async def create_message(conn, week, message, message_timestamp, slack_channel_id):
    """Create a record of a message sent in slack for a week"""
    cur = conn.cursor()

    # get database's channel id for slack channel id
    cur.execute(
        "SELECT id FROM channels WHERE slack_channel_id = ?", [slack_channel_id]
    )
    channel_id = cur.fetchone()[0]

    cur.execute(
        """INSERT INTO messages (week, message, message_timestamp, channel_id)
            VALUES (?, ?, ?, ?)""",
        [week, message, message_timestamp, channel_id],
    )

    # saves the change to the database
    conn.commit()


async def update_message(conn, week, message, message_timestamp, slack_channel_id):
    """Updates a record of a message sent in slack for a week"""
    cur = conn.cursor()

    # get database's channel id for slack channel id
    cur.execute(
        "SELECT id FROM channels WHERE slack_channel_id = ?", [slack_channel_id]
    )
    channel_id = cur.fetchone()[0]

    cur.execute(
        """UPDATE messages
            SET message = ?
            WHERE week = ? AND message_timestamp = ? AND channel_id = ?""",
        [message, week, message_timestamp, channel_id],
    )

    # saves the change to the database
    conn.commit()


async def get_messages(conn, week):
    """Get all messages sent in slack for a week"""
    cur = conn.cursor()
    cur.execute(
        """SELECT m.message, m.message_timestamp, c.slack_channel_id
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.week = ?""",
        [week],
    )
    return [
        {"message": x[0], "message_timestamp": x[1], "slack_channel_id": x[2]}
        for x in cur.fetchall()
    ]


async def get_slack_channel_ids(conn):
    """Get all slack channels that the bot is configured for"""
    cur = conn.cursor()
    cur.execute("SELECT slack_channel_id FROM channels")
    return [x[0] for x in cur.fetchall()]


async def add_channel(conn, slack_channel_id):
    """Add a slack channel to post in for the bot"""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO channels (slack_channel_id) VALUES (?)", [slack_channel_id]
    )

    # saves the change to the database
    conn.commit()


async def remove_channel(conn, channel_id):
    """Remove a slack channel to post in from the bot"""
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE slack_channel_id = ?", [channel_id])

    # saves the change to the database
    conn.commit()
