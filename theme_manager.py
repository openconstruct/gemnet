# --- START OF FILE theme_manager.py ---

from PySide6.QtWidgets import QApplication
import os

class ThemeManager:
    def __init__(self, app_instance):
        self.app = app_instance # Store QApplication or QMainWindow instance
        self.themes = {
            "dark": "styles/dark_theme.qss",
            "light": "styles/light_theme.qss",
            # <<< ADDED NEW THEMES >>>
            "gruvbox_dark": "styles/gruvbox.qss",
            "solarized_dark": "styles/solarized.qss",
            "nord": "styles/nord.qss",
        }
        self.ensure_styles_exist() # Keep this to ensure defaults exist

    def ensure_styles_exist(self):
         # Create styles directory if it doesn't exist
         if not os.path.exists("styles"):
            os.makedirs("styles")
            print("Created 'styles' directory.") # Log directory creation

         default_dark = self.themes["dark"]
         if not os.path.exists(default_dark):
             print(f"Default dark theme file missing ({default_dark}), creating basic fallback.")
             try:
                 with open(default_dark, "w") as f:
                     # Basic dark theme example (Refine significantly!)
                     f.write("""
     QWidget { background-color: #2b2b2b; color: #f0f0f0; }
     QTextEdit, QLineEdit { background-color: #3c3f41; color: #f0f0f0; border: 1px solid #555; }
     QTreeView { background-color: #313335; alternate-background-color: #3b3f41; border: 1px solid #555; }
     QTreeView::item:selected { background-color: #4a6987; }
     QPushButton { background-color: #555; border: 1px solid #666; padding: 5px; }
     QPushButton:hover { background-color: #666; }
     QPushButton:pressed { background-color: #444; }
     QMenuBar { background-color: #3c3f41; }
     QMenuBar::item:selected { background-color: #4a6987; }
     QMenu { background-color: #3c3f41; border: 1px solid #555; }
     QMenu::item:selected { background-color: #4a6987; }
     QSplitter::handle { background-color: #444; }
     QTabWidget::pane { border: 1px solid #555; }
     QTabBar::tab { background-color: #444; color: #ccc; padding: 5px;}
     QTabBar::tab:selected { background-color: #2b2b2b; color: #f0f0f0; }
     QTabBar::tab:!selected:hover { background-color: #555; }
     /* Add more specific styling */
                     """)
             except IOError as e:
                 print(f"Error creating fallback dark theme file: {e}")

         default_light = self.themes["light"]
         if not os.path.exists(default_light):
             print(f"Default light theme file missing ({default_light}), creating basic fallback.")
             try:
                 with open(default_light, "w") as f:
                     # Basic light theme (very simple - needs detail)
                      f.write("""
     QWidget { background-color: #f0f0f0; color: #000; }
     QTextEdit, QLineEdit { background-color: #ffffff; color: #000; border: 1px solid #ccc; }
     QTreeView { background-color: #ffffff; alternate-background-color: #f5f5f5; border: 1px solid #ccc; }
     QTreeView::item:selected { background-color: #cde8ff; }
     QPushButton { background-color: #e0e0e0; border: 1px solid #bbb; padding: 5px; }
     QPushButton:hover { background-color: #efefef; }
     QPushButton:pressed { background-color: #d0d0d0; }
     /* Add more */
                      """)
             except IOError as e:
                 print(f"Error creating fallback light theme file: {e}")

         # We don't automatically create the new theme files (gruvbox, solarized, nord) here.
         # It's assumed the user creates them manually with the provided QSS content.

    def set_theme(self, theme_name):
        qss_path = self.themes.get(theme_name)
        if qss_path and os.path.exists(qss_path):
            try:
                with open(qss_path, "r") as f:
                    style = f.read()
                    # Ensure we have a valid QApplication instance before setting stylesheet
                    app_instance = QApplication.instance()
                    if app_instance:
                        app_instance.setStyleSheet(style) # Apply to the whole app
                        print(f"Applied theme: {theme_name}") # Log or status update
                        # Optionally update status bar if self.app is the MainWindow instance
                        if hasattr(self.app, 'status_bar') and hasattr(self.app.status_bar, 'showMessage'):
                           self.app.status_bar.showMessage(f"Theme set to: {theme_name}", 3000)
                    else:
                        print("Error: QApplication instance not found.")

            except Exception as e:
                 print(f"Error loading or applying theme '{theme_name}' from {qss_path}: {e}")
        elif qss_path:
            print(f"Theme file not found: {qss_path}")
            # Optionally try applying a default theme as fallback
            # self.set_theme("dark")
        else:
            print(f"Theme name '{theme_name}' not defined in ThemeManager.")


# --- END OF FILE theme_manager.py ---
