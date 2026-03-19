import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import save_config


FIELD_LABELS = {
    "patient_name": "患者姓名",
    "record_no": "病案号",
    "gender": "性别",
    "age": "年龄",
    "diagnosis": "诊断",
    "admission_date": "入院日期",
    "discharge_date": "出院日期",
    "attending_doctor": "主管医师",
}


class ImportPreviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = []
        self.sample_rows = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("导入预览")
        self.resize(980, 520)
        layout = QVBoxLayout(self)

        self.summary_label = QLabel("暂无预览数据")
        self.summary_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 0, self)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

    def open_preview(self, columns, sample_rows):
        self.columns = columns or []
        self.sample_rows = sample_rows or []
        self.summary_label.setText(f"已识别 {len(self.columns)} 列，展示前 {len(self.sample_rows)} 行样例")
        self.table.clear()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setRowCount(len(self.sample_rows))
        for row_index, row_data in enumerate(self.sample_rows):
            for column_index, value in enumerate(row_data):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row_index, column_index, item)
        header = self.table.horizontalHeader()
        for column in range(len(self.columns)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.exec_()


class BatchManageDialog(QDialog):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.batches = []
        self.patients = []
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("导入批次管理")
        self.resize(1180, 680)
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        self.summary_label = QLabel("批次加载中...")
        self.summary_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        top_row.addWidget(self.summary_label)
        top_row.addStretch()
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh_content)
        top_row.addWidget(refresh_button)
        layout.addLayout(top_row)

        body = QHBoxLayout()

        left_frame = QFrame()
        left_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("导入批次"))
        self.batch_table = QTableWidget(0, 3, self)
        self.batch_table.setHorizontalHeaderLabels(["批次号", "导入数量", "导入时间"])
        self.batch_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.batch_table.setSelectionMode(QTableWidget.SingleSelection)
        self.batch_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.batch_table.setAlternatingRowColors(True)
        self.batch_table.verticalHeader().setVisible(False)
        self.batch_table.itemSelectionChanged.connect(self._load_selected_batch_patients)
        header = self.batch_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        left_layout.addWidget(self.batch_table)
        body.addWidget(left_frame, 1)

        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        patient_header = QHBoxLayout()
        self.patient_summary_label = QLabel("请选择左侧批次")
        self.patient_summary_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        patient_header.addWidget(self.patient_summary_label)
        patient_header.addStretch()
        delete_button = QPushButton("删除选中患者")
        delete_button.clicked.connect(self.delete_selected_patient)
        patient_header.addWidget(delete_button)
        right_layout.addLayout(patient_header)

        self.patient_table = QTableWidget(0, 8, self)
        self.patient_table.setHorizontalHeaderLabels(["患者姓名", "病案号", "性别", "年龄", "诊断", "出院日期", "主管医师", "回访状态"])
        self.patient_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.patient_table.setSelectionMode(QTableWidget.SingleSelection)
        self.patient_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.patient_table.setAlternatingRowColors(True)
        self.patient_table.verticalHeader().setVisible(False)
        patient_header_view = self.patient_table.horizontalHeader()
        for column in range(4):
            patient_header_view.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        patient_header_view.setSectionResizeMode(4, QHeaderView.Stretch)
        patient_header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        patient_header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        patient_header_view.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        right_layout.addWidget(self.patient_table)
        body.addWidget(right_frame, 2)

        layout.addLayout(body)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        close_row.addWidget(close_button)
        layout.addLayout(close_row)

    def open_dialog(self):
        self.refresh_content()
        self.exec_()

    def refresh_content(self):
        try:
            self.batches = self.api.list_patient_batches()
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "加载导入批次失败")
            return
        self.summary_label.setText(f"当前共 {len(self.batches)} 个导入批次")
        self._populate_batches()

    def _populate_batches(self):
        self.batch_table.setRowCount(len(self.batches))
        for row, batch in enumerate(self.batches):
            values = [
                batch.get("batch") or "",
                str(batch.get("count") or 0),
                batch.get("imported_at") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, batch)
                self.batch_table.setItem(row, column, item)
        if self.batches:
            self.batch_table.selectRow(0)
        else:
            self.patients = []
            self.patient_table.setRowCount(0)
            self.patient_summary_label.setText("暂无批次数据")

    def _selected_batch(self):
        row = self.batch_table.currentRow()
        if row < 0:
            return None
        item = self.batch_table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def _load_selected_batch_patients(self):
        batch = self._selected_batch()
        if not batch:
            return
        try:
            self.patients = self.api.list_patients(batch=batch.get("batch"))
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "加载批次患者失败")
            return
        self.patient_summary_label.setText(f"批次 {batch.get('batch')} 共 {len(self.patients)} 名患者")
        self._populate_patients()

    def _populate_patients(self):
        self.patient_table.setRowCount(len(self.patients))
        for row, patient in enumerate(self.patients):
            followup_status = []
            if patient.get("doctor_followup_done"):
                followup_status.append("医师已回访")
            if patient.get("nurse_followup_done"):
                followup_status.append("护士已回访")
            values = [
                patient.get("patient_name") or "",
                patient.get("record_no") or "",
                patient.get("gender") or "",
                "" if patient.get("age") is None else str(patient.get("age")),
                patient.get("diagnosis") or "",
                patient.get("discharge_date") or "",
                patient.get("attending_doctor") or "",
                " / ".join(followup_status) or "未回访",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, patient)
                self.patient_table.setItem(row, column, item)
        if self.patients:
            self.patient_table.selectRow(0)

    def _selected_patient(self):
        row = self.patient_table.currentRow()
        if row < 0:
            return None
        item = self.patient_table.item(row, 0)
        return item.data(Qt.UserRole) if item is not None else None

    def delete_selected_patient(self):
        patient = self._selected_patient()
        if not patient:
            QMessageBox.information(self, "提示", "请先选择一名患者")
            return
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确认删除患者“{patient.get('patient_name') or patient.get('record_no')}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            self.api.delete_patient(patient["id"])
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "删除患者失败")
            return
        self.refresh_content()


class PatientImportWindow(QMainWindow):
    def __init__(self, app_context, parent=None):
        super().__init__(parent)
        self.app_context = app_context
        self.api = app_context.api
        self.config = app_context.config
        self.selected_file = ""
        self.preview_columns = []
        self.sample_rows = []
        self.column_map_widgets = {}
        self.preview_dialog = ImportPreviewDialog(self)
        self.batch_dialog = BatchManageDialog(app_context, self)

        self.setWindowTitle("出院患者导入")
        self._restore_geometry()
        self._init_ui()

    def _restore_geometry(self):
        self.resize(int(self.config.get("patient_import_window_width", 1260) or 1260), int(self.config.get("patient_import_window_height", 780) or 780))
        x = self.config.get("patient_import_window_x")
        y = self.config.get("patient_import_window_y")
        if isinstance(x, int) and isinstance(y, int):
            self.move(x, y)

    def _init_ui(self):
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_label = QLabel("患者导入准备就绪")
        self.summary_label.setStyleSheet("font-size: 11pt; font-weight: 600;")
        layout.addWidget(self.summary_label)

        top_row = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("请选择 .xlsx / .xls / .csv 文件")
        self.file_path_input.setReadOnly(True)
        top_row.addWidget(self.file_path_input, 1)

        select_button = QPushButton("选择文件")
        select_button.clicked.connect(self.select_file)
        top_row.addWidget(select_button)

        preview_button = QPushButton("预览文件")
        preview_button.clicked.connect(self.preview_file)
        top_row.addWidget(preview_button)

        import_button = QPushButton("确认导入")
        import_button.clicked.connect(self.import_file)
        top_row.addWidget(import_button)
        layout.addLayout(top_row)

        action_row = QHBoxLayout()
        template_button = QPushButton("下载标准模板")
        template_button.clicked.connect(self.download_template)
        action_row.addWidget(template_button)

        backup_button = QPushButton("数据备份")
        backup_button.clicked.connect(self.backup_data)
        action_row.addWidget(backup_button)

        batches_button = QPushButton("批次管理")
        batches_button.clicked.connect(self.batch_dialog.open_dialog)
        action_row.addWidget(batches_button)

        clear_button = QPushButton("清空全部数据")
        clear_button.clicked.connect(self.clear_data)
        action_row.addWidget(clear_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        body = QHBoxLayout()
        body.setSpacing(12)

        left_frame = QFrame()
        left_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("列映射"))

        self.mapping_form = QFormLayout()
        self.mapping_form.setLabelAlignment(Qt.AlignRight)
        for field, label in FIELD_LABELS.items():
            combo = QComboBox()
            combo.addItem("不导入该字段", "")
            self.mapping_form.addRow(f"{label}：", combo)
            self.column_map_widgets[field] = combo
        left_layout.addLayout(self.mapping_form)
        body.addWidget(left_frame, 1)

        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background: white; border: none; border-radius: 12px; }")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)
        self.preview_summary_label = QLabel("请先选择文件并预览")
        self.preview_summary_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        right_layout.addWidget(self.preview_summary_label)

        self.preview_table = QTableWidget(0, 0, self)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setSelectionMode(QTableWidget.NoSelection)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.preview_table)
        body.addWidget(right_frame, 2)

        layout.addLayout(body)

    def closeEvent(self, event):
        pos = self.pos()
        size = self.size()
        self.config["patient_import_window_x"] = pos.x()
        self.config["patient_import_window_y"] = pos.y()
        self.config["patient_import_window_width"] = size.width()
        self.config["patient_import_window_height"] = size.height()
        save_config(self.config)
        super().closeEvent(event)

    def refresh_content(self, silent=False):
        user = self.config.get("user") or {}
        if user.get("role") != "admin":
            QMessageBox.warning(self, "无权限", "只有管理员可以使用患者导入页面")
            self.close()
            return
        self.summary_label.setText("患者导入准备就绪")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择患者导入文件",
            os.path.expanduser("~"),
            "数据文件 (*.xlsx *.xls *.csv)",
        )
        if not file_path:
            return
        self.selected_file = file_path
        self.file_path_input.setText(file_path)
        self.summary_label.setText("文件已选择，请先预览并确认列映射")

    def preview_file(self):
        if not self.selected_file:
            QMessageBox.information(self, "提示", "请先选择导入文件")
            return
        try:
            preview = self.api.preview_patients_file(self.selected_file)
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "预览文件失败")
            return
        self.preview_columns = preview.get("columns") or []
        self.sample_rows = preview.get("sample_rows") or []
        self._rebuild_mapping_options()
        self._auto_map_columns()
        self._populate_preview_table()
        self.preview_dialog.open_preview(self.preview_columns, self.sample_rows)
        self.summary_label.setText("预览完成，请确认列映射后再导入")

    def import_file(self):
        if not self.selected_file:
            QMessageBox.information(self, "提示", "请先选择导入文件")
            return
        if not self.preview_columns:
            QMessageBox.information(self, "提示", "请先完成文件预览")
            return
        try:
            result = self.api.import_patients(self.selected_file, self._column_map())
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "导入患者失败")
            return
        self.summary_label.setText(result.get("msg") or "导入完成")
        QMessageBox.information(self, "导入完成", result.get("msg") or "导入成功")
        self.batch_dialog.refresh_content()

    def download_template(self):
        try:
            exported = self.api.download_patient_template()
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "下载模板失败")
            return
        default_name = exported.get("filename") or "出院患者导入模板.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存模板",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not file_path:
            return
        self._save_exported_file(file_path, exported, "模板已下载")

    def backup_data(self):
        try:
            exported = self.api.backup_patients()
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "数据备份失败")
            return
        default_name = exported.get("filename") or "出院患者数据备份.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存备份",
            os.path.join(os.path.expanduser("~"), "Desktop", default_name),
            "Excel 文件 (*.xlsx)",
        )
        if not file_path:
            return
        self._save_exported_file(file_path, exported, "数据备份已下载")

    def clear_data(self):
        reply = QMessageBox.question(
            self,
            "确认清空",
            "确认清空全部出院患者数据和回访记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            result = self.api.clear_patients_data()
        except Exception as exc:
            self.app_context.handle_api_error(exc, self, "清空数据失败")
            return
        self.selected_file = ""
        self.file_path_input.clear()
        self.preview_columns = []
        self.sample_rows = []
        self._rebuild_mapping_options()
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.preview_summary_label.setText("数据已清空，请重新选择文件")
        self.summary_label.setText(result.get("msg") or "数据已清空")
        QMessageBox.information(self, "完成", result.get("msg") or "数据已清空")
        self.batch_dialog.refresh_content()

    def _column_map(self):
        result = {}
        for field, widget in self.column_map_widgets.items():
            column_name = widget.currentData()
            if column_name:
                result[field] = column_name
        return result

    def _rebuild_mapping_options(self):
        for widget in self.column_map_widgets.values():
            current = widget.currentData()
            widget.blockSignals(True)
            widget.clear()
            widget.addItem("不导入该字段", "")
            for column in self.preview_columns:
                widget.addItem(column, column)
            index = widget.findData(current)
            widget.setCurrentIndex(index if index >= 0 else 0)
            widget.blockSignals(False)

    def _auto_map_columns(self):
        reverse = {label: field for field, label in FIELD_LABELS.items()}
        for column in self.preview_columns:
            field = reverse.get(column)
            if field and field in self.column_map_widgets:
                combo = self.column_map_widgets[field]
                index = combo.findData(column)
                combo.setCurrentIndex(index if index >= 0 else 0)

    def _populate_preview_table(self):
        self.preview_summary_label.setText(f"已识别 {len(self.preview_columns)} 列，展示前 {len(self.sample_rows)} 行")
        self.preview_table.clear()
        self.preview_table.setColumnCount(len(self.preview_columns))
        self.preview_table.setHorizontalHeaderLabels(self.preview_columns)
        self.preview_table.setRowCount(len(self.sample_rows))
        for row_index, row_data in enumerate(self.sample_rows):
            for column_index, value in enumerate(row_data):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.preview_table.setItem(row_index, column_index, item)
        header = self.preview_table.horizontalHeader()
        for column in range(len(self.preview_columns)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

    def _save_exported_file(self, file_path, exported, success_message):
        try:
            with open(file_path, "wb") as file:
                file.write(exported["content"])
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        QMessageBox.information(self, "完成", success_message)

