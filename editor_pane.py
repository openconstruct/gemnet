# --- START OF FILE editor_pane.py ---

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QTabWidget, QTabBar,
                               QPushButton, QStyle, QHBoxLayout, QFileDialog, QMessageBox) # Added imports
from PySide6.QtCore import Signal, Qt, QDir, Slot # Added QDir, Slot
from PySide6.QtGui import QSyntaxHighlighter, QFont, QTextCursor # Added QFont, QSyntaxHighlighter, QTextCursor
import os

# Import the highlighter
from syntax_highlighter import PythonHighlighter

class EditorPane(QWidget):
    # Signal to request status bar updates in MainWindow
    status_message_requested = Signal(str)
    # content_changed = Signal(str) # Keep if needed later

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2) # Small margins

        # --- Toolbar ---
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0,0,0,5) # Space below toolbar

        self.open_button = QPushButton("Open")
        self.open_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.open_button.setToolTip("Open file(s)")
        self.open_button.clicked.connect(self.request_open_files)
        toolbar_layout.addWidget(self.open_button)

        self.save_button = QPushButton("Save")
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setToolTip("Save current file")
        self.save_button.clicked.connect(self.save_current_file)
        self.save_button.setEnabled(False) # Disabled initially
        toolbar_layout.addWidget(self.save_button)

        self.reload_button = QPushButton("Reload")
        self.reload_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.reload_button.setToolTip("Reload current file from disk (discard changes)")
        self.reload_button.clicked.connect(self.reload_current_file)
        self.reload_button.setEnabled(False) # Disabled initially
        toolbar_layout.addWidget(self.reload_button)

        toolbar_layout.addStretch(1) # Push buttons to the left

        layout.addLayout(toolbar_layout)
        # --- End Toolbar ---

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.update_button_states) # Update buttons on tab change
        # self.tab_widget.setMovable(True) # Allow reordering tabs

        layout.addWidget(self.tab_widget)

        self.highlighters = {} # Store highlighters to prevent garbage collection {editor_widget: highlighter_instance}

        # --- State for Editor Streaming ---
        self._is_editor_streaming = False

    # ... request_open_files, open_files, mark_tab_modified, save_current_file, reload_current_file, close_tab ...
    # (These methods remain largely the same, check diffs if needed)
    def request_open_files(self):
        """Shows a dialog to select files and opens them."""
        start_dir = QDir.homePath()
        current_path = self.get_current_path()
        if current_path:
             start_dir = os.path.dirname(current_path)

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", start_dir,
            "All Files (*);;Text Files (*.txt);;Python Files (*.py);;Markdown (*.md)"
        )
        if file_paths: self.open_files(file_paths)

    def open_files(self, file_paths):
        print(f"[DEBUG EditorPane open_files] Received request to open: {file_paths}")
        opened_new = False; newly_opened_paths = []
        for path in file_paths:
            if not os.path.isfile(path):
                self.status_message_requested.emit(f"Warning: '{os.path.basename(path)}' is not a valid file.")
                continue
            found_index = -1
            for index in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(index)
                 if widget and widget.property("file_path") == path: found_index = index; break
            if found_index != -1:
                self.tab_widget.setCurrentIndex(found_index)
                self.status_message_requested.emit(f"Switched to open tab: {os.path.basename(path)}")
                continue
            else:
                opened_new = True
                try:
                    content = None; encoding_used = None
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                         try:
                              with open(path, 'r', encoding=encoding) as f: content = f.read()
                              encoding_used = encoding; break
                         except UnicodeDecodeError: continue
                         except Exception as inner_e: raise inner_e
                    if content is None: raise ValueError(f"Could not decode file.")
                except Exception as e:
                    QMessageBox.critical(self, "Open Error", f"Could not open file:\n{path}\n\nError: {e}")
                    self.status_message_requested.emit(f"Failed to open {os.path.basename(path)}: {e}")
                    continue
                editor = QTextEdit()
                font = editor.font(); font.setFamily("Monospace"); font.setStyleHint(QFont.TypeWriter)
                editor.setFont(font)
                # Prevent textChanged signal during initial load
                editor.blockSignals(True)
                editor.setPlainText(content)
                editor.blockSignals(False)

                editor.setProperty("file_path", path)
                editor.setProperty("is_modified", False)
                editor.textChanged.connect(self.mark_tab_modified)
                tab_title = os.path.basename(path)
                index = self.tab_widget.addTab(editor, tab_title)
                self.tab_widget.setTabToolTip(index, path)
                self.tab_widget.setCurrentIndex(index)
                if path.lower().endswith(".py"):
                     highlighter = PythonHighlighter(editor.document())
                     self.highlighters[editor] = highlighter
                     print(f"[DEBUG EditorPane] Applied PythonHighlighter to {tab_title}")
                newly_opened_paths.append(path)
                self.status_message_requested.emit(f"Opened {os.path.basename(path)} (Encoding: {encoding_used})")

        if opened_new: self.update_button_states()
        # Return paths that were *actually* opened (for edit flow)
        return newly_opened_paths

    def mark_tab_modified(self):
        """Marks the current tab as modified when text changes."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
             # Prevent marking modified if we are currently streaming content into it
             if self._is_editor_streaming:
                 return
             if not current_widget.property("is_modified"):
                 current_index = self.tab_widget.currentIndex()
                 current_text = self.tab_widget.tabText(current_index)
                 if not current_text.startswith("*"):
                      self.tab_widget.setTabText(current_index, "*" + current_text)
                 current_widget.setProperty("is_modified", True)
                 self.update_button_states() # Enable save/reload

    def save_current_file(self):
        """Saves the content of the currently active tab to its file."""
        current_index = self.tab_widget.currentIndex()
        if current_index == -1: return
        widget = self.tab_widget.widget(current_index)
        if widget and isinstance(widget, QTextEdit):
            path = widget.property("file_path")
            if path:
                try:
                    content = widget.toPlainText()
                    with open(path, 'w', encoding='utf-8') as f: f.write(content)
                    self.status_message_requested.emit(f"File saved: {os.path.basename(path)}")
                    widget.setProperty("is_modified", False)
                    current_text = self.tab_widget.tabText(current_index)
                    if current_text.startswith("*"): self.tab_widget.setTabText(current_index, current_text[1:])
                    self.update_button_states()
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Could not save file:\n{path}\n\nError: {e}")
                    self.status_message_requested.emit(f"Error saving {os.path.basename(path)}: {e}")
            else:
                self.status_message_requested.emit("Cannot save: File has no associated path (Save As not implemented).")

    def reload_current_file(self):
         """Reloads the current file from disk, discarding changes."""
         current_index = self.tab_widget.currentIndex()
         if current_index == -1: return
         widget = self.tab_widget.widget(current_index)
         if widget and isinstance(widget, QTextEdit):
             path = widget.property("file_path"); is_modified = widget.property("is_modified")
             if path:
                 if is_modified:
                     reply = QMessageBox.question(self, 'Confirm Reload',
                                                  "Are you sure you want to reload the file?\nAll unsaved changes will be lost.",
                                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                     if reply == QMessageBox.No: return
                 try:
                    content = None; encoding_used = None
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                         try:
                              with open(path, 'r', encoding=encoding) as f: content = f.read()
                              encoding_used = encoding; break
                         except UnicodeDecodeError: continue
                         except Exception as inner_e: raise inner_e
                    if content is None: raise ValueError("Could not decode file.")

                    widget.blockSignals(True) # Block modify signal
                    widget.setPlainText(content)
                    widget.blockSignals(False) # Unblock modify signal

                    widget.setProperty("is_modified", False)
                    widget.setReadOnly(False)
                    current_text = self.tab_widget.tabText(current_index)
                    if current_text.startswith("*"): self.tab_widget.setTabText(current_index, current_text[1:])
                    self.status_message_requested.emit(f"File reloaded: {os.path.basename(path)} (Encoding: {encoding_used})")
                    self.update_button_states()

                    # Reapply highlighter
                    highlighter_instance = self.highlighters.get(widget)
                    if highlighter_instance:
                         print(f"[DEBUG EditorPane reload] Reapplying highlighter for {os.path.basename(path)}")
                         highlighter_instance.setDocument(widget.document()); highlighter_instance.rehighlight()
                    elif path.lower().endswith(".py"):
                         print(f"[DEBUG EditorPane reload] Applying new highlighter for {os.path.basename(path)}")
                         highlighter = PythonHighlighter(widget.document()); self.highlighters[widget] = highlighter
                 except Exception as e:
                     QMessageBox.critical(self, "Reload Error", f"Could not reload file:\n{path}\n\nError: {e}")
                     self.status_message_requested.emit(f"Error reloading {os.path.basename(path)}: {e}")
             else: self.status_message_requested.emit("Cannot reload: No file path associated with this tab.")

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget and isinstance(widget, QTextEdit):
            if widget.property("is_modified"):
                filename = self.tab_widget.tabText(index); filename = filename[1:] if filename.startswith("*") else filename
                reply = QMessageBox.question(self, 'Unsaved Changes',
                                             f"'{filename}' has unsaved changes.\nDo you want to save before closing?",
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel)
                if reply == QMessageBox.Save:
                    self.save_current_file()
                    if widget.property("is_modified"): return # Save failed
                elif reply == QMessageBox.Cancel: return
            if widget in self.highlighters:
                print(f"[DEBUG EditorPane close_tab] Removing highlighter for {self.tab_widget.tabText(index)}")
                del self.highlighters[widget]
            self.tab_widget.removeTab(index); widget.deleteLater()
        else:
             self.tab_widget.removeTab(index);
             if widget: widget.deleteLater()
        self.update_button_states()


    def get_current_content(self):
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            return current_widget.toPlainText()
        return None

    def get_current_path(self):
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            return current_widget.property("file_path")
        return None

    # --- REMOVED set_current_content (replaced by streaming slots) ---
    # def set_current_content(self, text): ...

    def update_button_states(self):
        """Enable/disable Save and Reload buttons based on current tab state."""
        current_widget = self.tab_widget.currentWidget()
        has_valid_path = False; is_modified = False; has_tab = current_widget is not None
        if has_tab and isinstance(current_widget, QTextEdit):
            path = current_widget.property("file_path")
            if path and os.path.isfile(path): has_valid_path = True
            is_modified = current_widget.property("is_modified")
        can_save = has_tab and is_modified and current_widget.property("file_path") is not None
        can_reload = has_tab and has_valid_path
        self.save_button.setEnabled(can_save)
        self.reload_button.setEnabled(can_reload)


    # --- Slots for Streaming Signals (Editor Context) ---
    @Slot(str, str)
    def handle_stream_started(self, sender, context_type):
        """Prepares the editor for incoming stream chunks."""
        if context_type != 'editor': return # Only handle editor streams

        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
             if self._is_editor_streaming:
                 print("[EditorPane WARN] New editor stream started while previous was active.")
                 # Decide how to handle: replace content anyway or show error? Replace for now.
             print(f"[EditorPane] Stream started for editor (sender: {sender})")
             self._is_editor_streaming = True
             # Clear existing content and block signals temporarily
             current_widget.blockSignals(True)
             current_widget.setPlainText("") # Clear content for replacement
             current_widget.blockSignals(False)
             self.status_message_requested.emit("Receiving suggested edit from Gemini...")
             current_widget.setFocus() # Ensure editor has focus
        else:
             print("[EditorPane ERROR] Editor stream started but no active editor tab found.")
             # Optionally emit status message
             self.status_message_requested.emit("Error: Cannot apply edit - no active editor tab.")
             # Need to signal back to controller? Maybe not, let it time out or error?

    @Slot(str)
    def handle_stream_chunk(self, chunk):
        """Appends a text chunk to the current editor during streaming."""
        if not self._is_editor_streaming: return # Not in editor streaming state

        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
             # Append text chunk
             current_widget.blockSignals(True) # Block modify signal during insertion
             cursor = current_widget.textCursor()
             cursor.movePosition(QTextCursor.End)
             cursor.insertText(chunk)
             current_widget.ensureCursorVisible()
             current_widget.blockSignals(False) # Unblock modify signal
        # else: error already logged in handle_stream_started if no widget

    @Slot(str, str)
    def handle_stream_finished(self, sender, context_type):
        """Finalizes the editor state after streaming is complete."""
        if context_type != 'editor' or not self._is_editor_streaming: return

        print(f"[EditorPane] Stream finished for editor (sender: {sender})")
        self._is_editor_streaming = False
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            # Manually mark as modified *after* streaming finishes
            if not current_widget.property("is_modified"):
                current_index = self.tab_widget.currentIndex()
                current_text = self.tab_widget.tabText(current_index)
                if not current_text.startswith("*"):
                    self.tab_widget.setTabText(current_index, "*" + current_text)
                current_widget.setProperty("is_modified", True)

            # Re-apply/re-highlight after content change
            highlighter_instance = self.highlighters.get(current_widget)
            if highlighter_instance:
                 print(f"[DEBUG EditorPane stream finished] Rehighlighting after AI edit")
                 highlighter_instance.rehighlight() # Force full rehighlight
            elif current_widget.property("file_path") and current_widget.property("file_path").lower().endswith(".py"):
                 print(f"[DEBUG EditorPane stream finished] Applying new highlighter after AI edit")
                 highlighter = PythonHighlighter(current_widget.document())
                 self.highlighters[current_widget] = highlighter

            self.update_button_states() # Ensure save is enabled
            self.status_message_requested.emit("Editor content updated by Gemini.")
        else:
             print("[EditorPane WARN] Editor stream finished, but no active editor tab found.")

    @Slot(str, str)
    def handle_stream_error(self, error_message, context_type):
        """Handles errors during editor streaming."""
        if context_type != 'editor': return

        print(f"[EditorPane] Stream error for editor: {error_message}")
        # Display error in status bar and maybe a message box?
        self.status_message_requested.emit(f"Error during edit: {error_message}")
        QMessageBox.warning(self, "Edit Error", f"Could not apply edit:\n{error_message}")

        # Reset streaming state
        self._is_editor_streaming = False
        # Should we revert changes? Maybe not, leave partial result for user to decide.
        # Manually mark modified if any content was added before error?
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit) and current_widget.toPlainText():
            if not current_widget.property("is_modified"):
                # Mark modified if error happened mid-stream after adding content
                current_index = self.tab_widget.currentIndex()
                current_text = self.tab_widget.tabText(current_index)
                if not current_text.startswith("*"):
                    self.tab_widget.setTabText(current_index, "*" + current_text)
                current_widget.setProperty("is_modified", True)
                self.update_button_states()


# --- END OF FILE editor_pane.py ---