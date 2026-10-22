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
