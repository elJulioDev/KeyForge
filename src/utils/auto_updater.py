"""Check for and open new releases from GitHub Releases."""

import requests
import webbrowser
from packaging import version
from src.config.constants import CURRENT_VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME

class AutoUpdater:
    """Update manager backed by GitHub Releases."""

    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

    def check_for_updates(self):
        """
        Query the GitHub API to see if a newer version exists.
        Returns: (has_update: bool, info: dict/str)
        """
        try:
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()

            data = response.json()
            latest_tag = data.get("tag_name", "v0.0.0")

            # Stripping the 'v' to compare bare numbers is not needed,
            # packaging.version handles 'v1.4.0' correctly.
            current_v = version.parse(CURRENT_VERSION)
            latest_v = version.parse(latest_tag)

            if latest_v > current_v:
                return True, {
                    "version": latest_tag,
                    "url": data.get("html_url", ""),
                    "body": data.get("body", "")
                }
            else:
                return False, CURRENT_VERSION

        except Exception as e:
            return False, str(e)

    def open_download_page(self, url):
        """Open the release page in the default browser."""
        if url:
            webbrowser.open(url)