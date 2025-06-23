"""Unit-test for Hardening checklist item 2-C (WebSocket task cleanup).

The test exercises the notify-manager without requiring Starlette’s full
WebSocket implementation.  All background *send* operations are registered
and must be cancelled once the client disconnects so that the global task
count returns to zero.
"""

import asyncio


from app.websocket.notify_manager import notify_manager  # type: ignore  # noqa: E402


class _DummyWebSocket:  # pylint: disable=too-few-public-methods
    """Very small stub mimicking the two WebSocket methods we use."""

    async def accept(self):
        return None

    async def send_json(self, _message):  # noqa: D401 – simple stub
        # Keep the task alive a moment so it is still *running* when we
        # disconnect – this mirrors real-life latency.
        await asyncio.sleep(0.1)


def test_tasks_cancelled_on_disconnect():
    """All tracked tasks for a user are cancelled when the WS disconnects."""

    async def _run():  # noqa: D401 – helper coroutine executed via asyncio.run
        user_id = 123

        ws = _DummyWebSocket()

        # 1. Connect & spawn background notifications
        await notify_manager.connect(ws, user_id)

        for _ in range(5):
            await notify_manager.send_async(user_id, {"ping": "pong"})

        # Ensure tasks actually exist
        stats_before = await notify_manager.task_manager.get_stats()
        assert stats_before["total_tasks"] >= 5

        # 2. Disconnect – this must cancel and purge all tasks
        await notify_manager.disconnect(ws, user_id)

        # Give callbacks a chance to run
        await asyncio.sleep(0.05)

        stats_after = await notify_manager.task_manager.get_stats()
        assert stats_after["total_tasks"] == 0, stats_after

    # Drive the async scenario
    asyncio.run(_run())
