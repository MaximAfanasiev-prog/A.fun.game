"""Refresh the local snapshot from MySQL, including related genres and mechanics.

Only SELECT/SHOW queries are executed; no database records are modified.
"""
import json
from app import ROOT, default_json, fetch_games


def main():
    games = fetch_games()
    if not games:
        raise RuntimeError("Refusing to replace the catalogue with an empty snapshot.")
    destination = ROOT / "data" / "catalogue.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(games, ensure_ascii=False, indent=2, default=default_json), encoding="utf-8")
    print(f"Exported {len(games)} games; genres: {sum(bool(g.get('genres')) for g in games)}; mechanics: {sum(bool(g.get('mechanics')) for g in games)}")


if __name__ == "__main__":
    main()
