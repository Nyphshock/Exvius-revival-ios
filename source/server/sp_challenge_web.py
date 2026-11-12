"""Offline details page for the SP Challenge WebView."""
from html import escape
from urllib.parse import unquote


def matches(path: str) -> bool:
    return unquote(path.split("?", 1)[0]).lower().endswith("/spchallenge.php")


def selected_quest_id(fields, available_ids) -> str:
    available = {str(quest_id) for quest_id in available_ids}
    for values in fields.values():
        for value in values if isinstance(values, (list, tuple)) else [values]:
            quest_id = str(value).strip()
            if quest_id in available:
                return quest_id
    return ""


def render(selected_id, picked, tables, daily_quests=()) -> str:
    titles = tables.get("titles") or {}
    schedule_names = tables.get("schedule_names") or {}
    sections = []

    daily_items = []
    for quest_id, quest in daily_quests:
        if str(quest_id) != selected_id:
            continue
        title = quest.get("name") or f"Daily Quest {quest_id}"
        detail = quest.get("detail") or ""
        try:
            target = int(quest.get("target", 0) or 0)
        except (TypeError, ValueError):
            target = 0
        goal = f"<p class=\"goal\">{escape(str(detail))}</p>" if detail else ""
        if target > 0:
            goal += f"<p class=\"goal\">Complete {target} time{'s' if target != 1 else ''}.</p>"
        daily_items.append(f"<li><h3>{escape(str(title))}</h3>{goal}</li>")
    if daily_items:
        sections.append(f"<section><h2>Daily Quests</h2><ol>{''.join(daily_items)}</ol></section>")

    for group_id, rows in picked:
        schedule_key = schedule_names.get(str(group_id), "")
        schedule_title = titles.get(schedule_key) or f"Quests {group_id}"
        quests = []
        for row in rows:
            quest_id = str(row.get("V36ygRYs", ""))
            if not quest_id or quest_id != selected_id:
                continue
            title = titles.get(f"MST_SPCHALLENGE_NAME_{quest_id}") or f"MST_SPCHALLENGE_NAME_{quest_id}"
            try:
                target = int(row.get("oz5Vt6AR", 0) or 0)
            except (TypeError, ValueError):
                target = 0
            target_text = (f"<p class=\"goal\">Complete {target} time"
                           f"{'s' if target != 1 else ''}.</p>") if target > 0 else ""
            quests.append(f"<li><h3>{escape(str(title))}</h3>{target_text}</li>")
        if quests:
            sections.append(
                f"<section><h2>{escape(str(schedule_title))}</h2><ol>{''.join(quests)}</ol></section>"
            )

    content = "".join(sections) or "<p>No details are available for the selected quest.</p>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quest Details</title>
<style>
body{{margin:0;background:#171923;color:#f5f5f5;font:16px -apple-system,BlinkMacSystemFont,sans-serif}}
main{{max-width:760px;margin:auto;padding:20px}}
h1{{font-size:24px}} section{{margin:20px 0;padding:16px;background:#252a38;border-radius:12px}}
h2{{margin:0 0 12px;color:#ffd66b;font-size:20px}}
ol{{padding-left:24px}} li{{padding:8px 0;border-bottom:1px solid #3b4050}}
li:last-child{{border-bottom:0}} h3{{margin:0;font-size:17px}} .goal{{margin:6px 0 0;color:#c5cad6}}
</style>
</head>
<body><main><h1>Quest Details</h1>{content}</main></body>
</html>"""


def page(fields) -> str:
    from ffbe_player import State, daily_quest_by_id, sp_challenge_picked, sp_challenge_tables

    tables = sp_challenge_tables()
    daily = []
    picked = sp_challenge_picked()
    available_ids = set()
    if State.player is not None:
        catalogue = daily_quest_by_id()
        daily = [(str(quest_id), catalogue[str(quest_id)])
                 for quest_id in State.player.daily_quest_ids() if str(quest_id) in catalogue]
        available_ids.update(quest_id for quest_id, _quest in daily)
    available_ids.update(str(row.get("V36ygRYs", ""))
                         for _group, rows in picked for row in rows if row.get("V36ygRYs"))

    selected_id = selected_quest_id(fields, available_ids)
    return render(selected_id, picked, tables, daily)
