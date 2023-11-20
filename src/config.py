"""
Location for configuration settings and app-wide constants.
"""

import os

from fastapi import FastAPI
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

API = FastAPI()

# configure Slack app
SLACK_APP = AsyncApp(
    token=os.environ.get("BOT_TOKEN"), signing_secret=os.environ.get("SIGNING_SECRET")
)
SLACK_APP_HANDLER = AsyncSlackRequestHandler(SLACK_APP)
