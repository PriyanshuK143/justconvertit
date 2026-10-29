"""Product posture: one-time install, offline-first, no remote services.

These constants are intentional product guarantees. Application code must not
add update checkers, telemetry, accounts, or cloud conversion endpoints.
"""

from __future__ import annotations

# Public product name (UI, installers, docs).
APP_NAME: str = "justconvertit"

# Core conversions run entirely on-device after installation.
OFFLINE_FIRST: bool = True

# No accounts, subscriptions, licensing servers, or mandatory sign-in.
REQUIRES_ACCOUNT: bool = False
REQUIRES_INTERNET: bool = False

# Explicitly disabled — rebuild and redistribute installers manually instead.
IN_APP_UPDATE_CHECKER: bool = False
AUTOMATIC_UPDATES: bool = False
TELEMETRY_ENABLED: bool = False
REMOTE_ANALYTICS: bool = False
CLOUD_CONVERSION: bool = False

# Optional engines are discovered only via local PATH / known binary names.
# First-run may invoke the OS package manager (apt/winget) with user consent;
# justconvertit never downloads engine binaries into its own install tree.
OPTIONAL_ENGINES_LOCAL_ONLY: bool = True

PRIVACY_SUMMARY: str = (
    "Your files stay on your computer. Nothing is uploaded. No account needed."
)

ABOUT_BLURB: str = (
    "justconvertit — a simple local file converter. Install once, use offline.\n"
    "Drop a file, pick a format, done. No accounts, no cloud, no fuss.\n\n"
    "I made this a little bit — hope it helps.\n"
    "Free to use (MIT)."
)

# Modules that must never appear as imports under src/omniconvert.
FORBIDDEN_NETWORK_MODULES: frozenset[str] = frozenset(
    {
        "urllib",
        "urllib.request",
        "urllib.error",
        "http",
        "http.client",
        "httplib",
        "requests",
        "httpx",
        "aiohttp",
        "websocket",
        "websockets",
        "ftplib",
        "smtplib",
        "socketserver",
    }
)
