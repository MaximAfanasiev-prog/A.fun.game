"""Fetch box art from a public catalogue; preserve provenance for each image."""
import json,re,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from app import ROOT,fetch_games
games=fetch_games()
by_id={}
by_name={}
for game in games:
    match=re.search(r"boardgamegeek.com/boardgame/(\d+)",game.get("source_urls") or "")
    if match: by_id[match[1]]=game
    by_name[(game.get("original_title") or "").casefold()]=game
found={int(g["id"]):(g,"",bgg_id) for bgg_id,g in by_id.items()}
extra={"Abandon All Artichokes":"302260","Deduckto":"380887","Dragonrealm":"272993","Sleeping Queens 2":"358050","Trash Pandas":"216439","Twin It!":"222887","Dragonwood":"172933","Forbidden Island":"65244","Forbidden Desert":"136063","Qwixx":"131260","Sushi Go!":"133473","Jackal":"42702","Sleeping Queens":"17053"}
for name,bgg_id in extra.items():
    game=by_name.get(name.casefold())
    if game:found[game["id"]]=(game,"",bgg_id)
print("Matched",len(found),"of",len(games),flush=True)
folder=ROOT/"web"/"images";folder.mkdir(exist_ok=True)
manifest_path=ROOT/"data"/"images.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
def download(item):
    game,url,bgg_id=item
    if str(game["id"]) in manifest:return game["id"],manifest[str(game["id"])]
    try:
        with urllib.request.urlopen("https://api.geekdo.com/api/geekitems?objectid="+str(bgg_id)+"&objecttype=thing",timeout=20) as response:
            item=json.load(response)["item"]
        url=item.get("imageurl@2x") or item["imageurl"]
        request=urllib.request.Request(url,headers={"User-Agent":"a_fun_game local catalogue"})
        with urllib.request.urlopen(request,timeout=20) as response:
            data=response.read(5_000_001)
        if len(data)>5_000_000: raise ValueError("image too large")
        if data.startswith(b"\xff\xd8\xff"):ext="jpg"
        elif data.startswith(b"\x89PNG"):ext="png"
        elif data[:4]==b"RIFF" and data[8:12]==b"WEBP":ext="webp"
        else:raise ValueError("not a supported image")
        name=str(game["id"])+"."+ext
        (folder/name).write_bytes(data)
        return game["id"],{"image_url":"/images/"+name,"image_source":"https://boardgamegeek.com/boardgame/"+bgg_id,"image_original":url}
    except Exception as error:
        print("Image unavailable:",game["id"],str(error),flush=True)
        return game["id"],None
with ThreadPoolExecutor(max_workers=3) as pool:
    for task in as_completed([pool.submit(download,item) for item in found.values()]):
        game_id,record=task.result()
        if record:manifest[str(game_id)]=record
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("Saved",len(manifest),"local covers",flush=True)

