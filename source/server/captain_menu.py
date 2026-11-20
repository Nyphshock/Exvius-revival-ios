"""King Mog's flat Item Exchange menu in the Farplane (operator's request, 2026-11-18).

ON GLOBAL (research/CAPTAIN_EXCHANGES.md): the wiki's "Farplane" page: "The Moogle Guard Captain is where you
exchange Super Trust Moogle Exchange Tickets for a Super Trust Moogle. Additionally, Dark Matter, obtained from
Dark Visions events, can be exchanged for weapons and recipes." The Update Schedule's Global history adds
"Super Trust Moogle & Super Trust Moogle Exchange Ticket" on 2019-08-08; every Dark Visions run page says
"Moogle Guard Captain will exchange various rewards for special currency within the event period", and lists
the dark weapons of that run's exchange: Dark Ragnarok and Dark Gambanteinn from run #1 (2020-04-23), Dark
Masamune and Dark Gandiva from #5 (2020-08-20), Dark Claymore from #15 (2021-07-22). Those six are the only
Captain stores with stock in Global's tables (F_STORE_ITEM_MST). The Farplane pack we ship
(`common_lang/sd/map/11/Ver128_211020100.cpk`, rebuilt from the Japanese data with English text) lists 18
exchanges in a six-page menu; 15 are Japan-only stores with no stock here.

THE MENU: King Mog's event conversation has one "Item Exchange" button, followed by a flat, alphabetized,
paginated list of in-stock exchange items whose currency the player holds. Each item opens its original store
with that store's currency and shared purchase count. Exhausted medal rows are omitted. The Mog Guard Captain
and Mog Minister exchange pages redirect to King Mog instead of presenting separate event selectors.

THE MAP SCRIPT (GL9 libgame). `map.bin` (CRILAYLA in the pack): int total size, int data version (0x41b), three
ints, an int when version >= 0x3fe, an int, then `count` x (short id, string) map chips, short count x int,
then short count of sub-maps, each `int size` (including itself) + `short id` + body
(`MapDrawManager::loadMapData` 0x1faacb8 skips the others by size). A sub-map's events are read in order
(`MapEventData::read` 0x1fc5290): int id, byte type, int x, int y, 7 shorts, 2 bytes, byte page count, pages.
A page (`MapEventPage::MapEventPage` 0x1fc7890): display byte (and, when non-zero, the NPC id and 16 bytes),
4 bytes, switch conditions (byte count x int id + bool), byte label count x short offset, int script length,
script. A script command is `byte cmd, short length, data` (`MapEventData::doScript` 0x1fc5ca4); commands up
to a `01` (step end) or a `04` (jump) run together. Used here: 08 show text (int id), 15 choice (byte count,
count x (int text, byte label), int prompt), 19 if items (byte mode 0 = all, byte count, count x (byte 0, byte
item type, int id, byte at least), byte label: `MapScriptData::procIfCmd` 0x1fd0180, `GameUtils::getItemNum`
type 20 = items), 44 open store (int store id), 02 wait (short frames), 04 jump (short label). King Mog's
events 2 and 7, Mog Minister event 4, and Captain events 5, 6 and 9 are in sub-map 67. The King pages open
base store 900104; the other exchange pages are replaced with a redirect to his Item Exchange menu.

HOW IT REACHES THE PHONE. The phone keeps every pack under its `Ver<N>_` name and fetches a new one only when
`F_RESOURCE_MAP_VERSION_MST_LOCALIZE` (served by ios_tables) names a new version, and it fetches that table at
login. So the list is worked out when the login's version table goes out (`ffbe_battle.serve_version_table`
-> `refresh`) and stays fixed until the next launch. When it changes, `rev` goes up (never down: at least
the hours since 2026-01-01), the pack gets version 20000 + rev and the table's advertised version rises by
rev. The pack is the shipped one with map.bin (stored uncompressed) and map_text_sg.txt replaced: both are
appended at the end and their file-table rows and the header's sizes patched in place; nothing else moves.
Built packs and the state are kept in the server root (`ios-cache/`).

STORE NAMES (operator's report, 2026-11-10). An exchange store shows its own name and owner from Global's text
(`F_TEXT_TOWN_STORE`, `F_TEXT_TOWN_STORE_OWNER_NAME`), which often names a different merchant than the one
opening it: Global's owner text names the other counter for 28 of the 67 event stores our store table gives to
King Mog or the Minister (Akademeia's 900107 says King Mog while the Minister runs it), and the Captain's menu
opens King Mog's and the Minister's stores.
`refresh` also works out `merchants` (the store King Mog shows: King Mog; the Minister's: Mog Minister; every store
in King Mog's Item Exchange) with a revision of its own
(`names_rev`), and ios_texts serves the two tables with those names under versions raised by it. A new week
renames stores without the Farplane pack being downloaded again.

PACK SIZE. `F_RESOURCE_MAP_CHECKSUM_MST` gives the Farplane pack (290001) 4,688,748 bytes, which matches neither the
pack we ship (5,001,656) nor the rebuilt one, and the phone downloaded the pack again on every visit. ios_tables
serves that row with the size of the pack actually served (`served_size`).

`EXVIUS_CAPTAIN_MENU=0` disables the custom King Mog menu and serves the shipped NPC scripts.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import struct
import threading
from collections import defaultdict
from datetime import datetime, timezone

SCENE = "211020100"
RESOURCE_ID = "290001"             # F_RESOURCE_MAP_MST row of 211020100.cpk
VERSION_FIELD = "OzT5lSz3"          # base (common_lang) file version in F_RESOURCE_MAP_VERSION_MST_LOCALIZE
VERSION_BASE = 20000
MENU_LAYOUT_REVISION = 6
SUBMAP = 67
KING_NPC = 0x05F5EC54               # King Mog's sprite (sub-map 67, events 2 and 7)
KING_STORE = 900104                 # King Mog's native store, opened by both event pages
MINISTER_NPC = 0x05F5F7A8           # Mog Minister's sprite (sub-map 67, event 4)
MINISTER_STORE = 900122
CAPTAIN_NPC = 0x0BED6C90
KING_PROMPT_SHIPPED = 110588       # "<name_npc=100002900><br>What do you want to exchange, Kupo?"
CAPTAIN_PROMPT_SHIPPED = 110719    # "<name=200028><br>Which exchange do you want to make?"
NEXT_TEXT, LEAVE_TEXT = 110717, 110718
TEXT_PROMPT, TEXT_NONE, TEXT_OUT, TEXT_MOVED, TEXT_ITEM_EXCHANGE, TEXT_ENTRY = (
    190001, 190002, 190003, 190004, 190005, 190100)
KING = "<name_npc=100002900><br>"
# Map text breaks its own lines (`<br>`, about 50 characters at most in the shipped lines).
TEXTS = {
    TEXT_PROMPT: KING + "What do you want to exchange, kupo?",
    TEXT_NONE: KING + "You don't have any exchange currency<br>right now, kupo. Come back when you do!",
    TEXT_OUT: KING + "You don't have any of that currency<br>left, kupo!",
    TEXT_MOVED: "All event exchanges are now available from King Mog.",
    TEXT_ITEM_EXCHANGE: "Item Exchange",
}
# Global's permanent and Dark Visions exchanges, now listed by King Mog when their currency is held.
OWN = (
    ("900146", "106211340", "Super Trust Moogle", "2019-08-08"),
    ("900157", "235018200", "Dark Ragnarok", "2020-04-23"),
    ("900164", "235018200", "Dark Gambanteinn", "2020-04-23"),
    ("900169", "235018200", "Dark Masamune", "2020-08-20"),
    ("900170", "235018200", "Dark Gandiva", "2020-08-20"),
    ("900190", "235018200", "Dark Claymore", "2021-07-22"),
)
# The merchant each exchange store is named after while he opens it (operator, 2026-11-10): see `merchants`.
KING_MOG, MINISTER, CAPTAIN_NAME = "King Mog", "Mog Minister", "Moogle Captain of the Guard"
COUNTER_NAMES = {"900104": KING_MOG, "900122": MINISTER}
_PATH = re.compile(r"(^|/)common_lang/sd/map/11/Ver(\d+)_" + SCENE + r"\.cpk$")
_LOCK = threading.Lock()


def enabled() -> bool:
    return str(os.environ.get("EXVIUS_CAPTAIN_MENU", "1")).strip().lower() not in ("0", "off", "false", "no")


# --- the list ---------------------------------------------------------------------------------------------

def _short(name: str) -> str:
    """A menu button's text: the exchange's name without "Exchange", the part before " - " when long."""
    name = re.sub(r"\s+Exchange$", "", str(name).strip())
    if len(name) > 34 and " - " in name:
        name = name.split(" - ")[0]
    name = re.sub(r"^FFBE\s+", "", name) if len(name) > 34 else name
    return name.replace("^", " ").replace("\n", " ")


def entries(now=None, week=None) -> list:
    """In-stock exchanges for owned currencies: [{store, currency, name, live, date}], live first."""
    import exvius_actions_shops as shops
    from exvius_shop_catalogue import shared_medal_counts
    week = week or shops._replay_week(now)
    opened, history = week[0], week[1]
    held = shops._held()
    towns = shops._table("F_TOWN_STORE_MST", "Z20mNDvL")
    medals = shops._table("F_MEDAL_EXCHANGE_MST", "S21FT3L8")
    bought = shared_medal_counts()
    store_rows = {}
    for row in shops._rows("F_STORE_ITEM_MST"):
        if str(row.get("YWF08vZS")) == "50":
            store_rows.setdefault(str(row["Z20mNDvL"]), []).append(str(row["6uIYE15X"]))

    def has_stock(row_ids):
        for row_id in row_ids:
            row = medals.get(str(row_id))
            if not row:
                continue
            mode = str(row.get("kR4n5DxP"))
            if mode == "2" or (mode == "1" and int(bought.get(str(row_id), 0)) < int(row["x0NDnEC9"])):
                return True
        return False

    own = {store: (currency, name, day) for store, currency, name, day in OWN}
    out, seen = [], set()
    for store, (currency, name, day) in own.items():
        if held.get(currency) and has_stock(store_rows.get(store, [])):
            out.append({"store": store, "currency": currency, "name": name, "live": False, "date": day})
            seen.add(store)
    runs = shops._area_runs()
    for ex in shops._event_exchanges().get("exchanges", []):
        store, currency = str(ex["store"]), str(ex["currency"])
        if (store in seen or store in own or not held.get(currency) or not ex.get("rows")
            or not has_stock(ex["rows"])):
            continue
        if (towns.get(store) or {}).get("kaG4xf3I") != "5":
            continue
        areas = [str(a) for a in ex.get("event_areas") or []]
        live = [opened[a] for a in areas if a in opened]
        ran = [r for a in areas for r in runs.get(a, []) if r < history]
        out.append({"store": store, "currency": currency, "name": _short(ex.get("name") or store),
                    "live": bool(live), "date": max(live + ran or [str(ex.get("first_run") or "")])})
        seen.add(store)
    out.sort(key=lambda e: (e["live"], e["date"], e["store"]), reverse=True)
    return out


def exchange_items(stores: list) -> list:
    """Flat, in-stock product list for the King Mog menu; each item retains its own store currency."""
    if not stores:
        return []
    import exvius_actions_shops as shops
    from exvius_shop_catalogue import catalogue, exhausted_medal_rows, labels

    stock_by_store = {}
    for row in shops._rows("F_STORE_ITEM_MST"):
        if str(row.get("YWF08vZS")) == "50":
            stock_by_store.setdefault(str(row["Z20mNDvL"]), []).append(str(row["6uIYE15X"]))
    offers_by_medal = defaultdict(list)
    for pid, offer in catalogue()[2].items():
        if offer.get("medal"):
            offers_by_medal[str(offer["medal"])].append((pid, offer))
    held = shops._held()
    names = labels()
    exhausted = exhausted_medal_rows()
    own_names = {store: name for store, _, name, _ in OWN}
    out, seen = [], set()
    for store in stores:
        store_id = str(store["store"])
        for medal in stock_by_store.get(store_id, []):
            if medal in exhausted or medal in seen:
                continue
            product_ids = offers_by_medal.get(medal) or []
            affordable = [(pid, offer) for pid, offer in product_ids
                          if (str((offer.get("cost") or ("", ""))[0]) == "20"
                              and held.get(str((offer.get("cost") or ("", ""))[1]), 0)
                              >= int(offer.get("price") or 0))]
            if not affordable:
                continue
            reward_name = names.get(affordable[0][0], {}).get("name")
            if not reward_name:
                reward_name = own_names.get(store_id)
            if not reward_name:
                continue
            event_name = _short(store["name"])
            words = event_name.split()
            suffix = " - " + event_name
            while (store_id not in own_names and words and event_name.lower() not in reward_name.lower()
                   and len(reward_name) + len(suffix) > 34):
                words = words[1:]
                suffix = " - " + " ".join(words) if words else ""
            if store_id not in own_names and suffix and event_name.lower() not in reward_name.lower():
                label = reward_name + suffix
            else:
                label = reward_name if len(reward_name) <= 34 else reward_name[:31].rstrip() + "..."
            out.append({"store": store_id, "currency": str(store["currency"]), "medal": medal, "name": label})
            seen.add(medal)
    out.sort(key=lambda item: (item["name"].casefold(), item["store"]))
    return out


def item_exchange_schedule() -> dict | None:
    """The native King Mog screen opens one store; its index aliases all eligible medal offers into it."""
    items = state().get("offers") or []
    if not items:
        return None
    primary = items[0]
    return {"Z20mNDvL": KING_STORE, "za2xsDj5": str(KING_STORE), "w7VR6ypY": "0",
            "VjJQ51uG": "2020-01-01 00:00:00", "m8ivD4NX": "2099-12-31 23:59:59",
            "suR36Jpm": "20:" + str(primary["currency"]), "89YmCAzo": "", "0euar5mZ": ""}


# --- the script -------------------------------------------------------------------------------------------

def _cmd(code: int, data: bytes = b"") -> bytes:
    return bytes([code]) + struct.pack(">H", len(data)) + data


STEP = _cmd(0x01)


def script(items: list) -> tuple[list, bytes]:
    """King Mog's single native Item Exchange button; products are rendered by the game's store scene."""
    n = len(items)
    if not n:
        body = _cmd(0x08, struct.pack(">I", TEXT_NONE)) + STEP
        return [len(body)], body
    choice = (bytes([2]) + struct.pack(">IB", TEXT_ITEM_EXCHANGE, 1)
              + struct.pack(">IB", LEAVE_TEXT, 2))
    menu = _cmd(0x15, choice + struct.pack(">I", TEXT_PROMPT)) + STEP
    open_store = (_cmd(0x44, struct.pack(">I", KING_STORE)) + _cmd(0x02, b"\x00\x01")
                  + STEP + _cmd(0x04, struct.pack(">H", 0)) + STEP)
    leave = STEP
    return [0, len(menu), len(menu) + len(open_store)], menu + open_store + leave


def texts(items: list) -> dict:
    return dict(TEXTS)


# --- map.bin and the text file ----------------------------------------------------------------------------

def _submaps(b: bytes):
    """(offset of each sub-map's size field, size, id) and the data version."""
    ver = struct.unpack_from(">I", b, 4)[0]
    p = 8 + 12 + (4 if ver >= 0x3fe else 0) + 4
    n = struct.unpack_from(">I", b, p)[0]
    p += 4
    for _ in range(n):
        p += 2
        p += 2 + struct.unpack_from(">H", b, p)[0]
    if ver > 0x3f6:
        p += 2 + 4 * struct.unpack_from(">H", b, p)[0]
    n = struct.unpack_from(">H", b, p)[0]
    p += 2
    out = []
    for _ in range(n):
        size, mid = struct.unpack_from(">IH", b, p)
        out.append((p, size, mid))
        p += size
    if p != len(b):
        raise ValueError("map.bin: sub-maps don't end at the end of the file")
    return out, ver


def _event(b: bytes, p: int, ver: int):
    """([(label table offset, end of script, script offset)] of each page, end) of the event at `p`."""
    p += 4 if ver >= 0x400 else 2
    kind = b[p]
    p += 1 + 8 + 14 + (2 if ver >= 0x416 else 0)
    pages = []
    count = b[p]
    p += 1
    for _ in range(count):
        disp = b[p]
        p += 1
        if disp >= 1:
            if kind == 1:
                p += 4
            elif kind == 0x1F:
                p += 4
                p += 2 + struct.unpack_from(">H", b, p)[0] + 1
            else:
                p += 2
            p += 4 + 5 + 2 + (1 if ver >= 0x40A else 0) + (1 if ver >= 0x415 else 0)
        p += 4
        p += 1 + 5 * b[p]
        at = p
        p += 1 + 2 * b[p]
        length = struct.unpack_from(">I", b, p)[0]
        p += 4
        pages.append((at, p + length, p))
        p += length
    return pages, p


def _commands(b: bytes, s: int, e: int):
    """[(offset, cmd, data)] of a script, or None when it doesn't parse to its exact end."""
    out, q = [], s
    while q < e:
        if q + 3 > e:
            return None
        ln = struct.unpack_from(">H", b, q + 1)[0]
        if q + 3 + ln > e:
            return None
        out.append((q, b[q], b[q + 3:q + 3 + ln]))
        q += 3 + ln
    return out


def _npc_pages(b: bytes, npc: int, accepts, name: str):
    """Find parsed pages for an NPC in the exchange sub-map that match a script predicate."""
    maps, ver = _submaps(b)
    sub = next((m for m in maps if m[2] == SUBMAP), None)
    if sub is None:
        raise ValueError(f"map.bin: no sub-map {SUBMAP}")
    lo, hi = sub[0], sub[0] + sub[1]
    head = 4 + 1 + 8 + 14 + (2 if ver >= 0x416 else 0) + 1
    marker = b"\x01" + struct.pack(">I", npc)
    pages, at, seen = [], b.find(marker, lo, hi), set()
    while at != -1:
        start = at - head
        if start >= lo and start not in seen and b[start + 4] == 1:
            seen.add(start)
            try:
                found, end = _event(b, start, ver)
            except (struct.error, IndexError):
                found, end = [], hi + 1
            for label_at, e, s in (found if end <= hi else []):
                cmds = _commands(b, s, e)
                if cmds and accepts(cmds):
                    pages.append((label_at, e))
        at = b.find(marker, at + 1, hi)
    if not pages:
        raise ValueError(f"map.bin: {name} exchange pages were not found")
    if any(a < e for (_, e), (a, _) in zip(pages, pages[1:])):
        raise ValueError(f"map.bin: overlapping {name} pages; not patched")
    return sub, pages


def _opens_store(store: int):
    return lambda cmds: any(cmd == 0x44 and len(data) == 4
                            and int.from_bytes(data, "big") == store for _, cmd, data in cmds)


def _king_pages(b: bytes):
    return _npc_pages(b, KING_NPC, _opens_store(KING_STORE), "King Mog")


def _captain_pages(b: bytes):
    def has_menu(cmds):
        return cmds[0][1] == 0x15 and int.from_bytes(cmds[0][2][-4:], "big") == CAPTAIN_PROMPT_SHIPPED
    return _npc_pages(b, CAPTAIN_NPC, has_menu, "Moogle Guard Captain")


def _minister_pages(b: bytes):
    return _npc_pages(b, MINISTER_NPC, _opens_store(MINISTER_STORE), "Mog Minister")


def _page_bytes(labels, body):
    return (bytes([len(labels)]) + struct.pack(">" + "H" * len(labels), *labels)
            + struct.pack(">I", len(body)) + body)


def patch_map(b: bytes, items: list) -> tuple[bytes, int]:
    """Move all exchange pages to King Mog; the Captain and Minister direct players to him."""
    sub, king_pages = _king_pages(b)
    captain_sub, captain_pages = _captain_pages(b)
    minister_sub, minister_pages = _minister_pages(b)
    if captain_sub[0] != sub[0] or minister_sub[0] != sub[0]:
        raise ValueError("map.bin: exchange NPCs are not in the same sub-map")
    labels, body = script(items)
    moved = _cmd(0x08, struct.pack(">I", TEXT_MOVED)) + STEP
    moved_page = _page_bytes([len(moved)], moved)
    replacements = [(at, end, _page_bytes(labels, body)) for at, end in king_pages]
    replacements.extend((at, end, moved_page) for at, end in captain_pages + minister_pages)
    replacements.sort(key=lambda entry: entry[0])
    out, prev, grow = bytearray(), 0, 0
    for at, end, replacement in replacements:
        if at < prev:
            raise ValueError("map.bin: overlapping exchange NPC pages; not patched")
        out += b[prev:at] + replacement
        grow += len(replacement) - (end - at)
        prev = end
    out += b[prev:]
    struct.pack_into(">I", out, sub[0], sub[1] + grow)   # the sub-map's size
    struct.pack_into(">I", out, 0, len(out))             # the file's
    return bytes(out), len(replacements)


def patch_text(text: bytes, items: list, columns: int = 8) -> bytes:
    """map_text_sg.txt (`id^EN^ZH^KO^FR^DE^ES^TH^ID`) with the Captain's lines added (English everywhere)."""
    new = texts(items)
    keep = [line for line in text.decode("utf-8").split("\n")
            if line and not (line.split("^", 1)[0].isdigit() and int(line.split("^", 1)[0]) in new)]
    for tid, line in sorted(new.items()):
        keep.append("^".join([str(tid)] + [line] * columns))
    return ("\n".join(keep) + "\n").encode("utf-8")


# --- the pack ---------------------------------------------------------------------------------------------

def build_pack(src: str, items: list, out_path: str) -> dict:
    """The shipped pack with map.bin and map_text_sg.txt replaced, written to `out_path`."""
    from ios_art import _cells, _plain, _mask, _FMT
    with open(src, "rb") as fh:
        blob = bytearray(fh.read())
    if blob[:4] != b"CPK ":
        raise ValueError("not a CPK")
    hsize = struct.unpack_from("<Q", blob, 8)[0]
    head_raw = bytes(blob[16:16 + hsize])
    header = bytearray(_plain(head_raw))
    hcols, hrows = _cells(bytes(header))
    h = {k: v[1] for k, v in hrows[0].items()}
    toc_off, content_off = h["TocOffset"], h["ContentOffset"]
    if blob[toc_off:toc_off + 4] != b"TOC ":
        raise ValueError("no TOC")
    tsize = struct.unpack_from("<Q", blob, toc_off + 8)[0]
    toc_raw = bytes(blob[toc_off + 16:toc_off + 16 + tsize])
    toc = bytearray(_plain(toc_raw))
    tcols, trows = _cells(bytes(toc))
    tfmt = {c[0]: _FMT[c[2]] for c in tcols}
    rows = {r["FileName"][1]: r for r in trows}

    def member(name):
        r = rows[name]
        at = toc_off + r["FileOffset"][1]
        data = bytes(blob[at:at + r["FileSize"][1]])
        if r["FileSize"][1] != r["ExtractSize"][1]:
            from crilayla import decompress
            data = decompress(data)
        return data

    new_map, replaced = patch_map(member("map.bin"), items)
    new_text = patch_text(member("map_text_sg.txt"), items)
    for name, data in (("map.bin", new_map), ("map_text_sg.txt", new_text)):
        blob += b"\0" * (-len(blob) % 8)
        r = rows[name]
        for field, value in (("FileOffset", len(blob) - toc_off), ("FileSize", len(data)),
                             ("ExtractSize", len(data))):
            struct.pack_into(tfmt[field], toc, r[field][0], value)
        blob += data
    _, trows2 = _cells(bytes(toc))
    sizes = [(r["FileSize"][1], r["ExtractSize"][1]) for r in trows2]
    hfmt = {c[0]: _FMT[c[2]] for c in hcols}
    values = {"FileSize": len(blob), "ContentSize": len(blob) - content_off,
              "TotalDataSize": len(blob) - content_off,
              "EnabledPackedSize": sum(s for s, _ in sizes), "EnabledDataSize": sum(x for _, x in sizes)}
    for name, value in values.items():
        if name in hrows[0]:
            struct.pack_into(hfmt[name], header, hrows[0][name][0], value)
    blob[16:16 + hsize] = bytes(header) if head_raw[:4] == b"@UTF" else _mask(bytes(header))
    blob[toc_off + 16:toc_off + 16 + tsize] = bytes(toc) if toc_raw[:4] == b"@UTF" else _mask(bytes(toc))
    tmp = out_path + ".tmp"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(tmp, "wb") as out:
        out.write(blob)
    os.replace(tmp, out_path)
    return {"pages": replaced, "entries": len(items), "size": len(blob)}


def source_pack(*roots) -> str | None:
    for root in roots:
        if root:
            hits = [p for p in glob.glob(os.path.join(root, "common_lang", "sd", "map", "11", f"Ver*_{SCENE}.cpk"))
                    if int(re.search(r"Ver(\d+)_", os.path.basename(p)).group(1)) < VERSION_BASE]
            if hits:
                return max(hits, key=lambda p: int(re.search(r"Ver(\d+)_", os.path.basename(p)).group(1)))
    return None


# --- state: what the phone was told at its last login -----------------------------------------------------

def cache_dir() -> str:
    import ios_art
    return ios_art.cache_dir()


def _state_path() -> str:
    return os.path.join(cache_dir(), "captain_menu.json")


def state() -> dict:
    try:
        with open(_state_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"rev": 0, "sig": "off", "entries": [], "offers": [],
                "names_rev": 0, "names_sig": "off", "names": {}}


def _signature(items) -> str:
    if items is None:
        return "off"
    return hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:16]


def _menu_signature(items) -> str:
    if items is None:
        return "off"
    payload = {"layout": MENU_LAYOUT_REVISION, "entries": items}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def merchants(week=None, items=None) -> dict | None:
    """{exchange store: merchant} for this week (operator, 2026-11-10). Each exchange store carries Global's own
    store and owner names (`F_TEXT_TOWN_STORE`, `F_TEXT_TOWN_STORE_OWNER_NAME`), and those often name the other
    counter (Akademeia's 900107 says King Mog, but our table gives it to the Minister) or, for the Captain's
    exchanges, King Mog or the Minister. So the store King Mog shows this week is named King Mog, the
    Minister's Mog Minister, and every store in the Captain's menu Moogle Captain of the Guard (his name in
    the Farplane). None when neither the counters (`EXVIUS_EXCHANGE_SCHEDULE`) nor the Captain follow the
    replay."""
    import exvius_actions_shops as shops
    counters = shops.exchange_schedule_enabled()
    if not counters and items is None:
        return None
    out = {}
    if counters:
        for row in shops.counter_schedules(week=week):
            name = COUNTER_NAMES.get(str(row.get("Z20mNDvL")))
            if name:
                out[str(row["za2xsDj5"])] = name
    for item in items or []:
        out[str(item["store"])] = KING_MOG
    return out


def _next_rev(old) -> int:
    """Revisions only go up, even if the state file is lost: at least the hours since 2026-01-01."""
    hours = int((datetime.now(timezone.utc) - datetime(2026, 1, 1, tzinfo=timezone.utc)).total_seconds() // 3600)
    return max(int(old or 0) + 1, hours)


def refresh(now=None) -> dict:
    """Work out King Mog's owned exchanges and item list for this login, plus the store-name overrides."""
    import exvius_actions_shops as shops
    from ffbe_state import State
    stores = offers = names = None
    if enabled() or shops.exchange_schedule_enabled():
        if State.player is None:
            return state()      # no save loaded: keep what the phone has
        try:
            week = shops._replay_week(now)
            stores = entries(now, week) if enabled() else None
            offers = exchange_items(stores) if stores is not None else None
            names = merchants(week, stores)
        except Exception as exc:  # noqa: BLE001 -- keep what the phone has
            print(f"[captain-menu] list not worked out ({exc!r}); keeping the last one", flush=True)
            return state()
    sig = _menu_signature({"stores": stores, "offers": offers} if stores is not None else None)
    names_sig = _signature(names)
    with _LOCK:
        st = state()
        changed = []
        if st.get("sig", "off") != sig:
            st.update(rev=_next_rev(st.get("rev")), sig=sig,
                      entries=stores or [], offers=offers or [])
            changed.append("menu")
        if st.get("names_sig", "off") != names_sig:
            st.update(names_rev=_next_rev(st.get("names_rev")), names_sig=names_sig, names=names or {})
            changed.append("names")
        if not changed:
            return st
        os.makedirs(cache_dir(), exist_ok=True)
        tmp = _state_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(st, fh, indent=1)
        os.replace(tmp, _state_path())
    if "menu" in changed:
          print(f"[king-menu] rev {st['rev']}: {len(st['entries'])} store(s), "
              f"{len(st['offers'])} item(s)" if sig != "off"
              else f"[king-menu] rev {st['rev']}: off, shipped menu", flush=True)
    if "names" in changed:
        print(f"[captain-menu] store names rev {st['names_rev']}: {len(st['names'])} store(s) renamed"
              if names_sig != "off" else f"[captain-menu] store names rev {st['names_rev']}: Global's", flush=True)
    return st


def names_rev() -> int:
    """Added to the two store-name text tables' versions and the text index's (ios_texts)."""
    return int(state().get("names_rev") or 0)


def store_texts() -> dict:
    """{text table: {key: (text, replace)}} naming each exchange store after the merchant opening it."""
    st = state()
    if st.get("names_sig", "off") == "off":
        return {}
    names = st.get("names") or {}
    return {"F_TEXT_TOWN_STORE": {f"MST_TOWNSTORE_NAME_{s}": (n, True) for s, n in names.items()},
            "F_TEXT_TOWN_STORE_OWNER_NAME": {f"MST_TOWN_STORE_OWNER_NAME_{s}": (n, True) for s, n in names.items()}}


def table_bump() -> int:
    """Added to F_RESOURCE_MAP_VERSION_MST_LOCALIZE's advertised version (0 until the menu was ever served)."""
    return int(state().get("rev") or 0)


def version() -> int | None:
    st = state()
    return VERSION_BASE + int(st["rev"]) if st.get("sig") != "off" and st.get("rev") else None


def version_sets(*roots) -> dict:
    """The Farplane pack's new version for the map version table; none without the shipped pack to build on
    (the phone would ask for a file nobody can serve and fail to enter the Farplane)."""
    v = version()
    return {RESOURCE_ID: {VERSION_FIELD: v}} if v and source_pack(*roots) else {}


def wants(rel: str) -> bool:
    m = _PATH.search(rel)
    return bool(m) and int(m.group(2)) >= VERSION_BASE and version() is not None


def built_pack(*roots) -> tuple[str, dict] | None:
    st = state()
    if st.get("sig") == "off":
        return None
    src = source_pack(*roots)
    if not src:
        return None
    path = os.path.join(cache_dir(), f"captain-{st['sig']}-{os.path.basename(src)}")
    with _LOCK:
        if not os.path.isfile(path):
            info = build_pack(src, st.get("offers") or [], path)
            for old in glob.glob(os.path.join(cache_dir(), "captain-*.cpk")):
                if old != path:
                    os.remove(old)
            print(f"[captain-menu] built {os.path.basename(path)}: {info}", flush=True)
    return path, st


def served_size(*roots) -> int | None:
    """Size of the Farplane pack the phone gets for the advertised version (F_RESOURCE_MAP_CHECKSUM_MST). The
    shipped size there (4,688,748) matches neither the pack we ship (5,001,656) nor the rebuilt one, and the
    phone downloaded the pack again on every visit (operator, 2026-11-10)."""
    src = source_pack(*roots)
    if not src:
        return None
    if version_sets(*roots):
        try:
            built = built_pack(*roots)
        except Exception:  # noqa: BLE001 -- serve() falls back to the shipped pack too
            built = None
        if built:
            return os.path.getsize(built[0])
    return os.path.getsize(src)


def serve(rel: str, *roots) -> tuple[bytes | None, str | None]:
    """The rebuilt pack; the shipped one under the new name if the build fails, so the Farplane still loads."""
    try:
        built = built_pack(*roots)
    except Exception as exc:  # noqa: BLE001
        print(f"[captain-menu] pack not built ({exc!r}); serving the shipped menu", flush=True)
        built = None
    if built:
        with open(built[0], "rb") as fh:
            return fh.read(), (f"Farplane pack with King Mog Item Exchange "
                               f"({len(built[1].get('offers') or [])} items, rev {built[1]['rev']})")
    src = source_pack(*roots)
    if not src:
        return None, None
    with open(src, "rb") as fh:
        return fh.read(), f"Farplane pack {os.path.basename(src)} (King Mog menu not rebuilt)"
