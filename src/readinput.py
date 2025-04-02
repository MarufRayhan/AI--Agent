"""
This module provides functionality for reading multiple lines from user input.
"""


def read_lines() -> str:
    """
    Reads lines from the user until "END" or EOF is encountered.
    Note:
    The function will keep reading lines until EOF (End Of File) is signaled by
    the user. This typically occurs when the user presses
    `Ctrl-D` (Unix-like) or `Ctrl-Z` (Windows).

    Returns:
        str: The lines read from the user.
    """
    lines = ""
    try:
        while True:
            line = input()
            if line == "END":
                break
            lines += line
            lines += "\n"
    except EOFError:
        pass
    return lines
