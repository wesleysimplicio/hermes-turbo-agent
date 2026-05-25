"""Networking primitives (Proposta J — HTTP/2 connection pool)."""

from agent.net.http_pool import HttpPool, HttpPoolUnavailable

__all__ = ["HttpPool", "HttpPoolUnavailable"]
