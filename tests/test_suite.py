"""
STEMMate A4 requirements-based test suite (v2).

Test IDs are A4-Txx, mapped to A3 requirement IDs in the traceability matrix.
Tests marked xfail(strict=True) describe behaviour the report claims but the
current code does not implement. They are kept as documented, honest failures.
If one starts passing, strict xfail turns it into a failure so the marker is removed.
"""
import re
from pathlib import Path
from unittest import mock

import pytest

from stemmate.core import (
    AccessGuard,
    ConflictResolver,
    RemoteSyncGateway,
    SessionPlan,
    SessionPlanService,
    SyncCoordinator,
    SyncQueueItem,
)

APP_PY = Path(__file__).resolve().parent.parent / "app.py"


# ---------------------------------------------------------------- A4-T01 (FR-03)
def test_a4_t01_plan_title_required():
    service = SessionPlanService()
    with pytest.raises(ValueError, match="Title is required"):
        service.validate(SessionPlan(title="", content="Lesson 1"))
    assert service.validate(SessionPlan(title="Maths 101", content="Algebra")) is True


# ---------------------------------------------------------------- A4-T02 (FR-05)
def test_a4_t02_non_overlapping_steps_merge():
    merged = ConflictResolver().merge({"steps": ["Step A"]}, {"steps": ["Step B"]})
    assert merged["status"] == "MERGED"
    assert set(merged["steps"]) == {"Step A", "Step B"}


def test_a4_t02b_title_clash_flags_manual_review():
    result = ConflictResolver().merge({"title": "Version A"}, {"title": "Version B"})
    assert result["status"] == "CONFLICT_MANUAL"


# ---------------------------------------------------------------- A4-T03 (FR-05)
def test_a4_t03_failed_send_schedules_retry():
    item = SyncQueueItem(id=101, data="Plan Data")
    with mock.patch.object(
        RemoteSyncGateway, "send", side_effect=Exception("503 Service Unavailable")
    ):
        SyncCoordinator().sync_item(item)
    assert item.retry_count == 1
    assert item.status == "RETRY_SCHEDULED"


# ---------------------------------------------------------------- A4-T04 (FR-05, QR-02)
@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="QR-02/FR-05: sync queue is in-memory only; no persistence method exists",
)
def test_a4_t04_queue_survives_restart():
    item = SyncQueueItem(id=102, data="Plan Data")
    SyncCoordinator().save_queue(item)  # not implemented


# ---------------------------------------------------------------- A4-T05 (FR-02)
@pytest.mark.xfail(
    strict=True,
    raises=ImportError,
    reason="FR-02: SessionPlanRepository is named in the report but not in the code",
)
def test_a4_t05_local_save_persists_across_restart():
    from stemmate.core import SessionPlanRepository  # noqa: F401


# ---------------------------------------------------------------- A4-T06 (FR-07)
@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="FR-07: SessionPlan has no expectedLearners field",
)
def test_a4_t06_expected_learners_range_1_to_200():
    SessionPlan(title="Maths 101", expectedLearners=0)
    with pytest.raises(ValueError):
        SessionPlan(title="Maths 101", expectedLearners=201)


# ---------------------------------------------------------------- A4-T07 (QR-01)
@pytest.mark.skip(
    reason="Manual test: device profiling on low-spec hardware. Record results in the report, not here."
)
def test_a4_t07_low_spec_profiling_manual():
    pass


# ---------------------------------------------------------------- A4-T08 (QR-02)
def test_a4_t08a_failed_send_does_not_change_item_data():
    item = SyncQueueItem(id=103, data="Plan Data")
    with mock.patch.object(
        RemoteSyncGateway, "send", side_effect=Exception("503 Service Unavailable")
    ):
        SyncCoordinator().sync_item(item)
    assert item.data == "Plan Data"


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="QR-02: merged copy is not written to device before upload is attempted",
)
def test_a4_t08b_merged_copy_kept_after_failed_upload():
    SyncCoordinator().keep_merged_copy({"steps": ["Step A"]})  # not implemented


# ---------------------------------------------------------------- A4-T09 (AR-01)
def _relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(fg: str, bg: str) -> float:
    hi, lo = sorted([_relative_luminance(fg), _relative_luminance(bg)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _css_background(selector: str, css: str) -> str:
    block = re.search(re.escape(selector) + r"\s*\{(.*?)\}", css, re.S)
    assert block, f"{selector} not found in app.py CSS"
    colour = re.search(r"background-color:\s*(#[0-9A-Fa-f]{6})", block.group(1))
    assert colour, f"no background-color for {selector}"
    return colour.group(1)


def test_a4_t09_status_badges_and_header_meet_wcag_aa_contrast():
    """Parses colours from app.py. White text is assumed, as set in the app's CSS."""
    css = APP_PY.read_text(encoding="utf-8")
    for selector in (".badge-online", ".badge-offline", ".stemmate-header"):
        bg = _css_background(selector, css)
        ratio = _contrast("#FFFFFF", bg)
        assert ratio >= 4.5, f"{selector} ({bg}) is {ratio:.2f}:1, below 4.5:1"


# ---------------------------------------------------------------- A4-T10 (PR-01)
@pytest.mark.xfail(
    strict=True,
    reason=(
        "PR-01: SessionPlanService.validate() checks only the title. "
        "The identifier check exists only in app.py, as a substring test for '081' and '@'. "
        "It misses 085 numbers and names."
    ),
)
def test_a4_t10_validate_blocks_phone_and_email_in_plan_text():
    plan = SessionPlan(
        title="Maths 101",
        content="Call 0811234567 or write to learner@school.na",
    )
    with pytest.raises(ValueError):
        SessionPlanService().validate(plan)


# ---------------------------------------------------------------- A4-T11 (SR-01)
def test_a4_t11a_wrong_credentials_rejected():
    guard = AccessGuard()
    assert guard.signIn(username="wrong", password="bad") is False
    assert guard.is_authenticated() is False


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="SR-01: AccessGuard has no profile PIN sign-in (signIn takes username and password)",
)
def test_a4_t11b_profile_pin_sign_in():
    assert AccessGuard().signIn(profileId="facilitator-a", pin="1234") is True


@pytest.mark.xfail(
    strict=True,
    raises=TypeError,
    reason="SR-01: no lockout after 5 wrong PIN attempts is implemented in AccessGuard",
)
def test_a4_t11c_lockout_after_five_wrong_pins():
    guard = AccessGuard()
    for _ in range(5):
        guard.signIn(profileId="facilitator-a", pin="0000")
    assert guard.signIn(profileId="facilitator-a", pin="1234") is False


# ---------------------------------------------------------------- A4-T12 (FR-02, QR-02)
@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="FR-02/QR-02: no disk-full handling in core; storage_full exists only as a UI toggle in app.py",
)
def test_a4_t12_disk_full_returns_handled_error_without_data_loss():
    SyncCoordinator().save_local(SyncQueueItem(id=104, data="Plan Data"), storage_full=True)