# -*- coding: utf-8 -*-
"""
FX RIG 9000 ― ゲームのお金で FX のしくみを体験（ランチャー）

しくみ
  1. このPCの中だけ（127.0.0.1）で小さなWebサーバを立てる
  2. Edge を「アプリ表示（--app）」で開き、FX RIG 9000 の画面を出す
  3. 画面を閉じると、しばらくしてサーバも自動で終わる
ネットにはつながりません。ゲームのお金は本物ではありません。
"""
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_NAME = 'FX RIG 9000'
PORT = 51807            # 固定（最高残高の記録はポート番号ごとに分かれるため変えない）
PORT_TRY = 10
ALIVE_TIMEOUT = 60      # 画面からの合図がこの秒数途切れたら終了
FIRST_TIMEOUT = 120     # 起動後この秒数のうちに画面がつながらなければ終了
BUNDLED_HTML = 'app.html'


def exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def res_dir():
    return getattr(sys, '_MEIPASS', exe_dir())


def data_home():
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    p = os.path.join(base, 'FXRig9000')
    os.makedirs(p, exist_ok=True)
    return p


def log(msg):
    try:
        with open(os.path.join(data_home(), 'log.txt'), 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')
    except Exception:
        pass


def message_box(text, title=APP_NAME):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
    except Exception:
        print(text)


ALIVE_JS = b"""<script>(function(){const ping=()=>fetch('/__alive',{cache:'no-store'}).catch(()=>{});ping();setInterval(ping,5000);})();</script>"""


def load_page():
    with open(os.path.join(res_dir(), BUNDLED_HTML), 'rb') as f:
        t = f.read()
    i = t.rfind(b'</body>')
    return t[:i] + ALIVE_JS + t[i:] if i >= 0 else t + ALIVE_JS


class State:
    page = b''
    last_alive = 0.0
    started = time.time()


class Handler(BaseHTTPRequestHandler):
    server_version = 'FXRig9000'

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body=b'', ctype='text/plain; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        h = (self.headers.get('Host') or '').split(':')[0]
        if h not in ('127.0.0.1', 'localhost'):
            return self._send(403, 'forbidden')
        path = urllib.parse.urlparse(self.path).path
        if path in ('/', '/index.html'):
            if not getattr(sys, 'frozen', False):     # 作っている途中（.py で動かすとき）は毎回読みなおす
                State.page = load_page()
            return self._send(200, State.page, 'text/html; charset=utf-8')
        if path == '/__ping':
            return self._send(200, 'fxrig9000')
        if path == '/__alive':
            State.last_alive = time.time()
            return self._send(204)
        return self._send(404, 'not found')


def already_running(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5) as s:
            s.sendall(b'GET /__ping HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n')
            return b'fxrig9000' in s.recv(1024)
    except OSError:
        return False


def start_server():
    for port in range(PORT, PORT + PORT_TRY):
        if already_running(port):
            return None, port            # すでに起動中 → 画面だけ開く
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            srv.daemon_threads = True
            return srv, port
        except OSError:
            continue
    raise RuntimeError('使えるポートがありません（%d〜%d）' % (PORT, PORT + PORT_TRY - 1))


def find_browser():
    cands = []
    for env in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
        b = os.environ.get(env)
        if b:
            cands.append(os.path.join(b, 'Microsoft', 'Edge', 'Application', 'msedge.exe'))
    for env in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        b = os.environ.get(env)
        if b:
            cands.append(os.path.join(b, 'Google', 'Chrome', 'Application', 'chrome.exe'))
    for c in cands:
        if os.path.isfile(c):
            return c
    for n in ('msedge', 'google-chrome', 'chromium'):
        p = shutil.which(n)
        if p:
            return p
    return None


def open_window(url):
    if os.environ.get('FXRIG_NOWIN'):           # 試験用：窓を開かずにサーバだけ動かす
        return None
    exe = find_browser()
    if not exe:
        webbrowser.open(url)
        return None
    prof = os.path.join(data_home(), 'EdgeProfile')
    args = [exe, '--app=' + url, '--user-data-dir=' + prof,
            '--no-first-run', '--no-default-browser-check',
            '--autoplay-policy=no-user-gesture-required',      # OP の音を鳴らすため
            '--disable-background-timer-throttling', '--disable-features=Translate',
            '--window-size=1366,860']
    flags = 0x08000000 if os.name == 'nt' else 0   # CREATE_NO_WINDOW
    return subprocess.Popen(args, creationflags=flags)


def main():
    try:
        State.page = load_page()
        srv, port = start_server()
        url = 'http://127.0.0.1:%d/' % port
        if len(sys.argv) > 1 and sys.argv[1].startswith('?'):
            url += sys.argv[1]           # 例：FXRIG9000.exe ?demo=play&seed=7（動画用）
        if srv is None:
            open_window(url)
            return
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log('start %s' % url)
        open_window(url)
        while True:
            time.sleep(2)
            now = time.time()
            if State.last_alive:
                if now - State.last_alive > ALIVE_TIMEOUT:
                    break
            elif now - State.started > FIRST_TIMEOUT and not os.environ.get('FXRIG_NOWIN'):
                break
        srv.shutdown()
        log('stop')
    except Exception as e:
        log(traceback.format_exc())
        message_box('起動できませんでした。\n\n%s' % e)


if __name__ == '__main__':
    main()
