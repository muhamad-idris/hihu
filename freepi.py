import argparse
import time
import webbrowser
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests


API_BASE_URL = "https://api.freepi.ai"
BASE_URL = f"{API_BASE_URL}/v1"
MODELS_URL = "https://freepi.ai/models"
CONSENT_VERSION = "4"
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": "node",
    "Accept-Encoding": "br, gzip, deflate, zstd",
    "Content-Type": "application/json",
    "accept-language": "*",
    "sec-fetch-mode": "cors",
}


class FreepiError(Exception):
    """Raised when Freepi returns an unusable response."""


def post_json(
    session: requests.Session,
    endpoint: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    response = session.post(
        f"{API_BASE_URL}{endpoint}",
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    try:
        body = response.json()
    except ValueError as error:
        raise FreepiError(f"Respons dari {endpoint} bukan JSON yang valid.") from error

    if not isinstance(body, dict):
        raise FreepiError(f"Respons dari {endpoint} harus berupa objek JSON.")
    return body


def required_string(body: Dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value:
        raise FreepiError(f"Respons API tidak berisi nilai {key!r} yang valid.")
    return value


def create_guest(session: requests.Session) -> Dict[str, Any]:
    return post_json(
        session,
        "/auth/guest",
        {"consent_version": CONSENT_VERSION},
        HEADERS,
    )


def start_login(session: requests.Session) -> Dict[str, Any]:
    return post_json(
        session,
        "/auth/connect/start",
        {
            "consent_version": CONSENT_VERSION,
            "client": {"os": "linux", "cli_version": "0.6.10"},
        },
        HEADERS,
    )


def poll_login(session: requests.Session, login: Dict[str, Any]) -> str:
    session_id = required_string(login, "session_id")
    poll_secret = required_string(login, "poll_secret")
    authorization = required_string(login, "token")

    try:
        interval = max(0.5, float(login["interval"]))
        expires_in = float(login["expires_in"])
    except (KeyError, TypeError, ValueError) as error:
        raise FreepiError("Respons API tidak berisi interval atau masa berlaku yang valid.") from error
    if expires_in <= 0:
        raise FreepiError("Sesi login sudah kedaluwarsa.")

    deadline = time.monotonic() + expires_in
    poll_headers = {**HEADERS, "authorization": authorization}
    print("Menunggu konfirmasi login...")

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FreepiError("Waktu tunggu login habis. Jalankan login kembali.")

        result = post_json(
            session,
            "/auth/connect/poll",
            {"session_id": session_id, "poll_secret": poll_secret},
            poll_headers,
        )
        token = result.get("token")
        if isinstance(token, str) and token:
            return token

        status = result.get("status")
        if (isinstance(status, str) and status.lower() in {"expired", "denied", "error"}) or result.get("error"):
            detail = result.get("error") or status
            raise FreepiError(f"Login gagal: {detail}")

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FreepiError("Waktu tunggu login habis. Jalankan login kembali.")
        time.sleep(min(interval, remaining))


def show_api_key(token: str) -> None:
    print(
        f"\nBaseUrl : {BASE_URL}"
        f"\nModels  : {MODELS_URL}"
        f"\nApiKey  : {token}"
    )


def run_guest_flow(session: requests.Session) -> None:
    result = create_guest(session)
    token = required_string(result, "token")
    show_api_key(token)
    print()
    # if result.get("claim_code"):
    #     print(f"Claim   : {result['claim_code']}")


def run_login_flow(session: requests.Session) -> None:
    login = start_login(session)
    connect_url = required_string(login, "connect_url")
    parsed_url = urlparse(connect_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "freepi.ai":
        raise FreepiError("Tautan konfirmasi login bukan URL Freepi yang aman.")

    print(f"Kode konfirmasi: {required_string(login, 'confirm_code')}")
    print(f"Buka tautan ini untuk login: {connect_url}")
    try:
        browser_opened = webbrowser.open(connect_url)
    except webbrowser.Error:
        browser_opened = False
    if not browser_opened:
        print("Browser tidak dapat dibuka otomatis; silakan buka tautan di atas.")

    token = poll_login(session, login)
    show_api_key(token)


def choose_mode() -> str:
    print("Pilih metode akses:")
    print("1. Guest")
    print("2. Login akun Freepi [15.000 Credit]")
    while True:
        choice = input("Pilihan [1/2]: ").strip()
        if choice == "1":
            return "guest"
        if choice == "2":
            return "login"
        print("Pilihan tidak valid. Masukkan 1 atau 2.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Buat API key Freepi sebagai guest atau login.")
    parser.add_argument("--mode", choices=("guest", "login"), help="Metode akses; tanpa opsi akan ditanyakan.")
    args = parser.parse_args(argv)
    mode = args.mode or choose_mode()

    try:
        with requests.Session() as session:
            if mode == "guest":
                run_guest_flow(session)
            else:
                run_login_flow(session)
    except requests.RequestException as error:
        print(f"Permintaan ke Freepi gagal: {error}")
        return 1
    except FreepiError as error:
        print(f"Error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
