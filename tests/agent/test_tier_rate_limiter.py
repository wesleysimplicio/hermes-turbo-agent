"""Tests for agent/tier_rate_limiter.py."""

from unittest.mock import patch

from agent.tier_rate_limiter import TierRateLimiter


def test_allows_up_to_capacity_then_rejects():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        # capacity defaults to rate_per_minute -> 3 tokens available up front.
        assert limiter.try_acquire("leaf", rate_per_minute=3) is True
        assert limiter.try_acquire("leaf", rate_per_minute=3) is True
        assert limiter.try_acquire("leaf", rate_per_minute=3) is True
        assert limiter.try_acquire("leaf", rate_per_minute=3) is False


def test_refills_over_time():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        # Explicit capacity=1 so a single acquire exhausts the bucket.
        assert limiter.try_acquire("leaf", rate_per_minute=60, capacity=1) is True
        assert limiter.try_acquire("leaf", rate_per_minute=60, capacity=1) is False
    # 60/min == 1/sec; after 1s exactly one token should be available again.
    with patch("time.monotonic", return_value=1001.0):
        assert limiter.try_acquire("leaf", rate_per_minute=60, capacity=1) is True
        assert limiter.try_acquire("leaf", rate_per_minute=60, capacity=1) is False


def test_tiers_are_independent():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        assert limiter.try_acquire("leaf", rate_per_minute=1) is True
        assert limiter.try_acquire("leaf", rate_per_minute=1) is False
        # A different tier has its own bucket, unaffected by "leaf" exhaustion.
        assert limiter.try_acquire("planner", rate_per_minute=1) is True


def test_explicit_capacity_overrides_rate_derived_default():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        # rate_per_minute=120 would normally give a burst of 120, but an
        # explicit capacity=2 caps the initial burst regardless.
        assert limiter.try_acquire("leaf", rate_per_minute=120, capacity=2) is True
        assert limiter.try_acquire("leaf", rate_per_minute=120, capacity=2) is True
        assert limiter.try_acquire("leaf", rate_per_minute=120, capacity=2) is False


def test_reset_single_tier_leaves_others_untouched():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        assert limiter.try_acquire("leaf", rate_per_minute=1) is True
        assert limiter.try_acquire("planner", rate_per_minute=1) is True

        limiter.reset("leaf")

        # "leaf" bucket was cleared -> fresh full bucket -> allowed again.
        assert limiter.try_acquire("leaf", rate_per_minute=1) is True
        # "planner" was untouched -> still exhausted.
        assert limiter.try_acquire("planner", rate_per_minute=1) is False


def test_reset_all_clears_every_tier():
    limiter = TierRateLimiter()
    with patch("time.monotonic", return_value=1000.0):
        limiter.try_acquire("leaf", rate_per_minute=1)
        limiter.try_acquire("planner", rate_per_minute=1)

        limiter.reset()

        assert limiter.try_acquire("leaf", rate_per_minute=1) is True
        assert limiter.try_acquire("planner", rate_per_minute=1) is True
