from PySide6.QtWidgets import QApplication
import os

class ThemeManager:
    def __init__(self, app_instance):
        self.app = app_instance # Store QApplication or QMainWindow instance
        self.themes = {
            "dark": "styles/dark_theme.qss",
            "light": "styles/light_theme.qss",
            # Add more themes here
        }
        self.ensure_styles_exist()

    def ensure_styles_exist(self):
         # Create dummy style files if they don't exist
         if not os.path.exists("styles"):
            os.makedirs("styles")
         if not os.path.exists(self.themes["dark"]):
             with open(self.themes["dark"], "w") as f:
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
         if not os.path.exists(self.themes["light"]):
             with open(self.themes["light"], "w") as f:
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

    def set_theme(self, theme_name):
        qss_path = self.themes.get(theme_name)
        if qss_path and os.path.exists(qss_path):
            try:
                with open(qss_path, "r") as f:
                    style = f.read()
                    QApplication.instance().setStyleSheet(style) # Apply to the whole app
                print(f"Applied theme: {theme_name}") # Log or status update
            except Exception as e:
                 print(f"Error loading theme {theme_name}: {e}")
        else:
            print(f"Theme '{theme_name}' not found or path invalid: {qss_path}")