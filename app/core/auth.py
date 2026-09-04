import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CLIENT_ID = "Ov23liT0WwQvkS2gxWhj"

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
SCOPES = "repo"


def copy_to_clipboard(text: str) -> bool:
    """Copies text to clipboard on Linux (Wayland/X11) or macOS."""
    clipboard_tools = [
        ("wl-copy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard", "--input"]),
        ("pbcopy", []),
    ]

    for tool, args in clipboard_tools:
        if shutil.which(tool):
            try:
                subprocess.run(
                    [tool] + args,
                    input=text.encode("utf-8"),
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception:
                continue
    return False


def request_device_code(client_id: str) -> dict:
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "scope": SCOPES,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEVICE_CODE_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "User-Agent": "gh-backup-cli",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8")
        sys.exit(f"Error requesting device code: {err.code} - {error_body}")


def poll_for_token(client_id: str, device_code: str, interval: int) -> str:
    payload = urllib.parse.urlencode({
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "User-Agent": "gh-backup-cli",
        },
    )

    while True:
        time.sleep(interval)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode("utf-8"))

            if "access_token" in data:
                return data["access_token"]

            error = data.get("error")
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5
            elif error == "expired_token":
                sys.exit("Verification code expired. Please run the login command again.")
            elif error == "access_denied":
                sys.exit("Login cancelled by user.")
            else:
                sys.exit(f"Unexpected authorization error: {error}")

        except urllib.error.HTTPError as err:
            sys.exit(f"HTTP communication error: {err}")


def save_token_to_env(token: str, env_path: Path = Path(".env")) -> None:
    lines = []
    token_written = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_lines = []
    for line in lines:
        if line.startswith("GITHUB_TOKEN="):
            updated_lines.append(f"GITHUB_TOKEN={token}\n")
            token_written = True
        else:
            updated_lines.append(line)

    if not token_written:
        updated_lines.append(f"GITHUB_TOKEN={token}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)


def main():
    client_id = os.getenv("GITHUB_CLIENT_ID", CLIENT_ID)

    if not client_id or client_id == "YOUR_CLIENT_ID_HERE":
        sys.exit(
            "Error: Client ID is missing. "
            "Please configure CLIENT_ID in app/core/auth.py or set GITHUB_CLIENT_ID environment variable."
        )

    print("Requesting device authorization from GitHub...")
    device_data = request_device_code(client_id)

    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    device_code = device_data["device_code"]
    interval = device_data.get("interval", 5)

    # Automatically copy code to clipboard
    is_copied = copy_to_clipboard(user_code)

    print("\n" + "=" * 50)
    print(f"One-time code:       {user_code}")
    if is_copied:
        print("Status:              Code copied to clipboard! (Press Ctrl+V in browser)")
    print(f"Verification URL:    {verification_uri}")
    print("=" * 50 + "\n")

    print("Opening browser...")
    try:
        webbrowser.open(verification_uri)
    except Exception:
        print("Could not open browser automatically. Please open the URL manually.")

    print("Waiting for confirmation in browser...")
    token = poll_for_token(client_id, device_code, interval)

    save_token_to_env(token)
    print("\nSuccess: Successfully authenticated and saved token to .env file.")


if __name__ == "__main__":
    main()