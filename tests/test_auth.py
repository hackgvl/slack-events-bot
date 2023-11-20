"""
Tests functions contained in src/auth.py
"""

import pytest

import auth


@pytest.mark.parametrize("mock_slack_bolt_async_app", ["auth"], indirect=True)
class TestAuth:
    """Groups tests for auth.py into a single scope"""

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_not_admin(self, mock_slack_bolt_async_app):
        """Tests when a user is NOT a workspace admin"""
        result = await auth.is_admin("regular_user")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_admin_when_user_is_admin(self, mock_slack_bolt_async_app):
        """Tests when a user is a workspace admin"""
        result = await auth.is_admin("admin_user")

        assert result is True
