# --- START OF FILE syntax_highlighter.py ---

from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
import re # Using re for slightly easier multi-line handling maybe

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.highlightingRules = []

        # Keywords
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor("#569CD6")) # Blueish
        keywordFormat.setFontWeight(QFont.Bold)
        keywords = [
            "\\bFalse\\b", "\\bNone\\b", "\\bTrue\\b", "\\band\\b", "\\bas\\b", "\\bassert\\b",
            "\\bbreak\\b", "\\bclass\\b", "\\bcontinue\\b", "\\bdef\\b", "\\bdel\\b", "\\belif\\b",
            "\\belse\\b", "\\bexcept\\b", "\\bfinally\\b", "\\bfor\\b", "\\bfrom\\b", "\\bglobal\\b",
            "\\bif\\b", "\\bimport\\b", "\\bin\\b", "\\bis\\b", "\\blambda\\b", "\\bnonlocal\\b",
            "\\bnot\\b", "\\bor\\b", "\\bpass\\b", "\\braise\\b", "\\breturn\\b", "\\btry\\b",
            "\\bwhile\\b", "\\bwith\\b", "\\byield\\b", "\\basync\\b", "\\bawait\\b"
        ]
        self.highlightingRules.extend([(QRegularExpression(pattern), keywordFormat) for pattern in keywords])

        # Built-in functions/types (subset)
        builtinFormat = QTextCharFormat()
        builtinFormat.setForeground(QColor("#4EC9B0")) # Teal
        builtins = [
            "\\bprint\\b", "\\blen\\b", "\\bstr\\b", "\\bint\\b", "\\bfloat\\b", "\\blist\\b",
            "\\bdict\\b", "\\bset\\b", "\\btuple\\b", "\\brange\\b", "\\btype\\b", "\\bsuper\\b",
            "\\bself\\b", "\\bcls\\b" # Treat self/cls like builtins for visibility
        ]
        self.highlightingRules.extend([(QRegularExpression(pattern), builtinFormat) for pattern in builtins])


        # Decorators
        decoratorFormat = QTextCharFormat()
        decoratorFormat.setForeground(QColor("#DCDCAA")) # Yellowish
        self.highlightingRules.append((QRegularExpression("^\\s*@\\w+"), decoratorFormat))

        # Single-line strings ('...' and "...")
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(QColor("#CE9178")) # Orange/Brown
        self.highlightingRules.append((QRegularExpression("'[^'\\\\]*(\\\\.[^'\\\\]*)*'"), stringFormat))
        self.highlightingRules.append((QRegularExpression("\"[^\"\\\\]*(\\\\.[^\"\\\\]*)*\""), stringFormat))

        # Numbers
        numberFormat = QTextCharFormat()
        numberFormat.setForeground(QColor("#B5CEA8")) # Greenish
        self.highlightingRules.append((QRegularExpression("\\b[0-9]+\\.?[0-9]*([eE][-+]?[0-9]+)?\\b"), numberFormat)) # Float/Int/Scientific

        # Comments (#...)
        commentFormat = QTextCharFormat()
        commentFormat.setForeground(QColor("#6A9955")) # Green
        commentFormat.setFontItalic(True)
        self.highlightingRules.append((QRegularExpression("#[^\n]*"), commentFormat))

        # Multi-line strings ("""...""" and '''...''') - Basic State Handling
        self.multiLineStringFormat = QTextCharFormat()
        self.multiLineStringFormat.setForeground(QColor("#CE9178")) # Orange/Brown
        self.tripleSingleQuoteStartRegex = QRegularExpression("'''")
        self.tripleDoubleQuoteStartRegex = QRegularExpression('"""')
        self.tripleSingleQuoteEndRegex = QRegularExpression("'''")
        self.tripleDoubleQuoteEndRegex = QRegularExpression('"""')


    def highlightBlock(self, text):
        # Apply single-line rules
        for pattern, format_ in self.highlightingRules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_)

        # Handle multi-line strings (state machine)
        self.setCurrentBlockState(0) # Default state

        startIndex = 0
        if self.previousBlockState() != 1: # Not inside a """ string
            startIndex = self.tripleDoubleQuoteStartRegex.match(text).capturedStart()
            if startIndex == -1: # Not starting """ on this line
                startIndex = self.tripleSingleQuoteStartRegex.match(text).capturedStart()
                if startIndex != -1: # Starting ''' on this line
                    match = self.tripleSingleQuoteEndRegex.match(text, startIndex + 3)
                    endIndex = match.capturedStart()
                    matchLength = 0
                    if endIndex == -1: # ''' doesn't end on this line
                         self.setCurrentBlockState(2) # State 2: Inside ''' string
                         matchLength = len(text) - startIndex
                    else: # ''' ends on this line
                         matchLength = endIndex - startIndex + match.capturedLength()
                    self.setFormat(startIndex, matchLength, self.multiLineStringFormat)

        # Handle state continuation for """ strings
        if self.previousBlockState() == 1: # Was inside a """ string
            match = self.tripleDoubleQuoteEndRegex.match(text)
            endIndex = match.capturedStart()
            matchLength = 0
            if endIndex == -1: # """ doesn't end on this line
                self.setCurrentBlockState(1) # Remain in state 1
                matchLength = len(text)
            else: # """ ends on this line
                matchLength = endIndex + match.capturedLength()
            self.setFormat(0, matchLength, self.multiLineStringFormat)
        else: # Check if """ starts on this line (if ''' didn't already)
             if self.currentBlockState() != 2: # Don't check if we already entered ''' state
                startIndex = self.tripleDoubleQuoteStartRegex.match(text).capturedStart()
                if startIndex != -1: # """ starts on this line
                    match = self.tripleDoubleQuoteEndRegex.match(text, startIndex + 3)
                    endIndex = match.capturedStart()
                    matchLength = 0
                    if endIndex == -1: # """ doesn't end on this line
                         self.setCurrentBlockState(1) # State 1: Inside """ string
                         matchLength = len(text) - startIndex
                    else: # """ ends on this line
                         matchLength = endIndex - startIndex + match.capturedLength()
                    self.setFormat(startIndex, matchLength, self.multiLineStringFormat)

         # Handle state continuation for ''' strings
        if self.previousBlockState() == 2: # Was inside a ''' string
            match = self.tripleSingleQuoteEndRegex.match(text)
            endIndex = match.capturedStart()
            matchLength = 0
            if endIndex == -1: # ''' doesn't end on this line
                self.setCurrentBlockState(2) # Remain in state 2
                matchLength = len(text)
            else: # ''' ends on this line
                matchLength = endIndex + match.capturedLength()
            self.setFormat(0, matchLength, self.multiLineStringFormat)
        # (Else clause for starting ''' is handled above before """ check)


# --- END OF FILE syntax_highlighter.py ---