"""Export the read-only catalogue for GitHub Pages, without MySQL credentials."""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def build():
    destination = ROOT / "dist"
    destination.mkdir(exist_ok=True)
    for name in ("index.html", "app.js", "style.css"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        if name == "index.html":
            text = text.replace('href="/', 'href="./').replace('src="/', 'src="./')
            text = text.replace('id="add-open"', 'id="add-open" hidden disabled')
        elif name == "app.js":
            text = text.replace('fetch("/api/games")', 'fetch("./catalogue.json")')
            text = text.replace('"◷ Резервная копия · только просмотр"', '"● Публичный каталог"')
        (destination / name).write_text(text, encoding="utf-8")
    shutil.copytree(ROOT / "web" / "images", destination / "images", dirs_exist_ok=True)
    games = json.loads((ROOT / "data" / "catalogue.json").read_text(encoding="utf-8"))
    images = json.loads((ROOT / "data" / "images.json").read_text(encoding="utf-8"))
    for game in games:
        game.update(images.get(str(game["id"]), {}))
        if game.get("image_url", "").startswith("/images/"):
            game["image_url"] = "." + game["image_url"]
        if game.get("image_url", "").startswith("./images/"):
            if not (destination / game["image_url"]).is_file():
                raise FileNotFoundError(game["image_url"])
    (destination / "catalogue.json").write_text(
        json.dumps({"games": games, "mode": "public"}, ensure_ascii=False), encoding="utf-8"
    )
    (destination / ".nojekyll").touch()
    print(f"Public catalogue: {len(games)} games -> {destination}")


if __name__ == "__main__":
    build()
