"""Error type for reporting malformed diff input at a precise location."""


class DiffFormatError(Exception):
    """Raised when unified diff text does not match the expected grammar.

    Carries the 1-indexed line and column of the offending text so a caller
    (or the CLI) can point straight at the problem instead of making someone
    scan the whole diff by hand.
    """

    def __init__(self, message, line, column, source_line=""):
        self.message = message
        self.line = line
        self.column = column
        self.source_line = source_line
        super().__init__(message)

    def __str__(self):
        location = f"line {self.line}, column {self.column}: {self.message}"
        if not self.source_line:
            return location
        pointer = " " * (self.column - 1) + "^"
        return f"{location}\n    {self.source_line}\n    {pointer}"
