# app/ui/components/folder_selector.py
from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QHBoxLayout
from PySide6.QtCore import Signal, Slot

class FolderSelector(QWidget):
    # Signal emitted when a folder is selected, carrying the folder path (str)
    folder_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # No margins for this component

        self.select_btn = QPushButton("Select Project Folder")
        self.select_btn.setObjectName("selectFolderButton")
        self.path_label = QLabel("No folder selected")
        self.path_label.setObjectName("pathLabel")
        self.path_label.setWordWrap(True)

        layout.addWidget(self.select_btn)
        layout.addWidget(self.path_label, 1) # Label takes remaining space

        # The actual folder dialog logic should be connected in the main window
        # self.select_btn.clicked.connect(self.open_folder_dialog)

    # Slot to update the label externally
    @Slot(str)
    def set_selected_folder(self, folder_path: str):
        if folder_path:
            self.path_label.setText(folder_path)
            self.path_label.setToolTip(folder_path) # Show full path on hover
        else:
            self.path_label.setText("No folder selected")
            self.path_label.setToolTip("") 