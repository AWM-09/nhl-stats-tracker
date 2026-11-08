#!/usr/bin/env python3
"""Build same-origin NHL Stats REST cache for GitHub Pages."""
import json, os, pathlib, time, urllib.parse, urllib.request, urllib.error, itertools
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

# Build every all-time franchise matchup from the NHL Stats game table. The
# table returns completed regular-season and playoff games with historic team
# IDs, scores and dates; team IDs are grouped by the NHL franchise lookup.
team_payload = fetch("https://api.nhle.com/stats/rest/en/team?limit=-1")
team_records = team_payload.get("data") if isinstance(team_payload, dict) else None
if not isinstance(team_records, list) or not team_records:
    raise SystemExit("NHL team identity lookup returned an unexpected schema.")
current_by_code = {}
for code in TEAM_CODES:
    candidates = [row for row in team_records if row.get("triCode") == code and row.get("franchiseId") is not None]
    if not candidates:
        raise SystemExit(f"NHL team identity lookup has no franchise for {code}.")
    current_by_code[code] = max(candidates, key=lambda row: int(row.get("id", 0)))
franchise_to_code = {}
for code, row in current_by_code.items():
    franchise = int(row["franchiseId"])
    if franchise in franchise_to_code:
        raise SystemExit(f"NHL franchise lookup maps more than one current team to franchise {franchise}.")
    franchise_to_code[franchise] = code
team_id_to_code = {}
team_id_to_name = {}
for row in team_records:
    franchise = row.get("franchiseId")
    if franchise is not None and int(franchise) in franchise_to_code:
        team_id_to_code[int(row["id"])] = franchise_to_code[int(franchise)]
        team_id_to_name[int(row["id"])] = row.get("fullName") or row.get("triCode") or "Historical NHL team"

game_params = urllib.parse.urlencode({"limit": "-1", "cayenneExp": "gameType>=2 and gameStateId=7"})
game_payload = fetch(f"{BASE}/game?{game_params}")
all_games = game_payload.get("data") if isinstance(game_payload, dict) else None
if not isinstance(all_games, list) or not all_games or len(all_games) != int(game_payload.get("total", -1)):
    raise SystemExit("All-time NHL game cache is incomplete or has an unexpected schema.")
h2h_dir = ROOT / "h2h"
h2h_dir.mkdir(parents=True, exist_ok=True)
game_dir = ROOT / "games" / "by-season"
game_dir.mkdir(parents=True, exist_ok=True)
pair_games = {tuple(sorted(pair)): [] for pair in itertools.combinations(TEAM_CODES, 2)}
season_games = {}
for game in all_games:
    home_id, away_id = int(game.get("homeTeamId", 0)), int(game.get("visitingTeamId", 0))
    home_code, away_code = team_id_to_code.get(home_id), team_id_to_code.get(away_id)
    if not home_code or not away_code or home_code == away_code:
        continue
    pair = tuple(sorted((home_code, away_code)))
    pair_games[pair].append({
        "id": game.get("id"), "gameDate": game.get("gameDate"),
        "season": game.get("season"), "gameType": game.get("gameType"),
        "homeTeam": {"franchiseCode": home_code, "name": team_id_to_name.get(home_id), "score": game.get("homeScore")},
        "awayTeam": {"franchiseCode": away_code, "name": team_id_to_name.get(away_id), "score": game.get("visitingScore")},
    })
    season_id = str(game.get("season") or "")
    start_year = season_id[:4]
    if len(start_year) == 4 and start_year.isdigit():
        season_games.setdefault(start_year, []).append({
            "id": game.get("id"), "gameDate": game.get("gameDate"),
            "season": game.get("season"), "gameType": game.get("gameType"),
            "home": home_code, "away": away_code,
            "homeScore": game.get("homeScore"), "awayScore": game.get("visitingScore"),
            "lastPeriodType": game.get("lastPeriodType") or game.get("gameOutcome", {}).get("lastPeriodType"),
        })
for (first, second), games in pair_games.items():
    games.sort(key=lambda item: (item.get("gameDate") or "", int(item.get("id") or 0)), reverse=True)
    target = h2h_dir / f"{first}-{second}.json"
    target.write_text(json.dumps({"first": first, "second": second, "source": "NHL Stats REST game and franchise tables", "games": games}, separators=(",", ":")), encoding="utf-8")
print(f"Cached all-time NHL matchup history for {len(pair_games)} franchise pairs ({sum(map(len, pair_games.values()))} completed games).")
for start_year, games in season_games.items():
    games.sort(key=lambda item: (item.get("gameDate") or "", int(item.get("id") or 0)))
    target = game_dir / f"{start_year}.json"
    target.write_text(json.dumps({"seasonStart": int(start_year), "source": "NHL Stats REST game and franchise tables", "games": games}, separators=(",", ":")), encoding="utf-8")
print(f"Cached completed game results for {len(season_games)} seasons ({sum(map(len, season_games.values()))} games).")

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

# Aggregate the cached team summaries across each franchise's historical team
# IDs. This gives the team hub a single, fast season-history file per franchise.
history_dir = ROOT / "team-history"
history_dir.mkdir(parents=True, exist_ok=True)
franchise_history = {code: {} for code in TEAM_CODES}
for year in YEARS:
    for phase, key in ((2, "regular"), (3, "playoffs")):
        source = OUT / f"{year}-{phase}-team.json"
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for row in payload.get("data", []):
            code = team_id_to_code.get(int(row.get("teamId", -1)))
            if not code:
                continue
            season = franchise_history[code].setdefault(
                year, {"year": year, "regular": None, "playoffs": None}
            )
            season[key] = row
for code, seasons in franchise_history.items():
    target = history_dir / f"{code}.json"
    target.write_text(json.dumps({
        "team": code,
        "source": "NHL Stats REST team summaries grouped by NHL franchise ID",
        "seasons": sorted(seasons.values(), key=lambda item: item["year"], reverse=True),
    }, separators=(",", ":")), encoding="utf-8")
print(f"Cached full team history for {len(franchise_history)} franchises.")

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
