"""Safe URL comparison keys that preserve the source URL for display."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class SourceUrlError(ValueError):
    """Raised when a source URL cannot be normalized safely."""


TRACKING_QUERY_PARAMETER_NAMES = frozenset(
    {
        "dclid",
        "fbclid",
        "gclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "vero_conv",
        "vero_id",
        "yclid",
    }
)
TRACKING_QUERY_PARAMETER_PREFIXES = ("utm_",)


def _is_tracking_parameter(name: str) -> bool:
    normalized = name.casefold()
    return normalized in TRACKING_QUERY_PARAMETER_NAMES or normalized.startswith(
        TRACKING_QUERY_PARAMETER_PREFIXES
    )


def normalize_source_url(url: str) -> str:
    """Return a conservative comparison key without changing source identity."""
    if not isinstance(url, str) or not url.strip() or url != url.strip():
        raise SourceUrlError("Source URL must be non-empty text without outer spaces.")
    parsed = urlsplit(url)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise SourceUrlError("Source URL must use HTTP or HTTPS and include a host.")
    if parsed.username is not None or parsed.password is not None:
        raise SourceUrlError("Source URL must not contain embedded credentials.")

    try:
        port = parsed.port
    except ValueError as error:
        raise SourceUrlError("Source URL contains an invalid port.") from error

    try:
        hostname = parsed.hostname.casefold().encode("idna").decode("ascii")
    except UnicodeError as error:
        raise SourceUrlError("Source URL contains an invalid host name.") from error
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        netloc = f"{display_host}:{port}"
    else:
        netloc = display_host

    query_pairs = [
        (name, value)
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_parameter(name)
    ]
    query_pairs.sort(key=lambda item: (item[0].casefold(), item[0], item[1]))

    return urlunsplit(
        (
            scheme,
            netloc,
            parsed.path or "/",
            urlencode(query_pairs, doseq=True),
            "",
        )
    )


def source_comparison_url(url: str, canonical_url: str | None = None) -> str:
    """Prefer a verified canonical URL when building a duplicate-comparison key."""
    return source_comparison_urls(url, canonical_url)[-1]


def source_comparison_urls(
    url: str,
    canonical_url: str | None = None,
) -> tuple[str, ...]:
    """Return every safe key needed to compare old and canonicalized records."""
    original = normalize_source_url(url)
    if canonical_url is None:
        return (original,)
    canonical = normalize_source_url(canonical_url)
    if canonical == original:
        return (original,)
    return (original, canonical)


def preferred_source_url(url: str, canonical_url: str | None = None) -> str:
    """Return the verified canonical URL for storage, or the original source URL."""
    source_comparison_urls(url, canonical_url)
    return canonical_url or url
