import os
import json

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".ks_qc_client.json")
DEFAULT_CONFIG = {
    "server_url": "http://localhost:5000",
    "browser_path": "",
    "compatibility_mode": "auto",
    "token": "",
    "user": None,
    "window_x": -1,
    "window_y": -1,
    "overlay_always_on_top": True,
    "auto_start": False,
    "overlay_refresh_minutes": 5,
    "overlay_max_items": 8,
    "overlay_show_summary": True,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    cfg.setdefault(k, v)
                return cfg
            except json.JSONDecodeError:
                pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

