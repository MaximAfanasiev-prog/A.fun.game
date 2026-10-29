"""Read-only regression and browser checks, using the saved catalogue, never MySQL.

Run: python -B qa_recommendations.py
Requires Playwright (existing .tools is supported) and an installed Chrome.
"""
import functools
import json
from pathlib import Path
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".tools"))
from playwright.sync_api import sync_playwright, expect
import app
from build_public import build


def check_model(page):
    result = page.evaluate("""() => {
      const R = Recommender, check = (ok, msg) => {if (!ok) throw Error(msg);};
      check(games.length === 72, 'Snapshot should contain 72 games');
      check(games.filter(g=>R.profile(g).genres.length).length===60, 'Genre coverage must reflect MySQL, including its 12 missing values');
      const g = {id:999, game_title:'Fixture', original_title:'Pandemic', min_players:2,
        max_players:4, min_recommended_players:2, max_recommended_players:4,
        max_play_time:60, complexity_of_game:5, time_for_rules_min:null, available_now:0,
        genres:['Стратегическая'], mechanics:['Броски кубиков'], impression:'Напряжённая',
        level_of_cooperation:'Полная кооперация', rules_difficulty:5};
      const p = {players:1, genre:'стратегическая', format:'coop', minutes:30, difficulty:5,
        rules:5, rulesDifficulty:1, mood:'спокойная', mechanic:'драфт карт', available:true, favorites:true,
        search:'Fixture', weights:R.defaults()};
      const item=R.evaluate(g,p,new Set());
      check(item!==null, 'Too few players must NOT exclude a game');
      check(item.warnings.length===1, 'Too few players need a warning');
      const expected = 20*0.2 + 24 + 22 + 14*0.5 + 12 + 30;
      check(Math.abs(item.total-expected)<0.00001, 'Weighted contributions must sum: '+item.total);
      check(item.possible===170, 'All active weights must be counted');
      check(item.percent===Math.round(expected/170*100), 'Percentage must be normalized');
      check(item.parts.find(c=>c.key==='rules').unknown, 'Unknown rules time must be explicit');
      check(item.parts.find(c=>c.key==='rules').points===0, 'Unknown time must not get matching points');
      check(item.parts.find(c=>c.key==='rulesDifficulty').points===0, '5/5 rules should not match a 1/5 request');
      check(R.evaluate({...g,rules_difficulty:1},{rulesDifficulty:1}).percent===100, 'Rules difficulty comes directly from numeric field');
      check(R.evaluate({...g,rules_difficulty:null},{rulesDifficulty:1}).parts[0].unknown, 'Missing rules difficulty must be unknown');
      const separate=R.evaluate({...g,time_for_rules_min:0},{rules:5,rulesDifficulty:1});
      check(separate.parts.find(c=>c.key==='rules').points===8 && separate.parts.find(c=>c.key==='rulesDifficulty').points===0, 'Rules time and difficulty are independent');
      check(R.evaluate(g,{...p,players:5})===null, 'Exceeding max_players must exclude');
      check(R.evaluate(g,{...p,players:4})!==null, 'Maximum is inclusive');
      check(R.evaluate({...g,max_players:null},{players:8}).warnings.length>0, 'Unknown maximum must be retained with a warning');
      check(R.evaluate(g,{minutes:1,rules:1,rulesDifficulty:1,difficulty:9,genre:'вечериночная',format:'duel',available:true,favorites:true,search:'NO_MATCH'})!==null, 'Soft mismatches must never exclude');
      check(R.evaluate(g,{players:5,weights:{players:0}})===null, 'Zero weight must not disable player capacity');
      check(R.evaluate(g,{players:1,weights:{players:0}}).warnings.length===1, 'Zero weight must not suppress caveat');
      check(R.evaluate(g,{}).percent===null, 'No preferences means no invented percentage');
      check(R.evaluate(g,{genre:'стратегическая',weights:{genre:0}}).percent===null, 'Zero contribution means no percentage');
      check(R.evaluate({...g,genres:[]},{genre:'стратегическая'}).parts[0].unknown, 'Known titles must not invent missing genres');
      check(R.evaluate({...g,impression:null},{mood:'спокойная'}).parts[0].unknown, 'Known titles must not invent impressions');
      const changed={...g,genres:['Семейная'],impression:'Уютная',level_of_cooperation:'Командное противостояние'};
      check(R.profile(changed).genres[0]==='семейная' && R.profile(changed).moods[0]==='уютная' && R.profile(changed).format==='teams', 'Database fields must override game identity');
      check(R.evaluate({...g,original_title:'Never seen before'},{genre:'стратегическая'}).percent===100, 'Unseen titles with real metadata must work');
      check(R.profile({...g,genres:[],genre:'Стратегия; Экономика'}).genres.includes('экономика'), 'Original text genres remain supported');
      check(R.profile({...g,genre:'Wrong old label'}).genres.length===1, 'Normalized genres take priority');
      const fiction={...g,id:1000,genres:['Семейная'],level_of_cooperation:'Соревнование'};
      check(R.rank([g,fiction],{genre:'стратегическая',format:'competitive',weights:{genre:30,format:10}})[0].game.id===999, 'Genre priority should win');
      check(R.rank([g,fiction],{genre:'стратегическая',format:'competitive',weights:{genre:10,format:30}})[0].game.id===1000, 'Changing weights should change the winner');
      check(R.profile({...g,level_of_cooperation:'Полукооперация; скрытые роли'}).format==='semi', 'Semi-cooperation must not become full cooperation');
      check(R.profile({...g,level_of_cooperation:'Кооперативная'}).format==='coop', 'Alternate cooperation labels supported');
      check(R.profile({...g,level_of_cooperation:'Неизвестный формат'}).format===null, 'Unknown cooperation must not be guessed');
      check(R.evaluate({...g,game_title:'Ещё одна'},{search:'еще'}).percent===100, 'Search should normalize Cyrillic yo');
      check(R.evaluate({...g,time_for_rules_min:0},{rules:5}).percent===100, 'Zero-minute rules are known and match');
      check(R.evaluate({...g,available_now:null},{available:true}).parts[0].unknown, 'Unknown availability is explicit');
      R.configure([...games,{game_title:'New',genres:['Новый жанр'],mechanics:['Новая механика'],impression:'Новое впечатление'}]);
      check(R.genres['новый жанр'] && R.mechanics['новая механика'] && R.moods['новое впечатление'], 'New database choices appear without a title map');
      R.configure(games);
      const ranked=R.rank(games,{players:4,genre:'стратегическая',format:'coop',minutes:15,rules:5,rulesDifficulty:1,difficulty:1,available:true,favorites:true,search:'ZZ_NO_MATCH'});
      check(ranked.length===games.filter(g=>g.max_players==null||g.max_players>=4).length, 'Only player maximum may change candidate count');
      check(ranked.every((r,i)=>!i||ranked[i-1].total>=r.total), 'Scores must descend');
      check(ranked.every(r=>r.percent>=0&&r.percent<=100), 'Percentages must stay in bounds');
      return {catalogue:games.length, weightedFixture:item.total, candidates:ranked.length, genres:Object.keys(R.genres).length, impressions:Object.keys(R.moods).length, mechanics:Object.keys(R.mechanics).length};
    }""")
    print("PASS model:", result)



def check_browser(page):
    expect(page.locator(".game")).to_have_count(12)
    expect(page.locator("#add-open")).to_be_disabled()
    check_model(page)
    page.locator('[data-preset="coop"]').click()
    expect(page.locator(".game")).to_have_count(6)
    assert page.locator("#format").input_value() == "coop"
    assert page.evaluate("ranked[0].tags.format === 'coop'")
    page.locator("#best-pick [data-detail]").click()
    expect(page.locator("#detail")).to_be_visible()
    expect(page.locator(".score-breakdown")).to_be_visible()
    assert page.locator(".score-row").count() == 3
    page.keyboard.press("Escape")

    for preset in ("duo", "quick", "party", "easy", "strategy"):
        page.locator(f'[data-preset="{preset}"]').click()
        assert page.locator(f'[data-preset="{preset}"]').get_attribute("aria-pressed") == "true"
        assert page.evaluate("Object.entries(presets[preset]).every(([key,val])=>document.getElementById(key).value===val)")
        assert page.evaluate("ranked.every((r,i)=>!i||ranked[i-1].total>=r.total)")
    page.locator("#genre").select_option("детективная")
    assert page.locator('[data-preset][aria-pressed="true"]').count() == 0

    page.locator("#reset").click()
    page.locator("#players").select_option("4")
    before = page.evaluate("ranked.length")
    for selector, value in (("minutes", "15"), ("rules", "5"), ("rulesDifficulty", "1"), ("genre", "экономическая"), ("format", "coop"), ("mood", "социальная"), ("mechanic", "драфт карт")):
        page.locator("#" + selector).select_option(value)
        assert page.evaluate("ranked.length") == before
    page.locator("#available").check()
    page.locator("#favorites-only").check()
    page.locator("#difficulty").fill("9")
    assert page.evaluate("ranked.length") == before
    page.locator("#search").fill("ZZZ_nonexistent")
    assert page.evaluate("ranked.length") == before
    assert page.evaluate("shown.every(g=>g.max_players==null||g.max_players>=4)")

    page.locator("#reset").click()
    page.locator("#search").fill("ZZZ_nonexistent")
    expect(page.locator("#empty")).not_to_be_visible()
    expect(page.locator("#best-pick")).to_contain_text("Точных совпадений нет")
    assert page.evaluate("ranked.length===games.length")
    page.locator("#search").fill("Запретный остров")
    assert page.evaluate("ranked[0].game.game_title==='Запретный остров'")
    page.locator("#reset").click()
    page.locator(".favorite").first.click()
    page.locator("#favorites-only").check()
    assert page.evaluate("favorites.has(ranked[0].game.id)")
    assert page.evaluate("ranked.length===games.length")
    page.locator("#reset").click()
    page.locator("#players").select_option("1")
    assert page.evaluate("ranked.length===games.length")
    page.locator("#genre").select_option("вечериночная")
    assert page.locator(".match-warning").count() > 0

    for id_, choices in (("genre", "genres"), ("format", "formats"), ("mood", "moods"), ("mechanic", "mechanics")):
        assert page.evaluate(f"Object.keys(Recommender.{choices}).every(value=>Recommender.rank(games,{{{id_}:value}})[0].percent===100)")
        values = page.evaluate(f"Object.keys(Recommender.{choices})")
        for value in values if id_ == "format" else values[:3]:
            page.locator("#reset").click()
            page.locator("#"+id_).select_option(value)
            assert page.evaluate("ranked[0].percent===100"), (id_, value)
            assert page.evaluate("ranked.length===games.length")

    page.locator("#reset").click()
    page.locator("#genre").select_option("стратегическая")
    page.locator(".weight-settings summary").click()
    page.locator("#weight-genre").fill("0")
    assert page.evaluate("weights.genre===0 && ranked.every(r=>r.percent===null)")
    page.locator("#weights-reset").click()
    assert page.evaluate("weights.genre===24 && ranked[0].percent===100")
    page.locator("#reset").click()
    expect(page.locator("#genre")).to_have_value("")
    expect(page.locator("#difficulty")).to_have_value("0")
    assert page.locator("#weight-genre").input_value() == "24"
    page.locator(".weight-settings summary").click()
    page.locator("#more").click()
    expect(page.locator(".game")).to_have_count(18)

    page.locator('[data-preset="strategy"]').click()
    top_three = page.evaluate("ranked.slice(0,3).map(r=>r.game.game_title)")
    page.locator("#random").click()
    expect(page.locator("#detail")).to_be_visible()
    assert page.locator("#detail-title").inner_text() in top_three
    page.keyboard.press("Escape")
    for value in ("title", "time", "new", "match"):
        page.locator("#sort").select_option(value)
        assert page.evaluate("shown.length===games.length")
    page.locator(".cover").first.focus()
    page.keyboard.press("Enter")
    expect(page.locator("#detail")).to_be_visible()
    page.keyboard.press("Escape")

    # Selected criteria yield six recommendations, then optional alternatives.
    expect(page.locator(".game")).to_have_count(6)
    page.locator("#more").click()
    expect(page.locator(".game")).to_have_count(12)
    page.locator(".cover img").evaluate_all("images=>images.forEach(img=>img.loading='eager')")
    page.wait_for_function("[...document.images].every(img=>img.complete&&img.naturalWidth>0)")

    for width in (360, 390, 768, 1024, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), f"Overflow at {width}"
        assert page.evaluate("[...document.querySelectorAll('.workspace, .cards, .best-pick, aside')].every(e=>e.getBoundingClientRect().right<=innerWidth)"), f"Offscreen content at {width}"
    page.set_viewport_size({"width": 1440, "height": 1100})
    page.screenshot(path=str(ROOT/"artifacts"/"recommendations-desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(ROOT/"artifacts"/"recommendations-mobile.png"), full_page=True)
    print("PASS browser: presets, every genre/format/mood, weights, soft preferences, search, favorites, details, keyboard, random top 3, pagination, images, responsive layout")


def main():
    (ROOT/"artifacts").mkdir(exist_ok=True)
    build()
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    public = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (server, public)]
    errors = []
    with patch.object(app, "fetch_games", side_effect=RuntimeError("QA: use snapshot")):
        for t in threads:
            t.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
                page = browser.new_page(viewport={"width":1440,"height":1100}, reduced_motion="reduce")
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: errors.append(f"HTTP {response.status}: {response.url}") if response.status>=400 and not response.url.endswith("favicon.ico") else None)
                page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="networkidle")
                check_browser(page)
                # A subdirectory mirrors GitHub Pages relative asset handling.
                page.goto(f"http://127.0.0.1:{public.server_port}/dist/", wait_until="networkidle")
                expect(page.locator("#connection")).to_contain_text("Публичный каталог")
                expect(page.locator("#add-open")).not_to_be_visible()
                expect(page.locator(".game")).to_have_count(12)
                page.locator('[data-preset="coop"]').click()
                expect(page.locator(".game")).to_have_count(6)
                assert page.evaluate("ranked[0].tags.format==='coop'")
                page.locator(".cover img").evaluate_all("images=>images.forEach(img=>img.loading='eager')")
                page.wait_for_function("[...document.images].every(img=>img.complete&&img.naturalWidth>0)")
                print("PASS public build: subdirectory paths, recommender script, images, weighted recommendations")
                assert not errors, errors
                browser.close()
        finally:
            for s in (server, public):
                s.shutdown()
                s.server_close()
            for t in threads:
                t.join()


if __name__ == "__main__":
    main()
