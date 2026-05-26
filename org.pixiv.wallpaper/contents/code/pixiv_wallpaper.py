#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import mimetypes
import os
import secrets
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


APP_API = "https://app-api.pixiv.net"
OAUTH_API = "https://oauth.secure.pixiv.net"
ALT_APP_API = "https://210.140.131.199"
ALT_OAUTH_API = "https://210.140.131.219"
PIXIV_IMAGE_HOST = "i.pximg.net"
ALT_IMAGE_HOST = "i.pixiv.re"
CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
HASH_SECRET = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
USER_AGENT = "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)"
LOGIN_URI = "pixiv://account/login"
LOGIN_INIT_URI = "pixiv-plasma-wallpaper://login"
ROTATE_NOW_URI = "pixiv-plasma-wallpaper://rotate-now"
FETCH_NOW_URI = "pixiv-plasma-wallpaper://fetch-now"
OAUTH_REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "pixiv-plasma-wallpaper"
INTEGRATION_DIR = Path.home() / ".local" / "share" / "pixiv-plasma-wallpaper"
RUNNER_PATH = INTEGRATION_DIR / "pixiv_wallpaper_runner.py"
VENV_DIR = INTEGRATION_DIR / "venv"
VENV_PYTHON = VENV_DIR / "bin" / "python3"
LOGIN_DESKTOP_NAME = "pixiv-plasma-wallpaper-login.desktop"
CALLBACK_DESKTOP_NAME = "pixiv-plasma-wallpaper-callback.desktop"
SERVICE_NAME = "pixiv-plasma-wallpaper.service"
TIMER_NAME = "pixiv-plasma-wallpaper.timer"


class PixivWallpaperError(RuntimeError):
    pass


def pixiv_api_class() -> Any:
    ensure_pixivpy3()
    try:
        from pixivpy3 import AppPixivAPI
    except ImportError as error:
        raise PixivWallpaperError("Missing dependency: PixivPy3. Install it with `/usr/bin/python3 -m pip install --user PixivPy3`.") from error
    return AppPixivAPI


def ensure_pixivpy3(install: bool = False) -> None:
    if importlib.util.find_spec("pixivpy3") is not None:
        return
    for site_packages in VENV_DIR.glob("lib/python*/site-packages"):
        if site_packages.is_dir() and str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
            if importlib.util.find_spec("pixivpy3") is not None:
                return
    if not install:
        raise PixivWallpaperError("Missing dependency: PixivPy3. Run wallpaper setup again to install the plugin venv.")
    import subprocess

    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    if not VENV_PYTHON.exists():
        process = subprocess.run(
            ["/usr/bin/python3", "-m", "venv", str(VENV_DIR)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
        if process.returncode != 0:
            message = (process.stderr or process.stdout or "Pixiv Wallpaper dependency venv creation failed").strip()
            raise PixivWallpaperError(message)

    process = subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "PixivPy3"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    if process.returncode != 0 or importlib.util.find_spec("pixivpy3") is None:
        for site_packages in VENV_DIR.glob("lib/python*/site-packages"):
            if site_packages.is_dir() and str(site_packages) not in sys.path:
                sys.path.insert(0, str(site_packages))
        if importlib.util.find_spec("pixivpy3") is None:
            message = (process.stderr or process.stdout or "PixivPy3 installation failed").strip()
            raise PixivWallpaperError(message)


def value_of(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def plain_value(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    dict_method = getattr(value, "dict", None)
    if callable(dict_method) and not isinstance(value, dict):
        return dict_method()
    if isinstance(value, list):
        return [plain_value(item) for item in value]
    if isinstance(value, dict):
        return {key: plain_value(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class Candidate:
    illust_id: int
    title: str
    user_name: str
    width: int
    height: int
    bookmarks: int
    views: int
    url: str
    score: float


def output(status: str, message: str, image: str | None = None) -> None:
    payload = {"status": status, "message": message}
    if image:
        payload["image"] = image
    print(json.dumps(payload, ensure_ascii=False))


def log_info(message: str) -> None:
    text = f"Pixiv Wallpaper: {message}"
    print(text, file=sys.stderr)
    try:
        evaluate_plasma(f"console.log({js_string(text)});")
    except Exception:
        pass


def notify(config: dict[str, str] | None, title: str, message: str, urgency: str = "normal") -> None:
    if config is None or not parse_bool(config.get("NotifyEvents"), True):
        return
    command = shutil_which("notify-send")
    if not command:
        log_info(f"notification skipped: {message}")
        return
    import subprocess

    subprocess.run(
        [command, "--app-name=Pixiv Wallpaper", "--urgency", urgency, title, message],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )


def emit_event(status: str, message: str, image: str | None = None, *, config: dict[str, str] | None = None, important: bool = False) -> None:
    log_info(message)
    if important:
        notify(config, "Pixiv Wallpaper", message, "critical" if status == "error" else "normal")
    output(status, message, image)


def cache_dir_from_args(args: argparse.Namespace) -> Path:
    return Path(args.cache_dir).expanduser()


def qdbus() -> str:
    for name in ("qdbus6", "qdbus-qt6", "qdbus"):
        if shutil_which(name):
            return name
    raise PixivWallpaperError("qdbus6 was not found")


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        path = Path(directory) / name
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return None


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def evaluate_plasma(script: str) -> str:
    import subprocess

    command = qdbus()
    process = subprocess.run(
        [command, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    if process.returncode != 0:
        raise PixivWallpaperError((process.stderr or process.stdout).strip() or "qdbus Plasma script failed")
    return process.stdout


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def read_plugin_config() -> dict[str, str]:
    script = """
var result = {};
var ds = desktops();
for (var i = 0; i < ds.length; i++) {
    if (ds[i].wallpaperPlugin !== 'org.pixiv.wallpaper') {
        continue;
    }
    ds[i].currentConfigGroup = ['Wallpaper', 'org.pixiv.wallpaper', 'General'];
    var keys = ['RefreshToken', 'Mode', 'Theme', 'RefreshMinutes', 'RotateMinutes', 'FetchCount', 'LocalImagePaths', 'LocalImageCache', 'LocalImageCacheKey', 'RotationMode', 'IncludeLocalImages', 'LocalImageRatio', 'MinBookmarks', 'MinViews', 'TagBlacklist', 'IncludeR18', 'IncludeAI', 'LandscapeOnly', 'FitTolerance', 'NotifyEvents', 'LastFetch', 'LastRotate', 'CurrentImage'];
    for (var k = 0; k < keys.length; k++) {
        result[keys[k]] = String(ds[i].readConfig(keys[k]));
    }
    var geometry = screenGeometry(ds[i].screen);
    result.Width = String(geometry.width);
    result.Height = String(geometry.height);
    break;
}
print(JSON.stringify(result));
"""
    raw = evaluate_plasma(script).strip().splitlines()
    if not raw:
        raise PixivWallpaperError("Pixiv Wallpaper is not active on any desktop")
    return json.loads(raw[-1])


def write_plugin_config(values: dict[str, Any]) -> None:
    writes = []
    for key, value in values.items():
        if isinstance(value, list):
            writes.append(f"ds[i].writeConfig({js_string(key)}, {json.dumps(value, ensure_ascii=False)});")
        else:
            writes.append(f"ds[i].writeConfig({js_string(key)}, {js_string(str(value))});")
    script = """
var ds = desktops();
for (var i = 0; i < ds.length; i++) {
    if (ds[i].wallpaperPlugin !== 'org.pixiv.wallpaper') {
        continue;
    }
    ds[i].currentConfigGroup = ['Wallpaper', 'org.pixiv.wallpaper', 'General'];
    WRITES
}
""".replace("WRITES", "\n    ".join(writes))
    evaluate_plasma(script)


def sync_cache_config(cache_dir: Path) -> None:
    manifest = sanitize_manifest(cache_dir)
    images = [str(entry.get("path")) for entry in manifest.get("images", [])]
    write_plugin_config(
        {
            "CachedImages": images,
            "CurrentIndex": str(manifest.get("index", -1)),
        }
    )


def reload_pixiv_wallpaper() -> None:
    script = """
var ds = desktops();
for (var i = 0; i < ds.length; i++) {
    if (ds[i].wallpaperPlugin !== 'org.pixiv.wallpaper') {
        continue;
    }
    ds[i].wallpaperPlugin = 'org.kde.color';
    ds[i].wallpaperPlugin = 'org.pixiv.wallpaper';
}
"""
    evaluate_plasma(script)


def parse_bool(value: Any, default: bool = False) -> bool:
    text = str(value).strip().lower()
    if not text or text == "undefined":
        return default
    return text in {"1", "true", "yes", "on"}


def parse_int(value: Any, default: int) -> int:
    try:
        text = str(value).strip()
        if not text or text == "undefined":
            return default
        return int(float(text))
    except (TypeError, ValueError):
        return default


def normalized_terms(value: str) -> list[str]:
    if not value or value == "undefined":
        return []
    terms = [part.strip().lower() for line in value.splitlines() for part in line.split(",")]
    return [term for term in terms if term]


def tag_names(illust: dict[str, Any]) -> list[str]:
    tags = []
    for tag in value_of(illust, "tags", []) or []:
        name = str(value_of(tag, "name", "")).strip().lower()
        translated = str(value_of(tag, "translated_name", "")).strip().lower()
        if name:
            tags.append(name)
        if translated:
            tags.append(translated)
    return tags


def tag_set(illust: dict[str, Any]) -> set[str]:
    return set(tag_names(illust))


def illust_views(illust: dict[str, Any]) -> int:
    for key in ("total_view", "total_views", "view_count", "total_view_count"):
        value = value_of(illust, key)
        if value is not None:
            return parse_int(value, 0)
    return 0


def matches_search_theme(illust: dict[str, Any], terms: list[str]) -> bool:
    if not terms:
        return True
    keyword_text = " ".join(
        [
            str(value_of(illust, "title") or "").lower(),
            str(value_of(illust, "caption") or "").lower(),
            str(value_of(illust, "description") or "").lower(),
            str(value_of(value_of(illust, "user", {}), "name") or "").lower(),
        ]
    )
    tags = tag_names(illust)
    return any(term in keyword_text or any(term in tag for tag in tags) for term in terms)


def matches_strict_tags(illust: dict[str, Any], required_tags: list[str]) -> bool:
    if not required_tags:
        return True
    tags = tag_set(illust)
    return any(tag in tags for tag in required_tags)


def matches_tag_blacklist(illust: dict[str, Any], blacklist: list[str]) -> bool:
    if not blacklist:
        return True
    tags = tag_set(illust)
    return not any(blocked in tags for blocked in blacklist)


def parse_time(value: str) -> float:
    if not value or value == "undefined":
        return 0
    try:
        return float(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0


def request_json(url: str, *, headers: dict[str, str] | None = None, data: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"

    encoded_data = None
    method = "GET"
    if data is not None:
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        method = "POST"

    request_headers = {
        "App-OS": "ios",
        "App-OS-Version": "14.6",
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7,ja;q=0.6",
    }
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, data=encoded_data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise PixivWallpaperError(f"HTTP {error.code}: {body[:500]}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise PixivWallpaperError(str(error)) from error


def request_json_with_fallback(
    primary_url: str,
    fallback_url: str,
    *,
    fallback_host: str,
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return request_json(primary_url, headers=headers, data=data, params=params)
    except PixivWallpaperError as primary_error:
        fallback_headers = dict(headers or {})
        fallback_headers["Host"] = fallback_host
        try:
            return request_json(fallback_url, headers=fallback_headers, data=data, params=params)
        except PixivWallpaperError as fallback_error:
            raise PixivWallpaperError(f"{primary_error}; fallback failed: {fallback_error}") from fallback_error


def s256(value: str) -> str:
    import base64

    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def oauth_state_file(cache_dir: Path) -> Path:
    return cache_dir / "oauth_state.json"


def build_authorize_url(cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    code_verifier = secrets.token_urlsafe(64)[:128]
    state = secrets.token_urlsafe(32)
    oauth_state_file(cache_dir).write_text(
        json.dumps({"code_verifier": code_verifier, "state": state, "created_at": int(time.time())}, indent=2),
        encoding="utf-8",
    )
    params = {
        "code_challenge": s256(code_verifier),
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    }
    return f"https://app-api.pixiv.net/web/v1/login?{urllib.parse.urlencode(params)}"


def auth_code(code: str, code_verifier: str) -> dict[str, Any]:
    local_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    client_hash = hashlib.md5((local_time + HASH_SECRET).encode("utf-8")).hexdigest()
    return request_json_with_fallback(
        f"{OAUTH_API}/auth/token",
        f"{ALT_OAUTH_API}/auth/token",
        fallback_host="oauth.secure.pixiv.net",
        headers={
            "X-Client-Time": local_time,
            "X-Client-Hash": client_hash,
        },
        data={
            "get_secure_url": 1,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": OAUTH_REDIRECT_URI,
            "include_policy": "true",
        },
    )


def create_pixiv_api(refresh_token: str, cache_dir: Path) -> Any:
    AppPixivAPI = pixiv_api_class()
    api = AppPixivAPI(timeout=45)
    api.set_accept_language("zh-CN,zh;q=0.9,en;q=0.7,ja;q=0.6")
    token_file = cache_dir / "token.json"
    if token_file.exists():
        try:
            cached = json.loads(token_file.read_text(encoding="utf-8"))
            if cached.get("access_token") and cached.get("expires_at", 0) > int(time.time()) + 120:
                api.set_auth(cached["access_token"], cached.get("refresh_token", refresh_token))
                return api
        except (OSError, json.JSONDecodeError):
            pass

    token = api.auth(refresh_token=refresh_token)
    response = token.get("response", token) if isinstance(token, dict) else value_of(token, "response", token)
    access_token = value_of(response, "access_token")
    next_refresh_token = value_of(response, "refresh_token", refresh_token) or refresh_token
    expires_in = parse_int(value_of(response, "expires_in", 3600), 3600)
    if not access_token:
        raise PixivWallpaperError("PixivPy3 did not return an access token")
    token_file.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": next_refresh_token,
                "expires_at": int(time.time()) + expires_in,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return api


def result_illusts(result: Any) -> list[Any]:
    return list(value_of(result, "illusts", []) or [])


def unique_illusts(illusts: list[Any]) -> list[Any]:
    seen: set[int] = set()
    result = []
    for illust in illusts:
        illust_id = int(value_of(illust, "id") or 0)
        if illust_id and illust_id in seen:
            continue
        if illust_id:
            seen.add(illust_id)
        result.append(illust)
    return result


def resolve_theme_tags(api: Any, terms: list[str]) -> list[str]:
    tags: list[str] = []
    for term in terms:
        result = api.search_illust(term, search_target="exact_match_for_tags", sort="date_desc", filter="for_ios")
        for illust in result_illusts(result):
            if term in tag_set(plain_value(illust)):
                tags.append(term)
                break
    return tags


def fetch_search_illusts(args: argparse.Namespace, api: Any) -> list[dict[str, Any]]:
    terms = normalized_terms(args.theme) or [args.theme.strip()]
    illusts: list[Any] = []
    for term in terms:
        for search_target in ("partial_match_for_tags", "title_and_caption"):
            kwargs: dict[str, Any] = {"search_target": search_target, "sort": "date_desc", "filter": "for_ios"}
            if args.include_ai:
                kwargs["search_ai_type"] = 1
            illusts.extend(result_illusts(api.search_illust(term, **kwargs)))
    return [plain_value(illust) for illust in unique_illusts(illusts)]


def fetch_illusts(args: argparse.Namespace, api: Any) -> list[dict[str, Any]]:
    if args.mode == "search":
        if not args.theme.strip():
            raise PixivWallpaperError("Theme search needs a keyword or tag")
        illusts = fetch_search_illusts(args, api)
    elif args.mode == "ranking":
        illusts = [plain_value(illust) for illust in result_illusts(api.illust_ranking(mode="day", filter="for_ios"))]
    elif args.mode == "follow":
        illusts = [plain_value(illust) for illust in result_illusts(api.illust_follow(restrict="public"))]
    else:
        illusts = [
            plain_value(illust)
            for illust in result_illusts(
                api.illust_recommended(
                    content_type="illust",
                    include_ranking_label=True,
                    filter="for_ios",
                    include_ranking_illusts=True,
                )
            )
        ]

    theme_terms = normalized_terms(args.theme)
    blacklist_terms = normalized_terms(args.tag_blacklist)
    if args.mode == "search":
        theme_filtered = [illust for illust in illusts if matches_search_theme(illust, theme_terms)]
    else:
        theme_tags = resolve_theme_tags(api, theme_terms)
        theme_filtered = [illust for illust in illusts if matches_strict_tags(illust, theme_tags)]
    return [illust for illust in theme_filtered if matches_tag_blacklist(illust, blacklist_terms)]


def image_url(illust: dict[str, Any]) -> str:
    meta_pages = illust.get("meta_pages") or []
    if meta_pages:
        first = meta_pages[0]
        urls = first.get("image_urls") or {}
        return urls.get("original") or urls.get("large") or urls.get("medium") or ""

    meta_single = illust.get("meta_single_page") or {}
    urls = illust.get("image_urls") or {}
    return meta_single.get("original_image_url") or urls.get("large") or urls.get("medium") or urls.get("square_medium") or ""


def is_r18(illust: dict[str, Any]) -> bool:
    x_restrict = int(illust.get("x_restrict") or 0)
    if x_restrict > 0:
        return True
    for tag in illust.get("tags") or []:
        name = str(tag.get("name", "")).lower()
        if name in {"r-18", "r18", "r-18g"}:
            return True
    return False


def is_ai(illust: dict[str, Any]) -> bool:
    if int(illust.get("illust_ai_type") or 0) == 2:
        return True
    for tag in illust.get("tags") or []:
        name = str(tag.get("name", "")).lower()
        translated = str(tag.get("translated_name", "")).lower()
        if name in {"ai生成", "aiイラスト", "aiart"} or "ai-generated" in translated:
            return True
    return False


def score_candidate(illust: dict[str, Any], url: str, args: argparse.Namespace) -> Candidate | None:
    width = int(illust.get("width") or 0)
    height = int(illust.get("height") or 0)
    bookmarks = int(illust.get("total_bookmarks") or 0)
    views = illust_views(illust)
    if not url or width <= 0 or height <= 0:
        return None
    if args.landscape_only and width < height:
        return None
    if bookmarks < args.min_bookmarks:
        return None
    if views < args.min_views:
        return None
    if not args.include_r18 and is_r18(illust):
        return None
    if not args.include_ai and is_ai(illust):
        return None

    screen_ratio = args.width / max(1, args.height)
    image_ratio = width / max(1, height)
    ratio_delta = abs(image_ratio - screen_ratio) / screen_ratio
    if ratio_delta > args.fit_tolerance / 100:
        return None

    larger_than_screen = width >= args.width and height >= args.height
    size_score = min(width / max(1, args.width), height / max(1, args.height))
    score = ratio_delta * 1000
    score -= min(bookmarks, 10000) / 10000
    score -= min(views, 1000000) / 1000000
    score -= min(size_score, 3) * 2
    if larger_than_screen:
        score -= 5

    user = illust.get("user") or {}
    return Candidate(
        illust_id=int(illust.get("id") or 0),
        title=str(illust.get("title") or "untitled"),
        user_name=str(user.get("name") or "unknown"),
        width=width,
        height=height,
        bookmarks=bookmarks,
        views=views,
        url=url,
        score=score,
    )


def select_candidates(illusts: list[dict[str, Any]], args: argparse.Namespace) -> list[Candidate]:
    candidates = []
    for illust in illusts:
        candidate = score_candidate(illust, image_url(illust), args)
        if candidate:
            candidates.append(candidate)
    candidates.sort(key=lambda item: item.score)
    return candidates


def suffix_for_url(url: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    guessed = mimetypes.guess_extension(mimetypes.guess_type(url)[0] or "")
    return guessed or ".jpg"


def download(candidate: Candidate, cache_dir: Path, api: Any) -> Path:
    images_dir = cache_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{candidate.illust_id}_{candidate.width}x{candidate.height}{suffix_for_url(candidate.url)}"
    target = images_dir / filename
    if target.exists() and target.stat().st_size > 0:
        return target

    api.download(candidate.url, path=str(images_dir), name=filename, replace=True)
    return target


def load_manifest(cache_dir: Path) -> dict[str, Any]:
    manifest_file = cache_dir / "manifest.json"
    if not manifest_file.exists():
        return {"images": [], "index": -1}
    try:
        return json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"images": [], "index": -1}


def save_manifest(cache_dir: Path, manifest: dict[str, Any]) -> None:
    (cache_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_manifest(cache_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(cache_dir)
    original_images = manifest.get("images", [])
    original_index = manifest.get("index", -1)
    images = [entry for entry in original_images if entry.get("path") and Path(entry.get("path", "")).exists()]
    index = parse_int(manifest.get("index", -1), -1)
    if not images:
        index = -1
    elif index >= len(images):
        index = len(images) - 1
    manifest["images"] = images
    manifest["index"] = index
    if images != original_images or index != original_index:
        save_manifest(cache_dir, manifest)
    return manifest


def manifest_image_paths(cache_dir: Path) -> list[str]:
    manifest = sanitize_manifest(cache_dir)
    return [str(entry.get("path")) for entry in manifest.get("images", [])]


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def local_image_paths(config: dict[str, str]) -> list[Path]:
    raw = config.get("LocalImagePaths", "")
    if not raw or raw == "undefined":
        return []
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images: list[Path] = []
    parts = [part.strip() for line in raw.splitlines() for part in line.split(",")]
    for part in parts:
        if not part:
            continue
        path = Path(part).expanduser()
        if path.is_file() and path.suffix.lower() in image_suffixes:
            images.append(path)
        elif path.is_dir():
            try:
                images.extend(sorted(child for child in path.iterdir() if child.is_file() and child.suffix.lower() in image_suffixes))
            except OSError:
                continue
    return unique_paths(images)


def local_image_cache_key(config: dict[str, str]) -> str:
    raw = config.get("LocalImagePaths", "")
    if not raw or raw == "undefined":
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cached_local_image_paths(config: dict[str, str]) -> list[Path]:
    if config.get("LocalImageCacheKey", "") != local_image_cache_key(config):
        return []
    paths = []
    for path in value_to_paths(config.get("LocalImageCache", "")):
        if path.is_file():
            paths.append(path)
    return unique_paths(paths)


def value_to_paths(value: Any) -> list[Path]:
    if isinstance(value, list):
        parts = value
    else:
        raw = str(value or "")
        if not raw or raw == "undefined":
            return []
        parts = [part.strip() for line in raw.splitlines() for part in line.split(",")]
    return [Path(str(part).strip()).expanduser() for part in parts if str(part).strip()]


def sync_local_image_cache(config: dict[str, str] | None = None) -> list[Path]:
    config = config or read_plugin_config()
    images = local_image_paths(config)
    write_plugin_config(
        {
            "LocalImageCache": [str(path) for path in images],
            "LocalImageCacheKey": local_image_cache_key(config),
        }
    )
    return images


def choose_from_paths(paths: list[Path], current: str, mode: str) -> tuple[Path, int]:
    if not paths:
        raise PixivWallpaperError("No wallpapers available yet")
    if mode == "random":
        index = random.randrange(len(paths))
        if len(paths) > 1 and str(paths[index]) == current:
            index = (index + 1) % len(paths)
        return paths[index], index
    path_strings = [str(path) for path in paths]
    current_index = path_strings.index(current) if current in path_strings else -1
    index = (current_index + 1) % len(paths)
    return paths[index], index


def rotate_from_config(config: dict[str, str], cache_dir: Path) -> tuple[Path, int]:
    cached = [Path(path) for path in manifest_image_paths(cache_dir)]
    configured_mode = config.get("RotationMode")
    mode = configured_mode if configured_mode in {"sequential", "random"} else "sequential"
    current = config.get("CurrentImage", "")
    if parse_bool(config.get("IncludeLocalImages"), False):
        local = cached_local_image_paths(config)
        if not local:
            local = sync_local_image_cache(config)
        ratio = max(0, min(100, parse_int(config.get("LocalImageRatio"), 50)))
        if local and (not cached or random.randrange(100) < ratio):
            return choose_from_paths(local, current, mode)
    return choose_from_paths(cached, current, mode)


def next_image(cache_dir: Path) -> tuple[Path, str]:
    manifest = sanitize_manifest(cache_dir)
    images = manifest.get("images", [])
    if not images:
        raise PixivWallpaperError("No cached Pixiv wallpapers yet")
    current_index = manifest.get("index", -1)
    if current_index is None:
        current_index = -1
    index = (int(current_index) + 1) % len(images)
    manifest["images"] = images
    manifest["index"] = index
    save_manifest(cache_dir, manifest)
    entry = images[index]
    return Path(entry["path"]), f"{entry.get('title', 'Pixiv')} by {entry.get('user_name', 'unknown')}"


def update_manifest(cache_dir: Path, selected: list[tuple[Candidate, Path]]) -> None:
    manifest = sanitize_manifest(cache_dir)
    existing = {entry.get("path"): entry for entry in manifest.get("images", []) if entry.get("path")}
    for candidate, path in selected:
        existing[str(path)] = {
            "path": str(path),
            "illust_id": candidate.illust_id,
            "title": candidate.title,
            "user_name": candidate.user_name,
            "width": candidate.width,
            "height": candidate.height,
            "bookmarks": candidate.bookmarks,
            "views": candidate.views,
            "fetched_at": int(time.time()),
        }

    images = sorted(existing.values(), key=lambda entry: entry.get("fetched_at", 0), reverse=True)[:80]
    manifest["images"] = images
    manifest["index"] = -1
    save_manifest(cache_dir, manifest)


def cleanup(cache_dir: Path) -> None:
    manifest = sanitize_manifest(cache_dir)
    keep = {entry.get("path") for entry in manifest.get("images", [])}
    images_dir = cache_dir / "images"
    if not images_dir.exists():
        return
    for path in images_dir.iterdir():
        if path.is_file() and str(path) not in keep and not path.name.endswith(".tmp"):
            path.unlink(missing_ok=True)


def command_fetch(args: argparse.Namespace) -> None:
    cache_dir = Path(args.cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    api = create_pixiv_api(args.refresh_token, cache_dir)
    illusts = fetch_illusts(args, api)
    candidates = select_candidates(illusts, args)
    if not candidates:
        raise PixivWallpaperError("No matching Pixiv illustrations found; loosen filters or try another source")

    top = candidates[: min(len(candidates), max(12, args.fetch_count * 2))]
    random.shuffle(top)
    downloaded: list[tuple[Candidate, Path]] = []
    last_error = ""
    for candidate in top:
        try:
            downloaded.append((candidate, download(candidate, cache_dir, api)))
            if len(downloaded) >= args.fetch_count:
                break
        except Exception as error:  # noqa: BLE001
            last_error = str(error)

    if not downloaded:
        raise PixivWallpaperError(f"Could not download matching images: {last_error}")

    update_manifest(cache_dir, downloaded)
    cleanup(cache_dir)
    image, description = next_image(cache_dir)
    emit_event("ok", f"Fetched {len(downloaded)} Pixiv image(s). Showing {description}.", str(image), important=True)


def command_next(args: argparse.Namespace) -> None:
    image, description = next_image(Path(args.cache_dir).expanduser())
    emit_event("ok", f"Showing cached {description}.", str(image))


def command_login(args: argparse.Namespace) -> None:
    import webbrowser

    url = build_authorize_url(cache_dir_from_args(args))
    if not webbrowser.open(url, new=2):
        raise PixivWallpaperError(f"Could not open browser automatically. Open this URL manually: {url}")
    emit_event("ok", "Opened Pixiv OAuth login page.")


def command_oauth_callback(args: argparse.Namespace) -> None:
    callback_url = args.url
    if callback_url.startswith(LOGIN_INIT_URI):
        command_login(args)
        return
    if callback_url.startswith(ROTATE_NOW_URI):
        command_rotate_now(args)
        return
    if callback_url.startswith(FETCH_NOW_URI):
        command_fetch_now(args)
        return
    parsed = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(parsed.query)
    code = (params.get("code") or [""])[0]
    if not code:
        raise PixivWallpaperError("OAuth callback did not contain an authorization code")

    cache_dir = cache_dir_from_args(args)
    state_file = oauth_state_file(cache_dir)
    if not state_file.exists():
        raise PixivWallpaperError("OAuth state is missing. Start login from the wallpaper settings button again.")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if int(time.time()) - int(state.get("created_at") or 0) > 600:
        raise PixivWallpaperError("OAuth state expired. Start login again.")

    payload = auth_code(code, state["code_verifier"])
    response = payload.get("response", {})
    refresh_token = response.get("refresh_token")
    access_token = response.get("access_token")
    expires_in = int(response.get("expires_in") or 3600)
    if not refresh_token or not access_token:
        raise PixivWallpaperError("Pixiv OAuth did not return tokens")

    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "token.json").write_text(
        json.dumps(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": int(time.time()) + expires_in,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    state_file.unlink(missing_ok=True)
    write_plugin_config(
        {
            "RefreshToken": refresh_token,
            "LastFetch": "",
        }
    )
    emit_event("ok", "Pixiv OAuth login succeeded.", config=read_plugin_config(), important=True)


def namespace_from_config(config: dict[str, str], cache_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        action="fetch",
        cache_dir=str(cache_dir),
        refresh_token=config.get("RefreshToken", ""),
        mode=config.get("Mode") if config.get("Mode") in {"recommended", "search", "ranking", "follow"} else "recommended",
        theme="" if config.get("Theme") == "undefined" else config.get("Theme", ""),
        width=parse_int(config.get("Width"), 1920),
        height=parse_int(config.get("Height"), 1080),
        fetch_count=max(1, parse_int(config.get("FetchCount"), 4)),
        min_bookmarks=max(0, parse_int(config.get("MinBookmarks"), 0)),
        min_views=max(0, parse_int(config.get("MinViews"), 0)),
        tag_blacklist="" if config.get("TagBlacklist") == "undefined" else config.get("TagBlacklist", ""),
        fit_tolerance=max(1, parse_int(config.get("FitTolerance"), 35)),
        include_r18=parse_bool(config.get("IncludeR18"), False),
        include_ai=parse_bool(config.get("IncludeAI"), False),
        landscape_only=parse_bool(config.get("LandscapeOnly"), True),
        output_json=True,
    )


def fetch_from_config(config: dict[str, str], cache_dir: Path, now: float) -> tuple[Path, str]:
    plugin_args = namespace_from_config(config, cache_dir)
    api = create_pixiv_api(plugin_args.refresh_token, cache_dir)
    illusts = fetch_illusts(plugin_args, api)
    candidates = select_candidates(illusts, plugin_args)
    if not candidates:
        raise PixivWallpaperError("No matching Pixiv illustrations found; loosen filters or try another source")
    top = candidates[: min(len(candidates), max(12, plugin_args.fetch_count * 2))]
    random.shuffle(top)
    downloaded: list[tuple[Candidate, Path]] = []
    for candidate in top:
        try:
            downloaded.append((candidate, download(candidate, cache_dir, api)))
            if len(downloaded) >= plugin_args.fetch_count:
                break
        except Exception:
            continue
    if not downloaded:
        raise PixivWallpaperError("Could not download any matching Pixiv images")
    update_manifest(cache_dir, downloaded)
    cleanup(cache_dir)
    image, description = next_image(cache_dir)
    manifest = sanitize_manifest(cache_dir)
    images = [str(entry.get("path")) for entry in manifest.get("images", [])]
    timestamp = str(int(now))
    write_plugin_config(
        {
            "CurrentImage": str(image),
            "CachedImages": images,
            "CurrentIndex": str(manifest.get("index", -1)),
            "LastFetch": timestamp,
            "LastRotate": timestamp,
        }
    )
    return image, f"Fetched {len(downloaded)} Pixiv image(s). Showing {description}."


def rotate_cached(cache_dir: Path, now: float, config: dict[str, str] | None = None) -> tuple[Path, str]:
    if config:
        image, index = rotate_from_config(config, cache_dir)
        description = image.name
    else:
        image, description = next_image(cache_dir)
        index = sanitize_manifest(cache_dir).get("index", -1)
    manifest = sanitize_manifest(cache_dir)
    images = [str(entry.get("path")) for entry in manifest.get("images", [])]
    message = f"Showing cached {description}."
    write_plugin_config(
        {
            "CurrentImage": str(image),
            "CachedImages": images,
            "CurrentIndex": str(index),
            "LastRotate": str(int(now)),
        }
    )
    return image, message


def command_rotate_now(args: argparse.Namespace) -> None:
    config = read_plugin_config()
    cache_dir = cache_dir_from_args(args)
    cache_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()

    try:
        image, message = rotate_cached(cache_dir, now, config)
        reload_pixiv_wallpaper()
        emit_event("ok", message, str(image), config=config, important=True)
        return
    except Exception:
        pass

    if not config.get("RefreshToken") or config.get("RefreshToken") == "undefined":
        emit_event("error", "Set a Pixiv refresh token in wallpaper settings first.", config=config, important=True)
        return

    try:
        image, message = fetch_from_config(config, cache_dir, now)
        reload_pixiv_wallpaper()
        emit_event("ok", message, str(image), config=config, important=True)
    except Exception as error:  # noqa: BLE001
        emit_event("error", str(error), config=config, important=True)


def command_fetch_now(args: argparse.Namespace) -> None:
    config = read_plugin_config()
    cache_dir = cache_dir_from_args(args)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not config.get("RefreshToken") or config.get("RefreshToken") == "undefined":
        emit_event("error", "Set a Pixiv refresh token in wallpaper settings first.", config=config, important=True)
        return

    now = time.time()
    try:
        image, message = fetch_from_config(config, cache_dir, now)
        reload_pixiv_wallpaper()
        emit_event("ok", message, str(image), config=config, important=True)
    except Exception as error:  # noqa: BLE001
        emit_event("error", str(error), config=config, important=True)


def command_sync_local_cache(args: argparse.Namespace) -> None:
    config = read_plugin_config()
    images = sync_local_image_cache(config)
    emit_event("ok", f"Cached {len(images)} local image path(s).")


def command_daemon_tick(args: argparse.Namespace) -> None:
    config = read_plugin_config()
    cache_dir = Path(args.cache_dir).expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not config.get("RefreshToken") or config.get("RefreshToken") == "undefined":
        emit_event("error", "Set a Pixiv refresh token in wallpaper settings first.", config=config, important=True)
        return

    now = time.time()
    refresh_minutes = max(1, parse_int(config.get("RefreshMinutes"), 360))
    rotate_minutes = max(1, parse_int(config.get("RotateMinutes"), 30))
    last_fetch = parse_time(config.get("LastFetch", ""))
    last_rotate = parse_time(config.get("LastRotate", ""))

    if not last_fetch or now - last_fetch >= refresh_minutes * 60:
        try:
            image, message = fetch_from_config(config, cache_dir, now)
            emit_event("ok", message, str(image), config=config, important=True)
            return
        except Exception as error:  # noqa: BLE001
            emit_event("error", str(error), config=config, important=True)
            return

    if now - last_rotate >= rotate_minutes * 60:
        try:
            image, message = rotate_cached(cache_dir, now, config)
            emit_event("ok", message, str(image), config=config, important=True)
            return
        except Exception as error:  # noqa: BLE001
            emit_event("error", str(error), config=config, important=True)
            return

    emit_event("ok", "No Pixiv wallpaper update due yet.", config.get("CurrentImage") if config.get("CurrentImage") != "undefined" else None)


def run_quiet(command: list[str]) -> None:
    import subprocess

    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def quote_desktop_exec(path: Path) -> str:
    return '"' + str(path).replace('"', '\\"') + '"'


def desktop_entry(name: str, comment: str, mime_type: str) -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={name}",
            f"Comment={comment}",
            f"Exec=/usr/bin/python3 {quote_desktop_exec(RUNNER_PATH)} oauth-callback --url %u",
            "Terminal=false",
            "NoDisplay=true",
            f"MimeType={mime_type};",
            "Categories=Network;",
            "",
        ]
    )


def runner_script() -> str:
    return f'''#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_SCRIPT = Path({str(SCRIPT_PATH)!r})
CACHE_DIR = Path({str(DEFAULT_CACHE_DIR)!r})
RUNNER_PATH = Path({str(RUNNER_PATH)!r})
LOGIN_DESKTOP_NAME = {LOGIN_DESKTOP_NAME!r}
CALLBACK_DESKTOP_NAME = {CALLBACK_DESKTOP_NAME!r}
SERVICE_NAME = {SERVICE_NAME!r}
TIMER_NAME = {TIMER_NAME!r}


def run_quiet(command):
    subprocess.run(command, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remove_mime_default(scheme, desktop_name):
    mimeapps = Path.home() / ".config" / "mimeapps.list"
    if not mimeapps.exists():
        return
    try:
        lines = mimeapps.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    key = f"x-scheme-handler/{{scheme}}="
    changed = False
    result = []
    for line in lines:
        if line.startswith(key) and desktop_name in line.split("=", 1)[1].split(";"):
            changed = True
            continue
        result.append(line)
    if changed:
        mimeapps.write_text("\\n".join(result) + "\\n", encoding="utf-8")


def cleanup():
    apps_dir = Path.home() / ".local" / "share" / "applications"
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    run_quiet(["systemctl", "--user", "disable", "--now", TIMER_NAME])
    for path in (
        systemd_dir / SERVICE_NAME,
        systemd_dir / TIMER_NAME,
        apps_dir / LOGIN_DESKTOP_NAME,
        apps_dir / CALLBACK_DESKTOP_NAME,
        Path({str(VENV_DIR)!r}),
    ):
        if path.is_dir():
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    remove_mime_default("pixiv-plasma-wallpaper", LOGIN_DESKTOP_NAME)
    remove_mime_default("pixiv", CALLBACK_DESKTOP_NAME)
    run_quiet(["systemctl", "--user", "daemon-reload"])
    RUNNER_PATH.unlink(missing_ok=True)


def main():
    if not PLUGIN_SCRIPT.exists():
        cleanup()
        return 0
    venv_python = Path({str(VENV_PYTHON)!r})
    python = str(venv_python) if venv_python.exists() else "/usr/bin/python3"
    args = [python, str(PLUGIN_SCRIPT), *sys.argv[1:], "--cache-dir", str(CACHE_DIR)]
    return subprocess.call(args)


if __name__ == "__main__":
    sys.exit(main())
'''


def remove_mime_default(scheme: str, desktop_name: str) -> None:
    mimeapps = Path.home() / ".config" / "mimeapps.list"
    if not mimeapps.exists():
        return
    try:
        lines = mimeapps.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    key = f"x-scheme-handler/{scheme}="
    changed = False
    result = []
    for line in lines:
        if line.startswith(key) and desktop_name in line.split("=", 1)[1].split(";"):
            changed = True
            continue
        result.append(line)
    if changed:
        mimeapps.write_text("\n".join(result) + "\n", encoding="utf-8")


def cleanup_integration() -> None:
    apps_dir = Path.home() / ".local" / "share" / "applications"
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    run_quiet(["systemctl", "--user", "disable", "--now", TIMER_NAME])
    for path in (
        systemd_dir / SERVICE_NAME,
        systemd_dir / TIMER_NAME,
        apps_dir / LOGIN_DESKTOP_NAME,
        apps_dir / CALLBACK_DESKTOP_NAME,
        RUNNER_PATH,
        VENV_DIR,
    ):
        if path.is_dir():
            import shutil
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    remove_mime_default("pixiv-plasma-wallpaper", LOGIN_DESKTOP_NAME)
    remove_mime_default("pixiv", CALLBACK_DESKTOP_NAME)
    run_quiet(["systemctl", "--user", "daemon-reload"])


def command_setup(args: argparse.Namespace) -> None:
    ensure_pixivpy3(install=True)

    apps_dir = Path.home() / ".local" / "share" / "applications"
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    apps_dir.mkdir(parents=True, exist_ok=True)
    systemd_dir.mkdir(parents=True, exist_ok=True)
    INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)

    (apps_dir / LOGIN_DESKTOP_NAME).write_text(
        desktop_entry(
            "Pixiv Plasma Wallpaper Login",
            "Start Pixiv OAuth login for the KDE Plasma Pixiv wallpaper plugin",
            "x-scheme-handler/pixiv-plasma-wallpaper",
        ),
        encoding="utf-8",
    )
    (apps_dir / CALLBACK_DESKTOP_NAME).write_text(
        desktop_entry(
            "Pixiv Plasma Wallpaper OAuth Callback",
            "Handle Pixiv OAuth callback for the KDE Plasma Pixiv wallpaper plugin",
            "x-scheme-handler/pixiv",
        ),
        encoding="utf-8",
    )
    RUNNER_PATH.write_text(runner_script(), encoding="utf-8")
    RUNNER_PATH.chmod(0o755)

    (systemd_dir / SERVICE_NAME).write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Update KDE Plasma Pixiv wallpaper",
                "",
                "[Service]",
                "Type=oneshot",
                f"ExecStart=/usr/bin/python3 {RUNNER_PATH} daemon-tick",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (systemd_dir / TIMER_NAME).write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Run KDE Plasma Pixiv wallpaper updater periodically",
                "",
                "[Timer]",
                "OnBootSec=30s",
                "OnUnitActiveSec=60s",
                "AccuracySec=10s",
                "Persistent=true",
                "",
                "[Install]",
                "WantedBy=timers.target",
                "",
            ]
        ),
        encoding="utf-8",
    )

    run_quiet(["xdg-mime", "default", LOGIN_DESKTOP_NAME, "x-scheme-handler/pixiv-plasma-wallpaper"])
    run_quiet(["xdg-mime", "default", CALLBACK_DESKTOP_NAME, "x-scheme-handler/pixiv"])
    run_quiet(["systemctl", "--user", "daemon-reload"])
    run_quiet(["systemctl", "--user", "enable", "--now", TIMER_NAME])
    emit_event("ok", "Pixiv Wallpaper integration installed.")


def command_cleanup(args: argparse.Namespace) -> None:
    cleanup_integration()
    emit_event("ok", "Pixiv Wallpaper integration removed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Pixiv wallpapers for a KDE Plasma wallpaper plugin.")
    parser.add_argument("action", choices={"fetch", "next", "daemon-tick", "login", "oauth-callback", "rotate-now", "fetch-now", "sync-local-cache", "setup", "cleanup"})
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "pixiv-plasma-wallpaper"))
    parser.add_argument("--url", default="")
    parser.add_argument("--refresh-token", default="")
    parser.add_argument("--mode", choices={"recommended", "search", "ranking", "follow"}, default="recommended")
    parser.add_argument("--theme", default="")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fetch-count", type=int, default=4)
    parser.add_argument("--min-bookmarks", type=int, default=0)
    parser.add_argument("--min-views", type=int, default=0)
    parser.add_argument("--tag-blacklist", default="")
    parser.add_argument("--fit-tolerance", type=int, default=35)
    parser.add_argument("--include-r18", action="store_true")
    parser.add_argument("--include-ai", action="store_true")
    parser.add_argument("--landscape-only", action="store_true")
    parser.add_argument("--output-json", action="store_true", help="Accepted for the QML caller; output is always JSON.")
    args = parser.parse_args()
    if args.action == "fetch" and not args.refresh_token.strip():
        raise PixivWallpaperError("Missing Pixiv refresh token")
    args.fit_tolerance = max(1, args.fit_tolerance)
    args.width = max(1, args.width)
    args.height = max(1, args.height)
    args.fetch_count = max(1, args.fetch_count)
    args.min_bookmarks = max(0, args.min_bookmarks)
    args.min_views = max(0, args.min_views)
    return args


def main() -> int:
    try:
        args = parse_args()
        if args.action == "next":
            command_next(args)
        elif args.action == "daemon-tick":
            command_daemon_tick(args)
        elif args.action == "login":
            command_login(args)
        elif args.action == "oauth-callback":
            command_oauth_callback(args)
        elif args.action == "rotate-now":
            command_rotate_now(args)
        elif args.action == "fetch-now":
            command_fetch_now(args)
        elif args.action == "sync-local-cache":
            command_sync_local_cache(args)
        elif args.action == "setup":
            command_setup(args)
        elif args.action == "cleanup":
            command_cleanup(args)
        else:
            command_fetch(args)
        return 0
    except Exception as error:  # noqa: BLE001
        emit_event("error", str(error), important=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
