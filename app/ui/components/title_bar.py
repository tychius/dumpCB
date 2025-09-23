# app/ui/components/title_bar.py
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QApplication, QStyle, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMouseEvent, QIcon

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(35)
        self.setObjectName("titleBarWidget")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0)
        layout.setSpacing(0)

        # App icon and title (kept subtle for professional look)
        self.app_icon = QLabel()
        self.app_icon.setObjectName("appIconLabel")
        self.app_icon.setPixmap(QIcon(":/logo.ico").pixmap(QSize(16, 16)))
        self.app_icon.setFixedSize(20, 20)
        layout.addWidget(self.app_icon)

        self.title = QLabel("dumpCB")
        self.title.setObjectName("windowTitleLabel")
        self.title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title)
        layout.setStretchFactor(self.title, 1)
        
        # Add stretch to push buttons to the right
        layout.addStretch(1)

        # --- Control Buttons (Using Standard Icons) --- 
        style = QApplication.style()
        button_size = 30 # Adjusted size slightly for standard icons

        self.min_btn = QPushButton()
        self.min_btn.setObjectName("minimizeButton")
        self.min_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.min_btn.setFixedSize(button_size, button_size) # Use variable
        self.min_btn.setToolTip("Minimize")
        self.min_btn.clicked.connect(self.on_minimize)
        layout.addWidget(self.min_btn)
        layout.setAlignment(self.min_btn, Qt.AlignmentFlag.AlignVCenter)

        self.max_btn = QPushButton()
        self.max_btn.setObjectName("maximizeButton")
        self.update_maximize_icon() # Use standard icons
        self.max_btn.setFixedSize(button_size, button_size) # Use variable
        self.max_btn.setCheckable(True)
        self.max_btn.setToolTip("Maximize")
        self.max_btn.clicked.connect(self.on_maximize_restore)
        layout.addWidget(self.max_btn)
        layout.setAlignment(self.max_btn, Qt.AlignmentFlag.AlignVCenter)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_btn.setFixedSize(button_size, button_size) # Use variable
        self.close_btn.setToolTip("Close")
        self.close_btn.clicked.connect(self.on_close)
        layout.addWidget(self.close_btn)
        layout.setAlignment(self.close_btn, Qt.AlignmentFlag.AlignVCenter)

        self._mouse_pressed = False
        self._mouse_pos = None

    def update_maximize_icon(self):
        # Use standard icons
        style = QApplication.style()
        if self.parent_window and self.parent_window.isMaximized():
            self.max_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
            self.max_btn.setToolTip("Restore")
        else:
            self.max_btn.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
            self.max_btn.setToolTip("Maximize")
    
    # on_minimize, on_maximize_restore, on_close remain the same
    # ... existing code ...
    def on_minimize(self):
        if self.parent_window:
            self.parent_window.showMinimized()

    def on_maximize_restore(self):
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
            else:
                self.parent_window.showMaximized()
            # Update icon after state change
            self.update_maximize_icon()

    def on_close(self):
        if self.parent_window:
            self.parent_window.close()

    # --- Allow dragging the window --- 
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = True
            self._mouse_pos = event.globalPosition().toPoint() - self.parent_window.pos()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._mouse_pressed and self._mouse_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._mouse_pos
            self.parent_window.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_pressed = False
            self._mouse_pos = None
            event.accept()
            
    # Handle double-click to maximize/restore
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_maximize_restore()
            event.accept() 