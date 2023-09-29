"""
    Tests for the bot.py file.
"""

import threading


def test_health_check_healthy_threads(test_client):
    """Happy path scenario for the /healthz route where nothing is wrong."""
    response = test_client.get("healthz")

    assert response.status_code == 200
    assert response.content == b'{"detail":"Everything is lookin\' good!"}'


def test_health_check_with_a_dead_thread(test_client, threads_appear_dead):
    """Tests what happens if a dead thread is found whenever this endpoint is hit."""
    response = test_client.get("healthz")

    first_thread = threading.enumerate()[0]

    assert response.status_code == 500
    assert response.json() == {
        "detail": f"The {first_thread.name} thread has died. This container will soon restart."
    }
