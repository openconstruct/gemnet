from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal, Qt

class ChatPane(QWidget):
    user_message_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)

        self.input_area = QLineEdit()
        self.input_area.setPlaceholderText("Enter your message or instructions...")
        self.input_area.returnPressed.connect(self.send_message) # Send on Enter

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_area)
        input_layout.addWidget(self.send_button)

        layout.addWidget(self.chat_history)
        layout.addLayout(input_layout)

    def add_message(self, sender, message, is_status=False):
        # Add basic formatting (bold sender)
        prefix = f"<b>{sender}:</b> "
        if is_status:
             prefix = f"<i>[{sender}]:</i> " # Italic for status

        # Handle multi-line messages better (replace \n with HTML <br>)
        formatted_message = message.replace('\n', '<br>')

        self.chat_history.append(prefix + formatted_message)
        # Auto-scroll to bottom
        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())


    def send_message(self):
        message = self.input_area.text().strip()
        if message:
            self.user_message_submitted.emit(message)
            self.input_area.clear()