"""Scope + authorization enforcement, SSRF protection, robots.txt and rate limiting."""
from __future__ import annotations

import ipaddress
import socket
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import requests

from .config import Config


class ScanNotAllowed(Exception):
    """Raised when a target is out of scope or authorization is missing."""


def is_url(target: str) -> bool:
    return target.strip().lower().startswith(("http://", "https://"))


def _is_private(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False  # fetch will fail later with a clear message
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


def validate_target(target: str, cfg: Config, authorized: bool) -> str:
    """Return 'url' or 'file' if the target is allowed, otherwise raise ScanNotAllowed."""
    if not authorized:
        raise ScanNotAllowed("Authorization not confirmed: tick the box confirming you may scan this target.")
    target = target.strip()
    if is_url(target):
        host = (urlparse(target).hostname or "").lower()
        if not host:
            raise ScanNotAllowed(f"Invalid URL: {target}")
        if not cfg.allowed_domains:
            raise ScanNotAllowed("No allowed domains configured. Set A11Y_ALLOWED_DOMAINS.")
        if not any(host == d or host.endswith("." + d) for d in cfg.allowed_domains):
            raise ScanNotAllowed(f"'{host}' is outside the allowed domains: {', '.join(cfg.allowed_domains)}")
        if not cfg.allow_private_hosts and _is_private(host):
            raise ScanNotAllowed(f"'{host}' resolves to a private/loopback address (blocked).")
        return "url"
    path = Path(target).expanduser().resolve()
    base = cfg.approved_local_dir.resolve()
    if base not in path.parents:
        raise ScanNotAllowed(f"Local file must be inside the approved directory: {base}")
    if path.suffix.lower() not in {".html", ".htm"} or not path.is_file():
        raise ScanNotAllowed(f"Not an existing .html/.htm file: {path}")
    return "file"


def robots_allowed(url: str, user_agent: str, timeout: int = 10) -> bool:
    """True if robots.txt permits fetching (or cannot be read: standard fail-open behaviour)."""
    try:
        robots_url = urljoin(url, "/robots.txt")
        resp = requests.get(robots_url, timeout=timeout, headers={"User-Agent": user_agent})
        if resp.status_code >= 400:
            return True
        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(user_agent, url)
    except requests.RequestException:
        return True


class RateLimiter:
    """Minimum delay between requests to the same host."""

    def __init__(self, min_delay_s: float):
        self.min_delay_s = min_delay_s
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> float:
        with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._last.get(host, 0.0) + self.min_delay_s - now)
            if wait:
                time.sleep(wait)
            self._last[host] = time.monotonic()
            return wait
