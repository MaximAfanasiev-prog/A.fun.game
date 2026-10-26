"""Browser smoke test; creates and removes only its own unique test record."""
import sys, uuid, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/".tools"))
from playwright.sync_api import sync_playwright, expect
from app import connect
ROOT=Path(__file__).parent
(ROOT/"artifacts").mkdir(exist_ok=True)
title="QA-"+uuid.uuid4().hex
created_id=None
errors=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1100},device_scale_factor=1)
        page.on("pageerror",lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8000",wait_until="networkidle")
        expect(page.locator("#connection")).to_contain_text("База подключена")
        expect(page.locator(".game")).to_have_count(12)
        expect(page).to_have_title("a_fun_game — настольный клуб")
        page.locator("#rules").select_option("5")
        assert page.evaluate("shown.length > 0 && shown.every(g=>g.time_for_rules_min != null && g.time_for_rules_min <= 5)")
        page.locator("#reset").click()
        assert page.locator("#rules").input_value()==""

        page.locator('[data-preset="quick"]').click()
        page.locator("#players").select_option("4")
        assert page.evaluate("shown.every(g=>g.max_play_time<=30&&g.min_players<=4&&g.max_players>=4)")
        assert page.locator(".game").count()>0
        page.locator(".game h3 button").first.click()
        expect(page.locator("#detail")).to_be_visible()
        page.keyboard.press("Escape")
        page.locator(".favorite").first.click()
        page.locator("#favorites-only").check()
        expect(page.locator(".game")).to_have_count(1)
        page.locator("#reset").click()
        page.locator("#search").fill("несуществующаяигра123456")
        expect(page.locator("#empty")).to_be_visible()
        page.locator("#empty-reset").click()
        page.locator("#search").fill("Запретный остров")
        expect(page.locator(".game")).to_have_count(1)
        page.locator("#reset").click()
        page.locator("#more").click()
        expect(page.locator(".game")).to_have_count(24)
        page.locator('[data-preset="coop"]').click()
        assert page.evaluate("shown.length > 0 && shown.every(g=>!g.level_of_cooperation.toLowerCase().includes('соревн'))")
        page.locator("#reset").click()
        page.locator("#random").click()
        expect(page.locator("#detail")).to_be_visible()
        page.keyboard.press("Escape")
        page.locator("#add-open").click()
        page.locator('[name="game_title"]').fill(title)
        page.locator('textarea[name="description"]').fill("Temporary browser verification record")
        page.locator('[name="time_for_rules_min"]').fill("7")
        with page.expect_response(lambda r:r.url.endswith("/api/games") and r.request.method=="POST") as response:
            page.locator('#add-form button[type="submit"]').click()
        result=response.value
        assert result.status==201,result.text()
        created_id=result.json()["id"]
        expect(page.locator("#add-dialog")).not_to_be_visible()
        expect(page.locator("#toast")).to_be_visible()
        page.locator("#add-open").click()
        page.locator('[name="game_title"]').fill(title)
        with page.expect_response(lambda r:r.url.endswith("/api/games") and r.request.method=="POST") as response:
            page.locator('#add-form button[type="submit"]').click()
        assert response.value.status==409
        expect(page.locator("#add-error")).to_contain_text("уже есть")
        page.keyboard.press("Escape")
        connection=connect()
        try:
            cursor=connection.cursor()
            cursor.execute("SELECT game_title,time_for_rules_min FROM games WHERE id=%s",(created_id,))
            assert cursor.fetchone()==(title,7)
            cursor.execute("DELETE FROM games WHERE id=%s AND game_title=%s",(created_id,title))
            connection.commit()
            created_id=None
        finally:
            connection.close()
        page.reload(wait_until="networkidle")
        page.locator("#reset").click()
        page.screenshot(path=str(ROOT/"artifacts"/"desktop.png"),full_page=True)
        page.set_viewport_size({"width":390,"height":844})
        page.screenshot(path=str(ROOT/"artifacts"/"mobile.png"),full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),"Horizontal overflow"
        page.locator('[data-preset="duo"]').click()
        assert page.evaluate("shown.every(g=>g.min_players<=2&&g.max_players>=2)")
        assert not errors,errors
        browser.close()
    print("PASS: load, filters, search, details, favorites, empty state, pagination, random, MySQL insert, duplicate rejection, mobile layout; no JS errors")
finally:
    if created_id is not None:
        connection=connect()
        try:
            cursor=connection.cursor()
            cursor.execute("DELETE FROM games WHERE id=%s AND game_title=%s",(created_id,title))
            connection.commit()
        finally:
            connection.close()



