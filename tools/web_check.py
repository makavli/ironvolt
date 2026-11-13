"""Plays the browser build in headless Chrome and checks it: serves build/web-src/build/web, waits, presses Enter to
start a game, saves screenshots to shots/web_*.png, and fails on a Python traceback in the page's console.

    python tools/web_check.py [seconds]        (after bash tools/web_build.sh; needs Chrome and websocket-client)
"""
import base64, functools, http.server, json, os, shutil, socketserver, subprocess, sys, tempfile, threading, time
import urllib.request

import websocket  # websocket-client

ROOT = os.path.join(os.path.dirname(__file__), "..")
WEB = os.path.join(ROOT, "build", "web-src", "build", "web")
SHOTS = os.path.join(ROOT, "shots")
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 40


def chrome():
    for p in (os.environ.get("CHROME", ""), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", shutil.which("google-chrome") or "",
              shutil.which("chromium") or "", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if p and os.path.exists(p):
            return p
    sys.exit("no Chrome found: set CHROME")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main():
    if not os.path.exists(os.path.join(WEB, "index.html")):
        sys.exit("no build: run bash tools/web_build.sh first")
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=WEB))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    profile = tempfile.mkdtemp()
    proc = subprocess.Popen([chrome(), "--headless=new", "--remote-debugging-port=9333", "--user-data-dir=" + profile,
                             "--autoplay-policy=no-user-gesture-required", "--window-size=1000,720",
                             "--no-first-run", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lines, n = [], [0]
    try:
        for _ in range(50):
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9333/json"))
                break
            except OSError:
                time.sleep(0.2)
        ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"])

        def call(method, **params):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": method, "params": params}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == n[0]:
                    return m.get("result", {})
                note(m)

        def note(m):
            if m.get("method") == "Runtime.consoleAPICalled":
                lines.append(" ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"]))
            elif m.get("method") == "Runtime.exceptionThrown":
                lines.append("EXCEPTION " + m["params"]["exceptionDetails"].get("text", ""))

        def pump(seconds):
            end = time.time() + seconds
            ws.settimeout(0.2)
            while time.time() < end:
                try:
                    note(json.loads(ws.recv()))
                except websocket.WebSocketTimeoutException:
                    pass
            ws.settimeout(None)

        def shot(name):
            data = call("Page.captureScreenshot", format="png")["data"]
            os.makedirs(SHOTS, exist_ok=True)
            with open(os.path.join(SHOTS, name), "wb") as f:
                f.write(base64.b64decode(data))

        def key(code, vk, text=""):
            for t in ("keyDown", "keyUp"):
                call("Input.dispatchKeyEvent", type=t, key=code, code=code, windowsVirtualKeyCode=vk, text=text if t == "keyDown" else "")

        call("Runtime.enable")
        call("Page.enable")
        call("Page.navigate", url="http://127.0.0.1:%d/%s" % (port, os.environ.get("WEB_HASH", "")))
        pump(WAIT)
        shot("web_title.png")
        call("Input.dispatchMouseEvent", type="mousePressed", x=500, y=360, button="left", clickCount=1)
        call("Input.dispatchMouseEvent", type="mouseReleased", x=500, y=360, button="left", clickCount=1)
        key("Enter", 13, "\r")
        pump(6)
        shot("web_play.png")
    finally:
        proc.terminate()
        srv.shutdown()
    text = "\n".join(lines)
    bad = [l for l in lines if "Traceback" in l or "Error" in l.split(":")[0] or l.startswith("EXCEPTION")]
    print("\n".join(lines[-25:]))
    print("screenshots: shots/web_title.png shots/web_play.png")
    if bad or "Traceback" in text:
        print("FAIL:", *bad[:5], sep="\n  ")
        sys.exit(1)
    print("web check passed")


if __name__ == "__main__":
    main()
