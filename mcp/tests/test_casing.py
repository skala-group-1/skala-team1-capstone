from mcp_common.casing import keys_to_camel, keys_to_snake


def test_round_trip():
    camel = {"holdExpiresAt": "x", "slot": {"doctorId": 1}, "items": [{"priceKrw": 1}]}
    snake = keys_to_snake(camel)
    assert snake == {"hold_expires_at": "x", "slot": {"doctor_id": 1}, "items": [{"price_krw": 1}]}
    assert keys_to_camel(snake) == camel
