# --- START OF FILE gemini_controller.py ---

from PySide6.QtCore import QObject, Signal
import os
# import time # Keep if needed
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import typing # Optional for type hinting

# Forward declaration hint for type hinting
if typing.TYPE_CHECKING:
    from file_pane import FilePane
    from editor_pane import EditorPane # Add EditorPane hint

class GeminiController(QObject):
    # Signals
    # explanation_ready = Signal(str, str) # Replaced by streaming
    # chat_response_ready = Signal(str, str) # Replaced by streaming
    # file_content_generated = Signal(str, str) # Replaced by streaming
    # editor_content_generated = Signal(str) # Replaced by streaming
    status_update = Signal(str, str)
    available_models_updated = Signal(list)
    initialization_status = Signal(str, bool)
    edit_file_requested_from_chat = Signal(str)
    edit_context_set_from_chat = Signal(str)

    # --- NEW Streaming Signals ---
    # Emitted when a streaming operation (chat, edit, create) begins
    stream_started = Signal(str, str) # sender, context_type ('chat', 'editor', 'file_create')
    # Emitted for each chunk of text received from the API
    stream_chunk_received = Signal(str) # chunk_text
    # Emitted when the stream finishes successfully
    stream_finished = Signal(str, str) # sender, context_type
    # Emitted if an error occurs during streaming or setup
    stream_error = Signal(str, str) # error_message, context_type

    # <<< MODIFIED __init__ >>>
    def __init__(self, file_pane_ref: 'FilePane', editor_pane_ref: 'EditorPane'): # Accept EditorPane
        super().__init__()
        self.file_pane = file_pane_ref
        self.editor_pane = editor_pane_ref # Store EditorPane reference
        self.current_context = {}
        self.selected_model_name = "gemini-1.5-flash-latest"
        self.available_models = []
        self.model_instance = None
        self._is_configured = False
        self._configure_gemini()

    # ... (_configure_gemini, update_available_models, set_selected_model, _read_files remain the same) ...
    def _configure_gemini(self):
        """Configures the Gemini API client using environment variables."""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.initialization_status.emit("API Key Error: GOOGLE_API_KEY environment variable not set.", False)
                self.status_update.emit("Error", "Gemini API Key not found. Please set GOOGLE_API_KEY.")
                self._is_configured = False; return
            genai.configure(api_key=api_key)
            self._is_configured = True
            self.initialization_status.emit("Gemini API Configured.", True)
            self.status_update.emit("GemNet", "Gemini API configured successfully.")
            self.set_selected_model(self.selected_model_name, initial_load=True)
            self.update_available_models()
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
            for m in models:
                if 'generateContent' in m.supported_generation_methods and m.name.startswith("models/"):
                    self.available_models.append(m.name.split('/')[-1])
            if self.selected_model_name not in self.available_models:
                if self.available_models:
                    new_default = next((m for m in self.available_models if 'flash' in m), self.available_models[0])
                    self.status_update.emit("Warning", f"Selected model '{self.selected_model_name}' invalid. Resetting to '{new_default}'.")
                    self.set_selected_model(new_default)
                else:
                    self.status_update.emit("Warning", "No suitable text generation models found.")
                    self.selected_model_name = ""; self.model_instance = None
            self.available_models_updated.emit(self.available_models)
            if self.available_models: self.status_update.emit("GemNet", f"Found {len(self.available_models)} models. Current: {self.selected_model_name}")
        except Exception as e:
            self.status_update.emit("Error", f"Could not fetch Gemini models: {e}")
            self.available_models = []; self.available_models_updated.emit([])

    def set_selected_model(self, model_short_name, initial_load=False):
        """Sets the active Gemini model instance based on its short name."""
        if not self._is_configured and not initial_load:
             self.status_update.emit("Error", "Gemini API not configured. Cannot set model."); return
        full_model_name = f"models/{model_short_name}"
        try:
            if self.available_models and model_short_name not in self.available_models and not initial_load:
                 self.status_update.emit("Warning", f"Model '{model_short_name}' not in known list. Attempting anyway.")
            self.status_update.emit("GemNet", f"Loading model: {model_short_name}...")
            safety_settings=[{"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            self.model_instance = genai.GenerativeModel(full_model_name, safety_settings=safety_settings)
            self.selected_model_name = model_short_name
            self.status_update.emit("GemNet", f"Model '{model_short_name}' loaded successfully.")
        except Exception as e:
            self.status_update.emit("Error", f"Failed to load model '{model_short_name}': {e}")
            self.model_instance = None
            if not initial_load: self.selected_model_name = ""

    def _read_files(self, file_paths):
        """Helper to read content from multiple files with size limits and encoding checks."""
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

    # <<< MODIFIED: _call_gemini_api now initiates streaming >>>
    def _stream_gemini_api(self, prompt: str, context_type: str, sender: str = "Gemini"):
        """
        Calls the configured Gemini model's generate_content method with streaming.
        Emits signals for start, chunks, finish, or error.
        """
        if not self.model_instance:
            self.stream_error.emit("Error: Gemini model not available.", context_type)
            return
        if not self.selected_model_name:
            self.stream_error.emit("Error: No model selected.", context_type)
            return

        self.status_update.emit(sender, f"Sending request to {self.selected_model_name}...")
        print(f"\n--- Gemini Prompt ({self.selected_model_name}) ---\n{prompt[:500]}...\n--- End Prompt ---")

        try:
            # Emit stream started *before* API call
            self.stream_started.emit(sender, context_type)

            # Make the streaming API call
            response = self.model_instance.generate_content(prompt, stream=True)

            print(f"--- Gemini Response Stream ({context_type}) ---") # Indicate stream start
            for chunk in response:
                # Check for safety blocks *within* the stream
                # Note: The prompt_feedback check is often on the *first* chunk or the *last*.
                # Candidates might be empty mid-stream if waiting for more data.
                if hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                     reason = chunk.prompt_feedback.block_reason.name
                     rating = next((r for r in chunk.prompt_feedback.safety_ratings if r.blocked), None)
                     category = getattr(rating.category, 'name', 'UNKNOWN') if rating else 'UNKNOWN'
                     error_msg = f"Error: Blocked by safety filters. Reason: {reason}. Category: {category}."
                     self.status_update.emit(sender, f"Request blocked: {reason} (Category: {category})")
                     self.stream_error.emit(error_msg, context_type)
                     print(f"Stream blocked: {reason} ({category})")
                     return # Stop processing stream on block

                # Process valid chunks with text
                if hasattr(chunk, 'text'):
                    print(chunk.text, end="", flush=True) # Print chunk to console for debugging
                    self.stream_chunk_received.emit(chunk.text)
                # else:
                    # Handle cases where a chunk might not have text (e.g., finish reason only)
                    # Usually fine to ignore these intermediate non-text chunks.
                    # print("[Stream Info Chunk Received - No Text]")

            # Finished iterating through chunks
            print("\n--- End Gemini Stream ---")
            self.status_update.emit(sender, "Received full response.")
            self.stream_finished.emit(sender, context_type)

        # --- Specific API Error Handling ---
        except google_exceptions.PermissionDenied as e:
             msg = f"Error: API Permission Denied. Check Key/Permissions. {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.ResourceExhausted as e:
             msg = f"Error: API Quota Exceeded. {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.InvalidArgument as e:
            if "User location is not supported" in str(e): msg = "Error: Location not supported by API."
            elif "API key not valid" in str(e): msg = f"Error: API key not valid. {e}"
            # "found no valid candidate" might indicate a safety block *before* any chunk yielded text
            elif "found no valid candidate" in str(e): msg = f"Error: No valid candidate found (Safety/Prompt issue?). {e}"
            else: msg = f"Error: Invalid API Argument. {e}"
            self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.NotFound as e:
             msg = f"Error: Model/Resource Not Found. {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.FailedPrecondition as e:
             msg = f"Error: API Precondition Failed (Billing?). {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.InternalServerError as e:
             msg = f"Error: API Internal Server Error. {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        except google_exceptions.ServiceUnavailable as e:
             msg = f"Error: API Service Unavailable. {e}"
             self.stream_error.emit(msg, context_type); print(msg)
        # --- Generic Exception Handling ---
        except Exception as e:
            error_msg = f"Error: API stream call failed: {type(e).__name__} - {e}"
            self.stream_error.emit(error_msg, context_type)
            print(error_msg)
        # --- Ensure status update if error happens ---
        finally:
            # Update status? The error signals should suffice.
            pass


    # request_explanation: called by right-click OR /explain command
    def request_explanation(self, file_paths):
        """Initiates a streaming explanation for the content of the given files."""
        contents = self._read_files(file_paths)
        if not contents:
            # Use stream_error for consistency, even if it's not a direct API error
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

        self._stream_gemini_api(prompt, context_type='chat', sender="Gemini") # Initiate stream
        self.current_context = {}

    # request_edit: called ONLY when processing an edit instruction message (after context is set)
    def request_edit(self, file_paths, instructions):
        """Initiates a streaming edit for the first file based on instructions."""
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
        # Edits update the editor pane
        self._stream_gemini_api(prompt, context_type='editor', sender="Gemini") # Initiate stream

    # <<< NEW HELPER for edit prompts >>>
    def _build_edit_prompt(self, target_filename, target_content, instructions, context_files=None):
        """Builds the prompt for editing, usable for both file and editor edits."""
        prompt = "You are a helpful coding assistant integrated into a development tool called GemNet.\n"
        prompt += f"The user wants to modify the code/text (currently in '{target_filename}' if known, otherwise in the editor tab) based on the following instructions.\n"

        # Add context from other files if provided (for file-based edits)
        if context_files:
             other_files = {p: c for p, c in context_files.items() if os.path.basename(p) != target_filename}
             if other_files:
                 prompt += "Additional context from other selected files is provided below the main content.\n"

        prompt += f"Instructions: '{instructions}'\n\n"
        prompt += f"--- Content to Edit ('{target_filename}' or Current Tab) ---\n"
        # Send more context for the content being edited
        truncated_content = target_content[:20000]
        prompt += truncated_content + ("\n[... content truncated ...]\n" if len(target_content) > 20000 else "")
        prompt += "\n---\n"

        # Add context from other files
        if context_files and other_files:
            for path, content in other_files.items():
                prompt += f"\n--- Context File: {os.path.basename(path)} ---\n"
                truncated_context = content[:5000]
                prompt += truncated_context + ("\n[... content truncated ...]\n" if len(content) > 5000 else "")
                prompt += "\n---\n"

        prompt += f"\nBased ONLY on the provided content and instructions, generate the COMPLETE, modified content.\n"
        prompt += f"IMPORTANT: Output *only* the raw, modified code/text. Do not include explanations, introductions, apologies, ```markdown formatting```, or any text other than the content itself."
        return prompt


    # <<< MODIFIED process_user_chat >>>
    def process_user_chat(self, message):
        """Processes chat messages, handling context, commands, and initiating streams."""
        print(f"[Controller DEBUG] Processing chat message: '{message[:100]}...'")

        # --- Check for active edit context FIRST ---
        action = self.current_context.get('action')
        if action == 'edit': # Edit instruction for file specified via /edit <file> or right-click
            files = self.current_context.get('files')
            if files:
                 print("[Controller DEBUG] Handling message as edit instruction (context: file).")
                 self.request_edit(files, message) # Initiates stream for editor
                 self.current_context = {} # Clear context *after* initiating stream
                 return
            else:
                 print("[Controller WARNING] Edit context active but no files found.")
                 self.stream_error.emit("Internal Error: Edit context lost file information.", 'editor')
                 self.current_context = {}
                 return
        elif action == 'edit_editor': # Edit instruction for the active editor tab
            print("[Controller DEBUG] Handling message as edit instruction (context: editor).")
            editor_path = self.current_context.get('path', 'current tab') # Get path if available
            editor_content = self.editor_pane.get_current_content()
            if editor_content is not None:
                 filename_hint = os.path.basename(editor_path) if editor_path and editor_path != 'current tab' else 'current tab'
                 prompt = self._build_edit_prompt(filename_hint, editor_content, message)
                 self._stream_gemini_api(prompt, context_type='editor', sender="Gemini") # Initiate stream
            else:
                 self.stream_error.emit("Cannot edit: No active editor tab found or content is inaccessible.", 'editor')
            self.current_context = {} # Clear context *after* initiating stream
            return
        elif action == 'create': # File creation description
            print("[Controller DEBUG] Handling message as create description.")
            filename = self.current_context.get('filename')
            description = message # The message *is* the description here
            if filename:
                content_prompt = "You are a helpful file generation assistant called GemNet.\n"
                content_prompt += f"The user wants to create a file named '{filename}' with the following purpose/content described:\n"
                content_prompt += f"Description: '{description}'\n\n"
                content_prompt += "Generate ONLY the raw file content based on the description.\n"
                content_prompt += "IMPORTANT: Do NOT include the filename, explanations, introductions, apologies, ```markdown formatting```, or any text other than the required file content itself."
                # Set context specific to file creation for the handler
                self.current_context['action'] = 'creating_file' # Update context state
                self._stream_gemini_api(content_prompt, context_type='file_create', sender="Gemini")
                # Don't clear full context yet, handler needs filename
            else:
                 print("[Controller WARNING] Create context active but no filename found.")
                 self.stream_error.emit("Internal Error: Create context lost filename information.", 'chat')
                 self.current_context = {}
            return


        # --- If no active context, check for commands ---
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args_str = parts[1].strip() if len(parts) > 1 else ""

        current_dir = self.file_pane.get_current_view_path()
        print(f"[Controller DEBUG] Current FilePane directory: {current_dir}")

        # --- /create ---
        if command == "/create":
             filename_raw = args_str
             if filename_raw:
                 # Sanitize filename
                 safe_filename = "".join(c for c in filename_raw if c.isalnum() or c in ('.', '_', '-', ' ')).strip()
                 if not safe_filename: safe_filename = "gemini_generated_file.txt"
                 if safe_filename in [".", "_", "-"]: safe_filename = f"gemini_generated_{safe_filename}.txt"
                 print(f"[Controller DEBUG] Sanitized filename for /create: '{safe_filename}'")

                 # Set context for the *next* message (which will be the description)
                 self.set_context({'action': 'create', 'filename': safe_filename})
                 prompt_msg = f"Creating '{safe_filename}'. Provide description/content prompt in next message."
                 self.edit_context_set_from_chat.emit(prompt_msg) # Use same signal for generic prompt
                 self.status_update.emit("GemNet", f"Ready for description for {safe_filename}...")

             else: self.stream_error.emit("Usage: /create <filename>\n(Provide description in the next message)", 'chat')
             return # Handled command (waits for next message)


        # --- /explain ---
        elif command == "/explain":
            filename = args_str
            if filename:
                 full_path = os.path.join(current_dir, filename)
                 print(f"[Controller DEBUG] /explain path: {full_path}")
                 if os.path.isfile(full_path):
                     # self.chat_response_ready.emit("User", f"Explain file: {filename}") # User msg added by ChatPane now
                     self.status_update.emit("GemNet", f"Requesting explanation for {filename}...")
                     self.request_explanation([full_path]) # Initiates stream for chat
                 else: self.stream_error.emit(f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.", 'chat')
            else: self.stream_error.emit("Usage: /explain <filename>", 'chat')
            return # Handled command

        # --- /edit ---
        elif command == "/edit":
             filename = args_str
             if filename:
                 full_path = os.path.join(current_dir, filename)
                 print(f"[Controller DEBUG] /edit path: {full_path}")
                 if os.path.isfile(full_path):
                     self.edit_file_requested_from_chat.emit(full_path) # Ask main to open
                     self.set_context({'action': 'edit', 'files': [full_path]}) # Set context for *next* message
                     prompt_msg = f"Editing '{filename}'. Provide instructions in next message."
                     self.edit_context_set_from_chat.emit(prompt_msg) # Ask main to add chat msg
                     self.status_update.emit("GemNet", f"Ready for edit instructions for {filename}...")
                 else: self.stream_error.emit(f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.", 'chat')
             else: self.stream_error.emit("Usage: /edit <filename>", 'chat')
             return # Handled command (context set, waiting for next message)

        # --- /explain_editor ---
        elif command == "/explain_editor":
            print("[Controller DEBUG] Detected /explain_editor command.")
            editor_content = self.editor_pane.get_current_content()
            editor_path = self.editor_pane.get_current_path()
            filename_hint = os.path.basename(editor_path) if editor_path else "current tab"

            if editor_content is not None:
                 # User msg added by ChatPane
                 self.status_update.emit("GemNet", f"Requesting explanation for {filename_hint}...")

                 prompt = "You are a helpful assistant integrated into a development tool called GemNet.\n"
                 prompt += f"Please explain the purpose and high-level functionality of the following code/text currently open in the editor tab (source file: '{filename_hint}'):\n\n"
                 prompt += f"--- Editor Content ---\n"
                 truncated_content = editor_content[:15000] # Limit context size
                 prompt += truncated_content + ("\n[... content truncated ...]\n" if len(editor_content) > 15000 else "")
                 prompt += "\n---\n"
                 prompt += "Provide the explanation below:"

                 self._stream_gemini_api(prompt, context_type='chat', sender="Gemini") # Initiate stream
            else:
                 self.stream_error.emit("Error: No active editor tab found to explain.", 'chat')
            return # Handled command

        # --- /edit_editor ---
        elif command == "/edit_editor":
             print("[Controller DEBUG] Detected /edit_editor command.")
             editor_path = self.editor_pane.get_current_path() # Check if a tab is open
             # Check content as well, maybe? No, allow editing empty file. Check path is enough.
             current_widget = self.editor_pane.tab_widget.currentWidget()
             if current_widget: # Check if *any* tab is open
                 editor_path_prop = current_widget.property("file_path") # Get path if it has one
                 filename_hint = os.path.basename(editor_path_prop) if editor_path_prop else "current tab"
                 self.set_context({'action': 'edit_editor', 'path': editor_path_prop if editor_path_prop else 'current tab'}) # Context for *next* message
                 prompt_msg = f"Editing content of '{filename_hint}'. Provide instructions in next message."
                 self.edit_context_set_from_chat.emit(prompt_msg) # Ask main to add chat msg
                 self.status_update.emit("GemNet", f"Ready for edit instructions for {filename_hint}...")
             else:
                  self.stream_error.emit("Error: No active editor tab found to edit.", 'chat')
             return # Handled command (context set, waiting for next message)

        # --- Standard Chat (if no command and no context) ---
        else:
            print("[Controller DEBUG] Handling as standard chat message.")
            # User msg added by ChatPane
            prompt = "You are a helpful assistant called GemNet. Respond concisely and helpfully.\n"
            # TODO: Add chat history to prompt for better context? (Adds complexity)
            prompt += f"\nUser: {message}\n\nAssistant:"
            self._stream_gemini_api(prompt, context_type='chat', sender="Gemini") # Initiate stream
            # No context to clear here usually

    def set_context(self, context):
        """Allows setting context (like files selected for editing)."""
        print(f"[Controller DEBUG] Setting context: {context}")
        self.current_context = context

    # <<< NEW Method to handle generated file content from stream >>>
    def finalize_generated_file(self, full_content):
        """Saves the complete content from a 'file_create' stream."""
        filename = self.current_context.get('filename')
        action = self.current_context.get('action') # Should be 'creating_file'

        if action == 'creating_file' and filename:
            print(f"[Controller DEBUG] Finalizing generated file: {filename}")
             # Trigger MainWindow to save the file
            # We lost the original signal, so we need a new way or reuse an old one.
            # Let's reuse the status update temporarily, MainWindow can listen for it.
            # A dedicated signal would be better.
            # self.file_content_generated.emit(filename, full_content) # Ideal, but need to add back

            # Workaround: Use chat message to signal completion
            self.stream_finished.emit("GemNet", f"create_success:{filename}") # Send filename in finish signal

            # Clear the create context
            self.current_context = {}

        elif action == 'creating_file' and not filename:
            print("[Controller ERROR] Tried to finalize file creation, but filename missing from context.")
            self.stream_error.emit("Internal Error: Filename lost during file creation.", 'chat')
            self.current_context = {}
        # else: This might be called inappropriately if context wasn't 'creating_file'


# --- END OF FILE gemini_controller.py ---