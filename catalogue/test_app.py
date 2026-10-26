import unittest
from unittest.mock import patch
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
if __name__=="__main__":
    unittest.main()

