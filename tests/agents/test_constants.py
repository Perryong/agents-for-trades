"""Tests for tradingagents.agents.options.constants module."""

from tradingagents.agents.options.constants import DTE_BUCKETS


def test_dte_buckets_importable():
    """DTE_BUCKETS can be imported from constants without ImportError."""
    assert DTE_BUCKETS is not None


def test_dte_buckets_has_four_entries():
    """DTE_BUCKETS contains exactly 4 bucket definitions."""
    assert len(DTE_BUCKETS) == 4


def test_each_bucket_has_required_keys():
    """Every bucket dict contains 'label', 'min', 'max', and 'tag' keys."""
    required_keys = {"label", "min", "max", "tag"}
    for bucket in DTE_BUCKETS:
        assert required_keys.issubset(bucket.keys()), (
            f"Bucket {bucket!r} is missing one or more required keys: {required_keys}"
        )


def test_bucket_tags_are_correct_and_ordered():
    """Tags are exactly ['SHORT', 'WEEKLY', 'MONTHLY', 'LONGER'] in order."""
    expected_tags = ["SHORT", "WEEKLY", "MONTHLY", "LONGER"]
    actual_tags = [b["tag"] for b in DTE_BUCKETS]
    assert actual_tags == expected_tags


def test_bucket_ranges_match_authoritative_source():
    """Bucket (min, max) ranges match the authoritative values in the plan."""
    expected_ranges = [(0, 5), (5, 14), (14, 45), (45, 90)]
    actual_ranges = [(b["min"], b["max"]) for b in DTE_BUCKETS]
    assert actual_ranges == expected_ranges
