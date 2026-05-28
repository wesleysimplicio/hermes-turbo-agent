"""Transport layer types and registry for provider response normalization.

Usage:
    from agent.transports import get_transport
    transport = get_transport("anthropic_messages")
    result = transport.normalize_response(raw_response)
"""

from functools import wraps

from agent.transports.types import (
    NormalizedResponse,
    ToolCall,
    Usage,
    build_tool_call,
    map_finish_reason,
)  # noqa: F401

_REGISTRY: dict = {}
_discovered: bool = False


def _prepare_messages(messages):
    try:
        from agent.simplicio_prompt import apply_simplicio_prompt

        return apply_simplicio_prompt(messages)
    except Exception:
        return messages


def _wrap_transport_class(transport_cls: type) -> type:
    build_kwargs = getattr(transport_cls, "build_kwargs", None)
    if build_kwargs is None or getattr(build_kwargs, "_simplicio_prompt_prepared", False):
        return transport_cls

    @wraps(build_kwargs)
    def _wrapped_build_kwargs(self, model, messages, tools=None, **params):
        return build_kwargs(
            self,
            model,
            _prepare_messages(messages),
            tools=tools,
            **params,
        )

    setattr(_wrapped_build_kwargs, "_simplicio_prompt_prepared", True)
    setattr(transport_cls, "build_kwargs", _wrapped_build_kwargs)
    return transport_cls


def register_transport(api_mode: str, transport_cls: type) -> None:
    """Register a transport class for an api_mode string."""
    _REGISTRY[api_mode] = _wrap_transport_class(transport_cls)


def get_transport(api_mode: str):
    """Get a transport instance for the given api_mode.

    Returns None if no transport is registered for this api_mode.
    This allows gradual migration — call sites can check for None
    and fall back to the legacy code path.
    """
    global _discovered
    if not _discovered:
        _discover_transports()
    cls = _REGISTRY.get(api_mode)
    if cls is None:
        # The registry can be partially populated when a specific transport
        # module was imported directly (for example chat_completions before
        # codex).  Discover on misses, not only when the registry is empty, so
        # test/order-dependent imports do not make valid api_modes unavailable.
        _discover_transports()
        cls = _REGISTRY.get(api_mode)
    if cls is None:
        return None
    return cls()


def _discover_transports() -> None:
    """Import all transport modules to trigger auto-registration."""
    global _discovered
    _discovered = True
    try:
        import agent.transports.anthropic  # noqa: F401
    except ImportError:
        pass
    try:
        import agent.transports.codex  # noqa: F401
    except ImportError:
        pass
    try:
        import agent.transports.chat_completions  # noqa: F401
    except ImportError:
        pass
    try:
        import agent.transports.bedrock  # noqa: F401
    except ImportError:
        pass
