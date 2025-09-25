import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from app.ui.main_widget_ui import Ui_MainWindow
from app.modules.main.handle_shot_generator import ShotGeneratorHandler

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Shot Builder Blend Comp")
        self.ui.label_version.setText("v0.1.2")

        self.ui.tabWidget_main.addTab(ShotGeneratorHandler(), "Shot Generator")
        # Additional UI setup can be done here

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec())

# pyinstaller --clean --noconsole --onefile -n ShotBuilderBlendComp -p . --collect-submodules app app/main.py
