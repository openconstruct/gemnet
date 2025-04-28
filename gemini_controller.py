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
    explanation_ready = Signal(str, str)
    chat_response_ready = Signal(str, str)
    file_content_generated = Signal(str, str)
    editor_content_generated = Signal(str) # Signal to update the *current* editor
    status_update = Signal(str, str)
    available_models_updated = Signal(list)
    initialization_status = Signal(str, bool)
    edit_file_requested_from_chat = Signal(str)
    edit_context_set_from_chat = Signal(str)

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

    # ... (_configure_gemini, update_available_models, set_selected_model, _read_files, _call_gemini_api remain the same) ...
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

    def _call_gemini_api(self, prompt):
        """Calls the configured Gemini model's generate_content method."""
        if not self.model_instance: return "Error: Gemini model not available."
        if not self.selected_model_name: return "Error: No model selected."
        self.status_update.emit("Gemini", f"Sending request to {self.selected_model_name}...")
        print(f"\n--- Gemini Prompt ({self.selected_model_name}) ---\n{prompt[:500]}...\n--- End Prompt ---")
        try:
            response = self.model_instance.generate_content(prompt)
            prompt_feedback = getattr(response, 'prompt_feedback', None)
            if prompt_feedback and prompt_feedback.block_reason:
                 reason = prompt_feedback.block_reason.name
                 rating = next((r for r in prompt_feedback.safety_ratings if r.blocked), None)
                 category = getattr(rating.category, 'name', 'UNKNOWN') if rating else 'UNKNOWN'
                 self.status_update.emit("Gemini", f"Request blocked: {reason} (Category: {category})")
                 return f"Error: Blocked by safety filters. Reason: {reason}. Category: {category}."
            elif not response.candidates:
                 reason = getattr(response, 'finish_reason', 'UNKNOWN')
                 self.status_update.emit("Warning", f"Gemini response missing candidates. Finish Reason: {reason}.")
                 return f"Error: No response candidates. Finish Reason: {reason}."
            if not hasattr(response, 'text'):
                 reason = getattr(response, 'finish_reason', 'UNKNOWN')
                 self.status_update.emit("Warning", f"Gemini response missing 'text'. Finish Reason: {reason}.")
                 return f"Error: Invalid response structure. Finish Reason: {reason}."
            response_text = response.text
            print(f"--- Gemini Response ---\n{response_text[:500]}...\n--- End Response ---")
            self.status_update.emit("Gemini", "Received response.")
            return response_text
        except google_exceptions.PermissionDenied as e: return f"Error: API Permission Denied. Check Key/Permissions. {e}"
        except google_exceptions.ResourceExhausted as e: return f"Error: API Quota Exceeded. {e}"
        except google_exceptions.InvalidArgument as e:
            if "User location is not supported" in str(e): return "Error: Location not supported by API."
            elif "API key not valid" in str(e): return f"Error: API key not valid. {e}"
            elif "found no valid candidate" in str(e): return f"Error: No valid candidate found (Safety/Prompt issue?). {e}"
            return f"Error: Invalid API Argument. {e}"
        except google_exceptions.NotFound as e: return f"Error: Model/Resource Not Found. {e}"
        except google_exceptions.FailedPrecondition as e: return f"Error: API Precondition Failed (Billing?). {e}"
        except google_exceptions.InternalServerError as e: return f"Error: API Internal Server Error. {e}"
        except google_exceptions.ServiceUnavailable as e: return f"Error: API Service Unavailable. {e}"
        except Exception as e: return f"Error: API call failed: {type(e).__name__} - {e}"

    # request_explanation: called by right-click OR /explain command
    def request_explanation(self, file_paths):
        """Generates an explanation for the content of the given files."""
        contents = self._read_files(file_paths)
        if not contents:
            self.chat_response_ready.emit("GemNet", "No files were read successfully to explain.")
            return

        prompt = "You are a helpful assistant integrated into a development tool called GemNet.\n"
        prompt += "Please explain the purpose and high-level functionality of the following file(s):\n\n"
        for path, content in contents.items():
            prompt += f"--- File: {os.path.basename(path)} ---\n"
            truncated_content = content[:10000]
            prompt += truncated_content + ("\n[... content truncated ...]\n" if len(content) > 10000 else "")
            prompt += "---\n"
        prompt += "Provide the explanation below:"

        explanation = self._call_gemini_api(prompt)
        # explanation_ready.emit("Gemini", explanation) # Keep if needed elsewhere
        self.chat_response_ready.emit("Gemini", explanation) # Send to chat
        self.current_context = {}

    # request_edit: called ONLY when processing an edit instruction message (after context is set)
    def request_edit(self, file_paths, instructions):
        """Generates modified content for the first file based on instructions (for file-based edit)."""
        contents = self._read_files(file_paths)
        if not contents or not file_paths:
            self.chat_response_ready.emit("GemNet", "Cannot edit: File(s) could not be read or path missing."); return

        target_file_path = file_paths[0]
        target_filename = os.path.basename(target_file_path)
        target_content = contents.get(target_file_path)

        if target_content is None:
             self.chat_response_ready.emit("GemNet", f"Could not read '{target_filename}' for editing."); return

        prompt = self._build_edit_prompt(target_filename, target_content, instructions, contents)
        modified_content = self._call_gemini_api(prompt)

        if modified_content and not modified_content.startswith("Error:"):
            self.editor_content_generated.emit(modified_content) # Signal to update editor
            self.chat_response_ready.emit("Gemini", f"OK, placed suggested changes for {target_filename} into the editor.")
        elif modified_content: self.chat_response_ready.emit("Gemini", modified_content) # Show API error
        else: self.chat_response_ready.emit("GemNet", "Failed to generate edit, no response from API.")

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
        """Processes chat messages, including commands like /create, /explain, /edit, /explain_editor, /edit_editor."""
        print(f"[Controller DEBUG] Processing chat message: '{message[:100]}...'")

        # --- Check for active edit context FIRST ---
        action = self.current_context.get('action')
        if action == 'edit': # Edit instruction for file specified via /edit <file> or right-click
            files = self.current_context.get('files')
            if files:
                 print("[Controller DEBUG] Handling message as edit instruction (context: file).")
                 self.request_edit(files, message) # message IS the instruction here
                 self.current_context = {} # Clear context *after* edit attempt
                 return
            else: # Should not happen, but clear context if invalid
                 print("[Controller WARNING] Edit context active but no files found.")
                 self.current_context = {}
        elif action == 'edit_editor': # Edit instruction for the active editor tab
            print("[Controller DEBUG] Handling message as edit instruction (context: editor).")
            editor_path = self.current_context.get('path', 'current tab') # Get path if available
            editor_content = self.editor_pane.get_current_content()
            if editor_content is not None:
                 # Use the helper to build the prompt
                 prompt = self._build_edit_prompt(os.path.basename(editor_path) if editor_path else 'current tab',
                                                  editor_content, message)
                 modified_content = self._call_gemini_api(prompt)
                 if modified_content and not modified_content.startswith("Error:"):
                     self.editor_content_generated.emit(modified_content) # Signal to update editor
                     self.chat_response_ready.emit("Gemini", f"OK, placed suggested changes for {os.path.basename(editor_path)} into the editor.")
                 elif modified_content: self.chat_response_ready.emit("Gemini", modified_content) # Show API error
                 else: self.chat_response_ready.emit("GemNet", "Failed to generate edit, no response from API.")
            else:
                 self.chat_response_ready.emit("GemNet", "Cannot edit: No active editor tab found.")
            self.current_context = {} # Clear context *after* edit attempt
            return

        # --- If no active context, check for commands ---
        parts = message.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        args_str = parts[1].strip() if len(parts) > 1 else ""

        current_dir = self.file_pane.get_current_view_path()
        print(f"[Controller DEBUG] Current FilePane directory: {current_dir}")

        # --- /create ---
        if command == "/create":
            create_parts = args_str.split(maxsplit=1)
            if len(create_parts) == 2:
                filename_raw, description = create_parts
                # ... (rest of /create logic remains the same) ...
                safe_filename = "".join(c for c in filename_raw if c.isalnum() or c in ('.', '_', '-', ' ')).strip()
                if not safe_filename: safe_filename = "gemini_generated_file.txt"
                if safe_filename in [".", "_", "-"]: safe_filename = f"gemini_generated_{safe_filename}.txt"
                print(f"[Controller DEBUG] Sanitized filename: '{safe_filename}'")
                content_prompt = "..." # Build prompt as before
                content_prompt = "You are a helpful file generation assistant called GemNet.\n"
                content_prompt += f"The user wants to create a file named '{safe_filename}' with the following purpose/content described:\n"
                content_prompt += f"Description: '{description}'\n\n"
                content_prompt += "Generate ONLY the raw file content based on the description.\n"
                content_prompt += "IMPORTANT: Do NOT include the filename, explanations, introductions, apologies, ```markdown formatting```, or any text other than the required file content itself."
                content_response = self._call_gemini_api(content_prompt)
                if content_response and not content_response.startswith("Error:"):
                     self.file_content_generated.emit(safe_filename, content_response)
                elif content_response: self.chat_response_ready.emit("Gemini", f"Error creating {safe_filename}: {content_response}")
                else: self.chat_response_ready.emit("GemNet", f"Failed to create {safe_filename}, no API response.")
            else: self.chat_response_ready.emit("GemNet", "Usage: /create <filename> <description>")
            return # Handled command

        # --- /explain ---
        elif command == "/explain":
            filename = args_str
            if filename:
                 full_path = os.path.join(current_dir, filename)
                 print(f"[Controller DEBUG] /explain path: {full_path}")
                 if os.path.isfile(full_path):
                     self.chat_response_ready.emit("User", f"Explain file: {filename}")
                     self.status_update.emit("GemNet", f"Requesting explanation for {filename}...")
                     self.request_explanation([full_path]) # This sends result to chat
                 else: self.chat_response_ready.emit("GemNet", f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.")
            else: self.chat_response_ready.emit("GemNet", "Usage: /explain <filename>")
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
                 else: self.chat_response_ready.emit("GemNet", f"Error: File '{filename}' not found in '{os.path.basename(current_dir)}'.")
             else: self.chat_response_ready.emit("GemNet", "Usage: /edit <filename>")
             return # Handled command (context set, waiting for next message)

        # --- /explain_editor ---
        elif command == "/explain_editor":
            print("[Controller DEBUG] Detected /explain_editor command.")
            editor_content = self.editor_pane.get_current_content()
            editor_path = self.editor_pane.get_current_path()
            filename_hint = os.path.basename(editor_path) if editor_path else "current tab"

            if editor_content is not None:
                 self.chat_response_ready.emit("User", f"Explain content of: {filename_hint}")
                 self.status_update.emit("GemNet", f"Requesting explanation for {filename_hint}...")

                 prompt = "You are a helpful assistant integrated into a development tool called GemNet.\n"
                 prompt += f"Please explain the purpose and high-level functionality of the following code/text currently open in the editor tab (source file: '{filename_hint}'):\n\n"
                 prompt += f"--- Editor Content ---\n"
                 truncated_content = editor_content[:15000] # Limit context size
                 prompt += truncated_content + ("\n[... content truncated ...]\n" if len(editor_content) > 15000 else "")
                 prompt += "\n---\n"
                 prompt += "Provide the explanation below:"

                 explanation = self._call_gemini_api(prompt)
                 self.chat_response_ready.emit("Gemini", explanation) # Send explanation to chat
            else:
                 self.chat_response_ready.emit("GemNet", "Error: No active editor tab found to explain.")
            return # Handled command

        # --- /edit_editor ---
        elif command == "/edit_editor":
             print("[Controller DEBUG] Detected /edit_editor command.")
             editor_path = self.editor_pane.get_current_path() # Check if a tab is open
             if editor_path is not None: # Check path, content might be empty initially
                 filename_hint = os.path.basename(editor_path) if editor_path else "current tab"
                 self.set_context({'action': 'edit_editor', 'path': editor_path}) # Context for *next* message
                 prompt_msg = f"Editing content of '{filename_hint}'. Provide instructions in next message."
                 self.edit_context_set_from_chat.emit(prompt_msg) # Ask main to add chat msg
                 self.status_update.emit("GemNet", f"Ready for edit instructions for {filename_hint}...")
             else:
                  self.chat_response_ready.emit("GemNet", "Error: No active editor tab found to edit.")
             return # Handled command (context set, waiting for next message)

        # --- Standard Chat (if no command and no context) ---
        else:
            print("[Controller DEBUG] Handling as standard chat message.")
            prompt = "You are a helpful assistant called GemNet. Respond concisely and helpfully.\n"
            prompt += f"\nUser: {message}\n\nAssistant:"
            chat_response = self._call_gemini_api(prompt)
            self.chat_response_ready.emit("Gemini", chat_response)
            # No context to clear here usually

    def set_context(self, context):
        """Allows setting context (like files selected for editing)."""
        print(f"[Controller DEBUG] Setting context: {context}")
        self.current_context = context

# --- END OF FILE gemini_controller.py ---