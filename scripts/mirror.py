#!/usr/bin/env python3
"""
LakayTV Direct's copy of TheSportsDB data: the same answers the app asks TheSportsDB for, as files, so Sports Radar
reads them here first and stays within the free key's 30 requests a minute.

Data: TheSportsDB (https://www.thesportsdb.com) — its terms: "You can scrape, copy and modify content returned from
the API using the official end points" and "must mention us as the source of the data". Artwork is linked, never
copied. Run daily by .github/workflows/mirror.yml; the key is the free public one unless the SPORTSDB_KEY secret is set.
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error, datetime

KEY = os.environ.get("SPORTSDB_KEY") or "123"
BASE = f"https://www.thesportsdb.com/api/v1/json/{KEY}/"
OUT = os.path.join(os.path.dirname(__file__), "..", "v1")
PAUSE = 2.2  # seconds between requests: under 30 a minute
MAX_TEAMS = int(os.environ.get("MAX_TEAMS", "1500"))

def get(endpoint, query):
    url = f"{BASE}{endpoint}.php?{query}"
    for attempt in range(3):
        time.sleep(PAUSE)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LakayTVDirect-data/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8")
                if not body.startswith("{"):
                    raise ValueError("not JSON")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(65)
                continue
            if e.code == 404:
                return None
            time.sleep(5)
        except Exception:
            time.sleep(5)
    return None

def save(endpoint, ident, data):
    if data is None:
        return False
    folder = os.path.join(OUT, endpoint)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{ident}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    return True

def teams_of(data):
    out = set()
    for e in (data or {}).get("events") or []:
        for k in ("idHomeTeam", "idAwayTeam"):
            v = e.get(k)
            if v and str(v).isdigit():
                out.add(str(v))
    return out

# Whole seasons, round by round (the free key answers a season list with 15 games only, a round in full): the leagues
# ESPN no longer carries (CFL) or never did (CEBL). The app builds their calendar, scores and tables from them.
EVENT_FIELDS = ("idEvent", "strTimestamp", "dateEvent", "strTime", "intRound", "idHomeTeam", "idAwayTeam", "strHomeTeam",
                "strAwayTeam", "intHomeScore", "intAwayScore", "strStatus", "strPostponed", "strVenue", "strHomeTeamBadge",
                "strAwayTeamBadge", "strEvent")
TEAM_FIELDS = ("idTeam", "strTeam", "strTeamShort", "strBadge", "strColour1", "strLocation", "strStadium")
PLAYOFF_ROUNDS = (125, 150, 160, 170, 180, 200)
MAX_ROUND = 30

def slim(rows, fields):
    return [{k: r.get(k) for k in fields if r.get(k) not in (None, "")} for r in rows or []]

def season_events(lid, season):
    """Every round 0..MAX_ROUND (round 0 holds unnumbered games) and the playoff rounds: about 37 requests a league."""
    events = {}
    for r in list(range(0, MAX_ROUND + 1)) + list(PLAYOFF_ROUNDS):
        for e in (get("eventsround", f"id={lid}&r={r}&s={season}") or {}).get("events") or []:
            events[e.get("idEvent")] = e
    return sorted(events.values(), key=lambda e: e.get("strTimestamp") or e.get("dateEvent") or "")

def copy_season(lid):
    info = (get("lookupleague", f"id={lid}") or {}).get("leagues") or []
    if not info:
        return False
    league = info[0]
    current = league.get("strCurrentSeason") or str(datetime.date.today().year)
    seasons = [current]
    if current.isdigit():
        seasons.append(str(int(current) - 1))  # the new season not begun yet: the last one
    for season in seasons:
        events = season_events(lid, season)
        if events:
            break
    teams = (get("search_all_teams", "l=" + urllib.parse.quote(league.get("strLeague") or "")) or {}).get("teams") or []
    teams = [t for t in teams if str(t.get("idLeague")) == str(lid) or not t.get("idLeague")]
    return save("season", lid, {"season": season, "league": league.get("strLeague"), "badge": league.get("strBadge"),
                                "events": slim(events, EVENT_FIELDS), "teams": slim(teams, TEAM_FIELDS)})

def read_index():
    try:
        with open(os.path.join(OUT, "index.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_index(index):
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

def copy_seasons():
    here = os.path.dirname(__file__)
    ids = [l.strip() for l in open(os.path.join(here, "..", "seasons.txt")) if l.strip() and not l.startswith("#")]
    return [lid for lid in ids if copy_season(lid)]

def main():
    if "--seasons-only" in sys.argv:
        index = read_index()
        index["seasons"] = copy_seasons()
        index["generated_seasons"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        if "season" not in index.setdefault("endpoints", []):
            index["endpoints"].append("season")
        write_index(index)
        print(f"{len(index['seasons'])} seasons")
        return
    here = os.path.dirname(__file__)
    leagues = [l.strip() for l in open(os.path.join(here, "..", "leagues.txt")) if l.strip() and not l.startswith("#")]
    teams, done_leagues = set(), []
    for lid in leagues:
        nxt = get("eventsnextleague", f"id={lid}")
        past = get("eventspastleague", f"id={lid}")
        info = get("lookupleague", f"id={lid}")
        if save("eventsnextleague", lid, nxt) | save("eventspastleague", lid, past) | save("lookupleague", lid, info):
            done_leagues.append(lid)
        teams |= teams_of(nxt) | teams_of(past)
    done_teams = []
    for tid in sorted(teams)[:MAX_TEAMS]:
        a = save("eventsnext", tid, get("eventsnext", f"id={tid}"))
        b = save("eventslast", tid, get("eventslast", f"id={tid}"))
        if a or b:
            done_teams.append(tid)
    done_seasons = copy_seasons()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    index = {
        "generated": now,
        "generated_seasons": now,
        "source": "TheSportsDB (https://www.thesportsdb.com)",
        "endpoints": ["eventsnextleague", "eventspastleague", "lookupleague", "eventsnext", "eventslast", "season"],
        "leagues": done_leagues,
        "teams": done_teams,
        "seasons": done_seasons,
    }
    write_index(index)
    print(f"{len(done_leagues)} leagues, {len(done_teams)} teams, {len(done_seasons)} seasons")

if __name__ == "__main__":
    main()
