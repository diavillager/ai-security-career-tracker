from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_security_career_tracker.source_urls import (
    SourceUrlError,
    normalize_source_url,
    preferred_source_url,
    source_comparison_url,
    source_comparison_urls,
)


class SourceUrlTests(unittest.TestCase):
    def test_tracking_parameters_fragment_host_and_default_port_are_normalized(self) -> None:
        normalized = normalize_source_url(
            "HTTPS://Example.COM:443/report?b=2&utm_source=newsletter&a=1#section"
        )

        self.assertEqual(normalized, "https://example.com/report?a=1&b=2")

    def test_root_url_and_query_order_have_stable_comparison_keys(self) -> None:
        self.assertEqual(
            normalize_source_url("https://example.com?z=2&a=1"),
            "https://example.com/?a=1&z=2",
        )

    def test_meaningful_query_parameters_are_preserved(self) -> None:
        normalized = normalize_source_url(
            "https://example.com/article?id=42&lang=ko&fbclid=tracking"
        )

        self.assertEqual(normalized, "https://example.com/article?id=42&lang=ko")

    def test_non_default_port_is_preserved(self) -> None:
        self.assertEqual(
            normalize_source_url("http://Example.com:8080/path"),
            "http://example.com:8080/path",
        )

    def test_embedded_credentials_are_rejected(self) -> None:
        with self.assertRaises(SourceUrlError):
            normalize_source_url("https://user:secret@example.com/report")

    def test_canonical_url_is_used_for_comparison_and_storage(self) -> None:
        original = "https://aggregator.example/item?utm_source=search"
        canonical = "https://publisher.example/report"

        self.assertEqual(source_comparison_url(original, canonical), canonical)
        self.assertEqual(
            source_comparison_urls(original, canonical),
            (
                "https://aggregator.example/item",
                "https://publisher.example/report",
            ),
        )
        self.assertEqual(preferred_source_url(original, canonical), canonical)

    def test_original_credentials_are_rejected_even_with_safe_canonical(self) -> None:
        with self.assertRaises(SourceUrlError):
            source_comparison_url(
                "https://user:secret@example.com/report",
                "https://example.com/report",
            )

    def test_original_url_is_not_rewritten_for_storage_without_canonical(self) -> None:
        original = "https://example.com/report?utm_source=newsletter"

        self.assertEqual(preferred_source_url(original), original)
        self.assertNotEqual(preferred_source_url(original), normalize_source_url(original))


if __name__ == "__main__":
    unittest.main()
