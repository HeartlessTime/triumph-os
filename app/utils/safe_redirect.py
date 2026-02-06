"""Safe redirect URL validation to prevent open redirect attacks."""

from urllib.parse import urlparse


def safe_redirect_url(url: str, fallback: str = "/") -> str:
    """Validate a redirect URL is a safe relative path.

    Only allows relative URLs starting with '/'.
    Rejects absolute URLs, protocol-relative URLs, and malformed paths.
    Returns fallback if the URL is invalid.
    """
    if not url or not isinstance(url, str):
        return fallback

    url = url.strip()

    # Must start with /
    if not url.startswith("/"):
        return fallback

    # Reject protocol-relative URLs like //evil.com
    if url.startswith("//"):
        return fallback

    # Parse and verify no scheme or netloc
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return fallback

    return url
