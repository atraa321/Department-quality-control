import os
from datetime import date

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import save_config


class DiscussionEditDialog(QDialog):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.record = None
        self.pending_tasks = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("病例讨论记录")
        self.resize(1040, 840)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.task_button = QPushButton("不关联任务")
        self.task_button.setMinimumHeight(42)
        self.task_button.clicked.connect(self._select_task)
        self.task_hint_label = QLabel("可选。保存后若已关联任务，将自动完成该任务。")
        self.task_hint_label.setStyleSheet("color: #64748b; font-size: 10pt;")

        task_layout = QVBoxLayout()
        task_layout.setSpacing(6)
        task_layout.addWidget(self.task_button)
        task_layout.addWidget(self.task_hint_label)

        self.record_no_input = QLineEdit()
        self.record_no_input.setPlaceholderText("留空则由系统自动生成")

        self.discussion_date_input = QDateEdit()
        self.discussion_date_input.setCalendarPopup(True)
        self.discussion_date_input.setDisplayFormat("yyyy-MM-dd")
        self.discussion_date_input.setDate(QDate.currentDate())

        self.patient_name_input = QLineEdit()
        self.diagnosis_input = QLineEdit()
        self.moderator_input = QLineEdit()
        self.speaker_input = QLineEdit()
        self.location_input = QLineEdit()
        self.participant_count_input = QSpinBox()
        self.participant_count_input.setRange(0, 999)
        self.discussion_purpose_input = QLineEdit()
        self.participants_input = QLineEdit()

        for line_edit in (
            self.record_no_input,
            self.patient_name_input,
            self.diagnosis_input,
            self.moderator_input,
            self.speaker_input,
            self.location_input,
            self.discussion_purpose_input,
            self.participants_input,
        ):
            line_edit.setMinimumHeight(40)
            line_edit.setStyleSheet("font-size: 12pt; padding: 6px 10px;")

        self.discussion_date_input.setMinimumHeight(40)
        self.discussion_date_input.setStyleSheet("font-size: 12pt; padding: 4px 8px;")
        self.participant_count_input.setMinimumHeight(40)
        self.participant_count_input.setStyleSheet("font-size: 12pt; padding: 4px 8px;")

        self.case_info_input = QTextEdit()
        self.case_info_input.setPlaceholderText("按自然书写方式输入病史摘要、当前病情、检查结果和讨论背景。")
        self.case_info_input.setMinimumHeight(150)
        self.discussion_content_input = QTextEdit()
        self.discussion_content_input.setPlaceholderText("直接记录讨论过程、不同意见、补充观点和处理思路。")
        self.discussion_content_input.setMinimumHeight(230)
        self.conclusion_input = QTextEdit()
        self.conclusion_input.setPlaceholderText("归纳最终结论、下一步方案和责任分工。")
        self.conclusion_input.setMinimumHeight(160)

        for text_edit in (self.case_info_input, self.discussion_content_input, self.conclusion_input):
            text_edit.setStyleSheet("font-size: 12pt; padding: 8px 10px; line-height: 1.6;")

        base_info_grid = QGridLayout()
        base_info_grid.setHorizontalSpacing(12)
        base_info_grid.setVerticalSpacing(12)
        base_info_grid.addWidget(self.patient_name_input, 0, 0)
        base_info_grid.addWidget(self.diagnosis_input, 0, 1)
        base_info_grid.addWidget(self.moderator_input, 1, 0)
        base_info_grid.addWidget(self.speaker_input, 1, 1)
        base_info_grid.addWidget(self.location_input, 2, 0)
        base_info_grid.addWidget(self.participants_input, 2, 1)

        purpose_grid = QGridLayout()
        purpose_grid.setHorizontalSpacing(12)
        purpose_grid.setVerticalSpacing(12)
        purpose_grid.addWidget(self.discussion_purpose_input, 0, 0)
        purpose_grid.addWidget(self.participant_count_input, 0, 1)

        form.addRow("关联任务：", task_layout)
        form.addRow("记录编号：", self.record_no_input)
        form.addRow("讨论日期：", self.discussion_date_input)
        form.addRow("基础信息：", base_info_grid)
        form.addRow("目的与人数：", purpose_grid)
        form.addRow("病例信息：", self.case_info_input)
        form.addRow("讨论内容：", self.discussion_content_input)
        form.addRow("讨论结论：", self.conclusion_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self._submit)
        cancel_button.setMinimumHeight(42)
        save_button.setMinimumHeight(42)
        cancel_button.setStyleSheet("font-size: 11pt; padding: 0 18px;")
        save_button.setStyleSheet("font-size: 11pt; font-weight: 600; padding: 0 18px;")
        button_row.addWidget(cancel_button)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

    def load_pending_tasks(self):
        tasks = self.api.list_tasks(type="discussion")
        self.pending_tasks = [task for task in tasks if task.get("status") != "completed"]

    def open_for_create(self, task=None):
        self.record = None
        self.setWindowTitle("新增病例讨论记录")
        self._reset_form()
        self.load_pending_tasks()
        if task:
            self.task_button.setProperty("task_id", task.get("id"))
            self.task_button.setText(task.get("title") or f"任务 #{task.get('id')}")
        return self.exec_()

    def open_for_edit(self, record):
        self.record = record
        self.setWindowTitle("编辑病例讨论记录")
        self._reset_form()
        self.load_pending_tasks()
        self.record_no_input.setText(record.get("record_no") or "")
        self.discussion_date_input.setDate(self._to_qdate(record.get("discussion_date")))
        self.patient_name_input.setText(record.get("patient_name") or "")
        self.diagnosis_input.setText(record.get("diagnosis") or "")
        self.moderator_input.setText(record.get("moderator") or "")
        self.speaker_input.setText(record.get("speaker") or "")
        self.location_input.setText(record.get("location") or "")
        self.participant_count_input.setValue(int(record.get("participant_count") or 0))
        self.discussion_purpose_input.setText(record.get("discussion_purpose") or "")
        self.participants_input.setText(record.get("participants") or "")
        self.case_info_input.setPlainText(record.get("case_info") or "")
        self.discussion_content_input.setPlainText(record.get("discussion_content") or "")
        self.conclusion_input.setPlainText(record.get("conclusion") or "")

        task_id = record.get("task_id")
        task_title = None
        for task in self.pending_tasks:
            if task.get("id") == task_id:
                task_title = task.get("title")
                break
        self.task_button.setProperty("task_id", task_id)
        self.task_button.setText(task_title or ("任务 #%s" % task_id if task_id else "不关联任务"))
        return self.exec_()

    def _reset_form(self):
        self.task_button.setProperty("task_id", None)
        self.task_button.setText("不关联任务")
        self.record_no_input.clear()
        self.discussion_date_input.setDate(QDate.currentDate())
        self.patient_name_input.clear()
        self.diagnosis_input.clear()
        self.moderator_input.clear()
        self.speaker_input.clear()
        self.location_input.clear()
        self.participant_count_input.setValue(0)
        self.discussion_purpose_input.clear()
        self.participants_input.clear()
        self.case_info_input.clear()
        self.discussion_content_input.clear()
        self.conclusion_input.clear()

    def _select_task(self):
        options = ["不关联任务"] + [task.get("title") or f"任务 #{task.get('id')}" for task in self.pending_tasks]
        current_task_id = self.task_button.property("task_id")
        current_index = 0
        for index, task in enumerate(self.pending_tasks, start=1):
            if task.get("id") == current_task_id:
                current_index = index
                break
        choice, ok = QInputDialog.getItem(self, "选择关联任务", "待完成的病例讨论任务", options, current_index, False)
        if not ok:
            return
        if choice == options[0]:
            self.task_button.setProperty("task_id", None)
            self.task_button.setText("不关联任务")
            return
        for task in self.pending_tasks:
            title = task.get("title") or f"任务 #{task.get('id')}"
            if title == choice:
                self.task_button.setProperty("task_id", task.get("id"))
                self.task_button.setText(title)
                return

    def _submit(self):
        payload = {
            "task_id": self.task_button.property("task_id"),
            "record_no": self.record_no_input.text().strip(),
            "discussion_date": self.discussion_date_input.date().toString("yyyy-MM-dd"),
            "patient_name": self.patient_name_input.text().strip(),
            "diagnosis": self.diagnosis_input.text().strip(),
            "moderator": self.moderator_input.text().strip(),
            "speaker": self.speaker_input.text().strip(),
            "location": self.location_input.text().strip(),
            "participant_count": self.participant_count_input.value(),
            "discussion_purpose": self.discussion_purpose_input.text().strip(),
            "participants": self.participants_input.text().strip(),
            "case_info": self.case_info_input.toPlainText().strip(),
            "discussion_content": self.discussion_content_input.toPlainText().strip(),
            "conclusion": self.conclusion_input.toPlainText().strip(),
        }
        if not payload["discussion_date"]:
            QMessageBox.warning(self, "提示", "请选择讨论日期")
            return
        try:
            if self.record:
                self.api.update_discussion(self.record["id"], payload)
            else:
                self.api.create_discussion(payload)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "保存病例讨论失败")
            return
        self.app_context.refresh_overlay()
        self.accept()

    def _to_qdate(self, iso_date):
        if iso_date:
            parsed = QDate.fromString(iso_date, "yyyy-MM-dd")
            if parsed.isValid():
                return parsed
        return QDate.currentDate()


class DiscussionDetailDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("病例讨论详情")
        self.resize(820, 720)
        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.summary_label)

        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        layout.addWidget(self.content_text)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def open_record(self, record):
        summary_lines = [
            f"记录编号：{record.get('record_no') or '-'}",
            f"讨论日期：{record.get('discussion_date') or '-'}",
            f"患者姓名：{record.get('patient_name') or '-'}",
            f"临床诊断：{record.get('diagnosis') or '-'}",
            f"主持人：{record.get('moderator') or '-'}",
            f"主讲人：{record.get('speaker') or '-'}",
            f"讨论地点：{record.get('location') or '-'}",
            f"参加人数：{record.get('participant_count') or 0}",
            f"讨论目的：{record.get('discussion_purpose') or '-'}",
            f"参与人员：{record.get('participants') or '-'}",
            f"记录人：{record.get('creator_name') or '-'}",
        ]
        self.summary_label.setText("\n".join(summary_lines))
        content_lines = [
            "【病例信息】",
            record.get("case_info") or "",
            "",
            "【讨论内容】",
            record.get("discussion_content") or "",
            "",
            "【讨论结论】",
            record.get("conclusion") or "",
        ]
        self.content_text.setPlainText("\n".join(content_lines))
        self.exec_()


class DiscussionWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.records = []
        self.edit_dialog = DiscussionEditDialog(app_context, self)
        self.detail_dialog = DiscussionDetailDialog(self)

        self.setWindowTitle("疑难病例讨论")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("discussion_window_width", 1240) or 1240), int(self.config.get("discussion_window_height", 760) or 760))
        x = self.config.get("discussion_window_x")
        y = self.config.get("discussion_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self.summary_label = QLabel("病例讨论加载中...")
        self.summary_label.setStyleSheet("font-size: 14pt; font-weight: 600;")
        header.addWidget(self.summary_label)
        header.addStretch()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setMinimumHeight(38)
        self.start_date.setStyleSheet("font-size: 11pt;")
        header.addWidget(QLabel("开始"))
        header.addWidget(self.start_date)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setMinimumHeight(38)
        self.end_date.setStyleSheet("font-size: 11pt;")
        header.addWidget(QLabel("结束"))
        header.addWidget(self.end_date)

        query_button = QPushButton("查询")
        query_button.clicked.connect(self.refresh_content)
        query_button.setMinimumHeight(38)
        header.addWidget(query_button)

        add_button = QPushButton("新增记录")
        add_button.clicked.connect(self.create_record)
        add_button.setMinimumHeight(38)
        header.addWidget(add_button)
        layout.addLayout(header)

        self.table = QTableWidget(0, 10, self)
        self.table.setStyleSheet("QTableWidget { font-size: 11pt; } QHeaderView::section { font-size: 11pt; padding: 8px; }")
        self.table.setHorizontalHeaderLabels(["编号", "日期", "患者", "诊断", "主持人", "主讲人", "人数", "地点", "结论", "记录人"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemDoubleClicked.connect(lambda *_: self.view_record())
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(8, QHeaderView.Stretch)
        header_view.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.view_button = QPushButton("查看详情")
        self.view_button.clicked.connect(self.view_record)
        self.export_button = QPushButton("导出 Word")
        self.export_button.clicked.connect(self.export_record)
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_record)
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_record)
        for button in (self.view_button, self.export_button, self.edit_button, self.delete_button):
            button.setMinimumHeight(38)
            buttons.addWidget(button)
        buttons.addStretch()
        layout.addLayout(buttons)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["discussion_window_x"] = pos.x()
        self.config["discussion_window_y"] = pos.y()
        self.config["discussion_window_width"] = size.width()
        self.config["discussion_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        params = {
            "start": self.start_date.date().toString("yyyy-MM-dd"),
            "end": self.end_date.date().toString("yyyy-MM-dd"),
        }
        try:
            self.records = self.api.list_discussions(**params)
        except Exception as exc:
            if self.app_context.handle_api_error(exc, self, "刷新病例讨论失败"):
                self.refresh_content(silent=silent)
                return
            if not silent:
                QMessageBox.warning(self, "刷新失败", str(exc))
            self.summary_label.setText("病例讨论加载失败")
            return
        self.summary_label.setText(f"共 {len(self.records)} 条病例讨论记录")
        self._populate_table()

    def open_for_task(self, task=None, auto_create=False):
        self.show()
        self.raise_()
        self.activateWindow()
        self.refresh_content(silent=True)
        if auto_create:
            self.create_record(task)

    def create_record(self, task=None):
        if self.edit_dialog.open_for_create(task) == QDialog.Accepted:
            self.refresh_content(silent=True)

    def view_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        self.detail_dialog.open_record(record)

    def edit_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        if self.edit_dialog.open_for_edit(record) == QDialog.Accepted:
            self.refresh_content(silent=True)

    def delete_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        reply = QMessageBox.question(self, "确认删除", f"确认删除记录“{record.get('record_no') or record.get('patient_name') or record.get('id')}”吗？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.delete_discussion(record["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "删除病例讨论失败")
            return
        self.refresh_content(silent=True)

    def export_record(self):
        record = self._selected_record()
        if not record:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        try:
            exported = self.api.export_discussion_word(record["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "导出 Word 失败")
            return
        default_name = exported.get("filename") or f"{record.get('record_no') or '病例讨论记录'}.docx"
        file_path, _ = QFileDialog.getSaveFileName(self, "保存 Word", os.path.join(os.path.expanduser("~"), "Desktop", default_name), "Word 文件 (*.docx)")
        if not file_path:
            return
        try:
            with open(file_path, "wb") as file:
                file.write(exported["content"])
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "完成", "Word 已导出")

    def _populate_table(self):
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                record.get("record_no") or "",
                record.get("discussion_date") or "",
                record.get("patient_name") or "",
                record.get("diagnosis") or "",
                record.get("moderator") or "",
                record.get("speaker") or "",
                str(record.get("participant_count") or 0),
                record.get("location") or "",
                record.get("conclusion") or "",
                record.get("creator_name") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, record)
                self.table.setItem(row, column, item)
        if self.records:
            self.table.selectRow(0)

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.UserRole)

