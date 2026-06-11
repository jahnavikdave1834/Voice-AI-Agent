from config.settings import Settings


def test_settings_exposes_base_year():
    assert Settings.model_fields["BASE_YEAR"].default == 2026
