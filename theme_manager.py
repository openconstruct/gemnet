# --- START OF FILE theme_manager.py ---

from PySide6.QtWidgets import QApplication
import os

class ThemeManager:
    def __init__(self, app_instance):
        self.app = app_instance # Store QApplication or QMainWindow instance
        self.themes = {
            "dark": "styles/dark_theme.qss",
            "light": "styles/light_theme.qss",
            "gruvbox_dark": "styles/gruvbox_dark_theme.qss",
            "solarized_dark": "styles/solarized_dark_theme.qss",
            "nord": "styles/nord_theme.qss",
        }
        self.ensure_styles_exist() # Create missing files on startup

    def ensure_styles_exist(self):
         """Checks for theme files and creates them from hardcoded strings if missing."""
         styles_dir = "styles"
         if not os.path.exists(styles_dir):
            try:
                os.makedirs(styles_dir)
                print(f"Created directory: {styles_dir}")
            except OSError as e:
                print(f"Error creating directory {styles_dir}: {e}")
                return # Cannot proceed if directory creation fails

         # --- Helper function to create a theme file ---
         def create_theme_file(filepath, content):
             if not os.path.exists(filepath):
                 print(f"Theme file missing, creating: {filepath}")
                 try:
                     with open(filepath, "w", encoding='utf-8') as f:
                         f.write(content)
                 except IOError as e:
                     print(f"Error creating theme file {filepath}: {e}")

         # --- Hardcoded Theme Strings ---

         dark_theme_content = """
/* Default Dark Theme */
QWidget { background-color: #2b2b2b; color: #f0f0f0; border: none; }
QTextEdit, QLineEdit, QPlainTextEdit { background-color: #3c3f41; color: #f0f0f0; border: 1px solid #555; selection-background-color: #4a6987; selection-color: #f0f0f0; padding: 2px;}
QTreeView { background-color: #313335; alternate-background-color: #3b3f41; border: 1px solid #555; color: #f0f0f0;}
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background-color: #4a6987; color: #f0f0f0;}
QTreeView::item:hover { background-color: #434343; color: #f0f0f0;}
QPushButton { background-color: #555; border: 1px solid #666; padding: 5px 10px; min-width: 60px; color: #f0f0f0;}
QPushButton:hover { background-color: #666; }
QPushButton:pressed { background-color: #444; }
QPushButton:disabled { background-color: #444; color: #888; }
QMenuBar { background-color: #3c3f41; color: #f0f0f0;}
QMenuBar::item { background-color: transparent; padding: 4px 8px;}
QMenuBar::item:selected { background-color: #4a6987; }
QMenuBar::item:pressed { background-color: #4a6987; }
QMenu { background-color: #3c3f41; border: 1px solid #555; padding: 5px; color: #f0f0f0;}
QMenu::item { padding: 4px 20px; }
QMenu::item:selected { background-color: #4a6987; }
QMenu::separator { height: 1px; background-color: #555; margin: 4px 0; }
QSplitter::handle { background-color: #444; border: 0px; width: 3px; margin: 1px 0;}
QSplitter::handle:horizontal { width: 3px; height: 1px; }
QSplitter::handle:vertical { height: 3px; width: 1px; }
QSplitter::handle:hover { background-color: #5e81ac; }
QTabWidget::pane { border: 1px solid #555; background-color: #2b2b2b; }
QTabBar::tab { background-color: #444; color: #ccc; border: 1px solid #555; border-bottom: none; padding: 5px 10px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;}
QTabBar::tab:selected { background-color: #2b2b2b; color: #f0f0f0; border-bottom: 1px solid #2b2b2b;}
QTabBar::tab:!selected:hover { background-color: #555; color: #f0f0f0;}
QTabBar::close-button { subcontrol-position: right; padding-left: 3px;}
QTabBar::close-button:hover { background-color: #bf616a; }
QStatusBar { background-color: #3c3f41; color: #ccc; }
QScrollBar:vertical { background: #2b2b2b; width: 10px; margin: 0px; border: 1px solid #555; border-radius: 4px; }
QScrollBar::handle:vertical { background: #555; min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #666; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: #2b2b2b; height: 10px; margin: 0px; border: 1px solid #555; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #555; min-width: 20px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #666; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QComboBox { background-color: #555; border: 1px solid #666; color: #f0f0f0; padding: 1px 18px 1px 3px; min-width: 6em; border-radius: 3px;}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #666;}
QComboBox QAbstractItemView { background-color: #3c3f41; border: 1px solid #555; selection-background-color: #4a6987; color: #f0f0f0; selection-color: #f0f0f0; }
"""

         light_theme_content = """
/* Default Light Theme */
QWidget { background-color: #f0f0f0; color: #000000; border: none;}
QTextEdit, QLineEdit, QPlainTextEdit { background-color: #ffffff; color: #000000; border: 1px solid #ccc; selection-background-color: #cde8ff; selection-color: #000000; padding: 2px;}
QTreeView { background-color: #ffffff; alternate-background-color: #f5f5f5; border: 1px solid #ccc; color: #000000;}
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background-color: #cde8ff; color: #000000;}
QTreeView::item:hover { background-color: #e8f4ff; color: #000000;}
QPushButton { background-color: #e0e0e0; border: 1px solid #bbb; padding: 5px 10px; min-width: 60px; color: #000000;}
QPushButton:hover { background-color: #efefef; }
QPushButton:pressed { background-color: #d0d0d0; }
QPushButton:disabled { background-color: #d0d0d0; color: #888; }
QMenuBar { background-color: #e8e8e8; color: #000000;}
QMenuBar::item { background-color: transparent; padding: 4px 8px;}
QMenuBar::item:selected { background-color: #cde8ff; }
QMenuBar::item:pressed { background-color: #cde8ff; }
QMenu { background-color: #ffffff; border: 1px solid #ccc; padding: 5px; color: #000000;}
QMenu::item { padding: 4px 20px; }
QMenu::item:selected { background-color: #cde8ff; }
QMenu::separator { height: 1px; background-color: #ccc; margin: 4px 0; }
QSplitter::handle { background-color: #d0d0d0; border: 0px; width: 3px; margin: 1px 0;}
QSplitter::handle:horizontal { width: 3px; height: 1px; }
QSplitter::handle:vertical { height: 3px; width: 1px; }
QSplitter::handle:hover { background-color: #b0c4de; }
QTabWidget::pane { border: 1px solid #ccc; background-color: #f0f0f0; }
QTabBar::tab { background-color: #e0e0e0; color: #333; border: 1px solid #ccc; border-bottom: none; padding: 5px 10px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;}
QTabBar::tab:selected { background-color: #f0f0f0; color: #000000; border-bottom: 1px solid #f0f0f0;}
QTabBar::tab:!selected:hover { background-color: #efefef; color: #000000;}
QTabBar::close-button { subcontrol-position: right; padding-left: 3px;}
QTabBar::close-button:hover { background-color: #ffaaaa; }
QStatusBar { background-color: #e8e8e8; color: #333; }
QScrollBar:vertical { background: #f0f0f0; width: 10px; margin: 0px; border: 1px solid #ccc; border-radius: 4px; }
QScrollBar::handle:vertical { background: #c0c0c0; min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #a0a0a0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: #f0f0f0; height: 10px; margin: 0px; border: 1px solid #ccc; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #c0c0c0; min-width: 20px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #a0a0a0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QComboBox { background-color: #e0e0e0; border: 1px solid #bbb; color: #000000; padding: 1px 18px 1px 3px; min-width: 6em; border-radius: 3px;}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #bbb;}
QComboBox QAbstractItemView { background-color: #ffffff; border: 1px solid #ccc; selection-background-color: #cde8ff; color: #000000; selection-color: #000000; }
"""

         gruvbox_dark_content = """
/* Gruvbox Dark Theme for GemNet */
/* Gruvbox Palette (Dark, Medium Contrast) */
/* bg0_h: #1d2021 */
/* bg0_s: #32302f */
/* bg1:   #3c3836 */
/* bg2:   #504945 */
/* bg3:   #665c54 */
/* bg4:   #7c6f64 */
/* fg:    #ebdbb2 */
/* fg1:   #ebdbb2 */
/* fg2:   #d5c4a1 */
/* fg3:   #bdae93 */
/* fg4:   #a89984 */
/* red:   #cc241d / #fb4934 (bright) */
/* green: #98971a / #b8bb26 (bright) */
/* yellow:#d79921 / #fabd2f (bright) */
/* blue:  #458588 / #83a598 (bright) */
/* purple:#b16286 / #d3869b (bright) */
/* aqua:  #689d6a / #8ec07c (bright) */
/* gray:  #a89984 */
/* orange:#d65d0e / #fe8019 (bright) */

QWidget {
    background-color: #1d2021; /* bg0_h */
    color: #ebdbb2; /* fg */
    border: none;
    font-family: "DejaVu Sans Mono", "Consolas", "Monaco", monospace; /* Example font */
}
QMainWindow, QDialog { background-color: #1d2021; }
QTextEdit, QLineEdit, QPlainTextEdit {
    background-color: #32302f; /* bg0_s */
    color: #ebdbb2; /* fg */
    border: 1px solid #504945; /* bg2 */
    selection-background-color: #458588; /* blue */
    selection-color: #1d2021; /* bg0_h */
    padding: 2px;
}
QTreeView {
    background-color: #32302f; /* bg0_s */
    color: #d5c4a1; /* fg2 */
    border: 1px solid #504945; /* bg2 */
    alternate-background-color: #3c3836; /* bg1 */
}
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background-color: #458588; /* blue */ color: #1d2021; /* bg0_h */ }
QTreeView::item:hover { background-color: #665c54; /* bg3 */ color: #ebdbb2; /* fg */ }
QPushButton { background-color: #665c54; /* bg3 */ color: #ebdbb2; /* fg */ border: 1px solid #7c6f64; /* bg4 */ padding: 5px 10px; min-width: 60px; }
QPushButton:hover { background-color: #7c6f64; /* bg4 */ border: 1px solid #928374; }
QPushButton:pressed { background-color: #504945; /* bg2 */ }
QPushButton:disabled { background-color: #504945; /* bg2 */ color: #a89984; /* gray */ }
QMenuBar { background-color: #3c3836; /* bg1 */ color: #d5c4a1; /* fg2 */ }
QMenuBar::item { background-color: transparent; padding: 4px 8px; }
QMenuBar::item:selected { background-color: #665c54; /* bg3 */ color: #ebdbb2; /* fg */ }
QMenuBar::item:pressed { background-color: #458588; /* blue */ color: #1d2021; /* bg0_h */ }
QMenu { background-color: #3c3836; /* bg1 */ color: #d5c4a1; /* fg2 */ border: 1px solid #504945; /* bg2 */ padding: 5px; }
QMenu::item { padding: 4px 20px 4px 20px; }
QMenu::item:selected { background-color: #458588; /* blue */ color: #1d2021; /* bg0_h */ }
QMenu::separator { height: 1px; background-color: #504945; /* bg2 */ margin-left: 10px; margin-right: 5px; }
QSplitter::handle { background-color: #504945; /* bg2 */ border: 0px solid #1d2021; width: 3px; margin: 1px 0; }
QSplitter::handle:horizontal { width: 3px; height: 1px; }
QSplitter::handle:vertical { height: 3px; width: 1px; }
QSplitter::handle:hover { background-color: #689d6a; /* aqua */ }
QTabWidget::pane { border: 1px solid #504945; /* bg2 */ background-color: #32302f; /* bg0_s */ }
QTabBar::tab { background-color: #504945; /* bg2 */ color: #bdae93; /* fg3 */ border: 1px solid #504945; border-bottom: none; padding: 5px 10px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background-color: #32302f; /* bg0_s (pane color) */ color: #ebdbb2; /* fg */ border: 1px solid #504945; border-bottom: 1px solid #32302f; /* Match pane bg */ }
QTabBar::tab:!selected:hover { background-color: #665c54; /* bg3 */ color: #ebdbb2; /* fg */ }
QTabBar::close-button { subcontrol-position: right; padding-left: 3px; }
QTabBar::close-button:hover { background-color: #fb4934; /* bright red */ }
QStatusBar { background-color: #3c3836; /* bg1 */ color: #bdae93; /* fg3 */ }
QScrollBar:vertical { background: #32302f; /* bg0_s */ width: 10px; margin: 0px 0px 0px 0px; border: 1px solid #504945; /* bg2 */ border-radius: 4px; }
QScrollBar::handle:vertical { background: #665c54; /* bg3 */ min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #7c6f64; /* bg4 */ }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: #32302f; /* bg0_s */ height: 10px; margin: 0px 0px 0px 0px; border: 1px solid #504945; /* bg2 */ border-radius: 4px; }
QScrollBar::handle:horizontal { background: #665c54; /* bg3 */ min-width: 20px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #7c6f64; /* bg4 */ }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QComboBox { background-color: #665c54; /* bg3 */ border: 1px solid #7c6f64; /* bg4 */ padding: 1px 18px 1px 3px; min-width: 6em; color: #ebdbb2;}
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #7c6f64; }
QComboBox QAbstractItemView { background-color: #3c3836; /* bg1 */ border: 1px solid #504945; /* bg2 */ selection-background-color: #458588; /* blue */ color: #d5c4a1; /* fg2 */ selection-color: #1d2021; /* bg0_h */ }
"""

         solarized_dark_content = """
/* Solarized Dark Theme for GemNet */
/* Solarized Palette */
/* base03:  #002b36 */
/* base02:  #073642 */
/* base01:  #586e75 */
/* base00:  #657b83 */
/* base0:   #839496 */
/* base1:   #93a1a1 */
/* base2:   #eee8d5 */
/* base3:   #fdf6e3 */
/* yellow:  #b58900 */
/* orange:  #cb4b16 */
/* red:     #dc322f */
/* magenta: #d33682 */
/* violet:  #6c71c4 */
/* blue:    #268bd2 */
/* cyan:    #2aa198 */
/* green:   #859900 */

QWidget {
    background-color: #002b36; /* base03 */
    color: #839496; /* base0 */
    border: none;
    font-family: "DejaVu Sans Mono", "Consolas", "Monaco", monospace; /* Example font */
}
QMainWindow, QDialog { background-color: #002b36; /* base03 */ }
QTextEdit, QLineEdit, QPlainTextEdit {
    background-color: #073642; /* base02 */
    color: #839496; /* base0 */
    border: 1px solid #586e75; /* base01 */
    selection-background-color: #268bd2; /* blue */
    selection-color: #002b36; /* base03 */
    padding: 2px;
}
QTreeView {
    background-color: #073642; /* base02 */
    color: #657b83; /* base00 */
    border: 1px solid #586e75; /* base01 */
    alternate-background-color: #002b36; /* base03 - subtle difference */
}
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background-color: #268bd2; /* blue */ color: #fdf6e3; /* base3 */ }
QTreeView::item:hover { background-color: #586e75; /* base01 */ color: #fdf6e3; /* base3 */ }
QPushButton { background-color: #586e75; /* base01 */ color: #fdf6e3; /* base3 */ border: 1px solid #657b83; /* base00 */ padding: 5px 10px; min-width: 60px; }
QPushButton:hover { background-color: #657b83; /* base00 */ border: 1px solid #839496; /* base0 */ }
QPushButton:pressed { background-color: #073642; /* base02 */ color: #839496; /* base0 */ }
QPushButton:disabled { background-color: #073642; /* base02 */ color: #586e75; /* base01 */ }
QMenuBar { background-color: #073642; /* base02 */ color: #839496; /* base0 */ }
QMenuBar::item { background-color: transparent; padding: 4px 8px; }
QMenuBar::item:selected { background-color: #586e75; /* base01 */ color: #fdf6e3; /* base3 */ }
QMenuBar::item:pressed { background-color: #268bd2; /* blue */ color: #fdf6e3; /* base3 */ }
QMenu { background-color: #073642; /* base02 */ color: #839496; /* base0 */ border: 1px solid #586e75; /* base01 */ padding: 5px; }
QMenu::item { padding: 4px 20px 4px 20px; }
QMenu::item:selected { background-color: #268bd2; /* blue */ color: #fdf6e3; /* base3 */ }
QMenu::separator { height: 1px; background-color: #586e75; /* base01 */ margin-left: 10px; margin-right: 5px; }
QSplitter::handle { background-color: #586e75; /* base01 */ border: 0px solid #002b36; width: 3px; margin: 1px 0; }
QSplitter::handle:horizontal { width: 3px; height: 1px; }
QSplitter::handle:vertical { height: 3px; width: 1px; }
QSplitter::handle:hover { background-color: #2aa198; /* cyan */ }
QTabWidget::pane { border: 1px solid #586e75; /* base01 */ background-color: #073642; /* base02 */ }
QTabBar::tab { background-color: #002b36; /* base03 */ color: #657b83; /* base00 */ border: 1px solid #586e75; border-bottom: none; padding: 5px 10px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background-color: #073642; /* base02 (pane color) */ color: #93a1a1; /* base1 */ border: 1px solid #586e75; border-bottom: 1px solid #073642; /* Match pane bg */ }
QTabBar::tab:!selected:hover { background-color: #586e75; /* base01 */ color: #fdf6e3; /* base3 */ }
QTabBar::close-button { subcontrol-position: right; padding-left: 3px; }
QTabBar::close-button:hover { background-color: #dc322f; /* red */ }
QStatusBar { background-color: #073642; /* base02 */ color: #657b83; /* base00 */ }
QScrollBar:vertical { background: #002b36; /* base03 */ width: 10px; margin: 0px 0px 0px 0px; border: 1px solid #586e75; /* base01 */ border-radius: 4px; }
QScrollBar::handle:vertical { background: #586e75; /* base01 */ min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #657b83; /* base00 */ }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: #002b36; /* base03 */ height: 10px; margin: 0px 0px 0px 0px; border: 1px solid #586e75; /* base01 */ border-radius: 4px; }
QScrollBar::handle:horizontal { background: #586e75; /* base01 */ min-width: 20px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #657b83; /* base00 */ }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QComboBox { background-color: #586e75; /* base01 */ border: 1px solid #657b83; /* base00 */ color: #fdf6e3; /* base3 */ padding: 1px 18px 1px 3px; min-width: 6em; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #657b83; }
QComboBox QAbstractItemView { background-color: #073642; /* base02 */ border: 1px solid #586e75; /* base01 */ selection-background-color: #268bd2; /* blue */ color: #839496; /* base0 */ selection-color: #fdf6e3; /* base3 */ }
"""

         nord_content = """
/* Nord Theme for GemNet */
/* Nord Palette */
/* Polar Night (Dark BG) */
/* nord0: #2E3440 */
/* nord1: #3B4252 */
/* nord2: #434C5E */
/* nord3: #4C566A */
/* Snow Storm (FG) */
/* nord4: #D8DEE9 */
/* nord5: #E5E9F0 */
/* nord6: #ECEFF4 */
/* Frost (Accents) */
/* nord7: #8FBCBB */ /* Turquoise */
/* nord8: #88C0D0 */ /* Lighter Blue */
/* nord9: #81A1C1 */ /* Blue */
/* nord10: #5E81AC */ /* Darker Blue */
/* Aurora (Other Accents) */
/* nord11: #BF616A */ /* Red */
/* nord12: #D08770 */ /* Orange */
/* nord13: #EBCB8B */ /* Yellow */
/* nord14: #A3BE8C */ /* Green */
/* nord15: #B48EAD */ /* Purple */

QWidget {
    background-color: #2E3440; /* nord0 */
    color: #D8DEE9; /* nord4 */
    border: none;
    font-family: "DejaVu Sans Mono", "Consolas", "Monaco", monospace; /* Example font */
}
QMainWindow, QDialog { background-color: #2E3440; /* nord0 */ }
QTextEdit, QLineEdit, QPlainTextEdit {
    background-color: #3B4252; /* nord1 */
    color: #ECEFF4; /* nord6 */
    border: 1px solid #4C566A; /* nord3 */
    selection-background-color: #5E81AC; /* nord10 */
    selection-color: #ECEFF4; /* nord6 */
    padding: 2px;
}
QTreeView {
    background-color: #3B4252; /* nord1 */
    color: #D8DEE9; /* nord4 */
    border: 1px solid #4C566A; /* nord3 */
    alternate-background-color: #434C5E; /* nord2 */
}
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background-color: #5E81AC; /* nord10 */ color: #ECEFF4; /* nord6 */ }
QTreeView::item:hover { background-color: #4C566A; /* nord3 */ color: #ECEFF4; /* nord6 */ }
QPushButton { background-color: #4C566A; /* nord3 */ color: #ECEFF4; /* nord6 */ border: 1px solid #5E697B; /* Slightly lighter than nord3 */ padding: 5px 10px; min-width: 60px; border-radius: 3px; }
QPushButton:hover { background-color: #5E697B; border: 1px solid #6A778C; }
QPushButton:pressed { background-color: #434C5E; /* nord2 */ }
QPushButton:disabled { background-color: #434C5E; /* nord2 */ color: #8892A4; /* Desaturated nord4 */ }
QMenuBar { background-color: #3B4252; /* nord1 */ color: #D8DEE9; /* nord4 */ }
QMenuBar::item { background-color: transparent; padding: 4px 8px; }
QMenuBar::item:selected { background-color: #4C566A; /* nord3 */ color: #ECEFF4; /* nord6 */ }
QMenuBar::item:pressed { background-color: #5E81AC; /* nord10 */ color: #ECEFF4; /* nord6 */ }
QMenu { background-color: #3B4252; /* nord1 */ color: #D8DEE9; /* nord4 */ border: 1px solid #4C566A; /* nord3 */ padding: 5px; }
QMenu::item { padding: 4px 20px 4px 20px; }
QMenu::item:selected { background-color: #5E81AC; /* nord10 */ color: #ECEFF4; /* nord6 */ }
QMenu::separator { height: 1px; background-color: #4C566A; /* nord3 */ margin-left: 10px; margin-right: 5px; }
QSplitter::handle { background-color: #434C5E; /* nord2 */ border: 0px solid #2E3440; width: 3px; margin: 1px 0; }
QSplitter::handle:horizontal { width: 3px; height: 1px; }
QSplitter::handle:vertical { height: 3px; width: 1px; }
QSplitter::handle:hover { background-color: #88C0D0; /* nord8 */ }
QTabWidget::pane { border: 1px solid #4C566A; /* nord3 */ background-color: #3B4252; /* nord1 */ }
QTabBar::tab { background-color: #434C5E; /* nord2 */ color: #D8DEE9; /* nord4 */ border: 1px solid #4C566A; border-bottom: none; padding: 5px 10px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background-color: #3B4252; /* nord1 (pane color) */ color: #ECEFF4; /* nord6 */ border: 1px solid #4C566A; border-bottom: 1px solid #3B4252; /* Match pane bg */ }
QTabBar::tab:!selected:hover { background-color: #4C566A; /* nord3 */ color: #ECEFF4; /* nord6 */ }
QTabBar::close-button { subcontrol-position: right; padding-left: 3px; }
QTabBar::close-button:hover { background-color: #BF616A; /* nord11 / red */ }
QStatusBar { background-color: #3B4252; /* nord1 */ color: #A5ABB6; /* Mid-tone gray */ }
QScrollBar:vertical { background: #2E3440; /* nord0 */ width: 10px; margin: 0px 0px 0px 0px; border: 1px solid #4C566A; /* nord3 */ border-radius: 4px; }
QScrollBar::handle:vertical { background: #4C566A; /* nord3 */ min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #5E697B; /* Lighter nord3 */ }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal { background: #2E3440; /* nord0 */ height: 10px; margin: 0px 0px 0px 0px; border: 1px solid #4C566A; /* nord3 */ border-radius: 4px; }
QScrollBar::handle:horizontal { background: #4C566A; /* nord3 */ min-width: 20px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #5E697B; /* Lighter nord3 */ }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QComboBox { background-color: #4C566A; /* nord3 */ border: 1px solid #5E697B; /* Lighter than nord3 */ color: #ECEFF4; /* nord6 */ padding: 1px 18px 1px 3px; min-width: 6em; border-radius: 3px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 15px; border-left: 1px solid #5E697B; }
QComboBox QAbstractItemView { background-color: #3B4252; /* nord1 */ border: 1px solid #4C566A; /* nord3 */ selection-background-color: #5E81AC; /* nord10 */ color: #D8DEE9; /* nord4 */ selection-color: #ECEFF4; /* nord6 */ }
"""

         # --- Create each theme file using the helper ---
         create_theme_file(os.path.join(styles_dir, "dark_theme.qss"), dark_theme_content)
         create_theme_file(os.path.join(styles_dir, "light_theme.qss"), light_theme_content)
         create_theme_file(os.path.join(styles_dir, "gruvbox_dark_theme.qss"), gruvbox_dark_content)
         create_theme_file(os.path.join(styles_dir, "solarized_dark_theme.qss"), solarized_dark_content)
         create_theme_file(os.path.join(styles_dir, "nord_theme.qss"), nord_content)


    def set_theme(self, theme_name):
        qss_path = self.themes.get(theme_name)
        # <<< Check if the file exists *after* ensuring styles exist >>>
        # ensure_styles_exist() # Called in __init__ now, no need to call here

        if qss_path and os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding='utf-8') as f:
                    style = f.read()
                app_instance = QApplication.instance()
                if app_instance:
                    app_instance.setStyleSheet(style)
                    print(f"Applied theme: {theme_name}")
                    if hasattr(self.app, 'status_bar') and hasattr(self.app.status_bar, 'showMessage'):
                       self.app.status_bar.showMessage(f"Theme set to: {theme_name}", 3000)
                else:
                    print("Error: QApplication instance not found.")
            except Exception as e:
                 print(f"Error loading or applying theme '{theme_name}' from {qss_path}: {e}")
        elif qss_path:
            print(f"Theme file not found (and could not be created?): {qss_path}")
            # Optionally try applying a default theme as fallback if creation failed
            # if theme_name != "dark": self.set_theme("dark")
        else:
            print(f"Theme name '{theme_name}' not defined in ThemeManager.")

# --- END OF FILE theme_manager.py ---
