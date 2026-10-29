"""Local board-game catalogue. Run: python app.py"""
from pathlib import Path
import ast
import json
import os
import sys
import decimal
import datetime
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))

def default_json(value):
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)

def connect():
    import mysql.connector
    # Read only the literal connection settings from the existing project.
    settings_file = ROOT / "note-book.py"
    raw = settings_file.read_bytes() if settings_file.exists() else b""
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        source = raw.decode("cp1251")
    settings = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "connect":
            settings = {k.arg: ast.literal_eval(k.value) for k in node.keywords}
            break
    for key in ("host", "user", "password", "database"):
        if os.getenv("MYSQL_" + key.upper()) is not None:
            settings[key] = os.environ["MYSQL_" + key.upper()]
    settings["connection_timeout"] = 5
    return mysql.connector.connect(**settings)

def fetch_games():
    connection = connect()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM games ORDER BY game_title")
        games = cursor.fetchall()
        # Normalized genres/mechanics live outside games in the current schema.
        # Older installations may still have only the original text columns.
        cursor.execute("SHOW TABLES")
        tables = {next(iter(row.values())) for row in cursor.fetchall()}
        by_id = {game["id"]: game for game in games}
        for game in games:
            for key, field in (("genres", "genre"), ("mechanics", "mechanics")):
                value = game.get(field)
                game[key] = [item.strip() for item in value.split(";") if item.strip()] if isinstance(value, str) else list(value or [])
        relations = (
            ("genres", "game_genres", "genres", "SELECT gg.game_id, gr.genre AS value FROM game_genres gg JOIN genres gr ON gr.id=gg.genre_id ORDER BY gg.game_id, gr.genre"),
            ("mechanics", "game_mechanics", "mechanics", "SELECT gm.game_id, m.mechanic AS value FROM game_mechanics gm JOIN mechanics m ON m.id=gm.mechanic_id ORDER BY gm.game_id, m.mechanic"),
        )
        for key, links, lookup, query in relations:
            if {links, lookup} <= tables:
                cursor.execute(query)
                values = {}
                for row in cursor.fetchall():
                    if row["game_id"] in by_id and row["value"]:
                        values.setdefault(row["game_id"], []).append(row["value"])
                for game_id, items in values.items():
                    by_id[game_id][key] = sorted(set(items))
        return games
    finally:
        connection.close()

def validate_game(data):
    title = str(data.get("game_title", "")).strip()
    if not title or len(title) > 255:
        raise ValueError("Название должно содержать от 1 до 255 символов.")
    def integer(key, low, high):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError("Проверьте числовые поля: " + key)
        return value
    low = integer("min_players", 1, 100)
    high = integer("max_players", 1, 100)
    minutes = integer("max_play_time", 1, 1440)
    difficulty = integer("complexity_of_game", 1, 9)
    if low > high:
        raise ValueError("Минимум игроков не может превышать максимум.")
    description = str(data.get("description", "")).strip()
    if len(description) > 5000:
        raise ValueError("Описание слишком длинное.")
    available = data.get("available_now")
    if available not in (None, 0, 1):
        raise ValueError("Некорректный статус наличия.")
    rules = data.get("time_for_rules_min")
    if rules is not None:
        rules = integer("time_for_rules_min", 0, 240)
    return (title, low, high, minutes, difficulty, description, available, rules)

def with_images(games):
    manifest = ROOT / "data" / "images.json"
    images = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    return [dict(g, **images.get(str(g["id"]), {})) for g in games]

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, mime="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, default=default_json).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/games":
            try:
                games = fetch_games()
                self.reply(200, {"games": with_images(games), "mode": "mysql"})
            except Exception:
                snapshot = ROOT / "data" / "catalogue.json"
                if snapshot.exists():
                    self.reply(200, {"games": with_images(json.loads(snapshot.read_text(encoding="utf-8"))), "mode": "snapshot"})
                else:
                    self.reply(503, {"error": "База недоступна. Запустите MySQL и обновите страницу."})
            return
        if re.fullmatch(r"/images/[0-9]+\.(jpg|png|webp)", path):
            image = ROOT / "web" / path.lstrip("/")
            if image.is_file():
                mime = {".jpg":"image/jpeg",".png":"image/png",".webp":"image/webp"}[image.suffix]
                self.reply(200, image.read_bytes(), mime)
            else:
                self.reply(404, {"error":"Image not found"})
            return
        static = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/recommender.js": ("recommender.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path in static:
            name, mime = static[path]
            self.reply(200, (ROOT / "web" / name).read_bytes(), mime)
        elif path == "/favicon.ico":
            self.reply(204, b"", "image/x-icon")
        else:
            self.reply(404, {"error": "Не найдено"})

    def do_POST(self):
        if self.path != "/api/games":
            self.reply(404, {"error": "Не найдено"})
            return
        expected = "http://" + self.headers.get("Host", "")
        if self.headers.get("Origin") != expected or self.headers.get("X-Catalogue-Request") != "1":
            self.reply(403, {"error": "Запрос разрешён только со страницы каталога."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 20000:
                raise ValueError("Недопустимый размер запроса.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Ожидается объект игры.")
            values = validate_game(data)
        except (ValueError, TypeError):
            self.reply(400, {"error": "Проверьте название, диапазон игроков, время и сложность (1–9)."})
            return
        connection = None
        try:
            connection = connect()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO games (game_title,min_players,max_players,max_play_time,complexity_of_game,description,available_now,time_for_rules_min) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", values)
            connection.commit()
            self.reply(201, {"id": cursor.lastrowid})
        except Exception as error:
            if connection:
                connection.rollback()
            if getattr(error, "errno", None) == 1062:
                self.reply(409, {"error": "Игра с таким названием уже есть."})
            else:
                self.reply(503, {"error": "Не удалось сохранить игру. Проверьте подключение к MySQL."})
        finally:
            if connection:
                connection.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"a_fun_game: http://127.0.0.1:{port}", flush=True)
    if "--open" in sys.argv:
        import webbrowser, threading
        threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


