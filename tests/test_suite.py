import pytest
from stemmate.core import SessionPlanService, ConflictResolver, SyncCoordinator, AccessGuard, SessionPlan, SyncQueueItem

def test_session_plan_validation():
    service = SessionPlanService()
    invalid_plan = SessionPlan(title="", content="Lesson 1") 
    with pytest.raises(ValueError, match="Title is required"):
        service.validate(invalid_plan)

    valid_plan = SessionPlan(title="Maths 101", content="Algebra")
    assert service.validate(valid_plan) is True

def test_conflict_resolution():
    resolver = ConflictResolver()
    local_version = {"id": 1, "steps": ["Step A"], "version": 1}
    remote_version = {"id": 1, "steps": ["Step B"], "version": 2}

    merged = resolver.merge(local_version, remote_version)
    assert "Step A" in merged["steps"]
    assert "Step B" in merged["steps"]

    local_conf = {"id": 1, "title": "Version A"}
    remote_conf = {"id": 1, "title": "Version B"}
    result = resolver.merge(local_conf, remote_conf)
    assert result["status"] == "CONFLICT_MANUAL"

def test_sync_retry_logic(mocker):
    mocker.patch('stemmate.core.RemoteSyncGateway.send', side_effect=Exception("503 Service Unavailable"))
    coordinator = SyncCoordinator()
    item = SyncQueueItem(id=101, data="Plan Data")

    coordinator.sync_item(item)
    assert item.retry_count == 1
    assert item.status == "RETRY_SCHEDULED"

def test_access_guard_auth():
    guard = AccessGuard()
    assert guard.signIn(username="wrong", password="bad") is False
    assert guard.signIn(username="prince_nde", password="secure_pass") is True
    assert guard.is_authenticated() is True
