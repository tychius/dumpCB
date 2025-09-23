from typing import Optional
from PySide6.QtCore import QPoint, QRect

MIN_WIDTH = 600
MIN_HEIGHT = 400

def calculate_resize_area(pos: QPoint, rect: QRect, margin: int) -> Optional[str]:
    """
    Determines if the mouse position is within a resize margin.

    Args:
        pos: The current mouse position within the widget coordinates.
        rect: The widget's current rectangle.
        margin: The pixel margin from the edge to trigger resize.

    Returns:
        A string indicating the resize area ('top', 'bottom-left', etc.)
        or None if the position is not in a resize margin.
    """
    top = pos.y() <= margin
    bottom = pos.y() >= rect.height() - margin
    left = pos.x() <= margin
    right = pos.x() >= rect.width() - margin

    if top and left: return "top-left"
    if top and right: return "top-right"
    if bottom and left: return "bottom-left"
    if bottom and right: return "bottom-right"
    if top: return "top"
    if bottom: return "bottom"
    if left: return "left"
    if right: return "right"
    return None

def calculate_new_geometry(
    current_geometry: QRect,
    drag_diff: QPoint,
    resize_direction: str,
    min_width: int = MIN_WIDTH,
    min_height: int = MIN_HEIGHT
) -> QRect:
    """
    Calculates the new window geometry based on mouse movement during resize.

    Args:
        current_geometry: The current window geometry (QRect).
        drag_diff: The difference in mouse position since the last move event (QPoint).
        resize_direction: The direction(s) of resize (e.g., 'top', 'bottom-right').
        min_width: The minimum allowed window width.
        min_height: The minimum allowed window height.

    Returns:
        The calculated new QRect for the window.
    """
    new_geo = QRect(current_geometry) # Create a copy

    if 'left' in resize_direction:
        new_geo.setLeft(new_geo.left() + drag_diff.x())
    if 'right' in resize_direction:
        new_geo.setRight(new_geo.right() + drag_diff.x())
    if 'top' in resize_direction:
        new_geo.setTop(new_geo.top() + drag_diff.y())
    if 'bottom' in resize_direction:
        new_geo.setBottom(new_geo.bottom() + drag_diff.y())

    # Enforce minimum size constraints
    if new_geo.width() < min_width:
        if 'left' in resize_direction:
            new_geo.setLeft(new_geo.right() - min_width)
        else: # 'right' or corners involving right
            new_geo.setRight(new_geo.left() + min_width)

    if new_geo.height() < min_height:
        if 'top' in resize_direction:
            new_geo.setTop(new_geo.bottom() - min_height)
        else: # 'bottom' or corners involving bottom
            new_geo.setBottom(new_geo.top() + min_height)
            
    return new_geo 