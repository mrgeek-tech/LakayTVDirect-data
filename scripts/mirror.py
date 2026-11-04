#!/usr/bin/env python3
"""
LakayTV Direct's copy of TheSportsDB data: the same answers the app asks TheSportsDB for, as files, so Sports Radar
reads them here first and stays within the free key's 30 requests a minute.

Data: TheSportsDB (https://www.thesportsdb.com) — its terms: "You can scrape, copy and modify content returned from
the API using the official end points" and "must mention us as the source of the data". Artwork is linked, never
copied. Run daily by .github/workflows/mirror.yml; the key is the free public one unless the SPORTSDB_KEY secret is set.
"""
import json, os, time, urllib.request, urllib.error, datetime

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

def main():
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
    index = {
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": "TheSportsDB (https://www.thesportsdb.com)",
        "endpoints": ["eventsnextleague", "eventspastleague", "lookupleague", "eventsnext", "eventslast"],
        "leagues": done_leagues,
        "teams": done_teams,
    }
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"{len(done_leagues)} leagues, {len(done_teams)} teams")

if __name__ == "__main__":
    main()
