# --- START OF FILE main.py ---


import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QSplitter, QStatusBar, QMenu, QLabel)
from PySide6.QtCore import Qt, Slot, QDir
from PySide6.QtGui import QAction, QActionGroup

# Import custom widgets
from file_pane import FilePane
from editor_pane import EditorPane
from chat_pane import ChatPane
from gemini_controller import GeminiController # Ensure GeminiController is imported
from theme_manager import ThemeManager
from model_selection_dialog import ModelSelectionDialog
import typing # Required for type hinting if used in controller

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GemNet - Local Gemini Interface")
        self.setGeometry(100, 100, 1200, 800)
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Initializing GemNet...")
        # Instantiate ThemeManager before applying theme
        self.theme_manager = ThemeManager(self) # Pass self (MainWindow instance)

        # Instantiate panes first
        self.file_pane = FilePane()
        self.editor_pane = EditorPane() # Instantiate before controller if controller needs it
        self.chat_pane = ChatPane()

        # <<< Pass BOTH file_pane and editor_pane to Controller >>>
        self.gemini_controller = GeminiController(
            file_pane_ref=self.file_pane,
            editor_pane_ref=self.editor_pane # Pass editor pane reference
        )

        # --- Store intermediate file content for /create ---
        self._streaming_file_content = "" # Temporary buffer

        self.setup_layout()
        self.setup_menus()
        self.connect_signals() # Connect signals after controller is created
        # Apply the default theme *after* layout and menus exist
        self.theme_manager.set_theme("dark") # Apply theme after layout exists
        # Controller internally calls update_available_models on init if configured
        # self.gemini_controller.update_available_models() # Fetch models after setup

    def setup_layout(self):
        h_splitter = QSplitter(Qt.Horizontal)
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.addWidget(self.editor_pane)
        v_splitter.addWidget(self.chat_pane)
        v_splitter.setSizes([500, 300]) # Adjust vertical split ratio if desired
        h_splitter.addWidget(self.file_pane)
        h_splitter.addWidget(v_splitter)
        h_splitter.setSizes([300, 900]) # Adjust horizontal split ratio if desired
        self.setCentralWidget(h_splitter)

    # <<< MODIFIED setup_menus >>>
    def setup_menus(self):
        menu_bar = self.menuBar()

        # --- File Menu ---
        file_menu = menu_bar.addMenu("File")
        open_action = file_menu.addAction("Open File(s)...")
        open_action.triggered.connect(self.editor_pane.request_open_files)
        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(self.editor_pane.save_current_file)
        reload_action = file_menu.addAction("Reload File")
        reload_action.triggered.connect(self.editor_pane.reload_current_file)
        file_menu.addSeparator()
        refresh_files_action = file_menu.addAction("Refresh Files View")
        refresh_files_action.triggered.connect(self.file_pane.refresh)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # --- View Menu ---
        view_menu = menu_bar.addMenu("View")
        theme_menu = view_menu.addMenu("Themes")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        # --- Add actions for ALL themes ---
        # Helper function to add theme actions to the menu and group
        def add_theme_action(name, display_text, is_default=False):
            action = QAction(display_text, self, checkable=True)
            # Use lambda with default argument capture to avoid late binding issues
            # Pass the theme 'name' (key in ThemeManager.themes)
            action.triggered.connect(lambda checked=False, theme_name=name: self.theme_manager.set_theme(theme_name))
            theme_menu.addAction(action)
            self.theme_group.addAction(action)
            # Set the initially checked theme
            if is_default:
                action.setChecked(True)

        # Define the themes and their display names
        # The 'name' should match the keys in ThemeManager.themes dictionary
        available_themes = {
            "dark": "Default Dark",
            "light": "Default Light",
            "gruvbox_dark": "Gruvbox Dark",
            "solarized_dark": "Solarized Dark",
            "nord": "Nord",
        }
        default_theme_key = "dark" # Set your desired default theme key here

        # Add actions for each theme
        for theme_key, theme_display_name in available_themes.items():
             # Check if this theme is the default one
             is_default = (theme_key == default_theme_key)
             add_theme_action(theme_key, theme_display_name, is_default=is_default)

        # --- Model Menu ---
        model_menu = menu_bar.addMenu("Model")
        self.select_model_action = model_menu.addAction("Select Model...")
        self.select_model_action.triggered.connect(self.open_model_selection_dialog)
        self.select_model_action.setEnabled(False) # Disabled until models are loaded
        model_menu.addSeparator()
        refresh_models_action = model_menu.addAction("Refresh Model List")
        refresh_models_action.triggered.connect(self.gemini_controller.update_available_models)

    @Slot(list)
    def handle_available_models_update(self, model_names):
        """Enables or disables the 'Select Model' action based on model list."""
        if model_names:
            self.select_model_action.setEnabled(True)
            self.status_bar.showMessage(f"Models loaded. Current: {self.gemini_controller.selected_model_name}", 4000)
        else:
            self.select_model_action.setEnabled(False)
            self.status_bar.showMessage("Failed to load models or none found. Check API Key/Config.", 5000)

    def open_model_selection_dialog(self):
        """Opens the modal dialog to select a Gemini model."""
        available = self.gemini_controller.available_models
        current = self.gemini_controller.selected_model_name
        success, new_model_name = ModelSelectionDialog.get_model(available, current, self)
        if success and new_model_name != current:
            self.status_bar.showMessage(f"Switching model to {new_model_name}...")
            self.gemini_controller.set_selected_model(new_model_name)
        elif success: self.status_bar.showMessage(f"Model selection unchanged ({current}).", 3000)
        else: self.status_bar.showMessage("Model selection cancelled.", 3000)

    # <<< connect_signals (no changes needed here) >>>
    def connect_signals(self):
        """Connect signals between UI elements and the controller."""
        # --- UI -> Controller / Other UI ---
        self.file_pane.open_files_requested.connect(self.editor_pane.open_files)
        self.file_pane.explain_files_requested.connect(self.handle_explain_request)
        self.file_pane.edit_files_requested.connect(self.handle_edit_request)
        self.chat_pane.user_message_submitted.connect(self.handle_chat_message)
        self.editor_pane.status_message_requested.connect(lambda msg: self.status_bar.showMessage(msg, 4000))

        # --- Controller -> UI ---
        # Status/Info updates
        self.gemini_controller.status_update.connect(self.update_status_bar)
        self.gemini_controller.initialization_status.connect(self.handle_initialization_status)
        self.gemini_controller.available_models_updated.connect(self.handle_available_models_update)
        # Signals for setting up chat-based edit/create flows
        self.gemini_controller.edit_file_requested_from_chat.connect(self.handle_edit_file_requested_from_chat)
        self.gemini_controller.edit_context_set_from_chat.connect(lambda msg: self.chat_pane.add_message("GemNet", msg, is_status=True))

        # --- Controller -> UI (Streaming) ---
        self.gemini_controller.stream_started.connect(self.handle_stream_started) # Route based on context
        self.gemini_controller.stream_chunk_received.connect(self.handle_stream_chunk) # Route based on context
        self.gemini_controller.stream_finished.connect(self.handle_stream_finished) # Route based on context
        self.gemini_controller.stream_error.connect(self.handle_stream_error)       # Route based on context


    @Slot(str, str)
    def update_status_bar(self, sender, message):
        """Updates the status bar with messages from components (Controller)."""
        prefix = f"[{sender}] " if sender not in ["Error", "Warning", "GemNet"] else ""
        timeout = 5000
        if sender == "GemNet" and "loaded successfully" in message:
             parts = message.split("'")
             if len(parts) >= 3: loaded_model = parts[1]; self.status_bar.showMessage(f"Model '{loaded_model}' ready.", 4000); return
             else: timeout = 4000
        elif "API Key Error" in message or "Error:" in message: timeout = 0 # Persistent error
        elif sender == "Gemini" and "Sending request" in message: timeout = 1500 # Short indicator
        elif sender == "Gemini" and "Received full response" in message: timeout = 3000 # Confirmation
        elif "Theme set to:" in message: timeout = 3000 # From theme manager

        self.status_bar.showMessage(prefix + message, timeout)

    @Slot(str, bool)
    def handle_initialization_status(self, message, success):
        """Handles the initial status message from the controller."""
        timeout = 5000
        if not success and "API Key Error" in message: timeout = 0 # Persistent
        self.status_bar.showMessage(message, timeout)

    # --- Action Handlers ---

    def handle_explain_request(self, file_paths):
        """Handles the request to explain files selected in the File Pane."""
        self.chat_pane.add_message("User", f"/explain {', '.join(map(os.path.basename, file_paths))}", is_user=True) # Show command used
        self.update_status_bar("GemNet", f"Requesting explanation for {len(file_paths)} file(s)...")
        # Controller handles setting context appropriately for explain
        self.gemini_controller.request_explanation(file_paths)

    def handle_edit_request(self, file_paths):
        """Sets up the context for editing files selected in the File Pane."""
        if file_paths:
            # 1. Open the first selected file in the editor
            opened_paths = self.editor_pane.open_files([file_paths[0]])
            if not opened_paths or opened_paths[0] != file_paths[0]:
                 self.update_status_bar("Error", f"Failed to open {os.path.basename(file_paths[0])} for editing.")
                 self.chat_pane.add_message("Error", f"Failed to open '{os.path.basename(file_paths[0])}' for editing.", is_error=True)
                 # Clear context if file opening fails
                 self.gemini_controller.set_context({})
                 return

            # 2. Set controller context for the *next* chat message
            self.gemini_controller.set_context({'action': 'edit', 'files': file_paths}) # Use full paths list for context
            # 3. Prompt user in chat to provide instructions
            base_filename = os.path.basename(file_paths[0])
            self.chat_pane.add_message("GemNet", f"Editing {base_filename}.\nPlease provide instructions in the chat.", is_status=True)
            self.update_status_bar("GemNet", f"Ready for edit instructions for {base_filename}...")
        else:
             self.update_status_bar("Warning", "Edit requested but no file paths provided.")
             self.gemini_controller.set_context({}) # Clear context if no files

    def handle_chat_message(self, message):
        """Processes user input from the chat, routing to controller."""
        # Controller now handles context and command parsing internally
        self.gemini_controller.process_user_chat(message)

    @Slot(str)
    def handle_edit_file_requested_from_chat(self, full_path):
        """Slot to open a file in the editor when requested via '/edit <file>' command."""
        print(f"[MainWindow DEBUG] Received request to open for edit: {full_path}")
        if os.path.isfile(full_path):
             opened_paths = self.editor_pane.open_files([full_path])
             if not opened_paths:
                  self.chat_pane.add_message("Error", f"Failed to open '{os.path.basename(full_path)}' in editor.", is_error=True)
                  # Clear the context set by the controller if opening fails
                  if self.gemini_controller.current_context.get('action') == 'edit':
                      self.gemini_controller.set_context({})
        else:
             self.chat_pane.add_message("Error", f"Cannot open file for edit: '{full_path}' not found.", is_error=True)
             # Clear the context set by the controller if file not found
             if self.gemini_controller.current_context.get('action') == 'edit':
                 self.gemini_controller.set_context({})


    # --- Streaming Handlers (Routing - No changes needed here) ---
    @Slot(str, str)
    def handle_stream_started(self, sender, context_type):
        """Routes stream_started signal based on context."""
        print(f"[MainWindow] Routing stream_started: {sender} / {context_type}")
        if context_type == 'editor':
            self.editor_pane.handle_stream_started(sender, context_type)
        elif context_type == 'chat' or context_type == 'file_create':
            # Reset file content buffer if starting a new file create stream
            if context_type == 'file_create':
                 print("[MainWindow] Resetting streaming file content buffer.") # Debug
                 self._streaming_file_content = ""
            self.chat_pane.handle_stream_started(sender, context_type)
        else:
            print(f"[MainWindow WARN] Unknown stream context started: {context_type}")

    @Slot(str)
    def handle_stream_chunk(self, chunk):
        """Routes stream_chunk_received signal based on controller's *current* streaming context."""
        current_stream_context = None
        if self.gemini_controller._active_worker:
             current_stream_context = self.gemini_controller._active_worker.context_type

        if current_stream_context == 'editor':
            self.editor_pane.handle_stream_chunk(chunk)
        elif current_stream_context == 'file_create':
             self._streaming_file_content += chunk
             self.chat_pane.handle_stream_chunk(chunk)
        else: # Default to chat pane (covers 'chat' context and potentially edge cases)
            self.chat_pane.handle_stream_chunk(chunk)

    @Slot(str, str)
    def handle_stream_finished(self, sender, context_type):
        """Routes stream_finished signal and handles file creation finalization."""
        print(f"[MainWindow] Routing stream_finished: {sender} / {context_type}")
        original_context = context_type # Keep original for logic below
        context_for_ui = context_type # May be modified for UI routing

        # Special handling for file creation success
        if original_context.startswith("create_success:"):
            context_for_ui = 'file_create' # Route to chat pane for visual finalization
            try:
                filename = original_context.split(":", 1)[1]
                print(f"[MainWindow] Finalizing streamed file creation for: {filename}")
                self._save_generated_file(filename, self._streaming_file_content)
                self._streaming_file_content = "" # Clear buffer after saving attempt

                # Finalize the chat visuals for the create stream
                self.chat_pane.handle_stream_finished(sender, context_for_ui)

                # Clear controller context AFTER successful processing in MainWindow
                if self.gemini_controller.current_context.get('action') == 'creating_file':
                    print("[MainWindow] Clearing controller context after successful file save.")
                    self.gemini_controller.set_context({})

            except IndexError:
                print(f"[MainWindow ERROR] Invalid 'create_success' context received: {original_context}")
                self.chat_pane.add_message("Error", "Internal error finishing file creation.", is_error=True)
                self._streaming_file_content = "" # Clear buffer on error too
                self.gemini_controller.set_context({}) # Clear context on error
            except IOError as e: # Catch specific save error from _save_generated_file
                 print(f"[MainWindow ERROR] Error during file save: {e}")
                 # Error message added by _save_generated_file already, just clear state
                 self._streaming_file_content = ""
                 self.gemini_controller.set_context({})
            except Exception as e:
                print(f"[MainWindow ERROR] Unexpected error during file finalization: {e}")
                self.chat_pane.add_message("Error", f"Unexpected error finishing file '{filename}': {e}", is_error=True)
                self._streaming_file_content = "" # Clear buffer on error too
                self.gemini_controller.set_context({}) # Clear context on error


        elif context_for_ui == 'editor':
            self.editor_pane.handle_stream_finished(sender, context_for_ui)
            # Assuming editor actions are self-contained, clear context only if needed?
            # If an edit was initiated from chat, clear context here.
            if self.gemini_controller.current_context.get('action') in ['edit', 'edit_editor']:
                 print("[MainWindow] Clearing controller context after editor stream finished.")
                 self.gemini_controller.set_context({})

        elif context_for_ui == 'chat': # Handle finish for standard chat visuals
            self.chat_pane.handle_stream_finished(sender, context_for_ui)
            # Chat doesn't usually involve persistent context, so clearing is safe
            print("[MainWindow] Clearing controller context after standard chat finished.")
            self.gemini_controller.set_context({})
        elif context_for_ui == 'file_create': # Should only happen if 'create_success:' wasn't emitted
             print(f"[MainWindow WARN] Stream finished with context 'file_create' but not 'create_success:'. Might indicate incomplete stream or error.")
             self.chat_pane.handle_stream_finished(sender, context_for_ui)
             self._streaming_file_content = "" # Clear the buffer as the creation didn't complete successfully
             self.gemini_controller.set_context({}) # Clear controller context
        else:
            print(f"[MainWindow WARN] Unknown stream context finished: {context_for_ui}")
            # Attempt to clear context as a fallback
            self.gemini_controller.set_context({})

    @Slot(str, str)
    def handle_stream_error(self, error_message, context_type):
        """Routes stream_error signal based on context and clears state."""
        print(f"[MainWindow] Routing stream_error: {context_type} - {error_message}")
        original_context_for_ui = context_type # Preserve for UI routing

        if context_type.startswith("create_success:"):
             # This shouldn't happen, error should have original context. Treat as file_create error.
             print(f"[MainWindow WARN] Stream error received with 'create_success' context? Routing as 'file_create'.")
             original_context_for_ui = 'file_create'

        # Route to appropriate UI pane
        if original_context_for_ui == 'editor':
            self.editor_pane.handle_stream_error(error_message, original_context_for_ui)
        elif original_context_for_ui in ['chat', 'file_create']:
             self.chat_pane.handle_stream_error(error_message, original_context_for_ui)
        else:
            print(f"[MainWindow WARN] Unknown stream context errored: {original_context_for_ui}. Showing in chat.")
            # Show generic error in chat pane as fallback
            self.chat_pane.add_message("Error", f"({original_context_for_ui}) {error_message}", is_error=True)

        # Clear buffer if it was a file creation attempt
        if original_context_for_ui == 'file_create':
             self._streaming_file_content = ""

        # Always clear controller context on any stream error
        print(f"[MainWindow] Clearing controller context due to stream error in context '{context_type}'.")
        self.gemini_controller.set_context({})


    # <<< Helper to save generated file content (No changes needed here) >>>
    def _save_generated_file(self, filename, content):
        """Saves the buffered content generated by Gemini to a new file."""
        current_view_dir = self.file_pane.get_current_view_path()
        save_dir = QDir.currentPath() # Default
        if os.path.isdir(current_view_dir) and current_view_dir != QDir.rootPath():
             if not os.access(current_view_dir, os.W_OK):
                 print(f"[MainWindow WARN] No write permission in File Pane dir: {current_view_dir}. Saving to CWD.")
                 self.chat_pane.add_message("Warning", f"No write permission in '{os.path.basename(current_view_dir)}'. Saving '{filename}' to application directory.", is_status=True)
             else:
                save_dir = current_view_dir
                print(f"[DEBUG MainWindow] Saving generated file in File Pane dir: {save_dir}")
        else:
             print(f"[DEBUG MainWindow] Saving generated file in CWD: {save_dir}")

        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-')).strip()
        if not safe_filename or safe_filename.startswith('.'):
            safe_filename = "gemini_generated_file.txt"
            print(f"[MainWindow WARN] Original filename '{filename}' was invalid/unsafe, using '{safe_filename}'")

        save_path = os.path.join(save_dir, safe_filename)

        new_filename = safe_filename
        if os.path.exists(save_path):
            base, ext = os.path.splitext(safe_filename)
            count = 1
            while os.path.exists(save_path):
                save_path = os.path.join(save_dir, f"{base}_{count}{ext}")
                count += 1
            new_filename = os.path.basename(save_path)
            print(f"[MainWindow WARN] File '{safe_filename}' exists. Saving as '{new_filename}'.")
            self.chat_pane.add_message("Warning", f"File '{safe_filename}' already exists. Saved as '{new_filename}'.", is_status=True)

        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)

            display_name = new_filename # Use the potentially modified filename
            if save_dir == current_view_dir:
                display_name = os.path.join(os.path.basename(current_view_dir), new_filename)
            elif save_dir == QDir.currentPath():
                 display_name = f"{new_filename} (in app directory)"
            else:
                 display_name = f"{new_filename} (in {save_dir})"

            self.chat_pane.add_message("GemNet", f"Created file: {display_name}", is_status=True)
            self.status_bar.showMessage(f"File created: {new_filename}", 4000)
            self.file_pane.refresh() # Refresh file view
        except Exception as e:
            # Raise the exception to be caught by the caller (handle_stream_finished)
            raise IOError(f"Failed to save file {new_filename}: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle('Fusion') # Optional: uncomment to force Fusion style
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# --- END OF FILE main.py ---
