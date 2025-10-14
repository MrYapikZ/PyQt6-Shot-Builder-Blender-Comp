from PyQt6.QtWidgets import QWidget, QFileDialog, QMessageBox, QAbstractItemView

from app.ui.apply_light_preset_ui import Ui_Form

class ApplyLightPresetHandler(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)