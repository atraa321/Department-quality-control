import os

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from async_worker import start_async_task
from config import save_config


EXCEL_MODULE_OPTIONS = [
    ("疑难病例讨论", "discussions"),
    ("业务学习", "studies"),
    ("病历检查", "checks"),
    ("回访记录", "followups"),
]


class ReportWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.summary = {}
        self._refresh_token = 0

        self.setWindowTitle("数据汇总")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("report_window_width", 1280) or 1280), int(self.config.get("report_window_height", 780) or 780))
        x = self.config.get("report_window_x")
        y = self.config.get("report_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_label = QLabel("汇总数据加载中...")
        self.summary_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("开始"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        toolbar.addWidget(self.start_date)

        toolbar.addWidget(QLabel("结束"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        toolbar.addWidget(self.end_date)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.refresh_content)
        toolbar.addWidget(query_button)

        self.excel_module_combo = QComboBox()
        for label, code in EXCEL_MODULE_OPTIONS:
            self.excel_module_combo.addItem(label, code)
        toolbar.addWidget(self.excel_module_combo)

        export_excel_button = QPushButton("导出 Excel")
        export_excel_button.clicked.connect(self.export_excel)
        toolbar.addWidget(export_excel_button)

        export_word_button = QPushButton("导出 Word 汇总")
        export_word_button.clicked.connect(self.export_word)
        toolbar.addWidget(export_word_button)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        stats_layout = QGridLayout()
        stats_layout.setHorizontalSpacing(12)
        stats_layout.setVerticalSpacing(12)

        self.tasks_card = self._create_stat_group("任务完成", ["总任务数", "已完成", "已过期", "完成率"])
        self.business_card = self._create_stat_group("业务工作", ["疑难讨论", "业务学习", "病历检查", "严重问题"])
        self.followup_card = self._create_stat_group("出院回访", ["出院患者", "回访次数", "平均满意度", "已整改"])
        stats_layout.addWidget(self.tasks_card, 0, 0)
        stats_layout.addWidget(self.business_card, 0, 1)
        stats_layout.addWidget(self.followup_card, 0, 2)
        layout.addLayout(stats_layout)

        summary_tables = QHBoxLayout()
        summary_tables.setSpacing(12)
        self.category_stats_table = self._create_summary_table(["分类", "总数", "严重", "已整改", "待整改"])
        self.doctor_stats_table = self._create_summary_table(["责任医师", "总数", "严重", "已整改", "待整改"])
        summary_tables.addWidget(self._wrap_summary_table("病历检查按分类统计", self.category_stats_table), 1)
        summary_tables.addWidget(self._wrap_summary_table("病历检查按责任医师统计", self.doctor_stats_table), 1)
        layout.addLayout(summary_tables)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["report_window_x"] = pos.x()
        self.config["report_window_y"] = pos.y()
        self.config["report_window_width"] = size.width()
        self.config["report_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        user = self.config.get("user") or {}
        if user.get("role") != "admin":
            QMessageBox.warning(self, "无权限", "只有管理员可以使用数据汇总页面")
            self.close()
            return

        self._refresh_token += 1
        token = self._refresh_token
        self.summary_label.setText("汇总数据加载中...")
        params = self._build_params()

        def load():
            return self.api.get_report_summary(**params)

        def on_success(summary):
            if token != self._refresh_token:
                return
            self.summary = summary
            self.summary_label.setText("已按当前时间范围同步汇总数据")
            self._populate_summary()

        def on_error(exc):
            if token != self._refresh_token:
                return
            if self.app_context.handle_api_error(exc, self, "加载汇总数据失败"):
                self.refresh_content(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("汇总数据加载失败")

        start_async_task(self, load, on_success, on_error)

    def export_excel(self):
        module = self.excel_module_combo.currentData()
        label = self.excel_module_combo.currentText()
        try:
            exported = self.api.export_report_excel(module=module, **self._build_params())
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "导出 Excel 失败")
            return

        default_name = exported.get("filename") or f"{label}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 Excel",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not file_path:
            return
        self._save_exported_file(file_path, exported, "Excel 已导出")

    def export_word(self):
        try:
            exported = self.api.export_report_word(**self._build_params())
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "导出 Word 汇总失败")
            return

        default_name = exported.get("filename") or "科室质控汇总报告.docx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 Word",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Word 文件 (*.docx)",
        )
        if not file_path:
            return
        self._save_exported_file(file_path, exported, "Word 汇总已导出")

    def _build_params(self):
        return {
            "start": self.start_date.date().toString("yyyy-MM-dd"),
            "end": self.end_date.date().toString("yyyy-MM-dd"),
        }

    def _save_exported_file(self, file_path, exported, success_message):
        try:
            with open(file_path, "wb") as file:
                file.write(exported["content"])
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "完成", success_message)

    def _populate_summary(self):
        tasks = self.summary.get("tasks") or {}
        discussions = self.summary.get("discussions") or {}
        studies = self.summary.get("studies") or {}
        checks = self.summary.get("checks") or {}
        patients = self.summary.get("patients") or {}
        followups = self.summary.get("followups") or {}

        self._set_stat_group_values(
            self.tasks_card,
            [
                str(tasks.get("total", 0)),
                str(tasks.get("completed", 0)),
                str(tasks.get("overdue", 0)),
                f"{tasks.get('completion_rate', 0)}%",
            ],
        )
        self._set_stat_group_values(
            self.business_card,
            [
                f"{discussions.get('count', 0)} 次",
                f"{studies.get('count', 0)} 次",
                f"{checks.get('count', 0)} 份",
                str(checks.get("serious", 0)),
            ],
        )
        self._set_stat_group_values(
            self.followup_card,
            [
                f"{patients.get('count', 0)} 人",
                f"{followups.get('count', 0)} 次",
                f"{followups.get('avg_satisfaction', 0)} / 5",
                str(checks.get("rectified", 0)),
            ],
        )

        self._fill_summary_table(
            self.category_stats_table,
            checks.get("category_stats") or [],
            [
                lambda item: item.get("label") or "",
                lambda item: str(item.get("count", 0)),
                lambda item: str(item.get("serious", 0)),
                lambda item: str(item.get("rectified", 0)),
                lambda item: str(item.get("pending", 0)),
            ],
        )
        self._fill_summary_table(
            self.doctor_stats_table,
            checks.get("doctor_stats") or [],
            [
                lambda item: item.get("doctor_name") or "未指定",
                lambda item: str(item.get("count", 0)),
                lambda item: str(item.get("serious", 0)),
                lambda item: str(item.get("rectified", 0)),
                lambda item: str(item.get("pending", 0)),
            ],
        )

    def _create_stat_group(self, title, row_titles):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0f172a;")
        layout.addWidget(title_label)

        rows = []
        for row_title in row_titles:
            row_layout = QHBoxLayout()
            label = QLabel(row_title)
            label.setStyleSheet("font-size: 10pt; color: #475569;")
            value_label = QLabel("--")
            value_label.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0f172a;")
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(value_label)
            layout.addLayout(row_layout)
            rows.append(value_label)
        frame.value_labels = rows
        return frame

    def _set_stat_group_values(self, frame, values):
        for index, value_label in enumerate(frame.value_labels):
            value_label.setText(values[index] if index < len(values) else "--")

    def _create_summary_table(self, headers):
        table = QTableWidget(0, len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        return table

    def _wrap_summary_table(self, title, table):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 10pt; font-weight: 700; color: #0f172a;")
        layout.addWidget(title_label)
        layout.addWidget(table)
        return frame

    def _fill_summary_table(self, table, rows, extractors):
        table.setRowCount(len(rows))
        for row_index, row_data in enumerate(rows):
            for column, extractor in enumerate(extractors):
                item = QTableWidgetItem(extractor(row_data))
                item.setTextAlignment(Qt.AlignCenter if column > 0 else (Qt.AlignLeft | Qt.AlignVCenter))
                table.setItem(row_index, column, item)

