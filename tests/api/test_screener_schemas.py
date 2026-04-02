"""TDD RED phase tests for ScreenRequest and ScreenResponse schemas (Task 1 behavior)."""
import pytest
from pydantic import ValidationError


def test_screen_request_defaults():
    """ScreenRequest() with no args produces correct defaults."""
    from api.schemas import ScreenRequest
    r = ScreenRequest()
    assert r.max_picks == 5
    assert r.universe == "sp500"
    assert r.llm_provider == "openai"
    assert r.quick_think_llm == "gpt-5-mini"


def test_screen_request_max_picks_cap():
    """ScreenRequest(max_picks=15) is rejected by Pydantic (le=10 constraint)."""
    from api.schemas import ScreenRequest
    with pytest.raises(ValidationError):
        ScreenRequest(max_picks=15)


def test_screen_request_min_picks():
    """ScreenRequest(max_picks=0) is rejected by Pydantic (ge=1 constraint)."""
    from api.schemas import ScreenRequest
    with pytest.raises(ValidationError):
        ScreenRequest(max_picks=0)


def test_screen_request_config_dict():
    """ScreenRequest().config_dict() returns dict with screener_n_picks, llm_provider, quick_think_llm."""
    from api.schemas import ScreenRequest
    r = ScreenRequest()
    c = r.config_dict()
    assert c["screener_n_picks"] == 5
    assert c["llm_provider"] == "openai"
    assert c["quick_think_llm"] == "gpt-5-mini"


def test_screen_response_requires_fields():
    """ScreenResponse requires status, data, screened_at fields."""
    from api.schemas import ScreenResponse
    from pydantic import ValidationError
    # Missing fields should raise
    with pytest.raises(ValidationError):
        ScreenResponse()
    # Valid construction
    resp = ScreenResponse(status="success", data={"picks": []}, screened_at="2026-04-02T12:00:00+00:00")
    assert resp.status == "success"
    assert resp.screened_at == "2026-04-02T12:00:00+00:00"
