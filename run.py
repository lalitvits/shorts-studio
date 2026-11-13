"""Start Shorts Studio:  python run.py   (then open http://localhost:8000)"""
import argparse
import threading
import webbrowser

from studio.server import serve

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to reach it from your phone on the same Wi-Fi")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    httpd = serve(a.host, a.port)
    url = f"http://localhost:{a.port}"
    print(f"Shorts Studio is running at {url}  (press Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
