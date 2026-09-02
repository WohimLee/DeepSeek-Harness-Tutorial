"""SessionStore plugin lifecycle and identity."""

from typing import cast

import pytest

from dsh.cordis import Context
from dsh.core.runtime.session import SessionId, SessionStore, plugin


async def test_store_creates_and_lists_sessions() -> None:
    context = Context()
    fiber = context.plugin(plugin)
    await fiber.wait()
    store = cast(SessionStore, context.get("sessions"))

    session = store.create(SessionId("one"))

    assert store.get_session(SessionId("one")) is session
    assert store.list_sessions() == (session,)
    with pytest.raises(ValueError, match="already exists"):
        store.create(SessionId("one"))

    await context.aclose()
