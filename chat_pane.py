from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal, Qt, Slot # Added Slot
from PySide6.QtGui import QTextCursor # Added QTextCursor
import markdown # Import markdown

class ChatPane(QWidget):
    user_message_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        # Allow rich text interaction if needed later (e.g., copying code)
        # self.chat_history.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        self.input_area = QLineEdit()
        self.input_area.setPlaceholderText("Enter message, command, or edit instruction...") # Updated placeholder
        self.input_area.returnPressed.connect(self.send_message) # Send on Enter

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_area)
        input_layout.addWidget(self.send_button)

        layout.addWidget(self.chat_history)
        layout.addLayout(input_layout)

        # --- State for Streaming ---
        self._is_streaming = False
        self._current_stream_sender = ""
        self._current_stream_markdown = "" # Store full markdown content for current stream
        self._stream_start_cursor_pos = -1 # Store cursor position where stream started

    # <<< MODIFIED add_message >>>
    def add_message(self, sender, message, is_status=False, is_error=False, is_user=False):
        """Adds a complete message (not streamed) to the chat history."""
        # Ensure streaming isn't active when adding a full message
        if self._is_streaming and sender != self._current_stream_sender:
             print("[ChatPane WARN] add_message called while another stream is active. Finishing previous stream visually.")
             self._finalize_stream_visuals() # Attempt to clean up previous stream

        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_history.setTextCursor(cursor)

        # Basic HTML formatting for sender
        if is_user:
            prefix = f"<b style='color: #aaddff;'>User:</b> " # Example user color
        elif is_error:
            prefix = f"<b style='color: #ffaaaa;'>Error:</b> "
            message = message.replace('\n', '<br>') # Basic newline handling for errors
        elif is_status:
            prefix = f"<i style='color: #cccccc;'>[{sender}]:</i> "
            message = message.replace('\n', '<br>') # Basic newline handling for status
        else: # Gemini or other non-user/status/error
             prefix = f"<b>{sender}:</b> "
             # Convert message *content* from Markdown to HTML for non-status/error
             # Use fenced_code for ``` blocks
             try:
                 html_content = markdown.markdown(message, extensions=['fenced_code'])
                 message = html_content # Replace original message with HTML
             except Exception as e:
                 print(f"[ChatPane ERROR] Markdown conversion failed: {e}")
                 prefix = f"<b>{sender} (Markdown Error):</b> "
                 message = message.replace('\n', '<br>') # Fallback formatting

        self.chat_history.insertHtml(prefix + message + "<br>") # Insert HTML prefix + content
        self.chat_history.ensureCursorVisible() # Auto-scroll

    # --- Slots for Streaming Signals ---
    @Slot(str, str)
    def handle_stream_started(self, sender, context_type):
        """Prepares the chat pane for incoming stream chunks."""
        if context_type != 'chat' and context_type != 'file_create' and not context_type.startswith("create_success"): # Only handle chat/create streams here
             return
        if self._is_streaming: # If already streaming, finalize previous one visually
             print(f"[ChatPane WARN] New stream '{sender}/{context_type}' started while previous '{self._current_stream_sender}' was active.")
             self._finalize_stream_visuals()

        print(f"[ChatPane] Stream started for '{sender}' (type: {context_type})")
        self._is_streaming = True
        self._current_stream_sender = sender
        self._current_stream_markdown = "" # Reset markdown buffer

        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_history.setTextCursor(cursor)

        # Add sender prefix
        prefix = f"<b>{sender}:</b> "
        self.chat_history.insertHtml(prefix)
        self._stream_start_cursor_pos = cursor.position() # Store position *after* prefix

        self.chat_history.ensureCursorVisible()

    @Slot(str)
    def handle_stream_chunk(self, chunk):
        """Appends a text chunk to the chat history during streaming."""
        if not self._is_streaming:
             # This might happen if chunks arrive after an error signal, ignore them.
             print("[ChatPane WARN] Received stream chunk but not in streaming state.")
             return

        # Append raw text chunk for now
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_history.setTextCursor(cursor)
        # Replace potential ```plain or ```text directives for better rendering later
        chunk = chunk.replace("```plain\n", "```\n").replace("```text\n", "```\n")
        self.chat_history.insertPlainText(chunk)
        self.chat_history.ensureCursorVisible()

        # Append to our internal markdown buffer
        self._current_stream_markdown += chunk

    @Slot(str, str)
    def handle_stream_finished(self, sender, context_type):
        """Finalizes the message formatting after streaming is complete."""
        if not self._is_streaming or sender != self._current_stream_sender:
            # Can happen if finish signal is duplicated or relates to a non-chat stream handled elsewhere
            # Or if an error occurred before finish signal was received.
            print(f"[ChatPane INFO] Received stream finish for '{sender}/{context_type}', but not matching active stream '{self._current_stream_sender}'. Ignoring.")
            return

        print(f"[ChatPane] Stream finished for '{sender}'. Finalizing visuals.")
        self._finalize_stream_visuals()

    @Slot(str, str)
    def handle_stream_error(self, error_message, context_type):
        """Displays an error message and stops the current stream."""
        if context_type != 'chat' and context_type != 'file_create': # Only handle chat/create errors here
            print(f"[ChatPane] Ignoring stream error for context '{context_type}'")
            return

        print(f"[ChatPane] Stream error for '{self._current_stream_sender}': {error_message}")
        if self._is_streaming:
            # If we were streaming, add a newline to separate the error clearly
            cursor = self.chat_history.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.chat_history.setTextCursor(cursor)
            self.chat_history.insertPlainText("\n") # Add separation
        # Add the error message using the standard method
        self.add_message("Error", error_message, is_error=True)

        # Reset streaming state as the stream has effectively ended
        self._is_streaming = False
        self._current_stream_sender = ""
        self._current_stream_markdown = ""
        self._stream_start_cursor_pos = -1

    def _finalize_stream_visuals(self):
        """Converts the streamed markdown to HTML and replaces the plain text."""
        if self._stream_start_cursor_pos == -1 or not self._current_stream_markdown:
             print("[ChatPane DEBUG] Finalize visuals called with no start position or no content.")
             self._reset_stream_state()
             return

        cursor = self.chat_history.textCursor()
        # Select the plain text that was inserted during the stream
        cursor.setPosition(self._stream_start_cursor_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor) # Select to end
        # Check if selection actually contains the streamed content (basic check)
        # A more robust check might be needed if user interacts mid-stream
        # selected_text = cursor.selectedText()
        # if selected_text != self._current_stream_markdown.replace('\r\n', '\n'):
        #     print("[ChatPane WARN] Text selection mismatch on finalize. History may have changed.")
             # Fallback: just append HTML? Or log error?
             # For now, proceed, but this indicates potential issues.

        # Convert the stored full markdown message to HTML
        try:
             # Using 'fenced_code' for ```python ... ``` blocks
             # Using 'nl2br' to convert single newlines to <br> (common Markdown behavior)
             # Using 'codehilite' requires pygments, add if needed: extensions=['fenced_code', 'nl2br', 'codehilite']
             html_content = markdown.markdown(self._current_stream_markdown, extensions=['fenced_code', 'nl2br'])
             # Remove the selected plain text
             cursor.removeSelectedText()
             # Insert the final HTML content
             cursor.insertHtml(html_content + "<br>") # Add final break
             print("[ChatPane DEBUG] Replaced streamed plain text with formatted HTML.")
        except Exception as e:
             print(f"[ChatPane ERROR] Markdown conversion failed during finalization: {e}")
             # Leave the plain text as is, maybe add an error note?
             cursor.movePosition(QTextCursor.End)
             self.chat_history.setTextCursor(cursor)
             self.chat_history.insertHtml(f"<br><i style='color:red;'>[Markdown rendering failed: {e}]</i><br>")

        self.chat_history.ensureCursorVisible()
        self._reset_stream_state()

    def _reset_stream_state(self):
        """Resets internal streaming state variables."""
        self._is_streaming = False
        self._current_stream_sender = ""
        self._current_stream_markdown = ""
        self._stream_start_cursor_pos = -1

    def send_message(self):
        message = self.input_area.text().strip()
        if message:
            # Add user message to chat immediately for responsiveness
            # Check context *before* echoing potentially sensitive edit instructions
            # (This check might be better in the controller before emitting signals)
            is_edit_instruction = False # Assume not edit instruction initially
            # A bit hacky: ideally controller would tell us, but we peek its state
            # This requires controller instance access or signal system
            # if self.controller_ref and self.controller_ref.current_context.get('action') in ['edit', 'edit_editor', 'create']:
            #     is_edit_instruction = True

            # Simple approach: always display user message for now
            # if not is_edit_instruction:
            self.add_message("User", message, is_user=True) # Add as HTML

            self.user_message_submitted.emit(message)
            self.input_area.clear()
        # else: handle empty message? (Ignore)


