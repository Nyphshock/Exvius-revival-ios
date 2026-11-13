"""Art for the deal banners (`gacha_deals.json`), downloaded once on startup.

Each deal banner names its list and detail images (`art.banner`, `art.detail_banner`, both `deal-<id>-*.png`)
and where Global published them (`art.urls`: the official news CDN, read through the Wayback Machine, or the
wiki). This module downloads each missing file into `DEAL_ART_ROOT` (`<data>/deal_art`), where the banner art
index finds it. Missing art is fetched on demand so the client does not race the background queue. If the
upstream is unreachable, a titled placeholder is served and the real art is retried on the next start.

Remove: delete `<data>/deal_art` (README, removal section). Off with EXVIUS_DEAL_ART_FETCH=0.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

PNG = b'\x89PNG\r\n\x1a\n'
_LOCKS_GUARD = threading.Lock()
_FILE_LOCKS: dict[str, threading.Lock] = {}


def _file_lock(name: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _FILE_LOCKS.setdefault(name, threading.Lock())


def _targets() -> list[tuple[str, str, str, tuple]]:
    """[(file name, url or "", title, size)] for every deal banner image."""
    from ffbe_config import GACHA_DEALS, GACHA_RAIDS
    banners = []
    import late_banners
    for path in (GACHA_DEALS, GACHA_RAIDS, late_banners.PATH):   # raid stand-ins (2026-11-10), late banners (11-12)
        try:
            with open(path, encoding='utf-8') as fh:
                banners += json.load(fh).get('banners', [])
        except (OSError, ValueError):
            pass
    out = []
    for banner in banners:
        art = banner.get('art') or {}
        for name, url in (art.get('urls') or {}).items():
            if name:
                size = (640, 392) if name == art.get('detail_banner') and name != art.get('banner') else (640, 160)
                out.append((name, url or '', str(banner.get('name') or ''), size))
    return out


def render(title: str, size: tuple) -> bytes:
    """A plain banner with the summon's title, for deals whose Global art is lost."""
    import io
    from PIL import Image, ImageDraw, ImageFont
    width, height = size
    image = Image.new('RGB', size, (18, 28, 64))
    draw = ImageDraw.Draw(image)
    for y in range(height):   # a simple vertical gradient
        shade = int(28 + 50 * y / height)
        draw.line([(0, y), (width, y)], fill=(18, shade, 96 + shade // 2))
    draw.rectangle([3, 3, width - 4, height - 4], outline=(226, 190, 96), width=3)
    try:
        font = ImageFont.load_default(size=30 if height <= 200 else 36)
    except TypeError:   # Pillow < 10.1
        font = ImageFont.load_default()
    words, lines, line = title.split(), [], ''
    for word in words:
        trial = (line + ' ' + word).strip()
        if draw.textlength(trial, font=font) > width - 48 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    step = (font.size if hasattr(font, 'size') else 12) + 8
    top = (height - step * len(lines)) // 2
    for i, text in enumerate(lines):
        x = (width - draw.textlength(text, font=font)) // 2
        draw.text((x + 2, top + i * step + 2), text, font=font, fill=(0, 0, 0))
        draw.text((x, top + i * step), text, font=font, fill=(255, 236, 170))
    out = io.BytesIO()
    image.save(out, 'PNG')
    return out.getvalue()


def _png(data: bytes) -> bytes:
    if data[:8] == PNG:
        return data
    import io
    from PIL import Image
    out = io.BytesIO()
    Image.open(io.BytesIO(data)).convert('RGBA').save(out, 'PNG')
    return out.getvalue()


def _save_target(folder: str, target: tuple, log=print) -> tuple[bool, bool]:
    name, url, title, size = target
    path = os.path.join(folder, name)
    retry_path = path + '.retry'
    has_file = os.path.isfile(path)
    if has_file and not os.path.isfile(retry_path):
        return False, True
    try:
        if not url:
            data = render(title, size)
        else:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (ExviusOffline deal art)'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _png(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            log(f'DEAL-ART {name}: {exc}')
            if has_file:
                return False, False
            data = render(title, size)
            reachable = False
        else:
            data = render(title, size)
            reachable = True
    except Exception as exc:  # noqa: BLE001 -- retried on the next request or start
        log(f'DEAL-ART {name}: {exc}')
        if has_file:
            return False, False
        data = render(title, size)
        reachable = False
    else:
        reachable = True
    if not reachable:
        with open(retry_path, 'w', encoding='utf-8') as fh:
            fh.write('retry on next start\n')
    with open(path + '.tmp', 'wb') as fh:
        fh.write(data)
    os.replace(path + '.tmp', path)
    if reachable and os.path.isfile(retry_path):
        os.remove(retry_path)
    return True, reachable


def fetch_one(name: str, log=print) -> str | None:
    """Fetch one missing deal image immediately, independently of the startup download queue."""
    if os.environ.get('EXVIUS_DEAL_ART_FETCH', '1') != '1':
        return None
    target = next((target for target in _targets() if target[0] == name), None)
    if target is None:
        return None
    import data_paths
    folder = data_paths.DEAL_ART_ROOT
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with _file_lock(name):
        changed, _reachable = _save_target(folder, target, log)
    if changed:
        import ffbe_gacha
        ffbe_gacha._BANNER_ART_INDEX.clear()
    return path if os.path.isfile(path) else None


def fetch(log=print) -> int:
    """Download the deal banners' missing art. Returns how many files were added."""
    if os.environ.get('EXVIUS_DEAL_ART_FETCH', '1') != '1':
        return 0
    import data_paths
    folder = data_paths.DEAL_ART_ROOT
    os.makedirs(folder, exist_ok=True)
    added = placeholders = failed = 0
    changed = False
    for name, url, title, size in sorted(_targets(), key=lambda t: bool(t[1])):
        with _file_lock(name):
            was_added, reachable = _save_target(folder, (name, url, title, size), log)
        changed = changed or was_added
        if not reachable:
            failed += 1
            if was_added:
                placeholders += 1
            continue
        if not was_added:
            continue
        added += 1
        if url:
            time.sleep(0.5)   # be gentle with the Wayback Machine
    if changed:
        import ffbe_gacha
        ffbe_gacha._BANNER_ART_INDEX.clear()   # rebuilt on the next lookup, now with these files
    if added or failed:
        log(f'DEAL-ART: {added} image(s) added, {placeholders} offline placeholder(s), '
            f'{failed} source(s) unreachable (retry next start)')
    return added
