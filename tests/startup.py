"""Exercise the first turn at normal speed on a constrained connection."""
import json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Thread
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect
from tablet import Assets

class RangeAssets(Assets):
    def send_head(self):
        self.path = urlsplit(self.path).path
        return super().send_head()

web, media = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
label = sys.argv[3]
inject = len(sys.argv) > 4
with TemporaryDirectory() as scratch:
    root = Path(scratch) / "site"
    shutil.copytree(web, root)
    for ep in (root / "episodes").iterdir():
        (ep / "film.mp4").symlink_to(media / ep.name / "film.mp4")
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(RangeAssets, directory=root))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
        page = browser.new_page(is_mobile=True, has_touch=True, viewport={"width": 1280, "height": 800})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        cdp = page.context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False, "latency": 125, "downloadThroughput": 143360, "uploadThroughput": 100000,
            "connectionType": "cellular3g"
        })
        url = base + "episodes/rainbow/index.html"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_function('typeof turns !== "undefined"')
        page.evaluate("""() => {
          window.log = [];
          const video = document.querySelector("video");
          for (const event of ["waiting","playing","pause","seeking","seeked","error"]) {
            video.addEventListener(event, () => log.push({event,t:video.currentTime,ms:Math.round(performance.now())}));
          }
        }""")
        if inject:
            # Return a real failed media response, then allow the replacement request.
            def fail_first(request):
                if "reconnect=" not in request.request.url:
                    request.fulfill(status=503, body="temporary failure")
                else:
                    request.continue_()
            page.route("**/film.mp4*", fail_first)
            page.evaluate("film.load()")
            expect(page.locator("#start")).to_have_text("다시 재생")
        page.locator("#start").click(timeout=20000)
        expect(page.locator("#next")).to_be_visible(timeout=32000)
        assert page.evaluate("film.paused && Math.abs(film.currentTime - turns[0][0]) < .09")
        events = page.evaluate("log")
        waits = [e for e in events if e["event"] == "waiting" and .4 < e["t"] < 7.4]
        print(label, json.dumps(events), "early stalls", len(waits), flush=True)
        if label == "before":
            assert waits, "baseline did not buffer before first turn"
        else:
            if inject:
                # Outage recovery is checked separately from uninterrupted startup.
                assert any(e["event"] == "error" for e in events)
                for i, event in enumerate(events):
                    if event not in waits:
                        continue
                    resumed = next(e for e in events[i+1:] if e["event"] == "playing")
                    assert resumed["ms"] - event["ms"] < 1000
            else:
                assert not waits, "revised playback stalled before first turn"
            expect(page.locator("#status")).to_contain_text("윤수 차례 1/12")
            page.wait_for_timeout(4300)
            assert page.evaluate("film.paused && Math.abs(film.currentTime - turns[0][0]) < .09")
            page.locator("#next").click()
            page.wait_for_function("film.currentTime >= 13.0 && !film.paused",timeout=16000)
            if inject:
                assert page.evaluate("film.currentSrc.includes('reconnect=')")
            assert not errors,errors
        browser.close()
    server.shutdown()
