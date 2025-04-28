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
        open_action.triggered.connect(self.editor_pane.request_open_files) # Connect to editor's open function

        save_action = file_menu.addAction("Save")
        save_action.triggered.connect(self.editor_pane.save_current_file) # Connect to editor's save function
        # TODO: Add Save As action

        reload_action = file_menu.addAction("Reload File")
        reload_action.triggered.connect(self.editor_pane.reload_current_file) # Connect to editor's reload function

        file_menu.addSeparator()

        refresh_files_action = file_menu.addAction("Refresh Files View") # Renamed slightly for clarity
        refresh_files_action.triggered.connect(self.file_pane.refresh) # Connect to FilePane's refresh method

        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close) # Close the main window


        # --- View Menu ---
        view_menu = menu_bar.addMenu("View")
        theme_menu = view_menu.addMenu("Themes")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)

        dark_action = QAction("Dark Theme", self, checkable=True)
        dark_action.triggered.connect(lambda: self.theme_manager.set_theme("dark"))
        theme_menu.addAction(dark_action)
        self.theme_group.addAction(dark_action)

        light_action = QAction("Light Theme", self, checkable=True)
        light_action.triggered.connect(lambda: self.theme_manager.set_theme("light"))
        theme_menu.addAction(light_action)
        self.theme_group.addAction(light_action)

        # Set initial check state based on the default theme applied
        if self.theme_manager.themes.get("dark"): # Check if dark theme exists
             dark_action.setChecked(True) # Assume dark is default if it exists
        # Add logic here if light is the default instead

        # --- Model Menu ---
        model_menu = menu_bar.addMenu("Model")
        self.select_model_action = model_menu.addAction("Select Model...")
        self.select_model_action.triggered.connect(self.open_model_selection_dialog)
        self.select_model_action.setEnabled(False) # Disabled until models load

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
        elif success:
             self.status_bar.showMessage(f"Model selection unchanged ({current}).", 3000)
        else:
            self.status_bar.showMessage("Model selection cancelled.", 3000)

    def connect_signals(self):
        """Connect signals between UI elements and the controller."""
        # --- UI -> Controller / Other UI ---
        # File Pane actions
        self.file_pane.open_files_requested.connect(self.editor_pane.open_files) # Right-click -> Open
        self.file_pane.explain_files_requested.connect(self.handle_explain_request) # Right-click -> Explain
        self.file_pane.edit_files_requested.connect(self.handle_edit_request)       # Right-click -> Edit (sets context)
        # Chat input
        self.chat_pane.user_message_submitted.connect(self.handle_chat_message)     # Handles commands & instructions
        # Editor Pane actions
        self.editor_pane.status_message_requested.connect(lambda msg: self.status_bar.showMessage(msg, 4000)) # Editor -> Status Bar

        # --- Controller -> UI ---
        # Gemini responses/output
        self.gemini_controller.explanation_ready.connect(lambda sender, msg: self.chat_pane.add_message(sender, msg)) # Handles explain output (mostly unused now?)
        self.gemini_controller.chat_response_ready.connect(lambda sender, msg: self.chat_pane.add_message(sender, msg)) # Handles general/error chat output
        self.gemini_controller.file_content_generated.connect(self.handle_generated_file) # Handles /create output
        self.gemini_controller.editor_content_generated.connect(self.editor_pane.set_current_content) # Handles edit output (/edit, /edit_editor)
        # Status/Info updates
        self.gemini_controller.status_update.connect(self.update_status_bar)
        self.gemini_controller.initialization_status.connect(self.handle_initialization_status)
        self.gemini_controller.available_models_updated.connect(self.handle_available_models_update)
        # Signals for setting up chat-based edit flows
        self.gemini_controller.edit_file_requested_from_chat.connect(self.handle_edit_file_requested_from_chat) # Handles /edit <file> step 1 (open file)
        self.gemini_controller.edit_context_set_from_chat.connect(lambda msg: self.chat_pane.add_message("GemNet", msg, is_status=True)) # Handles /edit or /edit_editor setup message

    @Slot(str, str)
    def update_status_bar(self, sender, message):
        """Updates the status bar with messages from components (Controller)."""
        prefix = f"[{sender}] " if sender not in ["Error", "Warning", "GemNet"] else ""
        timeout = 5000 # Default timeout
        # Special handling for model loading success
        if sender == "GemNet" and "loaded successfully" in message:
             parts = message.split("'")
             if len(parts) >= 3:
                 loaded_model = parts[1]
                 self.status_bar.showMessage(f"Model '{loaded_model}' ready.", 4000)
                 return # Don't show generic message too
             else:
                 timeout = 4000 # Shorter timeout for generic success
        # Persistent message for API key error
        elif "API Key Error" in message:
             timeout = 0 # 0 means show indefinitely

        self.status_bar.showMessage(prefix + message, timeout)

    @Slot(str, bool)
    def handle_initialization_status(self, message, success):
        """Handles the initial status message from the controller."""
        if not success and "API Key Error" in message:
             self.status_bar.showMessage(message) # Persistent API key error
        else:
             self.status_bar.showMessage(message, 5000)

    # --- Action Handlers ---

    # Triggered by RIGHT-CLICK -> Explain on File Pane
    def handle_explain_request(self, file_paths):
        """Handles the request to explain files selected in the File Pane."""
        self.chat_pane.add_message("User", f"Explain file(s): {', '.join(map(os.path.basename, file_paths))}")
        self.update_status_bar("GemNet", f"Requesting explanation for {len(file_paths)} file(s)...")
        # Controller's request_explanation now sends output directly to chat
        self.gemini_controller.request_explanation(file_paths)

    # Triggered by RIGHT-CLICK -> Edit on File Pane
    def handle_edit_request(self, file_paths):
        """Sets up the context for editing files selected in the File Pane."""
        if file_paths:
            # 1. Open the first selected file in the editor
            self.editor_pane.open_files([file_paths[0]])
            # 2. Set controller context for the *next* chat message
            self.gemini_controller.set_context({'action': 'edit', 'files': file_paths})
            # 3. Prompt user in chat to provide instructions
            base_filename = os.path.basename(file_paths[0])
            self.chat_pane.add_message("GemNet", f"Editing {base_filename}.\nPlease provide instructions in the chat.", is_status=True)
            self.update_status_bar("GemNet", f"Ready for edit instructions for {base_filename}...")
        else:
             self.update_status_bar("Warning", "Edit requested but no file paths provided.")

    # Triggered by Chat Input field submission
    def handle_chat_message(self, message):
        """Processes user input from the chat, routing to controller."""
        # Check context *before* echoing to avoid echoing edit instructions
        action = self.gemini_controller.current_context.get('action')
        if action not in ['edit', 'edit_editor']:
            self.chat_pane.add_message("User", message) # Echo normal chat/commands
        else:
            # Optionally add the instruction to the chat for clarity, but maybe label it
            filename_hint = "current editor"
            if action == 'edit':
                files = self.gemini_controller.current_context.get('files')
                if files: filename_hint = os.path.basename(files[0])
            elif action == 'edit_editor':
                 path = self.gemini_controller.current_context.get('path')
                 if path: filename_hint = os.path.basename(path)

            self.chat_pane.add_message("User", f"[Edit Instruction for {filename_hint}]: {message}")


        # Let the controller handle parsing commands, context, or standard chat
        self.gemini_controller.process_user_chat(message)

    @Slot(str, str)
    def handle_generated_file(self, filename, content):
        """Handles the signal to save content generated by Gemini to a new file."""
        # Save relative to file_pane's current directory if possible?
        current_view_dir = self.file_pane.get_current_view_path()
        # Check if current_view_dir is sensible (not root, exists)
        save_dir = QDir.currentPath() # Default to app CWD
        if os.path.isdir(current_view_dir) and current_view_dir != QDir.rootPath():
             save_dir = current_view_dir
             print(f"[DEBUG MainWindow] Saving generated file in File Pane dir: {save_dir}")
        else:
             print(f"[DEBUG MainWindow] Saving generated file in CWD: {save_dir}")


        save_path = os.path.join(save_dir, filename)
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            # Use status=True for GemNet messages for potential styling
            # Show relative path if saved in view dir, otherwise just filename
            display_name = filename
            if save_dir == current_view_dir:
                 display_name = os.path.join(os.path.basename(current_view_dir), filename) # Show parent dir + file
            else:
                 display_name = f"{filename} (in app directory)"

            self.chat_pane.add_message("GemNet", f"Created file: {display_name}", is_status=True)
            self.status_bar.showMessage(f"File created: {filename}", 4000)
            self.file_pane.refresh() # Refresh file view
        except Exception as e:
            self.chat_pane.add_message("Error", f"Failed to create file {filename}: {e}")
            self.status_bar.showMessage(f"Error creating file: {e}", 5000)

    @Slot(str)
    def handle_edit_file_requested_from_chat(self, full_path):
        """Slot to open a file in the editor when requested via '/edit <file>' command."""
        print(f"[MainWindow DEBUG] Received request to open for edit: {full_path}")
        if os.path.isfile(full_path):
             self.editor_pane.open_files([full_path])
        else:
             # This case should ideally be caught by the controller, but good fallback
             self.chat_pane.add_message("Error", f"Cannot open file for edit: '{full_path}' not found.")
             self.status_bar.showMessage(f"Error: File not found for edit request: {full_path}", 5000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Force style for better font rendering on some platforms (optional)
    # app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# --- END OF FILE main.py ---