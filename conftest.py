import pytest
from pathlib import Path
from a11y_auditor.config import Config, load_rules

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def rules():
    return load_rules()

@pytest.fixture
def cfg(tmp_path):
    return Config(allowed_domains=["example.com"], approved_local_dir=FIX, db_path=tmp_path / "t.db",
                  min_delay_s=0, respect_robots=False)
