from __future__ import annotations

from .token_saver import compress_command_output, compress_tool_result


def _mode() -> str:
    import os

    return os.getenv("HERMES_TOKEN_SAVER_MODE", "safe").strip().lower() or "safe"


def _min_chars() -> int:
    import os

    try:
        return int(os.getenv("HERMES_TOKEN_SAVER_MIN_CHARS", "1200"))
    except ValueError:
        return 1200


def _transform_terminal_output(**kwargs):
    return compress_command_output(
        command=str(kwargs.get("command") or ""),
        output=str(kwargs.get("output") or ""),
        returncode=int(kwargs.get("returncode") or 0),
        mode=_mode(),
        min_chars=_min_chars(),
    )


def _transform_tool_result(**kwargs):
    return compress_tool_result(
        tool_name=str(kwargs.get("tool_name") or ""),
        result=str(kwargs.get("result") or ""),
        mode=_mode(),
        min_chars=_min_chars(),
    )


def register(ctx):
    ctx.register_hook("transform_terminal_output", _transform_terminal_output)
    ctx.register_hook("transform_tool_result", _transform_tool_result)
