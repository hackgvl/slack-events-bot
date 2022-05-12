def create_tables(conn):
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
			channel_id INTEGER NOT NULL,
				CONSTRAINT fk_channel_id
				FOREIGN KEY(channel_id) REFERENCES channels(id)
				ON DELETE CASCADE
		);

		CREATE INDEX IF NOT EXISTS uuid_index ON messages (event_uuid);
	""")

    # saves the change to the database
    conn.commit()


async def create_event_message(conn, eventUUID, messageTimestamp, channelID):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO messages (event_uuid, message_timestamp, channel_id)
            VALUES (?, ?, ?)""",
        [eventUUID, messageTimestamp, channelID]
    )

    # saves the change to the database
    conn.commit()


async def event_messages_count(conn, eventUUID):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(event_uuid) FROM messages WHERE event_uuid = ?",
        [eventUUID]
    )
    return cur.fetchone()[0]


async def get_event_messages(conn, eventUUID):
    cur = conn.cursor()
    cur.execute(
        """SELECT m.message_timestamp, c.slack_channel_id
            FROM messages m
            JOIN channels c ON m.channel_id = c.id
            WHERE m.event_uuid = ?""",
        [eventUUID]
    )
    return [{'message_timestamp': x[0], 'slack_channel_id': x[1]} for x in cur.fetchall()]


async def get_slack_channel_ids(conn):
    cur = conn.cursor()
    cur.execute("SELECT slack_channel_id FROM channels")
    return [x[0] for x in cur.fetchall()]


async def get_slack_channel_id(conn, channelID):
    cur = conn.cursor()
    cur.execute(
        "SELECT slack_channel_id FROM channels WHERE id = ?", [channelID])
    return cur.fetchone()[0]


async def get_channel_id(conn, slackChannelID):
    cur = conn.cursor()
    cur.execute("SELECT id FROM channels WHERE slack_channel_id = ?", [
                slackChannelID])
    return cur.fetchone()[0]


async def add_channel(conn, slackChannelID):
    cur = conn.cursor()
    cur.execute("INSERT INTO channels (slack_channel_id) VALUES (?)", [
                slackChannelID])

    # saves the change to the database
    conn.commit()


async def remove_channel(conn, channelID):
    cur = conn.cursor()
    cur.execute("DELETE FROM channels WHERE slack_channel_id = ?", [channelID])

    # saves the change to the database
    conn.commit()
