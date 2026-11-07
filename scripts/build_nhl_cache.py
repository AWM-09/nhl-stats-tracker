#!/usr/bin/env python3
"""Build same-origin NHL Stats REST cache for GitHub Pages."""
import json, os, pathlib, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

OUT = pathlib.Path("site/data/seasons")
OUT.mkdir(parents=True, exist_ok=True)
ROOT = pathlib.Path("site/data")
ROOT.mkdir(parents=True, exist_ok=True)
YEARS = range(1950, 2027)
KINDS = ("skater", "goalie", "team")
PHASES = (2, 3)
BASE = "https://api.nhle.com/stats/rest/en"

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "AlexMyrus-NHL-Stats-Tracker/1.0", "Accept": "application/json"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise last

def write_snapshot(name, url):
    target = ROOT / name
    try:
        payload = fetch(url)
        target.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"Cached snapshot {name}")
    except Exception as exc:
        print(f"WARNING: snapshot {name}: {exc}")
        target.write_text(json.dumps({"cache_error": str(exc)}), encoding="utf-8")

write_snapshot("standings-now.json", "https://api-web.nhle.com/v1/standings/now")
write_snapshot("score-now.json", "https://api-web.nhle.com/v1/score/now")

# Current rosters and recent complete season schedules power team dossiers and H2H.
# Keep these same-origin so GitHub Pages does not depend on browser CORS access.
TEAM_CODES = ("ANA", "UTA", "BOS", "BUF", "CGY", "CAR", "CHI", "COL", "CBJ", "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NSH", "NJD", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR", "VAN", "VGK", "WPG", "WSH")
today = datetime.now(timezone.utc).date()
current_season_start = today.year if today.month >= 8 else today.year - 1
team_dir = ROOT / "teams"
team_dir.mkdir(parents=True, exist_ok=True)
for code in TEAM_CODES:
    write_snapshot(f"teams/{code}-roster.json", f"https://api-web.nhle.com/v1/roster/{code}/current")
    for start in (current_season_start - 1, current_season_start):
        write_snapshot(f"teams/{code}-schedule-{start}.json", f"https://api-web.nhle.com/v1/club-schedule-season/{code}/{start}{start+1}")

success = failures = 0
for year in YEARS:
    season = f"{year}{year+1}"
    for kind in KINDS:
        for phase in PHASES:
            params = urllib.parse.urlencode({
                "cayenneExp": f"seasonId={season} and gameTypeId={phase}",
                "sort": "points" if kind in ("skater", "team") else "wins",
                "dir": "DESC",
                "limit": "-1",
            })
            url = f"{BASE}/{kind}/summary?{params}"
            target = OUT / f"{year}-{phase}-{kind}.json"
            try:
                payload = fetch(url)
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise ValueError("Unexpected NHL API response schema")
                target.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
                success += 1
                print(f"Cached {year} phase {phase} {kind}: {len(payload['data'])} rows")
            except Exception as exc:
                failures += 1
                print(f"WARNING: {year} phase {phase} {kind}: {exc}")
                target.write_text(json.dumps({"data": [], "cache_error": str(exc)}), encoding="utf-8")
            time.sleep(0.15)
print(f"Cache complete: {success} successful, {failures} failed.")
if success == 0:
    raise SystemExit("No NHL data was cached; refusing to deploy an empty data cache.")


# Cache the entire current NHL season as weekly schedule snapshots for the full calendar.
today = datetime.now(timezone.utc).date()
schedule_dir = ROOT / "schedule"
schedule_dir.mkdir(parents=True, exist_ok=True)
season_start = today.year if today.month >= 8 else today.year - 1
week_anchor = datetime(season_start, 8, 1, tzinfo=timezone.utc).date()
season_end = datetime(season_start + 1, 7, 31, tzinfo=timezone.utc).date()
weekly_success = 0
while week_anchor <= season_end:
    name = f"week-{week_anchor.isoformat()}.json"
    try:
        payload = fetch(f"https://api-web.nhle.com/v1/schedule/{week_anchor.isoformat()}")
        if not isinstance(payload, dict) or not (isinstance(payload.get("gameWeek"), list) or isinstance(payload.get("games"), list)):
            raise ValueError("Unexpected weekly schedule response schema")
        (schedule_dir / name).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        weekly_success += 1
        print(f"Cached full-season schedule week {week_anchor.isoformat()}")
    except Exception as exc:
        (schedule_dir / name).write_text(json.dumps({"cache_error": str(exc)}), encoding="utf-8")
        print(f"WARNING: weekly schedule {week_anchor.isoformat()}: {exc}")
    week_anchor += timedelta(days=7)
if weekly_success < 40:
    raise SystemExit(f"Only {weekly_success} full-season schedule weeks were cached; refusing to publish an incomplete calendar.")

# Cache per-game player rows for recent seasons. Older season totals remain available across the full archive.
for year in range(2024, 2027):
    season = f"{year}{year+1}"
    for kind in ("skater", "goalie"):
        for phase in PHASES:
            params = urllib.parse.urlencode({
                "cayenneExp": f"seasonId={season} and gameTypeId={phase}",
                "sort": "gameDate",
                "dir": "ASC",
                "limit": "-1",
                "isGame": "true",
            })
            url = f"{BASE}/{kind}/summary?{params}"
            target = OUT / f"{year}-{phase}-{kind}-games.json"
            try:
                payload = fetch(url)
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise ValueError("Unexpected NHL per-game response schema")
                target.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
                print(f"Cached per-game {year} phase {phase} {kind}: {len(payload['data'])} rows")
            except Exception as exc:
                target.write_text(json.dumps({"data": [], "cache_error": str(exc)}), encoding="utf-8")
                print(f"WARNING: per-game {year} phase {phase} {kind}: {exc}")

# Cache schedule snapshots on the server so GitHub Pages visitors never call NHL Web API cross-origin.
from datetime import datetime, timedelta, timezone
schedule_dir = ROOT / "schedule"
games_dir = ROOT / "games"
schedule_dir.mkdir(parents=True, exist_ok=True)
games_dir.mkdir(parents=True, exist_ok=True)
today = datetime.now(timezone.utc).date()
recent_game_ids = set()
for offset in range(-7, 46):
    day = today + timedelta(days=offset)
    name = f"score-{day.isoformat()}.json"
    try:
        payload = fetch(f"https://api-web.nhle.com/v1/score/{day.isoformat()}")
        (schedule_dir / name).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"Cached schedule {day.isoformat()}")
        if offset <= 0:
            for game in payload.get("games", []):
                state = str(game.get("gameState", "")).upper()
                if state in ("FINAL", "OFF", "OVER"):
                    recent_game_ids.add(str(game.get("id")))
    except Exception as exc:
        (schedule_dir / name).write_text(json.dumps({"cache_error": str(exc)}), encoding="utf-8")
        print(f"WARNING: schedule {day.isoformat()}: {exc}")
for game_id in sorted(recent_game_ids):
    try:
        payload = fetch(f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore")
        (games_dir / f"{game_id}-boxscore.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"Cached boxscore {game_id}")
    except Exception as exc:
        print(f"WARNING: boxscore {game_id}: {exc}")
