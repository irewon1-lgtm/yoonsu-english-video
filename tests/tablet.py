"""Browser check of the bundled HTML and the Android bridge boundary."""
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import shutil
import sys

from playwright.sync_api import sync_playwright, expect

WEB = Path(__file__).resolve().parents[1] / "web"
MEDIA = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()

class Assets(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_head(self):
        range_header = self.headers.get("Range")
        if not range_header or not self.path.endswith(".mp4"):
            return super().send_head()
        path = Path(self.translate_path(self.path))
        size = path.stat().st_size
        first, bound = range_header.removeprefix("bytes=").split("-", 1)
        start = int(first)
        end = min(size - 1, int(bound) if bound else size - 1)
        self.send_response(206)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        stream = path.open("rb")
        stream.seek(start)
        self.remaining = end - start + 1
        return stream

    def copyfile(self, source, sink):
        if not hasattr(self, "remaining"):
            return super().copyfile(source, sink)
        while self.remaining:
            data = source.read(min(self.remaining, 65536))
            if not data:
                break
            try:
                sink.write(data)
            except (ConnectionResetError, BrokenPipeError):
                break
            self.remaining -= len(data)

def columns(deck):
    return deck.evaluate("(e) => getComputedStyle(e).gridTemplateColumns.split(' ').length")

def check():
    with TemporaryDirectory() as scratch:
        root = Path(scratch) / "site"
        shutil.copytree(WEB, root)
        for ep in (root / "episodes").iterdir():
            for name in ("cover.jpg", "film.mp4"):
                (ep / name).symlink_to(MEDIA / ep.name / name)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Assets, directory=root))
        Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}/"
        OUT.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
                                         args=["--autoplay-policy=document-user-activation-required"])
            page = browser.new_page(is_mobile=True, has_touch=True, viewport={"width": 1280, "height": 800})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script('''
                let denyOnce = true;
                const send = window.testMicEvent = (type, token = 0) =>
                    document.dispatchEvent(new CustomEvent("native-mic", {detail:{type,token}}));
                window.NativeMic = {
                    authorize() { setTimeout(() => {
                      send(denyOnce ? "permission-denied" : "permission-granted");
                      denyOnce = false;
                    },25); },
                    listen(level, token) { window.listening = {level,token}; },
                    stop() { window.listening = null; }
                };
            ''')
            page.goto(base)
            expect(page.locator(".card")).to_have_count(6)
            expect(page.locator(".empty")).to_have_count(2)
            deck = page.locator(".sheet")
            assert columns(deck) == 3
            assert page.locator(".album").bounding_box()["width"] >= 1210
            page.screenshot(path=OUT / "tab-album-landscape.png")
            page.set_viewport_size({"width": 800, "height": 1280})
            assert columns(deck) == 2
            assert page.locator(".album").bounding_box()["width"] == 800
            page.screenshot(path=OUT / "tab-album-portrait.png")
            page.set_viewport_size({"width": 1280, "height": 800})
            print("PASS Galaxy Tab layout at 1280x800 and 800x1280", flush=True)

            episodes = (("rainbow", 12), ("sandwich", 12), ("bubbles", 12), ("red-ball", 6))
            test_episode = os.environ.get("ALBUM_TEST_EPISODE")
            exercise_mic = test_episode or "rainbow"
            for slug, count in episodes:
                if test_episode and slug != test_episode:
                    continue
                page.locator(f'a[href*="/{slug}/"]').click()
                page.wait_for_function('film.videoWidth===1920 && film.videoHeight===1080')
                assert page.locator("video").bounding_box() == {"x": 0, "y": 0, "width": 1280, "height": 800}
                assert page.locator("video").evaluate("(e)=>getComputedStyle(e).objectFit") == "cover"
                page.locator("#start").click()
                page.locator("video").evaluate("(v)=>v.playbackRate=8")
                gates = page.evaluate("turns")
                assert len(gates) == count
                for i, (start, end, phrase) in enumerate(gates):
                    expect(page.locator("#next")).to_be_visible(timeout=11000)
                    expect(page.locator("#phrase")).to_have_text(phrase)
                    page.wait_for_function(f"film.paused && !film.seeking && Math.abs(film.currentTime-{start})<.08")
                    if i == 0:
                        page.screenshot(path=OUT / f"{slug}-landscape.png")
                        page.wait_for_timeout(4200)
                        assert abs(page.evaluate("film.currentTime") - start) < .08
                    if i == 0 and slug == exercise_mic:
                        page.locator("#mic").click()
                        expect(page.locator("#mic-note")).to_contain_text("앱의 마이크 권한")
                        page.locator("#mic").click()
                        page.wait_for_function("window.listening?.level === 8")
                        page.evaluate('testMicEvent("onset",listening.token); testMicEvent("end",listening.token)')
                        expect(page.locator("#next")).to_be_hidden()
                        page.wait_for_function(f"film.currentTime >= {end}-.05")
                        page.locator("#mic").click()
                    else:
                        page.locator("#next").click()
                expect(page.locator("#status")).to_contain_text("마쳤어요", timeout=8000)
                page.locator(".home").click()
                expect(page.locator(".card")).to_have_count(6)
                print(f"PASS {slug}: 1080p, full landscape, {count} stops", flush=True)

            assert not errors, errors
            browser.close()
        server.shutdown()

if __name__ == "__main__":
    check()
