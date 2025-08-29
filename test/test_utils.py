from src.utils import save_api_key, get_api_key, set_window_excluded_from_capture


def test_keyring_save_and_get(monkeypatch):
    # Mock keyring
    store = {}

    class DummyKeyring:
        @staticmethod
        def set_password(service, key, value):
            store[(service, key)] = value

        @staticmethod
        def get_password(service, key):
            return store.get((service, key))

    import src.utils as utils
    monkeypatch.setattr(utils, "keyring", DummyKeyring)

    save_api_key("abc123")
    assert get_api_key() == "abc123"


def test_set_window_excluded_non_windows(monkeypatch):
    import src.utils as utils
    monkeypatch.setattr(utils, "IS_WINDOWS", False)
    assert set_window_excluded_from_capture(0) is True
