"""Pygments token coloring for the bounded plain-text preview."""
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor
from pygments import lex
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.token import Keyword, String, Comment, Number, Name


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.lexer = TextLexer()

    def set_language(self, language):
        try:
            self.lexer = get_lexer_by_name(language.lower(), stripnl=False, ensurenl=False)
        except Exception:
            self.lexer = TextLexer()
        self.rehighlight()

    def highlightBlock(self, text):
        offset = 0
        for token, value in lex(text, self.lexer):
            color = next((color for kind, color in ((Keyword, "#9a73df"), (String, "#48977a"), (Comment, "#81859b"), (Number, "#c58b50"), (Name.Function, "#5799cc")) if token in kind), None)
            length = len(value.encode("utf-16-le")) // 2
            if color:
                style = QTextCharFormat()
                style.setForeground(QColor(color))
                self.setFormat(offset, length, style)
            offset += length
