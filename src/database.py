"""Contains all the functions that interact with the sqlite database"""
import os
import datetime
import sqlite3
from typing import Union, Generator

DB_PATH = os.path.abspath(os.environ.get("DB_PATH", "./slack-events-bot.db"))


def get_connection(commit: bool = False) -> Generator:
    """
    Yields a SQLite connection to another method.

    Once the other method has finished,
    the transaction if committed if the commit parameter is true,
    and then the connection is always closed.
    """
    conn = sqlite3.connect(DB_PATH)

    yield conn

    if commit:
        conn.commit()

    conn.close()


def create_tables():
    """Create database tables needed for slack events bot"""
    for conn in get_connection(commit=True):
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

            CREATE TABLE IF NOT EXISTS cooldowns (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                -- Unique identifier from whomever is accessing the resource.
                -- Can be a workspace, channel, user, etc..
                accessor TEXT NOT NULL,
                -- Unique identifier for whatever is rate-limited.
                -- Can be a method name, service name, etc..
                resource TEXT NOT NULL,
                -- ISO8601 timestamp for when the accessor
                -- will be allowed to access the resource once again.
                expires_at TEXT NOT NULL,
                UNIQUE(accessor,resource)
            );

            CREATE INDEX IF NOT EXISTS accessor_resource_index ON
                cooldowns (accessor, resource);
        """
        )


async def create_message(week, message, message_timestamp, slack_channel_id):
    """Create a record of a message sent in slack for a week"""
    for conn in get_connection(commit=True):
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


async def update_message(week, message, message_timestamp, slack_channel_id):
    """Updates a record of a message sent in slack for a week"""
    for conn in get_connection(commit=True):
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


async def get_messages(week):
    """Get all messages sent in slack for a week"""
    for conn in get_connection():
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


async def get_slack_channel_ids():
    """Get all slack channels that the bot is configured for"""
    for conn in get_connection():
        cur = conn.cursor()
        cur.execute("SELECT slack_channel_id FROM channels")
        return [x[0] for x in cur.fetchall()]


async def add_channel(slack_channel_id):
    """Add a slack channel to post in for the bot"""
    for conn in get_connection(commit=True):
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO channels (slack_channel_id) VALUES (?)", [slack_channel_id]
        )


async def remove_channel(channel_id):
    """Remove a slack channel to post in from the bot"""
    for conn in get_connection(commit=True):
        cur = conn.cursor()
        cur.execute("DELETE FROM channels WHERE slack_channel_id = ?", [channel_id])


async def create_cooldown(accessor: str, resource: str, cooldown_minutes: int) -> None:
    """
    Upserts a cooldown record for an entity which will let the system know when to make the resource
    available to them once again.
    """
    for conn in get_connection(commit=True):
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO cooldowns (accessor, resource, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(accessor,resource) DO UPDATE SET
                    accessor=excluded.accessor,
                    resource=excluded.resource,
                    expires_at=excluded.expires_at
            """,
            [
                accessor,
                resource,
                (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(minutes=cooldown_minutes)
                ).isoformat(),
            ],
        )


async def get_cooldown_expiry_time(accessor: str, resource: str) -> Union[str, None]:
    """
    Returns the time at which an accessor is able to access a resource
    or None if no restriction has ever been put in place.
    """
    for conn in get_connection():
        cur = conn.cursor()
        cur.execute(
            """SELECT expires_at FROM cooldowns
            WHERE accessor = ? AND resource = ?
            """,
            [accessor, resource],
        )

        expiry_time = cur.fetchone()

        return expiry_time[0] if expiry_time is not None else None
