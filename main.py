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
        self.theme_manager = ThemeManager(self)

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
        self.theme_manager.set_theme("dark") # Apply theme after layout exists
        self.gemini_controller.update_available_models() # Fetch models after setup

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
        dark_action = QAction("Dark Theme", self, checkable=True)
        dark_action.triggered.connect(lambda: self.theme_manager.set_theme("dark"))
        theme_menu.addAction(dark_action); self.theme_group.addAction(dark_action)
        light_action = QAction("Light Theme", self, checkable=True)
        light_action.triggered.connect(lambda: self.theme_manager.set_theme("light"))
        theme_menu.addAction(light_action); self.theme_group.addAction(light_action)
        if self.theme_manager.themes.get("dark"): dark_action.setChecked(True)

        # --- Model Menu ---
        model_menu = menu_bar.addMenu("Model")
        self.select_model_action = model_menu.addAction("Select Model...")
        self.select_model_action.triggered.connect(self.open_model_selection_dialog)
        self.select_model_action.setEnabled(False)
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

    # <<< MODIFIED connect_signals >>>
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


        # --- REMOVED OLD SIGNALS ---
        # self.gemini_controller.explanation_ready.connect(lambda sender, msg: self.chat_pane.add_message(sender, msg))
        # self.gemini_controller.chat_response_ready.connect(lambda sender, msg: self.chat_pane.add_message(sender, msg))
        # self.gemini_controller.file_content_generated.connect(self.handle_generated_file)
        # self.gemini_controller.editor_content_generated.connect(self.editor_pane.set_current_content)


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
        # User message is added in ChatPane now
        # self.chat_pane.add_message("User", f"Explain file(s): {', '.join(map(os.path.basename, file_paths))}")
        self.chat_pane.add_message("User", f"/explain {', '.join(map(os.path.basename, file_paths))}", is_user=True) # Show command used
        self.update_status_bar("GemNet", f"Requesting explanation for {len(file_paths)} file(s)...")
        self.gemini_controller.request_explanation(file_paths)

    def handle_edit_request(self, file_paths):
        """Sets up the context for editing files selected in the File Pane."""
        if file_paths:
            # 1. Open the first selected file in the editor
            # Use return value to ensure it was opened successfully before proceeding
            opened_paths = self.editor_pane.open_files([file_paths[0]])
            if not opened_paths or opened_paths[0] != file_paths[0]:
                 self.update_status_bar("Error", f"Failed to open {os.path.basename(file_paths[0])} for editing.")
                 self.chat_pane.add_message("Error", f"Failed to open '{os.path.basename(file_paths[0])}' for editing.", is_error=True)
                 return

            # 2. Set controller context for the *next* chat message
            self.gemini_controller.set_context({'action': 'edit', 'files': file_paths}) # Use full paths list for context
            # 3. Prompt user in chat to provide instructions
            base_filename = os.path.basename(file_paths[0])
            self.chat_pane.add_message("GemNet", f"Editing {base_filename}.\nPlease provide instructions in the chat.", is_status=True)
            self.update_status_bar("GemNet", f"Ready for edit instructions for {base_filename}...")
        else:
             self.update_status_bar("Warning", "Edit requested but no file paths provided.")

    def handle_chat_message(self, message):
        """Processes user input from the chat, routing to controller."""
        # Controller now handles context and command parsing internally
        self.gemini_controller.process_user_chat(message)

    # --- REMOVED handle_generated_file (handled via streaming finish) ---
    # @Slot(str, str) def handle_generated_file(...): ...

    @Slot(str)
    def handle_edit_file_requested_from_chat(self, full_path):
        """Slot to open a file in the editor when requested via '/edit <file>' command."""
        print(f"[MainWindow DEBUG] Received request to open for edit: {full_path}")
        if os.path.isfile(full_path):
             opened_paths = self.editor_pane.open_files([full_path])
             if not opened_paths:
                  self.chat_pane.add_message("Error", f"Failed to open '{os.path.basename(full_path)}' in editor.", is_error=True)
                  self.gemini_controller.set_context({}) # Clear broken context
        else:
             self.chat_pane.add_message("Error", f"Cannot open file for edit: '{full_path}' not found.", is_error=True)
             self.gemini_controller.set_context({}) # Clear broken context


    # --- Streaming Handlers (Routing) ---
    @Slot(str, str)
    def handle_stream_started(self, sender, context_type):
        """Routes stream_started signal based on context."""
        print(f"[MainWindow] Routing stream_started: {sender} / {context_type}")
        if context_type == 'editor':
            self.editor_pane.handle_stream_started(sender, context_type)
        elif context_type == 'chat' or context_type == 'file_create':
            # Reset file content buffer if starting a new file create stream
            if context_type == 'file_create':
                 self._streaming_file_content = ""
            self.chat_pane.handle_stream_started(sender, context_type)
        else:
            print(f"[MainWindow WARN] Unknown stream context started: {context_type}")

    @Slot(str)
    def handle_stream_chunk(self, chunk):
        """Routes stream_chunk_received signal based on controller's *current* context."""
        # We need to know the context the controller is *currently* processing
        # This is a bit fragile. Relying on controller context state.
        active_context = self.gemini_controller.current_context.get('action') # e.g., 'edit', 'edit_editor', 'creating_file', None (for chat/explain)
        # print(f"[MainWindow] Routing chunk. Active context: {active_context}") # DEBUG - Can be noisy

        if active_context in ['edit', 'edit_editor']:
            self.editor_pane.handle_stream_chunk(chunk)
        elif active_context == 'creating_file':
             self._streaming_file_content += chunk # Buffer content
             self.chat_pane.handle_stream_chunk(chunk) # Also show in chat
        else: # Default to chat pane (covers None, 'explain', maybe initial 'create' state?)
            self.chat_pane.handle_stream_chunk(chunk)

    @Slot(str, str)
    def handle_stream_finished(self, sender, context_type):
        """Routes stream_finished signal and handles file creation finalization."""
        print(f"[MainWindow] Routing stream_finished: {sender} / {context_type}")

        # Special handling for file creation success
        if context_type.startswith("create_success:"):
            filename = context_type.split(":", 1)[1]
            print(f"[MainWindow] Finalizing streamed file creation for: {filename}")
            # Now call the save logic with the buffered content
            self._save_generated_file(filename, self._streaming_file_content)
            self._streaming_file_content = "" # Clear buffer
            # Also finalize the chat visuals for the create stream
            self.chat_pane.handle_stream_finished(sender, 'file_create') # Use generic type for visuals
            # Ensure controller context is cleared if necessary (should be done in controller)
            if self.gemini_controller.current_context.get('action') == 'creating_file':
                 self.gemini_controller.set_context({})

        elif context_type == 'editor':
            self.editor_pane.handle_stream_finished(sender, context_type)
        elif context_type == 'chat' or context_type == 'file_create': # Handle finish for chat/file_create visuals
            self.chat_pane.handle_stream_finished(sender, context_type)
        else:
            print(f"[MainWindow WARN] Unknown stream context finished: {context_type}")

    @Slot(str, str)
    def handle_stream_error(self, error_message, context_type):
        """Routes stream_error signal based on context."""
        print(f"[MainWindow] Routing stream_error: {context_type} - {error_message}")
        if context_type == 'editor':
            self.editor_pane.handle_stream_error(error_message, context_type)
        elif context_type == 'chat' or context_type == 'file_create':
             self.chat_pane.handle_stream_error(error_message, context_type)
             # If file creation failed, clear buffer
             if context_type == 'file_create':
                  self._streaming_file_content = ""
        else:
            print(f"[MainWindow WARN] Unknown stream context errored: {context_type}")
            # Show generic error in chat pane as fallback?
            self.chat_pane.add_message("Error", f"({context_type}) {error_message}", is_error=True)

        # Ensure controller context is cleared on error to prevent stuck states
        self.gemini_controller.set_context({})


    # <<< NEW Helper to save generated file content >>>
    def _save_generated_file(self, filename, content):
        """Saves the buffered content generated by Gemini to a new file."""
        current_view_dir = self.file_pane.get_current_view_path()
        save_dir = QDir.currentPath() # Default
        if os.path.isdir(current_view_dir) and current_view_dir != QDir.rootPath():
             save_dir = current_view_dir
             print(f"[DEBUG MainWindow] Saving generated file in File Pane dir: {save_dir}")
        else:
             print(f"[DEBUG MainWindow] Saving generated file in CWD: {save_dir}")

        save_path = os.path.join(save_dir, filename)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            display_name = filename
            if save_dir == current_view_dir: display_name = os.path.join(os.path.basename(current_view_dir), filename)
            else: display_name = f"{filename} (in app directory)"

            # Use add_message for consistency, marked as status
            self.chat_pane.add_message("GemNet", f"Created file: {display_name}", is_status=True)
            self.status_bar.showMessage(f"File created: {filename}", 4000)
            self.file_pane.refresh()
        except Exception as e:
            self.chat_pane.add_message("Error", f"Failed to save created file {filename}: {e}", is_error=True)
            self.status_bar.showMessage(f"Error saving file: {e}", 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# --- END OF FILE main.py ---