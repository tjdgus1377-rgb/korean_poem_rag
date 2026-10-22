import pytest


def test_key_never_in_config_repr_or_error(tmp_path):
    from sidam.config import Config
    from sidam.models import Models, ModelError
    config = Config(tmp_path, api_key="test-secret-never-display")
    assert "test-secret-never-display" not in repr(config)
    model = Models(config)
    def fail(**kwargs):
        raise RuntimeError("test-secret-never-display")
    model.client.chat.completions.create = fail
    with pytest.raises(ModelError) as exc:
        model.complete("prompt", {})
    assert "test-secret-never-display" not in str(exc.value)


def test_json_mode_always_mentions_json_for_provider_contract(tmp_path):
    from types import SimpleNamespace
    from sidam.config import Config
    from sidam.models import Models
    model = Models(Config(tmp_path, api_key="test-only"))
    sent = []
    def create(**params):
        sent.append(params)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
    model.client.chat.completions.create = create
    assert model.complete("조건을 추출한다", {}, json_mode=True) == '{}'
    assert any("json" in message["content"].lower() for message in sent[0]["messages"])
