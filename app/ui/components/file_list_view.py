# app/ui/components/file_list_view.py
from PySide6.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QFrame,
    QTreeView,
    QAbstractItemView,
    QHeaderView,
    QMenu,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QIcon, QFont
from PySide6.QtCore import Qt, Signal
from pathlib import Path
from typing import List, Set, Tuple, Dict, Optional

class FileListView(QWidget):
    # Signal emitted when the selection changes (e.g., a checkbox is toggled)
    selection_changed = Signal()
    # Signal emitted with the total token estimate of currently selected files
    total_token_estimate_changed = Signal(int)
    # Signal emitted when user requests an explanation for an ignored entry
    # Use object for broad PySide compatibility with Python objects
    ignored_context_requested = Signal(object)

    # Constants for custom data roles
    PATH_ROLE = Qt.ItemDataRole.UserRole + 1
    TOKEN_ROLE = Qt.ItemDataRole.UserRole + 2
    IS_DIR_ROLE = Qt.ItemDataRole.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileListView") # For styling parent widget if needed

        # Main layout for this widget
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("fileListScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Use QTreeView instead of manual checkboxes
        self.tree_view = QTreeView(self.scroll)
        self.tree_view.setObjectName("fileListTreeView")
        self.tree_view.setHeaderHidden(False) # show header for name/tokens
        # Disable visual row selection, use checkboxes only
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        # Disable focus rectangle
        self.tree_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Improve spacing and visual hierarchy
        self.tree_view.setIndentation(12)  # Reduce indentation so checkboxes are closer to the edge
        self.tree_view.setRootIsDecorated(True)  # Show expand/collapse indicators
        self.scroll.setWidget(self.tree_view)
        # Flat background without zebra striping for a cleaner look
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setIndentation(18)
        # Context menu for directory bulk actions
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._on_context_menu_requested)

        self.main_layout.addWidget(self.scroll)

        self._all_paths: List[Path] = []
        self.model: Optional[QStandardItemModel] = None
        self._processing_change = False # Flag to prevent recursion in _handle_item_changed

        # Context menu provides expand/collapse options

    def _build_tree_model(self, file_data: List[Tuple[Path, int]], checked_paths: Set[Path], ignored_paths: Set[Path]) -> QStandardItemModel:
        """Builds the QStandardItemModel for the tree view."""
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Tokens"])
        root_node = model.invisibleRootItem()
        nodes: Dict[Path, QStandardItem] = {} # Store directory items

        # Sort file data for consistent tree structure
        file_data.sort(key=lambda x: x[0])

        for p, tokens in file_data:
            path_str = p.as_posix()
            parts = p.parts
            parent_item = root_node
            current_path = Path()

            # Create directory items
            for i, part in enumerate(parts[:-1]):
                current_path = current_path / part
                if current_path not in nodes:
                    # Directory item (column 1) with standard folder icon
                    dir_item = QStandardItem(part)
                    dir_item.setEditable(False)
                    dir_item.setCheckable(True)
                    dir_item.setCheckState(Qt.CheckState.Unchecked)
                    dir_item.setData(current_path, self.PATH_ROLE)
                    dir_item.setData(True, self.IS_DIR_ROLE)
                    dir_item.setIcon(QIcon(":/icons/folder.svg"))
                    # Bold folder names
                    bold = QFont()
                    bold.setBold(True)
                    dir_item.setFont(bold)
                    # Token column blank for directories
                    dir_token = QStandardItem("")
                    dir_token.setEditable(False)
                    parent_item.appendRow(dir_item)
                    # Ensure a second column exists for directories
                    parent_item.setChild(dir_item.row(), 1, dir_token)
                    nodes[current_path] = dir_item
                    # Check if this directory path itself is ignored
                    if current_path in ignored_paths:
                        dir_item.setEnabled(False)
                        dir_item.setCheckState(Qt.CheckState.Unchecked) # Ensure ignored folders are unchecked
                else:
                    # Handle case where a directory might be listed explicitly in ignored_paths
                    # even if encountered before via a file within it.
                    if current_path in ignored_paths and nodes[current_path].isEnabled():
                        nodes[current_path].setEnabled(False)
                        nodes[current_path].setCheckState(Qt.CheckState.Unchecked)

                parent_item = nodes[current_path]
                # If parent is disabled, this item should also be disabled
                if not parent_item.isEnabled():
                    nodes[current_path].setEnabled(False)


            # Create file item
            file_part = parts[-1]
            # Column 1: name with file icon
            file_item = QStandardItem(file_part)
            file_item.setEditable(False)
            file_item.setCheckable(True)
            file_item.setData(p, self.PATH_ROLE)
            file_item.setData(tokens, self.TOKEN_ROLE)
            file_item.setData(False, self.IS_DIR_ROLE)
            file_item.setIcon(QIcon(":/icons/file.svg"))

            # Column 2: token count, right-aligned
            token_item = QStandardItem(f"{tokens:,}" if tokens > 0 else "")
            token_item.setEditable(False)
            token_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Muted foreground for tokens
            token_item.setForeground(QColor("#888A90"))

            # Determine if the item should be enabled
            is_explicitly_ignored = p in ignored_paths
            # Root items parent is the invisibleRootItem, which is always enabled.
            # For non-root items, check if their actual parent item is enabled.
            parent_is_disabled = parent_item != root_node and not parent_item.isEnabled()
            is_enabled = not is_explicitly_ignored and not parent_is_disabled

            file_item.setEnabled(is_enabled)

            # Set check state based on whether it's enabled and in checked_paths
            if is_enabled:
                if p in checked_paths:
                    file_item.setCheckState(Qt.CheckState.Checked)
                else:
                    file_item.setCheckState(Qt.CheckState.Unchecked)
                file_item.setToolTip(path_str) # Show full path on hover
            else:
                # Ensure disabled items are always unchecked and have default background
                file_item.setCheckState(Qt.CheckState.Unchecked)

            parent_item.appendRow([file_item, token_item])

        # Update parent check states after all items are added
        self._update_all_parent_states(model)

        return model

    def _update_all_parent_states(self, model: QStandardItemModel):
        """Iterates through all directory items and sets their initial check state based on children."""
        root = model.invisibleRootItem()
        for row in range(root.rowCount()):
            self._update_parent_state_recursive(model, root.child(row))

    def _update_parent_state_recursive(self, model: QStandardItemModel, item: QStandardItem):
        """Recursively update parent states from bottom up."""
        if item and item.data(self.IS_DIR_ROLE):
            # First, ensure all children states are updated
            for r in range(item.rowCount()):
                self._update_parent_state_recursive(model, item.child(r))
            # Now update this item's state based on children
            self._update_parent_check_state(model, item)


    def populate(self, file_data: List[Tuple[Path, int]], checked_paths: Set[Path], ignored_paths: Set[Path]):
        """
        Populates the tree view with files and their token estimates.

        Args:
            file_data: List of tuples, each containing (relative_path, token_estimate).
            checked_paths: Set of paths that should be initially checked.
            ignored_paths: Set of paths that should be disabled (ignored).
        """
        if self.model:
            # Disconnect old model signals to prevent issues
            try:
                self.model.itemChanged.disconnect(self._handle_item_changed)
            except (TypeError, RuntimeError): # Catch if already disconnected or error
                pass

        # Store all paths for get_all_paths() compatibility - consider removing if not needed
        self._all_paths = sorted([p for p, _ in file_data])

        # Build the new model
        self.model = self._build_tree_model(file_data, checked_paths, ignored_paths)

        # Set the model on the tree view
        self.tree_view.setModel(self.model)
        header = self.tree_view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        # Right-align header text for Tokens
        self.model.setHeaderData(1, Qt.Orientation.Horizontal, Qt.AlignmentFlag.AlignRight, Qt.ItemDataRole.TextAlignmentRole)

        # Connect signal for the new model
        self.model.itemChanged.connect(self._handle_item_changed)

        # Expand top-level items for better visibility initially
        self.tree_view.expandToDepth(1)  # Expand first two levels for better overview
        # self.tree_view.expandAll() # Or expand all initially

        # Update totals and emit signals once after initial population
        self._update_totals_and_emit()

    def _handle_item_changed(self, item: QStandardItem):
        """Handles changes in item check state and propagates them."""
        if not self.model or self._processing_change:
            return # Avoid recursion or handling signals during setup/teardown

        self._processing_change = True # Block recursive signals
        try:
            # Ignore changes from token column
            if item and not item.isCheckable():
                return

            state = item.checkState()
            is_dir = item.data(self.IS_DIR_ROLE)

            if is_dir:
                # Propagate state to enabled descendants
                self._propagate_state_to_children(item, state)

            parent = item.parent()
            if parent:
                self._update_parent_check_state(self.model, parent)
                ancestor = parent.parent()
                while ancestor:
                    self._update_parent_check_state(self.model, ancestor)
                    ancestor = ancestor.parent()

            # 3. Update visuals and totals
            self._apply_row_background_recursive(item)
            self._update_totals_and_emit()
        finally:
            self._processing_change = False # Unblock signals

    def _set_row_background(self, item: QStandardItem, color: Optional[QColor]) -> None:
        """Apply background color to both columns of the item's row."""
        if not self.model or item is None:
            return
        parent = item.parent()
        row = item.row()
        # Column 0 is item itself; column 1 is sibling in same row
        if color is None:
            # Reset
            item.setBackground(QColor())
            if parent:
                sibling = parent.child(row, 1)
            else:
                sibling = self.model.invisibleRootItem().child(row, 1)
            if sibling:
                sibling.setBackground(QColor())
            return
        item.setBackground(color)
        if parent:
            sibling = parent.child(row, 1)
        else:
            sibling = self.model.invisibleRootItem().child(row, 1)
        if sibling:
            sibling.setBackground(color)

    def _apply_row_background_recursive(self, item: QStandardItem) -> None:
        """Set subtle backgrounds for checked/partially-checked states (modern visual cue)."""
        if not self.model or item is None:
            return
        is_dir = bool(item.data(self.IS_DIR_ROLE))
        if item.isEnabled():
            if item.checkState() == Qt.CheckState.Checked and not is_dir:
                self._set_row_background(item, QColor("#1F232B"))  # checked file
            elif item.checkState() == Qt.CheckState.PartiallyChecked and not is_dir:
                self._set_row_background(item, QColor("#181C22"))  # partial
            else:
                self._set_row_background(item, None)
        else:
            self._set_row_background(item, None)
        # Children
        for r in range(item.rowCount()):
            child = item.child(r)
            if child:
                self._apply_row_background_recursive(child)

    def _on_context_menu_requested(self, pos):
        if not self.model:
            return
        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return
        item = self.model.itemFromIndex(index)
        if not item:
            return

        path = item.data(self.PATH_ROLE)
        is_dir = bool(item.data(self.IS_DIR_ROLE))
        is_enabled = item.isEnabled()

        menu = QMenu(self)
        explain_action = None

        if not is_enabled and isinstance(path, Path):
            explain_action = menu.addAction("Explain why ignored")
        elif is_dir:
            select_all = menu.addAction("Select all in folder")
            clear_all = menu.addAction("Clear selection in folder")
            menu.addSeparator()
            toggle = menu.addAction("Collapse" if self.tree_view.isExpanded(index) else "Expand")
        else:
            return

        action = menu.exec(self.tree_view.viewport().mapToGlobal(pos))
        if not action:
            return

        if action == explain_action and isinstance(path, Path):
            self.ignored_context_requested.emit(path)
            return

        if is_dir:
            if action == select_all:
                self._set_descendants_state(item, Qt.CheckState.Checked)
            elif action == clear_all:
                self._set_descendants_state(item, Qt.CheckState.Unchecked)
            elif action == toggle:
                self.tree_view.setExpanded(index, not self.tree_view.isExpanded(index))
            self._update_totals_and_emit()

    def _set_descendants_state(self, item: QStandardItem, state: Qt.CheckState) -> None:
        """Set check state for all descendant files under a directory item."""
        stack = [item]
        while stack:
            node = stack.pop()
            for i in range(node.rowCount()):
                child = node.child(i)
                if not child or not child.isEnabled():
                    continue
                stack.append(child)
                if child.isCheckable():
                    child.setCheckState(state)
        # After bulk update, refresh parents and visuals
        if self.model:
            self._update_all_parent_states(self.model)
        self._refresh_all_row_backgrounds()

    def _propagate_state_to_children(self, item: QStandardItem, state: Qt.CheckState):
        """Recursively set the check state for all enabled children."""
        if state == Qt.CheckState.PartiallyChecked:
             # Don't propagate partial state down, it only flows up
            return
        for row in range(item.rowCount()):
            child = item.child(row)
            if child and child.isEnabled(): # Only affect enabled children
                child.setCheckState(state)
                if child.data(self.IS_DIR_ROLE): # If the child is also a directory
                    self._propagate_state_to_children(child, state) # Recurse

    def _update_parent_check_state(self, model: QStandardItemModel, parent: QStandardItem):
        """Updates a parent's check state based on its children's states."""
        if not parent or parent == model.invisibleRootItem():
            return

        if not parent.isCheckable():  # Should not happen with current logic, but safe check
            return

        checked_count = 0
        partially_checked_count = 0
        enabled_child_count = 0

        for row in range(parent.rowCount()):
            child = parent.child(row)
            if child and child.isEnabled():
                enabled_child_count += 1
                state = child.checkState()
                if state == Qt.CheckState.Checked:
                    checked_count += 1
                elif state == Qt.CheckState.PartiallyChecked:
                    partially_checked_count += 1

        new_state = Qt.CheckState.Unchecked
        if partially_checked_count > 0 or (0 < checked_count < enabled_child_count):
            new_state = Qt.CheckState.PartiallyChecked
        elif checked_count == enabled_child_count and enabled_child_count > 0:
            new_state = Qt.CheckState.Checked

        parent.setCheckState(new_state)

    def get_selected(self) -> List[Path]:
        """Returns a list of the currently selected (checked) file paths."""
        selected_paths = []
        if not self.model:
            return selected_paths

        root = self.model.invisibleRootItem()
        stack = [root.child(i) for i in range(root.rowCount())]

        while stack:
            item = stack.pop()
            if not item or not item.isEnabled():
                continue

            # Add children to stack for processing
            for i in range(item.rowCount()):
                stack.append(item.child(i))

            # Check if this item is a file and is checked
            if item.checkState() == Qt.CheckState.Checked and not item.data(self.IS_DIR_ROLE):
                path = item.data(self.PATH_ROLE)
                if path:
                    selected_paths.append(path)

        return selected_paths

    def get_all_paths(self) -> List[Path]:
        """Returns the list of all file paths originally populated."""
        # This might need adjustment if _all_paths isn't maintained reliably.
        # Alternatively, traverse the model and collect all file paths.
        return self._all_paths

    def set_selection_state(self, select_all: bool):
        """Checks or unchecks all *enabled* items in the tree."""
        if not self.model or self._processing_change:
             return

        self._processing_change = True # Block signals during bulk update
        new_state = Qt.CheckState.Checked if select_all else Qt.CheckState.Unchecked
        root = self.model.invisibleRootItem()

        stack = [root.child(i) for i in range(root.rowCount())]

        while stack:
            item = stack.pop()
            if not item or not item.isEnabled():
                continue

            # Queue children first
            for i in range(item.rowCount()):
                stack.append(item.child(i))

            if not item.isCheckable():
                continue

            current_flags = item.flags()
            item.setFlags(current_flags & ~Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(new_state)
            item.setFlags(current_flags)

        self._update_all_parent_states(self.model)
        self._refresh_all_row_backgrounds()

        self._processing_change = False # Unblock signals
        self._update_totals_and_emit() # Emit final state
        # Force a repaint to reflect checkbox changes immediately
        if self.tree_view and self.tree_view.viewport():
            self.tree_view.viewport().update()

    def _refresh_all_row_backgrounds(self) -> None:
        if not self.model:
            return
        root = self.model.invisibleRootItem()
        for i in range(root.rowCount()):
            top = root.child(i)
            if top:
                self._apply_row_background_recursive(top)

    def _update_totals_and_emit(self):
        """Calculates total tokens for selected files and emits signals."""
        current_total = 0
        if self.model:
            root = self.model.invisibleRootItem()
            stack = [root.child(i) for i in range(root.rowCount())]

            while stack:
                item = stack.pop()
                if not item or not item.isEnabled():
                    continue

                # Add children to stack
                for i in range(item.rowCount()):
                    stack.append(item.child(i))

                # Sum tokens for checked files
                if item.checkState() == Qt.CheckState.Checked and not item.data(self.IS_DIR_ROLE):
                    current_total += item.data(self.TOKEN_ROLE) or 0  # Add token count

        self.total_token_estimate_changed.emit(current_total)
        self.selection_changed.emit() # General signal that selection might have changed

    # Row background highlighting removed; no-op method retained for compatibility
    def _update_item_background(self, item: QStandardItem):
        pass
