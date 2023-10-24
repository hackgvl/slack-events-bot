"""
Custom errors for use in this application.
"""


class UnsafeMessageSpilloverError(Exception):
    """
    Raised whenever the number of messages needed to contain a week's events
    increases after the next week's messages have begun to be posted to a channel.
    """
