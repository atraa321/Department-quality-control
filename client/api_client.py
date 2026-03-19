import os
import re
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter


class ApiError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self, server_url, token=""):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=0)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _server_host(self):
        parsed = urlparse(self.server_url if "://" in self.server_url else f"http://{self.server_url}")
        return (parsed.hostname or "").strip().lower()

    def _network_error_hint(self):
        host = self._server_host()
        if host == "10.0.2.15":
            return (
                "当前地址 10.0.2.15 通常是 VirtualBox NAT 虚拟机自己的地址。\n"
                "如果后端和客户端在同一台虚拟机，请改填 http://127.0.0.1:5000 。\n"
                "如果后端在宿主机，请改填 http://10.0.2.2:5000 或宿主机局域网 IP。"
            )
        if host in ("127.0.0.1", "localhost"):
            return (
                "当前地址是本机回环地址。\n"
                "只有后端也运行在同一台电脑时才能这样填写；"
                "如果后端在另一台机器，请改填那台机器的实际 IP。"
            )
        return (
            "请检查后端是否已启动、地址和端口是否正确、"
            "以及防火墙是否放行 5000 端口。"
        )

    def _headers(self):
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _json_headers(self):
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        return headers

    def _extract_filename(self, response, default_name):
        disposition = response.headers.get("Content-Disposition", "")
        if not disposition:
            return default_name

        match = re.search(r'filename\*=(?:UTF-8\'\')?([^;]+)', disposition, re.IGNORECASE)
        if match:
            return requests.utils.unquote(match.group(1).strip().strip('"'))

        match = re.search(r'filename=([^;]+)', disposition, re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"')
        return default_name

    def _request(self, method, path, **kwargs):
        try:
            response = self.session.request(
                method,
                f"{self.server_url}{path}",
                timeout=kwargs.pop("timeout", 10),
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ApiError(f"网络请求失败：{exc}\n\n{self._network_error_hint()}") from exc

        if response.ok:
            content_type = response.headers.get("Content-Type", "")
            if response.content and "application/json" in content_type:
                return response.json()
            return None

        message = None
        try:
            message = response.json().get("msg")
        except ValueError:
            message = response.text.strip() or None
        raise ApiError(message or "请求失败", status_code=response.status_code)

    def _download(self, path, params=None, default_name="download.bin"):
        try:
            response = self.session.get(
                f"{self.server_url}{path}",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise ApiError(f"网络请求失败：{exc}\n\n{self._network_error_hint()}") from exc

        if not response.ok:
            message = None
            try:
                message = response.json().get("msg")
            except ValueError:
                message = response.text.strip() or None
            raise ApiError(message or "下载失败", status_code=response.status_code)

        return {
            "filename": self._extract_filename(response, default_name),
            "content": response.content,
            "content_type": response.headers.get("Content-Type", "application/octet-stream"),
        }

    def _upload_file(self, path, file_path, extra_form=None):
        filename = os.path.basename(file_path)
        try:
            with open(file_path, "rb") as file_obj:
                return self._request(
                    "POST",
                    path,
                    headers=self._headers(),
                    files={"file": (filename, file_obj)},
                    data=extra_form or {},
                    timeout=30,
                )
        except OSError as exc:
            raise ApiError(f"读取文件失败：{exc}") from exc

    def login(self, username, password):
        data = self._request("POST", "/api/auth/login", headers=self._json_headers(), json={"username": username, "password": password})
        self.token = data["token"]
        return data

    def get_me(self):
        return self._request("GET", "/api/auth/me", headers=self._headers())

    def list_users(self):
        return self._request("GET", "/api/auth/users", headers=self._headers())

    def create_user(self, data):
        return self._request("POST", "/api/auth/users", headers=self._json_headers(), json=data)

    def update_user(self, user_id, data):
        return self._request("PUT", f"/api/auth/users/{user_id}", headers=self._json_headers(), json=data)

    def change_password(self, data):
        return self._request("POST", "/api/auth/change-password", headers=self._json_headers(), json=data)

    def list_tasks(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/tasks", headers=self._headers(), params=clean_params)

    def create_task(self, data):
        return self._request("POST", "/api/tasks", headers=self._json_headers(), json=data)

    def get_task(self, task_id):
        return self._request("GET", f"/api/tasks/{task_id}", headers=self._headers())

    def update_task(self, task_id, data):
        return self._request("PUT", f"/api/tasks/{task_id}", headers=self._json_headers(), json=data)

    def delete_task(self, task_id):
        return self._request("DELETE", f"/api/tasks/{task_id}", headers=self._headers())

    def batch_delete_tasks(self, ids):
        return self._request("POST", "/api/tasks/batch-delete", headers=self._json_headers(), json={"ids": ids})

    def get_pending_tasks(self):
        return self._request("GET", "/api/tasks/my-pending", headers=self._headers())

    def _build_dashboard_summary_from_pending(self, pending_tasks):
        normalized_tasks = []
        pending_count = 0
        overdue_count = 0

        for task in pending_tasks or []:
            item = dict(task)
            is_overdue = bool(item.get("is_overdue"))
            if not is_overdue and item.get("status") == "overdue":
                is_overdue = True
                item["is_overdue"] = True

            if is_overdue:
                overdue_count += 1
            else:
                pending_count += 1
            normalized_tasks.append(item)

        return {
            "pending_tasks": normalized_tasks,
            "stats": {
                "pending_tasks": pending_count,
                "overdue_tasks": overdue_count,
                "completed_tasks": 0,
                "pending_followups": 0,
            },
            "legacy_fallback": True,
        }

    def get_dashboard_summary(self):
        try:
            return self._request("GET", "/api/tasks/dashboard-summary", headers=self._headers())
        except ApiError as exc:
            if exc.status_code != 404:
                raise
            return self._build_dashboard_summary_from_pending(self.get_pending_tasks())

    def list_discussions(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/discussions", headers=self._headers(), params=clean_params)

    def create_discussion(self, data):
        return self._request("POST", "/api/discussions", headers=self._json_headers(), json=data)

    def get_discussion(self, discussion_id):
        return self._request("GET", f"/api/discussions/{discussion_id}", headers=self._headers())

    def update_discussion(self, discussion_id, data):
        return self._request("PUT", f"/api/discussions/{discussion_id}", headers=self._json_headers(), json=data)

    def delete_discussion(self, discussion_id):
        return self._request("DELETE", f"/api/discussions/{discussion_id}", headers=self._headers())

    def export_discussion_word(self, discussion_id):
        return self._download(f"/api/discussions/{discussion_id}/export-word", default_name=f"discussion-{discussion_id}.docx")

    def list_studies(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/studies", headers=self._headers(), params=clean_params)

    def create_study(self, data):
        return self._request("POST", "/api/studies", headers=self._json_headers(), json=data)

    def get_study(self, study_id):
        return self._request("GET", f"/api/studies/{study_id}", headers=self._headers())

    def update_study(self, study_id, data):
        return self._request("PUT", f"/api/studies/{study_id}", headers=self._json_headers(), json=data)

    def delete_study(self, study_id):
        return self._request("DELETE", f"/api/studies/{study_id}", headers=self._headers())

    def export_study_word(self, study_id):
        return self._download(f"/api/studies/{study_id}/export-word", default_name=f"study-{study_id}.docx")

    def get_checks_meta(self):
        return self._request("GET", "/api/checks/meta", headers=self._headers())

    def get_check_stats(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/checks/stats", headers=self._headers(), params=clean_params)

    def list_checks(self, task_id=None, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        if task_id is not None:
            clean_params["task_id"] = task_id
        return self._request("GET", "/api/checks", headers=self._headers(), params=clean_params)

    def create_check(self, data):
        return self._request("POST", "/api/checks", headers=self._json_headers(), json=data)

    def get_check(self, check_id):
        return self._request("GET", f"/api/checks/{check_id}", headers=self._headers())

    def update_check(self, check_id, data):
        return self._request("PUT", f"/api/checks/{check_id}", headers=self._json_headers(), json=data)

    def delete_check(self, check_id):
        return self._request("DELETE", f"/api/checks/{check_id}", headers=self._headers())

    def list_patients(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/patients", headers=self._headers(), params=clean_params)

    def import_patients(self, file_path, column_map=None):
        extra_form = {}
        if column_map is not None:
            import json
            extra_form["column_map"] = json.dumps(column_map, ensure_ascii=False)
        return self._upload_file("/api/patients/import", file_path, extra_form=extra_form)

    def preview_patients_file(self, file_path):
        return self._upload_file("/api/patients/preview", file_path)

    def download_patient_template(self):
        return self._download("/api/patients/template", default_name="出院患者导入模板.xlsx")

    def list_patient_batches(self):
        return self._request("GET", "/api/patients/batches", headers=self._headers())

    def backup_patients(self):
        return self._download("/api/patients/backup", default_name="出院患者数据备份.xlsx")

    def clear_patients_data(self):
        return self._request("DELETE", "/api/patients/clear", headers=self._headers())

    def delete_patient(self, patient_id):
        return self._request("DELETE", f"/api/patients/{patient_id}", headers=self._headers())

    def list_followups(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/followups", headers=self._headers(), params=clean_params)

    def create_followup(self, data):
        return self._request("POST", "/api/followups", headers=self._json_headers(), json=data)

    def get_followup(self, followup_id):
        return self._request("GET", f"/api/followups/{followup_id}", headers=self._headers())

    def update_followup(self, followup_id, data):
        return self._request("PUT", f"/api/followups/{followup_id}", headers=self._json_headers(), json=data)

    def delete_followup(self, followup_id):
        return self._request("DELETE", f"/api/followups/{followup_id}", headers=self._headers())

    def get_followup_stats(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/followups/stats", headers=self._headers(), params=clean_params)

    def get_report_summary(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._request("GET", "/api/reports/summary", headers=self._headers(), params=clean_params)

    def export_report_excel(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._download("/api/reports/export/excel", params=clean_params, default_name="report.xlsx")

    def export_report_word(self, **params):
        clean_params = {key: value for key, value in params.items() if value not in (None, "")}
        return self._download("/api/reports/export/word", params=clean_params, default_name="report.docx")

