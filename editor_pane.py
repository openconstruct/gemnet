from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QTabWidget, QTabBar,
                               QPushButton, QStyle, QHBoxLayout, QFileDialog, QMessageBox) # Added imports
from PySide6.QtCore import Signal, Qt, QDir # Added QDir
from PySide6.QtGui import QSyntaxHighlighter, QFont # Added QFont, QSyntaxHighlighter (though actual class is imported separately)
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

        # Store references: {index: (editor, path, highlighter, is_modified)} -> Using properties now
        # self.editors = {} # No longer needed
        self.highlighters = {} # Store highlighters to prevent garbage collection {editor_widget: highlighter_instance}

    def request_open_files(self):
        """Shows a dialog to select files and opens them."""
        # Use the last opened directory or home directory as starting point
        # (Could store last directory in settings later)
        start_dir = QDir.homePath()
        # Try to get path from current tab if available
        current_path = self.get_current_path()
        if current_path:
             start_dir = os.path.dirname(current_path)

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Files",
            start_dir,
            "All Files (*);;Text Files (*.txt);;Python Files (*.py);;Markdown (*.md)" # Add more types
        )
        if file_paths:
            self.open_files(file_paths)

    def open_files(self, file_paths):
        print(f"[DEBUG EditorPane open_files] Received request to open: {file_paths}") # <<< DEBUG PRINT ADDED HERE >>>
        opened_new = False
        for path in file_paths:
            if not os.path.isfile(path):
                self.status_message_requested.emit(f"Warning: '{os.path.basename(path)}' is not a valid file.")
                continue

            # Check if already open
            found_index = -1
            for index in range(self.tab_widget.count()):
                 widget = self.tab_widget.widget(index)
                 # Ensure widget exists and has the property before checking
                 if widget and widget.property("file_path") == path:
                    found_index = index
                    break

            if found_index != -1:
                self.tab_widget.setCurrentIndex(found_index)
                self.status_message_requested.emit(f"Switched to open tab: {os.path.basename(path)}") # Info message
                continue # Already open, just switch to it
            else: # Not open, create new tab
                opened_new = True
                try:
                    # Try common encodings
                    content = None
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                         try:
                              with open(path, 'r', encoding=encoding) as f:
                                  content = f.read()
                              self.status_message_requested.emit(f"Opened {os.path.basename(path)} (Encoding: {encoding})") # Log success
                              break # Success
                         except UnicodeDecodeError:
                              continue
                         except Exception as inner_e:
                              # Log other read errors specifically
                              self.status_message_requested.emit(f"Error reading {os.path.basename(path)}: {inner_e}")
                              raise inner_e # Raise other read errors

                    if content is None:
                         # This means all tested encodings failed
                         self.status_message_requested.emit(f"Error opening {os.path.basename(path)}: Could not decode with tested encodings.")
                         raise ValueError(f"Could not decode file '{os.path.basename(path)}' with tested encodings.")

                except Exception as e:
                    # Catch the specific error or the generic one raised above
                    QMessageBox.critical(self, "Open Error", f"Could not open file:\n{path}\n\nError: {e}")
                    self.status_message_requested.emit(f"Failed to open {os.path.basename(path)}: {e}")
                    # Optionally open a tab with the error message, but might clutter
                    # content = f"Error loading file: {e}"
                    # is_error_content = True
                    continue # Skip creating tab for this file if error occurred
                else:
                    is_error_content = False # Content loaded successfully


                editor = QTextEdit()
                # Use Monospaced font for code editing
                font = editor.font()
                font.setFamily("Monospace") # Or Courier, Consolas, etc.
                font.setStyleHint(QFont.TypeWriter)
                editor.setFont(font)

                editor.setPlainText(content)
                editor.setProperty("file_path", path) # Store path with the widget
                editor.setProperty("is_modified", False) # Custom property for modified state
                editor.setReadOnly(is_error_content) # Make read-only if loading failed (shouldn't happen with 'continue' above)

                # Connect textChanged to mark modified *after* initial content is set
                editor.textChanged.connect(self.mark_tab_modified)

                tab_title = os.path.basename(path)
                index = self.tab_widget.addTab(editor, tab_title)
                self.tab_widget.setTabToolTip(index, path) # Show full path on hover
                self.tab_widget.setCurrentIndex(index)

                # --- Syntax Highlighting ---
                highlighter = None
                if not is_error_content and path.lower().endswith(".py"):
                     highlighter = PythonHighlighter(editor.document())
                     self.highlighters[editor] = highlighter # Keep reference
                     print(f"[DEBUG EditorPane] Applied PythonHighlighter to {tab_title}") # DEBUG
                # Add elif for other languages here...

                # No longer need self.editors dictionary

        if opened_new:
             self.update_button_states() # Update buttons after opening


    def mark_tab_modified(self):
        """Marks the current tab as modified when text changes."""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
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
                    # Try to save with UTF-8 first
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.status_message_requested.emit(f"File saved: {os.path.basename(path)}")

                    # Mark as unmodified
                    widget.setProperty("is_modified", False)
                    current_text = self.tab_widget.tabText(current_index)
                    if current_text.startswith("*"):
                        self.tab_widget.setTabText(current_index, current_text[1:])
                    self.update_button_states() # Disable save/reload maybe?

                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Could not save file:\n{path}\n\nError: {e}")
                    self.status_message_requested.emit(f"Error saving {os.path.basename(path)}: {e}")
            else:
                # Handle "Save As" logic here later if needed
                self.status_message_requested.emit("Cannot save: File has no associated path (Save As not implemented).")

    def reload_current_file(self):
         """Reloads the current file from disk, discarding changes."""
         current_index = self.tab_widget.currentIndex()
         if current_index == -1: return

         widget = self.tab_widget.widget(current_index)
         if widget and isinstance(widget, QTextEdit):
             path = widget.property("file_path")
             is_modified = widget.property("is_modified")

             if path:
                 confirm_msg = "Are you sure you want to reload the file?\nAll unsaved changes will be lost."
                 if is_modified:
                     reply = QMessageBox.question(self, 'Confirm Reload', confirm_msg,
                                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                     if reply == QMessageBox.No:
                         return

                 try:
                    # Reuse decoding logic from open_files
                    content = None
                    encoding_used = None
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                         try:
                              with open(path, 'r', encoding=encoding) as f:
                                  content = f.read()
                              encoding_used = encoding
                              break
                         except UnicodeDecodeError: continue
                         except Exception as inner_e: raise inner_e
                    if content is None: raise ValueError("Could not decode file.")

                    # Block signals temporarily to prevent marking modified immediately
                    widget.blockSignals(True)
                    widget.setPlainText(content)
                    widget.blockSignals(False)

                    widget.setProperty("is_modified", False)
                    widget.setReadOnly(False) # Ensure not read-only after reload
                    current_text = self.tab_widget.tabText(current_index)
                    if current_text.startswith("*"):
                         self.tab_widget.setTabText(current_index, current_text[1:])

                    self.status_message_requested.emit(f"File reloaded: {os.path.basename(path)} (Encoding: {encoding_used})")
                    self.update_button_states()

                    # Reapply highlighter if needed (might be cleared by setPlainText)
                    highlighter_instance = self.highlighters.get(widget)
                    if highlighter_instance:
                         print(f"[DEBUG EditorPane reload] Reapplying highlighter for {os.path.basename(path)}")
                         highlighter_instance.setDocument(widget.document()) # Re-associate with document
                         highlighter_instance.rehighlight() # Force re-highlight
                    elif path.lower().endswith(".py"): # If no instance existed but should have
                         print(f"[DEBUG EditorPane reload] Applying new highlighter for {os.path.basename(path)}")
                         highlighter = PythonHighlighter(widget.document())
                         self.highlighters[widget] = highlighter


                 except Exception as e:
                     QMessageBox.critical(self, "Reload Error", f"Could not reload file:\n{path}\n\nError: {e}")
                     self.status_message_requested.emit(f"Error reloading {os.path.basename(path)}: {e}")
             else:
                 self.status_message_requested.emit("Cannot reload: No file path associated with this tab.")


    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        if widget and isinstance(widget, QTextEdit):
            if widget.property("is_modified"):
                filename = self.tab_widget.tabText(index)
                if filename.startswith("*"): filename = filename[1:]
                reply = QMessageBox.question(self, 'Unsaved Changes',
                                             f"'{filename}' has unsaved changes.\nDo you want to save before closing?",
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                             QMessageBox.Cancel) # Default to Cancel

                if reply == QMessageBox.Save:
                    self.save_current_file()
                    # Check if save failed somehow? If it did, is_modified will still be true
                    if widget.property("is_modified"): # If save failed, don't close
                         return
                elif reply == QMessageBox.Cancel:
                    return # Don't close the tab
                # If Discard, proceed to close

            # Clean up highlighter reference if it exists
            if widget in self.highlighters:
                print(f"[DEBUG EditorPane close_tab] Removing highlighter for {self.tab_widget.tabText(index)}") # DEBUG
                del self.highlighters[widget]

            self.tab_widget.removeTab(index)
            widget.deleteLater() # Clean up widget
        else:
             # Should not happen with standard usage
             self.tab_widget.removeTab(index)
             if widget: widget.deleteLater()

        self.update_button_states() # Update buttons after closing

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

    def set_current_content(self, text):
        current_widget = self.tab_widget.currentWidget()
        if current_widget and isinstance(current_widget, QTextEdit):
            # Block signals to prevent immediate marking as modified by AI edit
            current_widget.blockSignals(True)
            # Preserve cursor position if possible (more complex, basic implementation below)
            # cursor = current_widget.textCursor()
            # old_pos = cursor.position()
            current_widget.setPlainText(text)
            # Try to restore cursor position (might be inaccurate if text changed drastically)
            # cursor.setPosition(min(old_pos, len(text))) # Basic restoration
            # current_widget.setTextCursor(cursor)
            current_widget.blockSignals(False)

            # Manually mark as modified after AI edit
            if not current_widget.property("is_modified"):
                 current_index = self.tab_widget.currentIndex()
                 current_text = self.tab_widget.tabText(current_index)
                 if not current_text.startswith("*"):
                      self.tab_widget.setTabText(current_index, "*" + current_text)
                 current_widget.setProperty("is_modified", True)

            # Re-apply/re-highlight after content change
            highlighter_instance = self.highlighters.get(current_widget)
            if highlighter_instance:
                 print(f"[DEBUG EditorPane set_current_content] Rehighlighting after AI edit")
                 highlighter_instance.rehighlight()
            elif current_widget.property("file_path") and current_widget.property("file_path").lower().endswith(".py"):
                 print(f"[DEBUG EditorPane set_current_content] Applying new highlighter after AI edit")
                 highlighter = PythonHighlighter(current_widget.document())
                 self.highlighters[current_widget] = highlighter


            self.update_button_states() # Ensure save is enabled
            self.status_message_requested.emit("Editor content updated by Gemini.") # Inform user
        else:
            print("Warning: Tried to set editor content, but no tab is selected or widget is not QTextEdit.")
            self.status_message_requested.emit("Error: Cannot update editor - no active tab.")


    def update_button_states(self):
        """Enable/disable Save and Reload buttons based on current tab state."""
        current_widget = self.tab_widget.currentWidget()
        has_valid_path = False # Check if path exists and is a file
        is_modified = False
        has_tab = current_widget is not None

        if has_tab and isinstance(current_widget, QTextEdit):
            path = current_widget.property("file_path")
            # Check if path exists and is a file for reload safety
            if path and os.path.isfile(path): # Check isfile for reload
                 has_valid_path = True
            is_modified = current_widget.property("is_modified")

        # Save is enabled if a tab exists, it's modified, AND it has *some* path (even if invalid for reload)
        can_save = has_tab and is_modified and current_widget.property("file_path") is not None
        # Reload is enabled only if a tab exists AND it has a valid, existing file path
        can_reload = has_tab and has_valid_path

        self.save_button.setEnabled(can_save)
        self.reload_button.setEnabled(can_reload)

