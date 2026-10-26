"""Back up existing games and add researched catalogue entries without overwrites."""
import json
from datetime import datetime
from app import ROOT, connect, default_json, fetch_games
ROWS = json.loads("[[\"Запретный остров\",\"Forbidden Island\",2,4,30,3,\"Кооперативная\",\"Приключение; командная работа\",\"Соберите четыре сокровища и покиньте остров до того, как он уйдёт под воду. Каждый участник помогает общей экспедиции.\",\"Forbidden-Island\"],[\"Запретная пустыня\",\"Forbidden Desert\",2,5,45,4,\"Кооперативная\",\"Приключение; выживание\",\"Исследуйте занесённый песком город, найдите части летательного аппарата и спаситесь вместе, пока не закончилась вода.\",\"Forbidden-Desert\"],[\"Суши Go!\",\"Sushi Go!\",2,5,15,2,\"Соревновательная\",\"Семейная; сбор наборов\",\"Выбирайте карту из руки и передавайте остальные соседу. Собирайте сочетания блюд, чтобы набрать больше очков.\",\"Sushi-Go\"],[\"Долой артишоки!\",\"Abandon All Artichokes\",2,4,20,3,\"Соревновательная\",\"Карточная; построение колоды\",\"Используйте способности овощей, чтобы избавиться от артишоков в своей колоде. Небольшая карточная игра о продуманных комбинациях.\",\"Abandon-All-Artichokes\"],[\"Спящие королевы\",\"Sleeping Queens\",2,5,20,2,\"Соревновательная\",\"Семейная; сказочная\",\"Разыгрывайте королей, рыцарей и волшебные карты, чтобы разбудить и собрать королев. Соперники могут вмешаться в ваши планы.\",\"Sleeping-Queens\"],[\"Квикс\",\"Qwixx\",2,5,15,2,\"Соревновательная\",\"Кубики; семейная\",\"Отмечайте числа в цветных рядах по результатам бросков. В каждом ходе участвуют все, а порядок отметок требует внимания.\",\"Qwixx\"],[\"Драконий лес\",\"Dragonwood\",2,4,20,3,\"Соревновательная\",\"Фэнтези; кубики; приключение\",\"Собирайте комбинации карт, получайте кубики и отправляйтесь против лесных чудовищ. Выбирайте между подготовкой и рискованной атакой.\",\"Dragonwood\"],[\"Спящие королевы 2\",\"Sleeping Queens 2\",2,5,20,3,\"Соревновательная\",\"Семейная; сказочная\",\"Королевы отправляются спасать королей. Ищите помощников и справляйтесь с волшебными препятствиями в новой самостоятельной игре.\",\"Sleeping-Queens-2\"],[\"Мусорные панды\",\"Trash Pandas\",2,4,20,2,\"Соревновательная\",\"Кубики; риск; весёлая\",\"Еноты собирают находки и прячут запасы. Бросайте кубик ради дополнительных действий, но вовремя остановитесь, чтобы не потерять ход.\",\"Trash-Pandas\"],[\"Королевство драконов\",\"Dragonrealm\",2,4,30,4,\"Соревновательная\",\"Фэнтези; контроль территорий\",\"Собирайте карты, исследуйте земли бросками кубиков и размещайте искателей приключений. Большинство в локации приносит сокровища.\",\"dragonrealm\"],[\"Дедакто\",\"Deduckto\",2,4,15,2,\"Соревновательная\",\"Дедукция; семейная\",\"Используйте подсказки, чтобы определить животное, маскировку и место на своей скрытой карте. Победит самый быстрый сыщик.\",\"deduckto\"],[\"Твин Ит!\",\"Twin It!\",2,6,10,1,\"Соревновательная\",\"Реакция; внимание; для компании\",\"Ищите одинаковые узоры среди открытых карт и успевайте забрать совпадение раньше других. Простая разминка для внимания.\",\"twin-it\"]]")
def main():
    connection = connect()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM games ORDER BY id")
        before = cursor.fetchall()
        cursor.execute("SHOW CREATE TABLE games")
        schema = list(cursor.fetchone().values())[1]
        folder = ROOT / "backups"
        folder.mkdir(exist_ok=True)
        backup = folder / ("games-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
        backup.write_text(json.dumps({"schema": schema, "games": before},ensure_ascii=False,indent=2,default=default_json),encoding="utf-8")
        added = 0
        for title, original, low, high, minutes, difficulty, cooperation, mood, description, slug in ROWS:
            cursor.execute("SELECT id FROM games WHERE game_title=%s OR original_title=%s",(title,original))
            if cursor.fetchone():
                continue
            cursor.execute("INSERT INTO games (game_title,original_title,min_players,max_players,min_play_time,max_play_time,complexity_of_game,level_of_cooperation,impression,description,source_urls,available_now) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)",(title,original,low,high,minutes,minutes,difficulty,cooperation,mood,description,"https://gamewright.com/product/"+slug))
            added += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    (ROOT/"data").mkdir(exist_ok=True)
    catalogue=fetch_games()
    (ROOT/"data"/"catalogue.json").write_text(json.dumps(catalogue,ensure_ascii=False,indent=2,default=default_json),encoding="utf-8")
    print(f"Added: {added}; total: {len(catalogue)}; backup: {backup.name}")
if __name__=="__main__":
    main()

