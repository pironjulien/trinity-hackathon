import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from jobs.influencer.core.x_client import XClient

# Mock data paths
TEST_MEMORIES = Path("/tmp/trinity_test/memories")


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("X_API_KEY", "fake")
    monkeypatch.setenv("X_API_SECRET", "fake")
    monkeypatch.setenv("X_ACCESS_TOKEN", "fake")
    monkeypatch.setenv("X_ACCESS_SECRET", "fake")
    monkeypatch.setenv("X_BEARER_TOKEN", "fake")


@pytest.fixture
def client(tmp_path, mock_env):
    # Patch MEMORIES_DIR to use tmp_path
    with patch("jobs.influencer.core.x_client.MEMORIES_DIR", tmp_path):
        client = XClient()
        # Mock AsyncClient to avoid real calls
        client.async_client_v2 = AsyncMock()
        client._authenticated = True
        return client


@pytest.mark.asyncio
async def test_quota_limit_enforcement(client):
    """Test strict enforcement of daily quota."""

    # 1. Setup: Consume all quota (2 calls)
    quota_file = client.QUOTA_FILE
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")

    # Manually write full quota state
    import json

    quota_file.parent.mkdir(parents=True, exist_ok=True)
    with open(quota_file, "w") as f:
        json.dump({"date": today, "count": 2}, f)

    # 2. Verify _check_limit returns False
    assert client._check_limit() is False

    # 3. Verify get_me_async aborts when identity is missing & quota full
    # Ensure no identity cache
    if client.IDENTITY_FILE.exists():
        client.IDENTITY_FILE.unlink()

    result = await client.get_me_async()
    assert result is None
    # Verify NO call was made
    client.async_client_v2.get_me.assert_not_called()


@pytest.mark.asyncio
async def test_quota_reset_next_day(client):
    """Verify quota resets on new day."""
    quota_file = client.QUOTA_FILE

    # Create stale quota file (yesterday)
    import json

    quota_file.parent.mkdir(parents=True, exist_ok=True)
    with open(quota_file, "w") as f:
        json.dump({"date": "2000-01-01", "count": 2}, f)

    # Verify _check_limit returns True (reset)
    assert client._check_limit() is True

    # Verify file updated
    with open(quota_file, "r") as f:
        data = json.load(f)
        from datetime import datetime

        assert data["date"] == datetime.now().strftime("%Y-%m-%d")
        assert data["count"] == 1


@pytest.mark.asyncio
async def test_perform_daily_sync_aborts_on_limit(client):
    """Verify perform_daily_sync respects limit."""
    # 1. Full Quota
    quota_file = client.QUOTA_FILE
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")

    quota_file.parent.mkdir(parents=True, exist_ok=True)
    import json

    with open(quota_file, "w") as f:
        json.dump({"date": today, "count": 2}, f)

    # 2. Call Sync
    await client.perform_daily_sync()

    # 3. Verify NO calls
    client.async_client_v2.get_users_mentions.assert_not_called()
    client.async_client_v2.get_users_tweets.assert_not_called()
