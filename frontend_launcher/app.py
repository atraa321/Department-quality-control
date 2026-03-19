# -*- coding: utf-8 -*-
import json
import mimetypes
import os
import posixpath
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "科室质控平台前端启动器"
DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:5000",
    "browser_path": "",
}
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
mimetypes.add_type("application/javascript", ".js")


def _runtime_root():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _frontend_dist_dir():
    return os.path.join(_runtime_root(), "frontend_dist")


def _config_path():
    appdata_dir = os.environ.get("APPDATA")
    if appdata_dir:
        base_dir = os.path.join(appdata_dir, "KsQcFrontendLauncher")
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".ksqc_frontend_launcher")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "config.json")


def _load_config():
    path = _config_path()
    if not os.path.exists(path):
        return dict(DEFAULT_CONFIG)

    try:
        with open(path, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, ValueError):
        return dict(DEFAULT_CONFIG)

    config = dict(DEFAULT_CONFIG)
    config.update({key: value for key, value in loaded.items() if key in DEFAULT_CONFIG})
    return config


def _save_config(config):
    with open(_config_path(), "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def _validate_server_url(server_url):
    parsed = urllib.parse.urlsplit((server_url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class FrontendRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "KsQcFrontendLauncher/1.0"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self._dispatch()

    def do_HEAD(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def do_PUT(self):
        self._dispatch()

    def do_PATCH(self):
        self._dispatch()

    def do_DELETE(self):
        self._dispatch()

    def do_OPTIONS(self):
        self._dispatch()

    def _dispatch(self):
        request_path = urllib.parse.urlsplit(self.path).path or "/"
        if request_path == "/api" or request_path.startswith("/api/"):
            self._proxy_request()
            return
        self._serve_static()

    def _proxy_request(self):
        target_url = self.server.backend_url.rstrip("/") + self.path
        body = self._read_request_body()
        request = urllib.request.Request(target_url, data=body, method=self.command)

        for header_name, header_value in self.headers.items():
            lowered = header_name.lower()
            if lowered in HOP_BY_HOP_HEADERS or lowered in {"host", "content-length", "accept-encoding"}:
                continue
            request.add_header(header_name, header_value)

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        try:
            with opener.open(request, timeout=60) as response:
                payload = response.read()
                self._write_response(response.status, response.headers.items(), payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self._write_response(exc.code, exc.headers.items(), payload)
        except Exception as exc:
            payload = json.dumps({"msg": "后端连接失败", "detail": str(exc)}, ensure_ascii=False).encode("utf-8")
            self._write_response(
                502,
                [("Content-Type", "application/json; charset=utf-8")],
                payload,
            )

    def _serve_static(self):
        dist_dir = os.path.realpath(self.server.dist_dir)
        request_path = urllib.parse.urlsplit(self.path).path or "/"
        relative_path = posixpath.normpath(urllib.parse.unquote(request_path)).lstrip("/")
        relative_parts = [part for part in relative_path.split("/") if part and part not in {".", ".."}]
        file_path = os.path.realpath(os.path.join(dist_dir, *relative_parts))

        try:
            is_inside_dist = os.path.commonpath([dist_dir, file_path]) == dist_dir
        except ValueError:
            is_inside_dist = False

        if not is_inside_dist:
            self.send_error(403)
            return

        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")

        if not os.path.isfile(file_path):
            if self._should_fallback_to_index(relative_path):
                file_path = os.path.join(dist_dir, "index.html")
            else:
                self.send_error(404)
                return

        try:
            with open(file_path, "rb") as file:
                payload = file.read()
        except OSError:
            self.send_error(500)
            return

        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(payload))),
            ("Cache-Control", "no-cache"),
        ]
        self._write_response(200, headers, payload)

    def _should_fallback_to_index(self, relative_path):
        if not relative_path:
            return True
        basename = posixpath.basename(relative_path)
        return "." not in basename

    def _read_request_body(self):
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return None

        try:
            length = int(content_length)
        except ValueError:
            return None

        if length <= 0:
            return None
        return self.rfile.read(length)

    def _write_response(self, status_code, headers, payload):
        body = payload or b""
        self.send_response(status_code)

        has_content_length = False
        for header_name, header_value in headers:
            lowered = header_name.lower()
            if lowered in HOP_BY_HOP_HEADERS:
                continue
            if lowered == "content-length":
                has_content_length = True
            self.send_header(header_name, header_value)

        if not has_content_length:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        if self.command != "HEAD" and body:
            self.wfile.write(body)


class FrontendServer:
    def __init__(self, dist_dir, backend_url, launcher):
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), FrontendRequestHandler)
        self._httpd.dist_dir = dist_dir
        self._httpd.backend_url = backend_url.rstrip("/")
        self._httpd.launcher = launcher
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def backend_url(self):
        return self._httpd.backend_url

    @property
    def url(self):
        host, port = self._httpd.server_address
        return "http://%s:%s/" % (host, port)

    def start(self):
        self._thread.start()

    def stop(self):
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2)


class LauncherApp:
    def __init__(self):
        self.config = _load_config()
        self.dist_dir = _frontend_dist_dir()
        self.server = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("660x300")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.server_var = tk.StringVar(value=self.config["server_url"])
        self.browser_var = tk.StringVar(value=self.config["browser_path"])
        self.local_url_var = tk.StringVar(value="未启动")
        self.status_var = tk.StringVar(value="准备就绪")

        self._build_ui()
        self.root.after(250, self.auto_start)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="后端地址").grid(row=0, column=0, sticky="w", pady=(0, 10))
        server_entry = ttk.Entry(frame, textvariable=self.server_var, width=62)
        server_entry.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="浏览器路径").grid(row=1, column=0, sticky="w", pady=(0, 10))
        browser_entry = ttk.Entry(frame, textvariable=self.browser_var, width=62)
        browser_entry.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        browse_button = ttk.Button(frame, text="选择", command=self.pick_browser)
        browse_button.grid(row=1, column=2, padx=(8, 0), pady=(0, 10))

        ttk.Label(frame, text="本地入口").grid(row=2, column=0, sticky="w", pady=(0, 10))
        local_url_entry = ttk.Entry(frame, textvariable=self.local_url_var, width=62, state="readonly")
        local_url_entry.grid(row=2, column=1, sticky="ew", pady=(0, 10))

        button_bar = ttk.Frame(frame)
        button_bar.grid(row=3, column=1, sticky="w", pady=(8, 10))

        ttk.Button(button_bar, text="保存配置", command=self.save_config).pack(side="left")
        ttk.Button(button_bar, text="启动前端", command=self.start_server).pack(side="left", padx=(8, 0))
        ttk.Button(button_bar, text="打开浏览器", command=self.open_browser).pack(side="left", padx=(8, 0))
        ttk.Button(button_bar, text="停止服务", command=self.stop_server).pack(side="left", padx=(8, 0))
        ttk.Button(button_bar, text="退出", command=self.close).pack(side="left", padx=(8, 0))

        status_frame = ttk.LabelFrame(frame, text="状态", padding=12)
        status_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(12, 0))
        ttk.Label(status_frame, textvariable=self.status_var, wraplength=600, justify="left").pack(anchor="w")

        tips = [
            "1. 前端页面由本地 exe 提供，API 请求会自动代理到上方后端地址。",
            "2. Win7 不支持 IE11，请填写 Chrome/360 极速浏览器等 Chromium 内核浏览器路径，或确保系统默认浏览器可用。",
            "3. 后端默认地址为 http://127.0.0.1:5000，可按现场部署修改。",
        ]
        for index, tip in enumerate(tips):
            ttk.Label(frame, text=tip, foreground="#555555").grid(
                row=5 + index, column=0, columnspan=3, sticky="w", pady=(6 if index == 0 else 2, 0)
            )

        frame.columnconfigure(1, weight=1)

    def auto_start(self):
        try:
            self.start_server()
            self.open_browser()
        except Exception as exc:
            self.on_log(str(exc))

    def pick_browser(self):
        selected = filedialog.askopenfilename(
            title="选择浏览器可执行文件",
            filetypes=[("Executable", "*.exe"), ("All Files", "*.*")],
        )
        if selected:
            self.browser_var.set(selected)

    def save_config(self):
        config = self._build_config()
        if not _validate_server_url(config["server_url"]):
            messagebox.showerror(APP_NAME, "后端地址格式不正确，请填写 http://ip:port")
            return

        _save_config(config)
        self.config = config
        self.on_log("配置已保存")

    def start_server(self):
        config = self._build_config()
        if not _validate_server_url(config["server_url"]):
            raise RuntimeError("后端地址格式不正确，请填写 http://ip:port")

        if self.server is not None:
            if self.server.backend_url != config["server_url"].rstrip("/"):
                self.stop_server()
            else:
                self.local_url_var.set(self.server.url)
                self.on_log("前端服务已在运行")
                return

        if not os.path.isfile(os.path.join(self.dist_dir, "index.html")):
            raise RuntimeError("未找到内置前端资源，请重新打包 exe。")

        _save_config(config)
        self.config = config

        self.server = FrontendServer(self.dist_dir, config["server_url"], self)
        self.server.start()
        self.local_url_var.set(self.server.url)
        self.on_log("前端服务已启动，后端代理地址：%s" % config["server_url"])

    def stop_server(self):
        if self.server is None:
            self.on_log("前端服务未启动")
            return

        self.server.stop()
        self.server = None
        self.local_url_var.set("未启动")
        self.on_log("前端服务已停止")

    def open_browser(self):
        if self.server is None:
            self.start_server()

        local_url = self.server.url
        browser_path = (self.browser_var.get() or "").strip()
        if browser_path:
            if not os.path.exists(browser_path):
                raise RuntimeError("浏览器路径不存在：%s" % browser_path)
            subprocess.Popen([browser_path, local_url], cwd=os.path.dirname(browser_path))
        else:
            if not webbrowser.open(local_url, new=1):
                raise RuntimeError("无法调用系统默认浏览器，请改为手动指定 Chromium 浏览器路径。")

        self.on_log("已打开浏览器：%s" % local_url)

    def on_log(self, message):
        self.status_var.set(message)

    def close(self):
        try:
            config = self._build_config()
            if _validate_server_url(config["server_url"]):
                _save_config(config)
        except Exception:
            pass

        if self.server is not None:
            self.server.stop()
            self.server = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()

    def _build_config(self):
        return {
            "server_url": (self.server_var.get() or "").strip(),
            "browser_path": (self.browser_var.get() or "").strip(),
        }


def main():
    try:
        app = LauncherApp()
        app.run()
    except Exception as exc:
        messagebox.showerror(APP_NAME, str(exc))


if __name__ == "__main__":
    main()
