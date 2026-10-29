import unittest
from unittest.mock import MagicMock, patch
import tempfile
import pathlib
import threading
import urllib.request
import json
import app

class ValidationTests(unittest.TestCase):
    def valid(self):
        return dict(game_title="Игра",min_players=2,max_players=4,max_play_time=30,complexity_of_game=3,description="",available_now=None)
    def test_good(self):
        self.assertEqual(app.validate_game(self.valid())[0],"Игра")
    def test_invalid(self):
        for key,value in [("game_title"," "),("min_players",5),("max_players",0),("max_play_time",-1),("complexity_of_game",10),("min_players",2.5),("time_for_rules_min",-1),("time_for_rules_min",241),("time_for_rules_min",2.5)]:
            data=self.valid();data[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                app.validate_game(data)

class FallbackTests(unittest.TestCase):
    def test_snapshot_when_mysql_down(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            (root/"data").mkdir()
            (root/"data"/"catalogue.json").write_text('[{"id":1}]',encoding="utf-8")
            with patch.object(app,"ROOT",root),patch.object(app,"fetch_games",side_effect=RuntimeError("offline")):
                server=app.ThreadingHTTPServer(("127.0.0.1",0),app.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    data=json.load(urllib.request.urlopen("http://127.0.0.1:"+str(server.server_port)+"/api/games"))
                    self.assertEqual(data,{"games":[{"id":1}],"mode":"snapshot"})
                finally:
                    server.shutdown();server.server_close();thread.join()

class CatalogueDataTests(unittest.TestCase):
    def connection(self, results):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchall.side_effect = results
        return connection, cursor

    def test_normalized_genres_and_mechanics_are_loaded_by_game_id(self):
        connection, cursor = self.connection([
            [{"id": 17, "game_title": "Игра", "rules_difficulty": 4,
              "impression": "Спокойная; тактическая", "level_of_cooperation": "Полная кооперация"},
             {"id": 25, "game_title": "Без связей"}],
            [{"Tables_in_test": name} for name in ("games", "genres", "game_genres", "mechanics", "game_mechanics")],
            [{"game_id": 17, "value": "Семейная"}, {"game_id": 17, "value": "Стратегическая"}],
            [{"game_id": 17, "value": "Драфт карт"}],
        ])
        with patch.object(app, "connect", return_value=connection):
            games = app.fetch_games()
        self.assertEqual(games[0]["genres"], ["Семейная", "Стратегическая"])
        self.assertEqual(games[0]["mechanics"], ["Драфт карт"])
        self.assertEqual(games[0]["rules_difficulty"], 4)
        self.assertEqual(games[0]["impression"], "Спокойная; тактическая")
        self.assertEqual(games[0]["level_of_cooperation"], "Полная кооперация")
        self.assertEqual(games[1]["genres"], [])
        self.assertEqual(games[1]["mechanics"], [])
        self.assertTrue(all(call.args[0].startswith(("SELECT", "SHOW")) for call in cursor.execute.call_args_list))
        connection.close.assert_called_once()

    def test_original_text_columns_work_without_relation_tables(self):
        connection, _ = self.connection([
            [{"id": 1, "genre": "Стратегия; Экономика", "mechanics": "Торговля; Драфт карт"}],
            [{"Tables_in_test": "games"}],
        ])
        with patch.object(app, "connect", return_value=connection):
            game = app.fetch_games()[0]
        self.assertEqual(game["genres"], ["Стратегия", "Экономика"])
        self.assertEqual(game["mechanics"], ["Торговля", "Драфт карт"])

    def test_broken_relation_query_is_not_misreported_as_live_data(self):
        connection, cursor = self.connection([
            [{"id": 1}], [{"Tables_in_test": "genres"}, {"Tables_in_test": "game_genres"}],
        ])
        def execute(query):
            if "JOIN genres" in query:
                raise RuntimeError("relationship read failed")
        cursor.execute.side_effect = execute
        with patch.object(app, "connect", return_value=connection), self.assertRaises(RuntimeError):
            app.fetch_games()
        connection.close.assert_called_once()
if __name__=="__main__":
    unittest.main()

