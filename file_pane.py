# --- START OF FILE file_pane.py ---

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QFileSystemModel,
                               QMenu, QAbstractItemView, QPushButton, QStyle, QLabel)
from PySide6.QtCore import Signal, QDir, Qt, QPoint, QModelIndex, Slot # Added Slot, QModelIndex
from PySide6.QtGui import QIcon
import os

class FilePane(QWidget):
    open_files_requested = Signal(list)      # list of file paths
    explain_files_requested = Signal(list)   # list of file paths
    edit_files_requested = Signal(list)      # list of file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Start in Home Directory
        initial_path = QDir.homePath()
        print(f"[DEBUG FilePane __init__] Target initial path (Home): {initial_path}") # DEBUG

        self.model = QFileSystemModel()
        # Set model root to the absolute filesystem root ('/' on Linux)
        self.model.setRootPath(QDir.rootPath())
        print(f"[DEBUG FilePane __init__] Model root path set to: {self.model.rootPath()}") # DEBUG

        # Up Button
        self.up_button = QPushButton("  Up")
        self.up_button.setFixedHeight(30)
        # Remove the yellow background style unless needed for debugging
        # self.up_button.setStyleSheet("background-color: yellow; color: black; border: 1px solid black;")

        try:
            up_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent)
            if not up_icon.isNull():
                 self.up_button.setIcon(up_icon)
                 print("[DEBUG FilePane __init__] Successfully loaded Up button icon.") # DEBUG
            else:
                 print("[DEBUG FilePane __init__] WARNING: Could not load standard Up button icon.") # DEBUG
        except Exception as e:
             print(f"[DEBUG FilePane __init__] ERROR loading icon: {e}") # DEBUG

        self.up_button.setToolTip("Go to Parent Directory")
        self.up_button.clicked.connect(self.go_up_directory)
        layout.addWidget(self.up_button)
        print("[DEBUG FilePane __init__] Up button created, styled, and added to layout.") # DEBUG

        # Tree View
        self.tree = QTreeView()
        self.tree.setModel(self.model)

        initial_view_index = self.model.index(initial_path)
        if initial_view_index.isValid():
            print(f"[DEBUG FilePane __init__] Setting initial TREE view root index to: {self.model.filePath(initial_view_index)}") # DEBUG
            self.tree.setRootIndex(initial_view_index)
        else:
            fallback_index = self.model.index(self.model.rootPath())
            print(f"[DEBUG FilePane __init__] Home path invalid for model? Falling back TREE view root index to: {self.model.filePath(fallback_index)}") # DEBUG
            self.tree.setRootIndex(fallback_index)

        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.doubleClicked.connect(self.handle_double_click) # <<< CONNECTED doubleClicked SIGNAL >>>
        self.tree.setAnimated(True)
        self.tree.setIndentation(15)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)

        layout.addWidget(self.tree)

        # Update button state initially
        self._update_up_button_state()
        print("[DEBUG FilePane __init__] Initial button state updated.") # DEBUG

    # <<< METHOD ADDED IN PREVIOUS STEP >>>
    def get_current_view_path(self) -> str:
        """Returns the absolute path of the directory currently shown in the tree view."""
        current_root_index: QModelIndex = self.tree.rootIndex()
        if current_root_index.isValid():
            path = self.model.filePath(current_root_index)
            print(f"[DEBUG FilePane get_current_view_path] Returning path: {path}") # DEBUG
            return path
        else:
            # Fallback
            path = QDir.currentPath()
            print(f"[DEBUG FilePane get_current_view_path] Root index invalid, returning fallback: {path}") # DEBUG
            return path

    def go_up_directory(self):
        """Navigates the tree view to the parent directory."""
        print("[DEBUG FilePane go_up_directory] 'Up' button clicked!") # DEBUG
        current_view_root_index: QModelIndex = self.tree.rootIndex()
        current_view_path = self.model.filePath(current_view_root_index)
        print(f"[DEBUG FilePane go_up_directory] Current TREE view root index path: {current_view_path}") # DEBUG

        parent_index: QModelIndex = current_view_root_index.parent()
        is_parent_valid = parent_index.isValid()
        parent_path = self.model.filePath(parent_index) if is_parent_valid else "N/A"
        print(f"[DEBUG FilePane go_up_directory] Parent index in MODEL valid? {is_parent_valid}, Path: {parent_path}") # DEBUG

        is_already_at_root = (current_view_path == QDir.rootPath()) or \
                             (current_view_path == self.model.rootPath())
        print(f"[DEBUG FilePane go_up_directory] Current view path is root ('/')? {is_already_at_root}") # DEBUG

        if is_parent_valid:
            print(f"[DEBUG FilePane go_up_directory] Setting TREE view root index to parent: {parent_path}") # DEBUG
            self.tree.setRootIndex(parent_index)
            print(f"[DEBUG FilePane go_up_directory] Tree view root index set. Updating button state...") # DEBUG
            self._update_up_button_state()
        else:
            print(f"[DEBUG FilePane go_up_directory] Cannot go up. Parent index is invalid (already at model root?).") # DEBUG

    def _update_up_button_state(self):
        """Disables the 'Up' button if the view is at the filesystem root ('/')."""
        print("[DEBUG FilePane _update_up_button_state] Updating button state...") # DEBUG
        current_view_root_index: QModelIndex = self.tree.rootIndex()
        current_view_path = self.model.filePath(current_view_root_index)
        print(f"[DEBUG FilePane _update_up_button_state] Current TREE view path: {current_view_path}") # DEBUG

        can_go_up = (current_view_path != QDir.rootPath()) and \
                    (current_view_path != self.model.rootPath())

        print(f"[DEBUG FilePane _update_up_button_state] Calculated can_go_up (view path != '/'): {can_go_up}") # DEBUG
        self.up_button.setEnabled(can_go_up)
        print(f"[DEBUG FilePane _update_up_button_state] Button enabled: {can_go_up}") # DEBUG

    def get_selected_paths(self):
        selected_indexes = self.tree.selectionModel().selectedIndexes()
        paths = set()
        for index in selected_indexes:
            model_index = index
            if model_index.column() == 0:
                 file_path = self.model.filePath(model_index)
                 # Ensure it's actually a file, not a directory getting selected somehow
                 if self.model.fileInfo(model_index).isFile():
                     paths.add(file_path)
        return list(paths)

    def show_context_menu(self, pos: QPoint):
        index_at_pos = self.tree.indexAt(pos)
        selected_paths = self.get_selected_paths() # Get selected FILES
        menu = QMenu()

        # Actions for selected files
        if selected_paths:
            # Use f-string for clarity if opening multiple or single
            num_files = len(selected_paths)
            open_text = f"Open {num_files} File{'s' if num_files > 1 else ''} in Editor"
            edit_text = f"Edit {num_files} File{'s' if num_files > 1 else ''} with Gemini"
            explain_text = f"Explain {num_files} File{'s' if num_files > 1 else ''} with Gemini"

            open_action = menu.addAction(open_text)
            edit_action = menu.addAction(edit_text)
            explain_action = menu.addAction(explain_text)
            menu.addSeparator()
        else:
            open_action = None
            edit_action = None
            explain_action = None

        # General actions
        refresh_action = menu.addAction("Refresh View")

        # Optional: Set directory as root view on right-click
        # if index_at_pos.isValid() and self.model.isDir(index_at_pos):
        #    set_root_action = menu.addAction("Set as Root View")

        action = menu.exec(self.tree.mapToGlobal(pos))

        # Handle actions
        if action == open_action and selected_paths:
            print("[DEBUG FilePane show_context_menu] 'Open' action triggered.") # DEBUG
            self.open_files_requested.emit(selected_paths)
        elif action == edit_action and selected_paths:
            print("[DEBUG FilePane show_context_menu] 'Edit' action triggered.") # DEBUG
            self.edit_files_requested.emit(selected_paths)
        elif action == explain_action and selected_paths:
            print("[DEBUG FilePane show_context_menu] 'Explain' action triggered.") # DEBUG
            self.explain_files_requested.emit(selected_paths)
        elif action == refresh_action:
            self.refresh()
        # elif action == set_root_action:
        #     if index_at_pos.isValid() and self.model.isDir(index_at_pos):
        #         self.tree.setRootIndex(index_at_pos)
        #         self._update_up_button_state()

    def refresh(self):
        current_root = self.tree.rootIndex()
        current_path = self.model.filePath(current_root)
        print(f"[DEBUG FilePane refresh] Refreshing view at: {current_path}") # DEBUG
        self.model.refresh(current_root)
        # Refresh parent as well in case of directory changes affecting the view
        parent_root = current_root.parent()
        if parent_root.isValid():
            self.model.refresh(parent_root)
        print(f"[DEBUG FilePane refresh] Refresh complete for: {current_path}") # DEBUG
        self._update_up_button_state()

    # <<< ADDED METHOD: handle_double_click >>>
    @Slot(QModelIndex)
    def handle_double_click(self, index: QModelIndex):
        """Handles double-clicking on an item in the tree view."""
        if not index.isValid():
            print("[DEBUG FilePane handle_double_click] Invalid index clicked.") # DEBUG
            return # Ignore invalid index clicks

        file_info = self.model.fileInfo(index)
        if file_info.isFile():
            file_path = self.model.filePath(index)
            print(f"[DEBUG FilePane handle_double_click] File double-clicked: {file_path}") # DEBUG
            # Emit the same signal used by the context menu
            self.open_files_requested.emit([file_path])
        elif file_info.isDir():
             print(f"[DEBUG FilePane handle_double_click] Directory double-clicked: {self.model.filePath(index)}") # DEBUG
             # Optional: Navigate into directory on double-click
             # self.tree.setRootIndex(index)
             # self._update_up_button_state()
        else:
             print(f"[DEBUG FilePane handle_double_click] Double-clicked non-file/dir item.") # DEBUG

# --- END OF FILE file_pane.py ---