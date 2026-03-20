import os
import sys
from pathlib import Path

# Ensure the backend directory is in sys.path so 'app' can be imported
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.core.config import settings

@pytest.fixture(autouse=True)
def override_blog_digest_interval(request, monkeypatch):
    """
    Automatically override the blog digest interval for tests related to this feature.
    """
    # Check if the test is in a file related to the blog digest feature
    relevant_files = ["test_automated_job.py", "test_jobs.py"]
    if any(rf in request.node.fspath.strpath for rf in relevant_files):
        # Use monkeypatch to safely override the setting for the duration of the test
        monkeypatch.setattr(settings, "AUTO_BLOG_DIGEST_INTERVAL_SECONDS", 10)
