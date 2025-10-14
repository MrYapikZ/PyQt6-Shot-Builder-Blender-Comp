from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QAbstractItemView

from app.ui.apply_light_preset_ui import Ui_Form
from app.data.project import project_list, division_list
from app.services.csv_manager import CSVManager
from app.services.file_manager import FileManager


class ApplyLightPresetHandler(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.csv_data = None
        self._available_widget_order = []

        for project in project_list:
            self.ui.comboBox_project.addItem(project[1])
        self.ui.pushButton_scan.clicked.connect(self.on_scan_files)
        self.ui.listWidget_available.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.ui.listWidget_available.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.listWidget_selected.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.ui.listWidget_selected.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.pushButton_listControl_add.clicked.connect(self.on_move_available_item)
        self.ui.pushButton_listControl_remove.clicked.connect(self.on_move_selected_item)

    def on_scan_files(self):
        project_data = next((p for p in project_list if p[1] == self.ui.comboBox_project.currentText()), None)
        if not project_data:
            QMessageBox.warning(self, "Error", "No project selected")
            return

        self.ui.listWidget_available.clear()

        csv_path = self.ui.lineEdit_csv.text()
        if not csv_path:
            QMessageBox.warning(self, "Error", "CSV path is empty")
            return

        # Read CSV file
        csv_data = CSVManager().read(file_path=csv_path, skip_header=True)
        self.csv_data = csv_data
        for row in csv_data:
            # Expecting CSV format: EP, SEQ, SHOT, START_FRAME, END_FRAME
            ep, seq, shot, start_frame, end_frame = row[0].lower(), row[1].lower(), row[2].lower(), int(row[3]), int(
                row[4])
            # print(
            #     f"Scanning for EP: {ep}, SEQ: {seq}, SHOT: {shot}, Frames: {start_frame}-{end_frame} in project path: {project_path}")

            file_name = FileManager().generate_file_name(project_code=project_data[2], ep=ep, seq=seq, shot=shot,
                                                         division=division_list[1][0],
                                                         extension="blend")  # Assuming 'lgt' division (target)
            # print(f"File name: {file_name}")
            self.ui.listWidget_available.addItem(file_name)
            self._available_widget_order.append(file_name)

    def on_move_available_item(self):
        sel = self.ui.listWidget_available.selectedItems()
        for item in sel:
            row = self.ui.listWidget_available.row(item)
            item = self.ui.listWidget_available.takeItem(row)
            self.ui.listWidget_selected.addItem(item)

    def on_move_selected_item(self):
        sel = self.ui.listWidget_selected.selectedItems()
        for item in sel:
            insert_row = self._find_insert_row_for_label(item.text())
            row = self.ui.listWidget_selected.row(item)
            item = self.ui.listWidget_selected.takeItem(row)
            self.ui.listWidget_available.insertItem(insert_row, item)

    def _available_order_index(self, label: str) -> int:
        try:
            return self._available_widget_order.index(label)
        except ValueError:
            return len(self._available_widget_order)

    def _find_insert_row_for_label(self, label: str) -> int:
        """Cari posisi penyisipan berdasarkan urutan awal"""
        target_idx = self._available_order_index(label)
        lw = self.ui.listWidget_available
        for row in range(lw.count()):
            other_label = lw.item(row).text()
            if self._available_order_index(other_label) > target_idx:
                return row
        return lw.count()

    def _wire_search_available(self):
        le = getattr(self.ui, "lineEdit_availableSearch", None)
        if le:
            le.textChanged.connect(self._filter_available_list)

    def _filter_available_list(self, text: str):
        lw = self.ui.listWidget_available
        text_low = (text or "").lower().strip()
        for i in range(lw.count()):
            item = lw.item(i)
            item.setHidden(text_low not in item.text().lower())

    def _wire_search_selected(self):
        le = getattr(self.ui, "lineEdit_selectedSearch", None)
        if le:
            le.textChanged.connect(self._filter_selected_list)

    def _filter_selected_list(self, text: str):
        lw = self.ui.listWidget_selected
        text_low = (text or "").lower().strip()
        for i in range(lw.count()):
            item = lw.item(i)
            item.setHidden(text_low not in item.text().lower())

    def on_clear(self):
        self.ui.listWidget_selected.clear()
        self.ui.listWidget_available.clear()
        self.csv_data.clear()
