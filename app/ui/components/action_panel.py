# app/ui/components/action_panel.py
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal

class ActionPanel(QWidget):
    # Define signals for actions
    select_all_clicked = Signal()
    deselect_all_clicked = Signal()
    generate_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.select_all    = QPushButton("Select All Files")
        self.select_all.setObjectName("selectAllButton")
        self.deselect_all  = QPushButton("Deselect All")
        self.deselect_all.setObjectName("deselectAllButton")
        self.generate      = QPushButton("Generate Context")
        self.generate.setObjectName("generateButton")

        layout.addWidget(self.select_all)
        layout.addWidget(self.deselect_all)
        layout.addStretch()
        layout.addWidget(self.generate)

        # Connect internal button clicks to signals
        self.select_all.clicked.connect(self.select_all_clicked)
        self.deselect_all.clicked.connect(self.deselect_all_clicked)
        self.generate.clicked.connect(self.generate_clicked)

    def set_enabled_state(self, enabled: bool):
        """Enable or disable all buttons in the panel."""
        self.select_all.setEnabled(enabled)
        self.deselect_all.setEnabled(enabled)
        self.generate.setEnabled(enabled) 