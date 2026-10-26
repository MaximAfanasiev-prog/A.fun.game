import sys,json,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/".tools"))
from playwright.sync_api import sync_playwright
data=json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/games"))
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",headless=True)
    page=browser.new_page(viewport={"width":1440,"height":1000})
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.goto("http://127.0.0.1:8000",wait_until="networkidle")
    results=page.evaluate("""async (games) => await Promise.all(games.map(g => new Promise(resolve => {
      const image=new Image();
      image.onload=()=>resolve({id:g.id,ok:image.naturalWidth>0});
      image.onerror=()=>resolve({id:g.id,ok:false});
      image.src=g.image_url;
    })))""",data["games"])
    assert all(r["ok"] for r in results),results
    page.locator("#rules").select_option("5")
    assert page.evaluate("shown.length>0 && shown.every(g=>g.time_for_rules_min!=null && g.time_for_rules_min<=5)")
    page.locator("#reset").click()
    page.screenshot(path="artifacts/desktop.png",full_page=True)
    page.set_viewport_size({"width":390,"height":844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path="artifacts/mobile.png",full_page=True)
    assert not errors,errors
    browser.close()
print("PASS: all",len(results),"local covers decode; rules filter; desktop/mobile; no JS errors")

