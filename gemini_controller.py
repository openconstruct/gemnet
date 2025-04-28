# --- START OF FILE gemini_controller.py ---

from PySide6.QtCore import QObject, Signal, Slot, QThread # Added Slot, QThread
import os
# import time
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import typing

# Forward declaration hint for type hinting
if typing.TYPE_CHECKING:
    from file_pane import FilePane
    from editor_pane import EditorPane

# --- Worker Class ---
class GeminiWorker(QObject):
    """Runs the Gemini API call in a separate thread."""
    # Signals mirrored from controller for thread communication
    started = Signal(str, str)      # sender, context_type
    chunk_received = Signal(str)    # chunk_text
    finished = Signal(str, str)     # sender, context_type
    error = Signal(str, str)        # error_message, context_type

    def __init__(self, model_name: str, prompt: str, context_type: str, sender: str = "Gemini"):
        super().__init__()
        self.model_name = model_name
        self.prompt = prompt
        self.context_type = context_type
        self.sender = sender
        self._is_cancelled = False # Basic cancellation flag

    @Slot()
    def run(self):
        """Performs the blocking API call and emits signals."""
        model_instance = None
        try:
            print(f"[Worker {QThread.currentThread()}] Configuring Gemini for worker...")
            # It's generally safer to re-configure/get model within the thread
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in worker thread.")
            genai.configure(api_key=api_key) # Configure within the thread

            full_model_name = f"models/{self.model_name}"
            safety_settings = [{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            model_instance = genai.GenerativeModel(full_model_name, safety_settings=safety_settings)

            print(f"[Worker {QThread.currentThread()}] Starting API call...")
            # --- Emit started signal *before* blocking call ---
            self.started.emit(self.sender, self.context_type)

            response = model_instance.generate_content(self.prompt, stream=True)

            print(f"[Worker {QThread.currentThread()}] --- Gemini Response Stream ({self.context_type}) ---")
            for chunk in response:
                 if self._is_cancelled:
                      print(f"[Worker {QThread.currentThread()}] Stream cancelled by request.")
                      # Don't emit finished, maybe a specific cancelled signal or error?
                      self.error.emit("Stream cancelled", self.context_type)
                      return

                 # Check for safety blocks
                 if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                      reason = chunk.prompt_feedback.block_reason.name
                      rating = next((r for r in chunk.prompt_feedback.safety_ratings if r.blocked), None)
                      category = getattr(rating.category, 'name', 'UNKNOWN') if rating else 'UNKNOWN'
                      error_msg = f"Error: Blocked by safety filters. Reason: {reason}. Category: {category}."
                      print(f"[Worker {QThread.currentThread()}] Stream blocked: {reason} ({category})")
                      self.error.emit(error_msg, self.context_type)
                      return # Stop processing

                 if hasattr(chunk, 'text'):
                    # print(chunk.text, end="", flush=True) # DEBUG on Worker Thread Console
                    self.chunk_received.emit(chunk.text)
                 # else:
                    # print(f"[Worker {QThread.currentThreadId()}] [Stream Info Chunk - No Text]")
                    pass

            # --- Finished successfully ---
            print(f"\n[Worker {QThread.currentThread()}] --- End Gemini Stream ---")
            self.finished.emit(self.sender, self.context_type)

        # --- Error Handling within the Thread ---
        except google_exceptions.PermissionDenied as e: msg = f"API Permission Denied: {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.ResourceExhausted as e: msg = f"API Quota Exceeded: {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.InvalidArgument as e:
            if "User location is not supported" in str(e): msg = "API Error: Location not supported."
            elif "API key not valid" in str(e): msg = f"API Error: API key not valid. {e}"
            elif "found no valid candidate" in str(e): msg = f"API Error: No valid candidate found (Safety/Prompt issue?). {e}"
            else: msg = f"API Invalid Argument: {e}"
            self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.NotFound as e: msg = f"API Not Found: {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.FailedPrecondition as e: msg = f"API Precondition Failed (Billing?): {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.InternalServerError as e: msg = f"API Internal Server Error: {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except google_exceptions.ServiceUnavailable as e: msg = f"API Service Unavailable: {e}"; self.error.emit(msg, self.context_type); print(f"[Worker Error] {msg}")
        except Exception as e:
            error_msg = f"Worker Thread Error: {type(e).__name__} - {e}"
            self.error.emit(error_msg, self.context_type)
            print(error_msg) # Also print for debugging
        finally:
            # Important: Ensure finished signal is emitted if run completes without error
            # This is handled above now. If an error occurs, error signal is emitted.
            pass

    def cancel(self):
        self._is_cancelled = True

# --- Main Controller Class ---
class GeminiController(QObject):
    # Keep original signals for UI connection
    status_update = Signal(str, str)
    available_models_updated = Signal(list)
    initialization_status = Signal(str, bool)
    edit_file_requested_from_chat = Signal(str)
    edit_context_set_from_chat = Signal(str)
    stream_started = Signal(str, str)
    stream_chunk_received = Signal(str)
    stream_finished = Signal(str, str)
    stream_error = Signal(str, str)

    def __init__(self, file_pane_ref: 'FilePane', editor_pane_ref: 'EditorPane'):
        super().__init__()
        self.file_pane = file_pane_ref
        self.editor_pane = editor_pane_ref
        self.current_context = {}
        self.selected_model_name = "gemini-1.5-flash-latest"
        self.available_models = []
        self.model_instance = None # Keep for non-streaming potentially, but worker handles streaming model
        self._is_configured = False
        self._active_thread = None # Keep track of the running thread
        self._active_worker = None # Keep track of the running worker
        self._configure_gemini()

    def _configure_gemini(self):
        """Configures the Gemini API client using environment variables."""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.initialization_status.emit("API Key Error: GOOGLE_API_KEY environment variable not set.", False)
                self.status_update.emit("Error", "Gemini API Key not found. Please set GOOGLE_API_KEY.")
                self._is_configured = False; return

            # No need to configure globally here if worker does it, but harmless
            genai.configure(api_key=api_key)
            self._is_configured = True
            self.initialization_status.emit("Gemini API Configured.", True)
            self.status_update.emit("GemNet", "Gemini API configured successfully.")
            # Don't load model instance here for streaming
            # self.set_selected_model(self.selected_model_name, initial_load=True)
            self.update_available_models() # Fetch models after configuring API key access
        except Exception as e:
            error_msg = f"Gemini Configuration Failed: {e}"
            self.initialization_status.emit(error_msg, False)
            self.status_update.emit("Error", f"Failed to configure Gemini: {e}")
            self._is_configured = False
            self.available_models = []; self.available_models_updated.emit([])

    def update_available_models(self):
        """Fetches and updates the list of available generative models."""
        if not self._is_configured:
            self.status_update.emit("GemNet", "Cannot fetch models, API not configured.")
            self.available_models = []; self.available_models_updated.emit([])
            return
        try:
            self.status_update.emit("GemNet", "Fetching available Gemini models...")
            models = genai.list_models()
            self.available_models = []
            # Filter for models supporting 'generateContent' and use the short name
            for m in models:
                # Example: m.name is 'models/gemini-1.5-flash-latest'
                if 'generateContent' in m.supported_generation_methods and m.name.startswith("models/"):
                    self.available_models.append(m.name.split('/')[-1]) # Get 'gemini-1.5-flash-latest'

            # Default model logic
            if not self.available_models:
                 self.status_update.emit("Warning", "No suitable text generation models found.")
                 self.selected_model_name = ""; # No models, clear selection
            elif self.selected_model_name not in self.available_models:
                # Try to find flash, otherwise take the first
                new_default = next((m for m in self.available_models if 'flash' in m), self.available_models[0])
                self.status_update.emit("Warning", f"Selected model '{self.selected_model_name}' invalid or unavailable. Resetting to '{new_default}'.")
                self.selected_model_name = new_default # Update the selection state

            self.available_models_updated.emit(self.available_models) # Update UI list
            if self.available_models:
                self.status_update.emit("GemNet", f"Found {len(self.available_models)} models. Current: {self.selected_model_name}")

        except google_exceptions.PermissionDenied as e:
             msg = f"API Key Error: Could not list models. Check Key Permissions. {e}"
             self.status_update.emit("Error", msg); print(msg)
             self.available_models = []; self.available_models_updated.emit([])
        except google_exceptions.InvalidArgument as e:
            if "API key not valid" in str(e): msg = f"API Key Error: Key is not valid. {e}"
            else: msg = f"API Error listing models: {e}"
            self.status_update.emit("Error", msg); print(msg)
            self.available_models = []; self.available_models_updated.emit([])
        except Exception as e:
            self.status_update.emit("Error", f"Could not fetch Gemini models: {e}")
            self.available_models = []; self.available_models_updated.emit([])

    # No longer loads instance, just sets name
    def set_selected_model(self, model_short_name, initial_load=False):
        """Sets the *name* of the active Gemini model."""
        if not self._is_configured and not initial_load:
             self.status_update.emit("Error", "Gemini API not configured. Cannot set model."); return
        # Check if the requested model is actually in our fetched list (optional but good practice)
        if self.available_models and model_short_name not in self.available_models and not initial_load:
             self.status_update.emit("Warning", f"Model '{model_short_name}' not in known list. Selection may fail if invalid.")

        self.selected_model_name = model_short_name
        self.status_update.emit("GemNet", f"Selected model set to: {model_short_name}")
        # No need to load the model instance here anymore for streaming


    def _read_files(self, file_paths):
        # (Keep _read_files as it was)
        contents = {}; total_size = 0
        max_size_per_file = 250*1024; max_total_size = 1.5*1024*1024
        for path in file_paths:
            try:
                if not os.path.exists(path): self.status_update.emit("Error", f"File not found: {path}"); continue
                if not os.path.isfile(path): self.status_update.emit("Warning", f"Skipping directory: {os.path.basename(path)}"); continue
                f_size = os.path.getsize(path)
                if f_size > max_size_per_file: self.status_update.emit("Warning", f"Skipping large file {os.path.basename(path)}"); continue
                if total_size + f_size > max_total_size: self.status_update.emit("Warning", f"Total size limit reached, skipping {os.path.basename(path)}"); break
                self.status_update.emit("GemNet", f"Reading file: {os.path.basename(path)}...")
                content = None
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with open(path, 'r', encoding=encoding) as f: content = f.read(); break
                    except UnicodeDecodeError: continue
                    except Exception as e_read: self.status_update.emit("Error", f"Error reading {path}: {e_read}"); content = None; break
                if content is None:
                     if 'e_read' in locals() and not isinstance(e_read, UnicodeDecodeError): pass # Error already emitted
                     else: self.status_update.emit("Error", f"Could not decode {path}");
                     continue
                contents[path] = content; total_size += f_size
            except Exception as e: self.status_update.emit("Error", f"Could not access {path}: {e}")
        return contents

    # <<< REPLACED _call_gemini_api with _stream_gemini_api >>>
    def _stream_gemini_api(self, prompt: str, context_type: str, sender: str = "Gemini"):
        """
        Starts the Gemini API streaming call in a separate thread.
        """
        if not self._is_configured:
             self.stream_error.emit("Error: Gemini API not configured.", context_type)
             return
        if not self.selected_model_name:
            self.stream_error.emit("Error: No model selected.", context_type)
            return

        # --- Cancel previous thread if running ---
        if self._active_thread and self._active_thread.isRunning():
            print("[Controller] Attempting to cancel previous stream request...")
            if self._active_worker:
                self._active_worker.cancel() # Signal worker to stop
            # Optionally wait a short time? Or just start the new one?
            # self._active_thread.quit() # Request thread to quit
            # self._active_thread.wait(1000) # Wait briefly for clean exit

        self.status_update.emit(sender, f"Sending request to {self.selected_model_name}...")
        print(f"\n--- Gemini Prompt ({self.selected_model_name}) ---\n{prompt[:500]}...\n--- End Prompt ---")

        # --- Setup Worker and Thread ---
        self._active_thread = QThread()
        self._active_worker = GeminiWorker(self.selected_model_name, prompt, context_type, sender)
        self._active_worker.moveToThread(self._active_thread)

        # --- Connect Worker Signals to Controller Slots (to run on main thread) ---
        self._active_worker.started.connect(self.on_stream_started)
        self._active_worker.chunk_received.connect(self.on_stream_chunk_received)
        self._active_worker.finished.connect(self.on_stream_finished)
        self._active_worker.error.connect(self.on_stream_error)

        # --- Connect Thread Signals ---
        self._active_thread.started.connect(self._active_worker.run) # Start worker's task when thread starts
        # Cleanup after worker finishes (or errors)
        self._active_worker.finished.connect(self._cleanup_thread)
        self._active_worker.error.connect(self._cleanup_thread) # Also cleanup on error

        # Start the thread
        self._active_thread.start()


    # --- Slots to receive signals from Worker (run on Main Thread) ---
    @Slot(str, str)
    def on_stream_started(self, sender, context_type):
        print(f"[Controller MainThread] Worker reported stream started ({sender}/{context_type})")
        self.stream_started.emit(sender, context_type) # Re-emit for UI

    @Slot(str)
    def on_stream_chunk_received(self, chunk):
        # print(f"[Controller MainThread] Worker sent chunk: {chunk[:30]}...") # DEBUG
        self.stream_chunk_received.emit(chunk) # Re-emit for UI

    @Slot(str, str)
    def on_stream_finished(self, sender, context_type):
        print(f"[Controller MainThread] Worker reported stream finished ({sender}/{context_type})")
        self.status_update.emit(sender, "Received full response.")
        self.stream_finished.emit(sender, context_type) # Re-emit for UI

    @Slot(str, str)
    def on_stream_error(self, error_message, context_type):
        print(f"[Controller MainThread] Worker reported error ({context_type}): {error_message}")
        self.status_update.emit("Error", f"Stream Error: {error_message}")
        self.stream_error.emit(error_message, context_type) # Re-emit for UI

    @Slot()
    def _cleanup_thread(self):
        """Cleans up the thread and worker after completion or error."""
        print("[Controller MainThread] Cleaning up worker thread...")
        if self._active_thread and self._active_thread.isRunning():
             self._active_thread.quit() # Request thread to stop event loop
             self._active_thread.wait(500) # Wait briefly for it to finish

        # Schedule objects for deletion
        if self._active_worker:
             self._active_worker.deleteLater()
        if self._active_thread:
             self._active_thread.deleteLater()

        self._active_thread = None
        self._active_worker = None
        print("[Controller MainThread] Cleanup complete.")

    # --- Request Methods (Unchanged, they now call _stream_gemini_api) ---

    def request_explanation(self, file_paths):
        # (Keep implementation as it was, it calls _stream_gemini_api)
        contents = self._read_files(file_paths)
        if not contents:
            self.stream_error.emit("No files were read successfully to explain.", 'chat')
            return

        prompt = "You are a helpful assistant integrated into a development tool called GemNet.\n"
        prompt += "Please explain the purpose and high-level functionality of the following file(s):\n\n"
        for path, content in contents.items():
            prompt += f"--- File: {os.path.basename(path)} ---\n"
            truncated_content = content[:10000]
            prompt += truncated_content + ("\n[... content truncated ...]\n" if len(content) > 10000 else "")
            prompt += "---\n"
        prompt += "Provide the explanation below:"

        self._stream_gemini_api(prompt, context_type='chat', sender="Gemini")
        self.current_context = {}


    def request_edit(self, file_paths, instructions):
        # (Keep implementation as it was, it calls _stream_gemini_api)
        contents = self._read_files(file_paths)
        if not contents or not file_paths:
            self.stream_error.emit("Cannot edit: File(s) could not be read or path missing.", 'editor')
            return

        target_file_path = file_paths[0]
        target_filename = os.path.basename(target_file_path)
        target_content = contents.get(target_file_path)

        if target_content is None:
             self.stream_error.emit(f"Could not read '{target_filename}' for editing.", 'editor')
             return

        prompt = self._build_edit_prompt(target_filename, target_content, instructions, contents)
        self._stream_gemini_api(prompt, context_type='editor', sender="Gemini")

    def _build_edit_prompt(self, target_filename, target_content, instructions, context_files=None):
        # (Keep implementation as it was)
        prompt = "You are a helpful coding assistant integrated into a development tool called GemNet.\n"
        prompt += f"The user wants to modify the code/text (currently in '{target_filename}' if known, otherwise in the editor tab) based on the following instructions.\n"
        if context_files:
             other_files = {p: c for p, c in context_files.items() if os.path.basename(p) != target_filename}
             if other_files:
                 prompt += "Additional context from other selected files is provided below the main content.\n"
        prompt += f"Instructions: '{instructions}'\n\n"
        prompt += f"--- Content to Edit ('{target_filename}' or Current Tab) ---\n"
        truncated_content = target_content[:20000]
        prompt += truncated_content + ("\n[... content truncated ...]\n" if len(target_content) > 20000 else "")
        prompt += "\n---\n"
        if context_files and other_files:
            for path, content in other_files.items():
                prompt += f"\n--- Context File: {os.path.basename(path)} ---\n"
                truncated_context = content[:5000]
                prompt += truncated_context + ("\n[... content truncated ...]\n" if len(content) > 5000 else "")
                prompt += "\n---\n"
        prompt += f"\nBased ONLY on the provided content and instructions, generate the COMPLETE, modified content.\n"
        prompt += f"IMPORTANT: Output *only* the raw, modified code/text. Do not include explanations, introductions, apologies, ```markdown formatting```, or any text other than the content itself."
        return prompt

    def process_user_chat(self, message):
        # (Keep implementation as it was, it calls relevant request methods or _stream_gemini_api)
        print(f"[Controller DEBUG] Processing chat message: '{message[:100]}...'")
        action = self.current_context.get('action')

        if action == 'edit':
            files = self.current_context.get('files')
            if files:
                 print("[Controller DEBUG] Handling message as edit instruction (context: file).")
                 self.request_edit(files, message)
                 self.current_context = {}
                 return
            else: # Error case
                 self.stream_error.emit("Internal Error: Edit context lost file information.", 'editor')
                 self.current_context = {}
                 return
        elif action == 'edit_editor':
            print("[Controller DEBUG] Handling message as edit instruction (context: editor).")
            editor_path = self.current_context.get('path', 'current tab')
            editor_content = self.editor_pane.get_current_content()
            if editor_content is not None:
                 filename_hint = os.path.basename(editor_path) if editor_path and editor_path != 'current tab' else 'current tab'
                 prompt = self._build_edit_prompt(filename_hint, editor_content, message)
                 self._stream_gemini_api(prompt, context_type='editor', sender="Gemini")
            else: self.stream_error.emit("Cannot edit: No active editor tab found or content is inaccessible.", 'editor')
            self.current_context = {}
            return
        elif action == 'create':
            print("[Controller DEBUG] Handling message as create description.")
            filename = self.current_context.get('filename')
            description = message
            if filename:
                content_prompt = "You are a helpful file generation assistant called GemNet.\n"
                content_prompt += f"The user wants to create a file named '{filename}' with the following purpose/content described:\n"
                content_prompt += f"Description: '{description}'\n\n"
                content_prompt += "Generate ONLY the raw file content based on the description.\n"
                content_prompt += "IMPORTANT: Do NOT include the filename, explanations, introductions, apologies, ```markdown formatting```, or any text other than the required file content itself."
                self.current_context['action'] = 'creating_file' # Update state
                self._stream_gemini_api(content_prompt, context_type='file_create', sender="Gemini")
                # Context cleared by MainWindow on create_success finish signal
            else: # Error case
                 self.stream_error.emit("Internal Error: Create context lost filename information.", 'chat')
                 self.current_context = {}
            return

        # --- Command parsing ---
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args_str = parts[1].strip() if len(parts) > 1 else ""
        current_dir = self.file_pane.get_current_view_path()

        if command == "/create":
             filename_raw = args_str
             if filename_raw:
                 safe_filename = "".join(c for c in filename_raw if c.isalnum() or c in ('.', '_', '-', ' ')).strip()
                 if not safe_filename or safe_filename in [".", "_", "-"]: safe_filename = f"gemini_generated_{safe_filename}.txt" if safe_filename else "gemini_generated_file.txt"
                 self.set_context({'action': 'create', 'filename': safe_filename})
                 prompt_msg = f"Creating '{safe_filename}'. Provide description/content prompt in next message."
                 self.edit_context_set_from_chat.emit(prompt_msg)
                 self.status_update.emit("GemNet", f"Ready for description for {safe_filename}...")
             else: self.stream_error.emit("Usage: /create <filename>\n(Provide description in the next message)", 'chat')
             return
        elif command == "/explain":
            filename = args_str
            if filename:
                 full_path = os.path.join(current_dir, filename)
                 if os.path.isfile(full_path):
                     self.status_update.emit("GemNet", f"Requesting explanation for {filename}...")
                     self.request_explanation([full_path])
                 else: self.stream_error.emit(f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.", 'chat')
            else: self.stream_error.emit("Usage: /explain <filename>", 'chat')
            return
        elif command == "/edit":
             filename = args_str
             if filename:
                 full_path = os.path.join(current_dir, filename)
                 if os.path.isfile(full_path):
                     self.edit_file_requested_from_chat.emit(full_path)
                     self.set_context({'action': 'edit', 'files': [full_path]})
                     prompt_msg = f"Editing '{filename}'. Provide instructions in next message."
                     self.edit_context_set_from_chat.emit(prompt_msg)
                     self.status_update.emit("GemNet", f"Ready for edit instructions for {filename}...")
                 else: self.stream_error.emit(f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.", 'chat')
             else: self.stream_error.emit("Usage: /edit <filename>", 'chat')
             return
        elif command == "/explain_editor":
            editor_content = self.editor_pane.get_current_content()
            editor_path = self.editor_pane.get_current_path()
            filename_hint = os.path.basename(editor_path) if editor_path else "current tab"
            if editor_content is not None:
                 self.status_update.emit("GemNet", f"Requesting explanation for {filename_hint}...")
                 prompt = "You are a helpful assistant integrated into a development tool called GemNet.\n"
                 prompt += f"Please explain the purpose and high-level functionality of the following code/text currently open in the editor tab (source file: '{filename_hint}'):\n\n"
                 prompt += f"--- Editor Content ---\n"
                 truncated_content = editor_content[:15000]
                 prompt += truncated_content + ("\n[... content truncated ...]\n" if len(editor_content) > 15000 else "")
                 prompt += "\n---\n"
                 prompt += "Provide the explanation below:"
                 self._stream_gemini_api(prompt, context_type='chat', sender="Gemini")
            else: self.stream_error.emit("Error: No active editor tab found to explain.", 'chat')
            return
        elif command == "/edit_editor":
             current_widget = self.editor_pane.tab_widget.currentWidget()
             if current_widget:
                 editor_path_prop = current_widget.property("file_path")
                 filename_hint = os.path.basename(editor_path_prop) if editor_path_prop else "current tab"
                 self.set_context({'action': 'edit_editor', 'path': editor_path_prop if editor_path_prop else 'current tab'})
                 prompt_msg = f"Editing content of '{filename_hint}'. Provide instructions in next message."
                 self.edit_context_set_from_chat.emit(prompt_msg)
                 self.status_update.emit("GemNet", f"Ready for edit instructions for {filename_hint}...")
             else: self.stream_error.emit("Error: No active editor tab found to edit.", 'chat')
             return
        else: # Standard Chat
            print("[Controller DEBUG] Handling as standard chat message.")
            prompt = "You are a helpful assistant called GemNet. Respond concisely and helpfully.\n"
            prompt += f"\nUser: {message}\n\nAssistant:"
            self._stream_gemini_api(prompt, context_type='chat', sender="Gemini")


    def set_context(self, context):
        """Allows setting context (like files selected for editing)."""
        print(f"[Controller DEBUG] Setting context: {context}")
        self.current_context = context

    # Removed finalize_generated_file - this logic is now implicitly handled
    # by MainWindow receiving the stream_finished signal with 'create_success:<filename>'

# --- END OF FILE gemini_controller.py ---
