import pytest
from a11y_auditor.security import ScanNotAllowed, validate_target, RateLimiter
from conftest import FIX


def test_requires_authorization(cfg):
    with pytest.raises(ScanNotAllowed):
        validate_target("https://example.com", cfg, authorized=False)


def test_domain_scope(cfg):
    with pytest.raises(ScanNotAllowed):
        validate_target("https://evil.org/", cfg, authorized=True)


def test_private_blocked(cfg):
    cfg.allowed_domains = ["127.0.0.1"]
    with pytest.raises(ScanNotAllowed):
        validate_target("http://127.0.0.1:8000/", cfg, authorized=True)


def test_local_file_scope(cfg, tmp_path):
    assert validate_target(str(FIX / "good_page.html"), cfg, True) == "file"
    outside = tmp_path / "x.html"; outside.write_text("<html></html>")
    with pytest.raises(ScanNotAllowed):
        validate_target(str(outside), cfg, True)


def test_rate_limiter():
    rl = RateLimiter(0.05); rl.wait("h"); assert rl.wait("h") > 0
