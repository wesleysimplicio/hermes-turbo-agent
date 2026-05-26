from agent._hermes_fast import (
    estimate_messages_tokens,
    estimate_tokens,
    estimate_tokens_many,
    parse_tool_call_delta,
    truncate_messages_to_limit,
)


def test_estimate_tokens_many_matches_scalar_estimator():
    texts = ["", "a", "abcd", "abcde", "hello world"]

    assert estimate_tokens_many(texts) == [estimate_tokens(text) for text in texts]


def test_estimate_messages_tokens_counts_message_roles_and_content():
    messages = [
        {"role": "system", "content": "abcd"},
        {"role": "user", "content": "abcdefgh"},
    ]

    expected = (
        estimate_tokens("system")
        + estimate_tokens("abcd")
        + 4
        + estimate_tokens("user")
        + estimate_tokens("abcdefgh")
        + 4
    )
    assert estimate_messages_tokens(messages) == expected


def test_truncate_messages_to_limit_uses_message_token_budget():
    system = {"role": "system", "content": "keep"}
    drop = {"role": "user", "content": "x" * 80}
    tail = {"role": "assistant", "content": "keep"}
    limit = estimate_messages_tokens([system, tail])

    assert truncate_messages_to_limit([system, drop, tail], limit) == [system, tail]


def test_parse_tool_call_delta_handles_nested_tool_payloads():
    payload = (
        ' {"id":"tc_1","function":{"name":"search","arguments":"{\\"q\\":true}"},'
        '"items":[1,2.5,null],"ok":true} trailing'
    )

    ok, value, consumed = parse_tool_call_delta(payload)

    assert ok is True
    assert value["function"]["name"] == "search"
    assert value["function"]["arguments"] == '{"q":true}'
    assert value["items"] == [1, 2.5, None]
    assert value["ok"] is True
    assert payload[consumed:] == " trailing"
