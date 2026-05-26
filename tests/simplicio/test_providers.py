"""Provider-config tests — no network, no SDKs required."""

import pytest

from simplicio import providers


_ENV_KEYS = (
    "SIMPLICIO_MODEL", "SIMPLICIO_BASE_URL", "SIMPLICIO_API_KEY",
    "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_info_unset():
    assert providers.info() == "model=(unset) base=anthropic-native key=MISSING"


def test_info_set(monkeypatch):
    monkeypatch.setenv("SIMPLICIO_MODEL", "openai/gpt-4.1")
    monkeypatch.setenv("SIMPLICIO_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("SIMPLICIO_API_KEY", "sk-test")
    info = providers.info()
    assert "model=openai/gpt-4.1" in info
    assert "base=https://openrouter.ai/api/v1" in info
    assert "key=set" in info


def test_key_fallback_priority(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
    assert providers._cfg()["key"] == "or-key"
    monkeypatch.setenv("SIMPLICIO_API_KEY", "primary")
    assert providers._cfg()["key"] == "primary"


def test_msgs_without_feedback():
    msgs = providers._msgs("do the thing", None)
    assert msgs == [{"role": "user", "content": "do the thing"}]


def test_msgs_with_feedback():
    msgs = providers._msgs("do the thing", "AssertionError: nope")
    assert len(msgs) == 2
    assert msgs[0] == {"role": "user", "content": "do the thing"}
    assert "The test FAILED" in msgs[1]["content"]
    assert "AssertionError: nope" in msgs[1]["content"]


def test_generate_requires_model():
    with pytest.raises(SystemExit) as ei:
        providers.generate("hello")
    assert "SIMPLICIO_MODEL" in str(ei.value)


def test_generate_requires_key(monkeypatch):
    monkeypatch.setenv("SIMPLICIO_MODEL", "some/model")
    with pytest.raises(SystemExit) as ei:
        providers.generate("hello")
    assert "SIMPLICIO_API_KEY" in str(ei.value)
