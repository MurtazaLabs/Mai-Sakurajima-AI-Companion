"""Shared SSRF guard for outbound HTTP (plugins, research).

One implementation so a scraper plugin and a research fetcher cannot drift on
what counts as a public destination.
"""
from __future__ import annotations

import ipaddress
import os
import socket
import urllib.error
from urllib.parse import urlparse


def private_targets_allowed() -> bool:
    return os.environ.get("MAI_SCRAPER_ALLOW_PRIVATE", "").strip().lower() in (
        "1", "true", "yes",
    )


def resolves_to_public_ip(url: str) -> bool:
    """True when EVERY resolved address for the host is globally routable."""
    host = urlparse(url).hostname
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError, UnicodeError):
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def require_public_target(url: str) -> None:
    """Refuse private/loopback/link-local destinations."""
    if private_targets_allowed():
        return
    if not resolves_to_public_ip(url):
        raise urllib.error.URLError(f"Blocked non-public target: {url}")


def ip_is_non_public(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )
