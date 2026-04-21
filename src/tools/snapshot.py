"""Snapshot caching for scraped LinkedIn data.

Stores scraped profile and company data as JSON files inside
``data/snapshots/<company_name>/`` so that expensive Playwright scraping
can be skipped on subsequent runs (e.g. after an AI-pipeline failure).
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse


_SNAPSHOT_ROOT = Path("data/snapshots")
_FALLBACK_COMPANY = "unknown_company"


def _slug_from_url(url: str) -> str:
    """Extract the last meaningful path segment from a LinkedIn URL.

    Examples
    -------
    >>> _slug_from_url("https://www.linkedin.com/in/john-doe/")
    'john-doe'
    >>> _slug_from_url("https://www.linkedin.com/company/google/")
    'google'
    """
    path = urlparse(url).path.rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    # Sanitise for filesystem safety
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug or "unknown"


class SnapshotManager:
    """Read / write JSON snapshots of scraped LinkedIn data.

    Directory layout::

        data/snapshots/
        └── <company_slug>/
            ├── company_profile.json
            ├── <user_slug>_profile.json
            └── <user_slug>_profile.json
    """

    def __init__(self, root: Path = _SNAPSHOT_ROOT) -> None:
        self.root = root

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _company_dir(self, company_url: str | None) -> Path:
        if company_url:
            slug = _slug_from_url(company_url)
        else:
            slug = _FALLBACK_COMPANY
        return self.root / slug

    @staticmethod
    def _user_filename(profile_url: str) -> str:
        return f"{_slug_from_url(profile_url)}_profile.json"

    # ------------------------------------------------------------------
    # Profile snapshots
    # ------------------------------------------------------------------

    def has_profile(self, profile_url: str, company_url: str | None) -> bool:
        """Return *True* if a cached profile snapshot exists."""
        path = self._company_dir(company_url) / self._user_filename(profile_url)
        return path.exists()

    def load_profile(self, profile_url: str, company_url: str | None) -> dict[str, str]:
        """Load a previously saved profile snapshot."""
        path = self._company_dir(company_url) / self._user_filename(profile_url)
        return json.loads(path.read_text(encoding="utf-8"))

    def save_profile(
        self,
        profile_url: str,
        company_url: str | None,
        data: dict[str, str],
    ) -> Path:
        """Persist scraped profile data and return the file path."""
        directory = self._company_dir(company_url)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / self._user_filename(profile_url)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path

    # ------------------------------------------------------------------
    # Company snapshots
    # ------------------------------------------------------------------

    def has_company(self, company_url: str) -> bool:
        """Return *True* if a cached company snapshot exists."""
        path = self._company_dir(company_url) / "company_profile.json"
        return path.exists()

    def load_company(self, company_url: str) -> dict[str, str]:
        """Load a previously saved company snapshot."""
        path = self._company_dir(company_url) / "company_profile.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def save_company(
        self,
        company_url: str,
        data: dict[str, str],
    ) -> Path:
        """Persist scraped company data and return the file path."""
        directory = self._company_dir(company_url)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "company_profile.json"
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return path
