from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from typing import Optional

from app.ui.utils.window_geometry_helper import calculate_resize_area, calculate_new_geometry

class FramelessWindowMixin:
    """
    Provides frameless window behavior, enabling dragging and resizing.

    This mixin overrides mouse press, move, and release events to detect
    when the user is clicking on the title bar area (for dragging) or near
    the window edges (for resizing). It assumes the class using this mixin
    has a `title_bar_widget` attribute that defines the draggable region
    and standard QWidget methods like `geometry()`, `frameGeometry()`,
    `setGeometry()`, `move()`, `rect()`, and `setCursor()`.
    """
    resize_margin = 8  # Pixels from edge to trigger resize
    resizing = False
    resize_direction: Optional[str] = None
    drag_position: Optional[QPoint] = None # Use QPoint instead of Any

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse press events to initiate dragging or resizing.

        Checks if the press occurred in a resize margin or the title bar.
        Sets internal state (`resizing`, `resize_direction`, `drag_position`)
        accordingly. Passes the event to the superclass if not handled here.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Use helper function to check resize area
            resize_area = calculate_resize_area(event.position().toPoint(), self.rect(), self.resize_margin) # type: ignore[attr-defined]
            if resize_area:
                self.resizing = True
                self.resize_direction = resize_area
                self.drag_position = event.globalPosition().toPoint()
                event.accept()
                return
            if self.title_bar_widget.geometry().contains(event.position().toPoint()): # type: ignore[attr-defined]
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft() # type: ignore[attr-defined]
                event.accept()
            else:
                self.drag_position = None
                super_fn = getattr(super(), 'mousePressEvent', None)
                if super_fn:
                    super_fn(event)
        else:
            super_fn = getattr(super(), 'mousePressEvent', None)
            if super_fn:
                super_fn(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse move events for dragging or resizing the window.

        If resizing, calculates the new geometry based on mouse movement and
        resize direction.
        If dragging (not resizing), moves the window based on mouse movement.
        Updates the mouse cursor based on position (resize handles or arrow).
        Passes the event to the superclass if not handled here.
        """
        if self.resizing and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint()
            diff = new_pos - self.drag_position
            self.drag_position = new_pos
            geo = self.geometry() # type: ignore[attr-defined]
            if self.resize_direction:
                # Use helper function to calculate new geometry
                new_geo = calculate_new_geometry(geo, diff, self.resize_direction)
                self.setGeometry(new_geo) # type: ignore[attr-defined]
                event.accept()
                return
            else:
                # This case shouldn't happen if self.resizing is True, but handle defensively
                pass
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        # Use helper function to check resize area for cursor update
        resize_area = calculate_resize_area(pos, self.rect(), self.resize_margin) # type: ignore[attr-defined]
        if resize_area:
            if resize_area == "top-left" or resize_area == "bottom-right":
                self.setCursor(Qt.CursorShape.SizeFDiagCursor) # type: ignore[attr-defined]
            elif resize_area == "top-right" or resize_area == "bottom-left":
                self.setCursor(Qt.CursorShape.SizeBDiagCursor) # type: ignore[attr-defined]
            elif resize_area == "left" or resize_area == "right":
                self.setCursor(Qt.CursorShape.SizeHorCursor) # type: ignore[attr-defined]
            elif resize_area == "top" or resize_area == "bottom":
                self.setCursor(Qt.CursorShape.SizeVerCursor) # type: ignore[attr-defined]
            return
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor) # type: ignore[attr-defined]
        if hasattr(event, 'buttons') and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None and not self.resizing:
            self.move(event.globalPosition().toPoint() - self.drag_position) # type: ignore[attr-defined]
            event.accept()
            return
        if hasattr(event, 'ignore'):
            event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse release events to finalize dragging or resizing.

        Resets the internal state (`resizing`, `resize_direction`, `drag_position`)
        when the left mouse button is released after a drag or resize operation.
        Passes the event to the superclass if not handled here.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_direction = None
                event.accept()
                return
            if self.drag_position is not None:
                self.drag_position = None
                event.accept()
                return
        super_fn = getattr(super(), 'mouseReleaseEvent', None)
        if super_fn:
            super_fn(event)

    # Removed _get_resize_area as it's now in the helper module 