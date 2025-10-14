from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QAbstractItemView

from app.config import Config
from app.services.blender_settings import BlenderSettings
from app.services.execute_program import ExecuteProgram
from app.services.json_manager import JSONManager
from app.ui.apply_light_preset_ui import Ui_Form
from app.data.project import project_list, division_list
from app.services.csv_manager import CSVManager
from app.services.file_manager import FileManager
from app.data.blender_config import character_collection_name, lighting_plugin_key


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
        self.ui.toolButton_blender.clicked.connect(lambda: self.on_select_file("blender", "Select Blender Program"))
        self.ui.toolButton_csv.clicked.connect(
            lambda: self.on_select_file("csv", "Select CSV File"))
        self.ui.toolButton_presetBlend.clicked.connect(
            lambda: self.on_select_file("lighting_blend", "Select Lighting Preset Blend File"))
        self.ui.toolButton_presetJson.clicked.connect(
            lambda: self.on_select_file("lighting_json", "Select Lighting Preset JSON File"))
        self.ui.pushButton_buttonClear.clicked.connect(self.on_clear)
        self.ui.pushButton_buttonExecute.clicked.connect(self.on_generate)

        self._wire_search_available()
        self._wire_search_selected()

    def on_load(self):
        data = JSONManager.read_json(Config.CONFIG_PATH)
        if not data:
            return
        self.ui.lineEdit_blender.setText(data.get("blender_path", ""))
        self.ui.lineEdit_csv.setText(data.get("csv_path", ""))
        self.ui.lineEdit_presetBlend.setText(data.get("preset_blend_path", ""))
        self.ui.lineEdit_presetJson.setText(data.get("preset_json_path", ""))
        project_name = data.get("project_name", "")
        if project_name:
            index = self.ui.comboBox_project.findText(project_name)
            if index != -1:
                self.ui.comboBox_project.setCurrentIndex(index)

    def on_save(self):
        data = {
            "blender_path": self.ui.lineEdit_blender.text(),
            "csv_path": self.ui.lineEdit_csv.text(),
            "preset_blend_path": self.ui.lineEdit_presetBlend.text(),
            "preset_json_path": self.ui.lineEdit_presetJson.text(),
            "project_name": self.ui.comboBox_project.currentText()
        }
        JSONManager.write_json(Config.CONFIG_PATH, data)

    def on_select_file(self, file_type: str, message: str):
        file_path, _ = QFileDialog.getOpenFileName(self, message, "", "All Files (*)")
        if file_path:
            if file_type == "csv":
                self.ui.lineEdit_csv.setText(file_path)
            elif file_type == "blender":
                self.ui.lineEdit_blender.setText(file_path)
            elif file_type == "lighting_blend":
                self.ui.lineEdit_presetBlend.setText(file_path)
            elif file_type == "lighting_json":
                self.ui.lineEdit_presetJson.setText(file_path)

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

    def on_generate(self):
        project_data = next((p for p in project_list if p[1] == self.ui.comboBox_project.currentText()), None)
        if not project_data:
            QMessageBox.warning(self, "Error", "No project selected")
            return

        project_production_path = FileManager().get_project_path(project_data[0])

        # Get Blender executable path
        blender_executable = self.ui.lineEdit_blender.text()
        if not blender_executable or not FileManager().combine_paths(blender_executable).exists:
            QMessageBox.warning(self, "Error", "Blender executable path is empty.")
            return

        for index in range(self.ui.listWidget_selected.count()):
            shot_file = self.ui.listWidget_selected.item(index).text()
            print(f"Generating for shot file: {shot_file}")

            for row in self.csv_data:
                ep, seq, shot, start_frame, end_frame = row[0].lower(), row[1].lower(), row[2].lower(), int(
                    row[3]), int(row[4])
                expected_shot_file = FileManager().generate_file_name(project_code=project_data[2], ep=ep, seq=seq,
                                                                      shot=shot,
                                                                      division=division_list[1][0], extension="blend")
                if shot_file == expected_shot_file:
                    lighting_path = FileManager().generate_shot_path(project_path=project_production_path,
                                                                     production=division_list[1][2],
                                                                     division=division_list[1][3], ep=ep, seq=seq,
                                                                     shot=shot)
                    lighting_file = FileManager().combine_paths(lighting_path, shot_file)
                    lighting_progress_dir = FileManager().combine_paths(lighting_path, "progress", mkdir=True)
                    print(f"Lighting file path: {lighting_file}")
                    next_path, nextversion, next_filename = FileManager().get_latest_version(
                        progress_dir=str(lighting_progress_dir), shot_prefix=shot_file, ext=".blend")
                    print(
                        f"Next version path: {next_path}, next version: {nextversion}, next filename: {next_filename}")

                    apply_preset_script = BlenderSettings.generate_apply_preset_script(
                        master_file=str(shot_file),
                        character_collection=character_collection_name,
                        output_path=str(lighting_file),
                        output_path_progress=str(next_path),
                        blend_preset_filepath=str(self.ui.lineEdit_presetBlend.text()),
                        json_preset_filepath=str(self.ui.lineEdit_presetJson.text()),
                        lighting_plugin_key=lighting_plugin_key
                    )

                    execute_blender = ExecuteProgram().blender_execute(blender_path=str(blender_executable),
                                                                       script=apply_preset_script)

                    if execute_blender:
                        print(f"Successfully applied lighting preset to {shot_file}")
                    else:
                        print(f"Failed to apply lighting preset to {shot_file}")
                        QMessageBox.warning(self, "Error", "Failed to apply lighting preset to {shot_file}")
                    break

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
        self.ui.lineEdit_availableSearch.clear()
        self.ui.lineEdit_selectedSearch.clear()
        self.csv_data = None
