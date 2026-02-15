from farmbot_actions import light_off, light_on


def test_light_on_default_peripheral():
    result = light_on({})
    assert result == {"peripheral": 7, "state": "on"}


def test_light_off_default_peripheral():
    result = light_off({})
    assert result == {"peripheral": 7, "state": "off"}
