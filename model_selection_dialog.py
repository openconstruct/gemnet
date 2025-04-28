# model_selection_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox,
                               QDialogButtonBox)
from PySide6.QtCore import Qt

class ModelSelectionDialog(QDialog):
    def __init__(self, available_models, current_model, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Gemini Model")
        self.setMinimumWidth(350) # Set a reasonable minimum width

        # Ensure modality is set (blocks parent window)
        self.setWindowModality(Qt.WindowModal)

        self.available_models = available_models
        self.selected_model_name = current_model # Store initially

        # Layout
        layout = QVBoxLayout(self)

        # Label
        label = QLabel("Please select the Gemini model to use:")
        layout.addWidget(label)

        # Combo Box
        self.model_combo = QComboBox()
        if not available_models:
            # Handle case where no models were found
            self.model_combo.addItem("No models found / Check API Key")
            self.model_combo.setEnabled(False)
        else:
            # Populate with models
            self.model_combo.addItems(available_models)
            # Set the initial selection
            if current_model in available_models:
                self.model_combo.setCurrentText(current_model)
            elif available_models:
                 # If current_model isn't valid, select the first available one
                 self.model_combo.setCurrentIndex(0)

        # Store the selected model whenever the combo box changes
        self.model_combo.currentTextChanged.connect(self._update_selection)
        layout.addWidget(self.model_combo)

        # Standard Buttons (OK & Cancel)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept) # Connect OK to accept
        button_box.rejected.connect(self.reject) # Connect Cancel to reject

        # Disable OK if no valid models are available
        if not available_models:
             button_box.button(QDialogButtonBox.Ok).setEnabled(False)

        layout.addWidget(button_box)

    def _update_selection(self, text):
        """Internal slot to update the stored selection."""
        self.selected_model_name = text

    def get_selected_model(self):
        """Returns the model name selected when OK was clicked."""
        # Return the stored name, which reflects the combo box state at acceptance
        return self.selected_model_name

    @staticmethod
    def get_model(available_models, current_model, parent=None):
        """Static method to create, show, and get the result."""
        dialog = ModelSelectionDialog(available_models, current_model, parent)
        result = dialog.exec() # Show the dialog modally

        if result == QDialog.Accepted:
            return True, dialog.get_selected_model() # Return success and model name
        else:
            return False, current_model # Return failure and the original model