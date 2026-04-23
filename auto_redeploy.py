# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://api.containers.back4app.com"
STATE_FILE = "runtime_state.json"
BEIJING_TZ = timezone(timedelta(hours=8))
QUIET_START_HOUR = 1
ACTIVE_START_HOUR = 6
WINDOW_DELAY_MINUTES = 55
WINDOW_DURATION_MINUTES = 10
CYCLE_INTERVAL_MINUTES = 60
def build_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "auto-deploy/1.0", "Connection": "close"})
    return session


def load_runtime_config():
    load_dotenv(override=True)
    cookie = os.getenv("BACK4APP_COOKIE", "").strip()
    raw_app_id_map = os.getenv("APP_ID_MAP_JSON", "").strip()

    app_id_map = {}
    if raw_app_id_map:
        try:
            parsed = json.loads(raw_app_id_map)
            if isinstance(parsed, dict):
                app_id_map = {str(key): str(value) for key, value in parsed.items() if value}
            else:
                raise ValueError("APP_ID_MAP_JSON must be a JSON object")
        except Exception as exc:
            raise RuntimeError(f"APP_ID_MAP_JSON parse failed: {exc}") from exc

    headers = {
        "Content-type": "application/json",
        "Cookie": cookie,
        "Referer": "https://dashboard.back4app.com/",
    }
    return cookie, headers, app_id_map


def ensure_cookie_present(cookie):
    if cookie:
        return
    raise RuntimeError(
        "Missing BACK4APP_COOKIE. Run `python get_cookie.py` first or set BACK4APP_COOKIE in .env"
    )


def now_in_beijing():
    return datetime.now(BEIJING_TZ)


def parse_timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def format_timestamp(value):
    return value.isoformat(timespec="seconds")


def load_runtime_state():
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError as exc:
            logger.warning("State file {} is invalid, reset it: {}", STATE_FILE, exc)
            return {}


def save_runtime_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, ensure_ascii=False)


def is_quiet_hours(current_time):
    return QUIET_START_HOUR <= current_time.hour < ACTIVE_START_HOUR


def compute_window(anchor_time):
    window_start = anchor_time + timedelta(minutes=WINDOW_DELAY_MINUTES)
    window_end = window_start + timedelta(minutes=WINDOW_DURATION_MINUTES)
    return window_start, window_end


def get_anchor_time(state, current_time):
    anchor_time = parse_timestamp(state.get("anchor_time"))
    if anchor_time is None:
        # Bootstrap with an immediate detection window after first startup.
        anchor_time = current_time - timedelta(minutes=WINDOW_DELAY_MINUTES)
        state["anchor_time"] = format_timestamp(anchor_time)
        save_runtime_state(state)
        logger.info("Initialized detection anchor at {}", format_timestamp(anchor_time))
    return anchor_time


def align_anchor_time(state, current_time):
    anchor_time = get_anchor_time(state, current_time)
    advanced = False

    while True:
        _, window_end = compute_window(anchor_time)
        if current_time < window_end:
            break
        anchor_time += timedelta(minutes=CYCLE_INTERVAL_MINUTES)
        advanced = True

    if advanced:
        state["anchor_time"] = format_timestamp(anchor_time)
        save_runtime_state(state)

    return anchor_time


def set_anchor_time(state, anchor_time):
    state["anchor_time"] = format_timestamp(anchor_time)
    state["last_deploy_time"] = format_timestamp(anchor_time)
    save_runtime_state(state)


def update_env_app_id_map(app_id, service_env_id, env_path=".env"):
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()

    raw_value = ""
    for line in lines:
        if line.strip().startswith("APP_ID_MAP_JSON="):
            raw_value = line.split("=", 1)[1].strip()
            break

    current_map = {}
    if raw_value:
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                current_map = {str(key): str(value) for key, value in parsed.items() if value}
        except Exception as exc:
            logger.warning("Failed to parse existing APP_ID_MAP_JSON, overwrite with new mapping: {}", exc)

    app_id = str(app_id)
    service_env_id = str(service_env_id)
    if current_map.get(app_id) == service_env_id:
        return current_map

    current_map[app_id] = service_env_id
    new_line = f"APP_ID_MAP_JSON={json.dumps(current_map, ensure_ascii=False)}"

    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("APP_ID_MAP_JSON="):
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(new_line)

    with open(env_path, "w", encoding="utf-8") as file:
        file.write("\n".join(new_lines) + "\n")

    os.environ["APP_ID_MAP_JSON"] = json.dumps(current_map, ensure_ascii=False)
    logger.success("Persisted APP_ID_MAP_JSON mapping: {} -> {}", app_id, service_env_id)
    return current_map


def request_graphql(payload, headers):
    session = build_session()
    try:
        response = session.post(API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response
    except requests.exceptions.SSLError as exc:
        logger.warning("GraphQL SSL error: {}", exc)
        raise
    except requests.RequestException as exc:
        logger.warning("GraphQL request failed: {}", exc)
        raise
    finally:
        session.close()


def fetch_apps(headers):
    payload = {
        "query": (
            "query Apps { apps { id name mainService { repository { fullName } "
            "mainServiceEnvironment { id } mainServiceEnvironment { mainCustomDomain { status } } } } }"
        )
    }
    response = request_graphql(payload, headers)
    data = response.json()
    return data.get("data", {}).get("apps", [])


def try_refresh_cookie():
    logger.warning("Cookie may be invalid, trying to refresh it")
    import get_cookie

    get_cookie.main()
    cookie, headers, _ = load_runtime_config()
    ensure_cookie_present(cookie)
    return headers


def list_apps():
    cookie, headers, _ = load_runtime_config()
    ensure_cookie_present(cookie)
    try:
        apps = fetch_apps(headers)
    except Exception as exc:
        logger.warning("Fetch app list failed: {}", exc)
        try:
            headers = try_refresh_cookie()
            apps = fetch_apps(headers)
        except Exception as refresh_exc:
            logger.error("Fetch app list still failed after cookie refresh: {}", refresh_exc)
            return []

    logger.info("Fetched {} apps", len(apps))
    for app in apps:
        logger.info(
            "App: name={}, app_id={}, service_env_id={}, domain_status={}",
            app["mainService"]["repository"]["fullName"],
            app["id"],
            app["mainService"]["mainServiceEnvironment"]["id"],
            app["mainService"]["mainServiceEnvironment"]["mainCustomDomain"]["status"],
        )
    return apps


def resolve_service_env_id(app, app_id_map):
    return app_id_map.get(app["id"], "")


def trigger_deploy(service_env_id, headers):
    payload = {
        "operationName": "triggerManualDeployment",
        "variables": {"serviceEnvironmentId": service_env_id},
        "query": (
            "mutation triggerManualDeployment($serviceEnvironmentId: String!) { "
            "triggerManualDeployment(serviceEnvironmentId: $serviceEnvironmentId) { id status } }"
        ),
    }

    try:
        response = request_graphql(payload, headers)
        if response.status_code == 200 and "error" not in response.text:
            return True
        logger.error("Deploy response: {}", response.text)
    except Exception as exc:
        logger.error("Trigger deploy failed: {}", exc)
    return False


def auto_redeploy():
    cookie, headers, app_id_map = load_runtime_config()
    ensure_cookie_present(cookie)

    current_time = now_in_beijing()
    if is_quiet_hours(current_time):
        logger.info("Quiet hours in effect (UTC+8), skip checks until 06:00")
        return

    state = load_runtime_state()
    anchor_time = align_anchor_time(state, current_time)
    window_start, window_end = compute_window(anchor_time)
    if current_time < window_start:
        logger.info(
            "Detection window not started yet, next window: {} to {} (UTC+8)",
            format_timestamp(window_start),
            format_timestamp(window_end),
        )
        return

    logger.info(
        "Detection window active: {} to {} (UTC+8)",
        format_timestamp(window_start),
        format_timestamp(window_end),
    )

    apps = list_apps()
    if not apps:
        logger.warning("No apps fetched, skipping this round")
        return

    for app in apps:
        app_name = app["mainService"]["repository"]["fullName"]
        domain_status = app["mainService"]["mainServiceEnvironment"]["mainCustomDomain"]["status"]
        env_id = resolve_service_env_id(app, app_id_map)

        if domain_status != "EXPIRED":
            logger.info("{} status is normal: {}", app_name, domain_status)
            continue

        if not env_id:
            discovered_env_id = app["mainService"]["mainServiceEnvironment"]["id"]
            if discovered_env_id:
                app_id_map = update_env_app_id_map(app["id"], discovered_env_id)
                env_id = app_id_map.get(app["id"], "")
                logger.warning(
                    "{} mapping was missing and has been written to .env: {} -> {}",
                    app_name,
                    app["id"],
                    discovered_env_id,
                )
            else:
                logger.warning("{} missing service environment id mapping", app_name)
                continue

        logger.warning("{} domain expired, triggering redeploy", app_name)
        if trigger_deploy(env_id, headers):
            deploy_time = now_in_beijing()
            set_anchor_time(state, deploy_time)
            logger.success("{} deploy triggered successfully", app_name)
        else:
            logger.error("{} deploy failed", app_name)


def main():
    logger.remove()
    logger.add(sys.stdout, level=os.getenv("LOG_LEVEL", "INFO"))
    auto_redeploy()


if __name__ == "__main__":
    main()
