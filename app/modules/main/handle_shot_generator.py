from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QAbstractItemView

from app.config import Config
from app.services.execute_program import ExecuteProgram
from app.services.json_manager import JSONManager
from app.ui.shot_generator_widget_ui import Ui_Form
from app.data.project import project_list, division_list
from app.data.blender_config import collection_list, camera_collection_name, scene_name, cryptomatte_node, \
    character_collection_name, output_node, lighting_plugin_key
from app.services.csv_manager import CSVManager
from app.services.file_manager import FileManager
from app.services.blender_settings import BlenderSettings


class ShotGeneratorHandler(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.ui.toolButton_csv.clicked.connect(lambda: self.on_select_file("csv", "Select CSV File"))
        self.ui.toolButton_blender.clicked.connect(lambda: self.on_select_file("blender", "Select Blender Program"))
        self.ui.pushButton_generate_scan.clicked.connect(self.on_scan_files)
        self.ui.toolButton_mastershot.clicked.connect(
            lambda: self.on_select_file("mastershot", "Select Mastershot File"))
        for project in project_list:
            self.ui.comboBox_project.addItem(project[1])
        self.ui.listWidget_available.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.ui.listWidget_available.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.listWidget_selected.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.ui.listWidget_selected.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.pushButton_listControl_add.clicked.connect(self.on_move_available_item)
        self.ui.pushButton_listControl_remove.clicked.connect(self.on_move_selected_item)
        self.ui.pushButton_generate.clicked.connect(self.on_generate)
        self.ui.pushButton_generate_clear.clicked.connect(self.on_clear)
        self.ui.lineEdit_lightingPresetBlend.setEnabled(False)
        self.ui.lineEdit_lightingPresetJson.setEnabled(False)
        self.ui.toolButton_lightingPresetBlend.setEnabled(False)
        self.ui.toolButton_lightingPresetJson.setEnabled(False)
        self.ui.toolButton_lightingPresetBlend.clicked.connect(
            lambda: self.on_select_file("lighting_blend", "Select Lighting Preset Blend File"))
        self.ui.toolButton_lightingPresetJson.clicked.connect(
            lambda: self.on_select_file("lighting_json", "Select Lighting Preset JSON File"))
        self.ui.checkBox_lightingApply.clicked.connect(self.on_lighting_preset_toggle)
        self.ui.lineEdit_lightingPresetBlend.setText(
            "/mnt/J/03_post_production/01_lighting/preset_lighting/lighting_setup/lighting_setup.blend")

        self.csv_data = None

        self.on_load()

    def on_load(self):
        data = JSONManager.read_json(Config.CONFIG_PATH)
        if 'shot_generator' in data:
            sg_data = data['shot_generator']
            self.ui.lineEdit_csv.setText(sg_data.get('csv_path', ''))
            self.ui.lineEdit_blender.setText(sg_data.get('blender_path', ''))
            self.ui.lineEdit_mastershot.setText(sg_data.get('mastershot_path', ''))
            project = sg_data.get('project', '')
            index = self.ui.comboBox_project.findText(project)
            if index != -1:
                self.ui.comboBox_project.setCurrentIndex(index)
            method_link = sg_data.get('method_link', True)
            method_append = sg_data.get('method_append', False)
            if method_link:
                self.ui.radioButton_methodLink.setChecked(True)
            elif method_append:
                self.ui.radioButton_methodAppend.setChecked(True)
            lighting_apply = sg_data.get('lighting_preset_apply', False)
            self.ui.checkBox_lightingApply.setChecked(lighting_apply)
            self.ui.lineEdit_lightingPresetBlend.setText(sg_data.get('lighting_preset_blend', ''))
            self.ui.lineEdit_lightingPresetJson.setText(sg_data.get('lighting_preset_json', ''))
            self.on_lighting_preset_toggle()  # Update UI based on checkbox state

    def on_save(self):
        print("Saving…")
        data = {}
        data['shot_generator'] = {
            'csv_path': self.ui.lineEdit_csv.text(),
            'blender_path': self.ui.lineEdit_blender.text(),
            'mastershot_path': self.ui.lineEdit_mastershot.text(),
            'project': self.ui.comboBox_project.currentText(),
            'method_link': self.ui.radioButton_methodLink.isChecked(),
            'method_append': self.ui.radioButton_methodAppend.isChecked(),
            'lighting_preset_apply': self.ui.checkBox_lightingApply.isChecked(),
            'lighting_preset_blend': self.ui.lineEdit_lightingPresetBlend.text(),
            'lighting_preset_json': self.ui.lineEdit_lightingPresetJson.text(),
        }
        JSONManager.write_json(Config.CONFIG_PATH, data)

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

    def on_select_file(self, file_type: str, message: str):
        file_path, _ = QFileDialog.getOpenFileName(self, message, "", "All Files (*)")
        if file_path:
            if file_type == "csv":
                self.ui.lineEdit_csv.setText(file_path)
            elif file_type == "blender":
                self.ui.lineEdit_blender.setText(file_path)
            elif file_type == "mastershot":
                self.ui.lineEdit_mastershot.setText(file_path)
            elif file_type == "lighting_blend":
                self.ui.lineEdit_lightingPresetBlend.setText(file_path)
            elif file_type == "lighting_json":
                self.ui.lineEdit_lightingPresetJson.setText(file_path)

    def on_move_available_item(self):
        for item in self.ui.listWidget_available.selectedItems():
            self.ui.listWidget_selected.addItem(item.text())
            self.ui.listWidget_available.takeItem(self.ui.listWidget_available.row(item))

    def on_move_selected_item(self):
        for item in self.ui.listWidget_selected.selectedItems():
            self.ui.listWidget_available.addItem(item.text())
            self.ui.listWidget_selected.takeItem(self.ui.listWidget_selected.row(item))

    def on_lighting_preset_toggle(self):
        if self.ui.checkBox_lightingApply.isChecked():
            self.ui.lineEdit_lightingPresetBlend.setEnabled(True)
            self.ui.lineEdit_lightingPresetJson.setEnabled(True)
            self.ui.toolButton_lightingPresetBlend.setEnabled(True)
            self.ui.toolButton_lightingPresetJson.setEnabled(True)
        else:
            self.ui.lineEdit_lightingPresetBlend.setEnabled(False)
            self.ui.lineEdit_lightingPresetJson.setEnabled(False)
            self.ui.toolButton_lightingPresetBlend.setEnabled(False)
            self.ui.toolButton_lightingPresetJson.setEnabled(False)

    def on_generate(self):
        project_data = next((p for p in project_list if p[1] == self.ui.comboBox_project.currentText()), None)
        if not project_data:
            QMessageBox.warning(self, "Error", "No project selected")
            return

        # Get radio button
        if self.ui.radioButton_methodLink.isChecked():
            link = True
        elif self.ui.radioButton_methodAppend.isChecked():
            link = False
        else:
            QMessageBox.warning(self, "Error", "No method selected")
            return

        # Get project path
        project_production_path = FileManager().get_project_path(project_data[0])
        project_output_path = FileManager().get_project_path(project_data[-1])

        # Get mastershot file path
        mastershot_path = self.ui.lineEdit_mastershot.text()
        if not mastershot_path or not FileManager().combine_paths(mastershot_path).exists():
            QMessageBox.warning(self, "Error", "Mastershot file path is empty.")
            return

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
                    print(f"Match found in CSV for shot file: {shot_file} with frames {start_frame}-{end_frame}")

                    # Get animation file
                    animation_path = FileManager().generate_shot_path(project_path=project_production_path,
                                                                      production=division_list[0][2],
                                                                      division=division_list[0][3], ep=ep, seq=seq,
                                                                      shot=shot)
                    animation_name = FileManager().generate_file_name(project_code=project_data[2], ep=ep, seq=seq,
                                                                      shot=shot,
                                                                      division=division_list[0][0], extension="blend")
                    animation_file = FileManager().combine_paths(animation_path, animation_name)

                    # Check if animation file exists
                    if not animation_file.exists():
                        reply = QMessageBox.question(
                            self,
                            "Animation File Missing",
                            "Animation file not found. Do you want to skip anyway?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.No
                        )

                        if reply == QMessageBox.StandardButton.No:
                            return
                        else:
                            break

                    # Generate lighting path
                    lighting_path = FileManager().generate_shot_path(project_path=project_production_path,
                                                                     production=division_list[1][2],
                                                                     division=division_list[1][3], ep=ep, seq=seq,
                                                                     shot=shot)
                    lighting_file = FileManager().combine_paths(lighting_path, shot_file)
                    lighting_progress_dir = FileManager().combine_paths(lighting_path, "progress", mkdir=True)
                    versioned_name = FileManager().add_version_to_filename(shot_file, version=0)
                    lighting_progress_file = FileManager().combine_paths(str(lighting_progress_dir), versioned_name)

                    print(lighting_progress_dir)
                    print(lighting_file)
                    print(lighting_progress_file)
                    output_node_data = []
                    comp_path, comp_filename = FileManager().generate_png_comp(
                        project_code=project_data[2],
                        project_path=project_output_path,
                        ep=ep,
                        seq=seq,
                        shot=shot,
                        file_type="png",
                        export_type="comp"
                    )
                    preview_path, preview_filename = FileManager().generate_png_comp(
                        project_code=project_data[2],
                        project_path=project_output_path,
                        ep=ep,
                        seq=seq,
                        shot=shot,
                        file_type="png",
                        export_type="preview"
                    )
                    output_node_data.append((output_node[0], comp_path, comp_filename))
                    output_node_data.append((output_node[1], preview_path, preview_filename))

                    lighting_script = BlenderSettings.generate_lighting_script(
                        master_file=str(mastershot_path),
                        animation_file=str(animation_file),
                        collection_list=collection_list,
                        camera_collection=camera_collection_name,
                        character_collection=character_collection_name,
                        start_frame=start_frame,
                        end_frame=end_frame,
                        output_path=str(lighting_file),
                        output_path_progress=str(lighting_progress_file),
                        scene_name=scene_name,
                        crypto_node=cryptomatte_node,
                        output_node=output_node_data,
                        method=link
                    )

                    lighting_script_with_preset = BlenderSettings.generate_lighting_with_light_script(
                        master_file=str(mastershot_path),
                        animation_file=str(animation_file),
                        collection_list=collection_list,
                        camera_collection=camera_collection_name,
                        character_collection=character_collection_name,
                        start_frame=start_frame,
                        end_frame=end_frame,
                        output_path=str(lighting_file),
                        output_path_progress=str(lighting_progress_file),
                        scene_name=scene_name,
                        crypto_node=cryptomatte_node,
                        output_node=output_node_data,
                        method=link,
                        blend_preset_filepath=str(self.ui.lineEdit_lightingPresetBlend.text()),
                        json_preset_filepath=str(self.ui.lineEdit_lightingPresetJson.text()),
                        lighting_plugin_key=lighting_plugin_key
                    )

                    if self.ui.checkBox_lightingApply.isChecked():
                        execute_blender = ExecuteProgram().blender_execute(blender_path=blender_executable,
                                                                           script=lighting_script_with_preset)
                    else:
                        execute_blender = ExecuteProgram().blender_execute(blender_path=blender_executable,
                                                                           script=lighting_script)

                    if execute_blender:
                        print(f"Blender process for {shot_file} completed successfully.")
                    else:
                        print(f"Blender process for {shot_file} failed.")
                        QMessageBox.critical(self, "Error", f"Failed to generate lighting file for: {shot_file}")
                    break
        QMessageBox.information(self, "Success", "Successfully generated lighting file")

    def on_clear(self):
        self.ui.listWidget_selected.clear()
        self.ui.listWidget_available.clear()
        self.csv_data.clear()

    def closeEvent(self, event):
        # This method is called when the window is closed
        self.on_save()
        event.accept()
