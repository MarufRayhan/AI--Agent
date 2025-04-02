"""
This module contains the ColorPrinter class, which is a callable object that
prints text in a specified color.
"""
import colorama

colorama.just_fix_windows_console()

COLORS = {
    "BLACK": colorama.Fore.BLACK,
    "RED": colorama.Fore.RED,
    "GREEN": colorama.Fore.GREEN,
    "YELLOW": colorama.Fore.YELLOW,
    "BLUE": colorama.Fore.BLUE,
    "MAGENTA": colorama.Fore.MAGENTA,
    "CYAN": colorama.Fore.CYAN,
    "WHITE": colorama.Fore.WHITE,
    "RESET": colorama.Fore.RESET,
    "LIGHTBLACK_EX": colorama.Fore.LIGHTBLACK_EX,
    "LIGHTRED_EX": colorama.Fore.LIGHTRED_EX,
    "LIGHTGREEN_EX": colorama.Fore.LIGHTGREEN_EX,
    "LIGHTYELLOW_EX": colorama.Fore.LIGHTYELLOW_EX,
    "LIGHTBLUE_EX": colorama.Fore.LIGHTBLUE_EX,
    "LIGHTMAGENTA_EX": colorama.Fore.LIGHTMAGENTA_EX,
    "LIGHTCYAN_EX": colorama.Fore.LIGHTCYAN_EX,
    "LIGHTWHITE_EX": colorama.Fore.LIGHTWHITE_EX,
}


class ColorPrinter:
    """
    A callable object that prints text in a specified color.

    Attributes:
        name (str): The name of the printer.
        color (str): The colorama.Fore color of the agent's output text.

    Examples:
        >>> from printer import ColorPrinter
        >>> color_printer = ColorPrinter("Agent", colorama.Fore.RED)
        >>> color_printer("Hello, World!")
        ### Agent ###
        Hello, World!  # <-- red color
    """

    def __init__(
        self,
        color: str,
    ) -> None:
        """
        Initialize the ColorPrinter object.

        Args:
            color (str): The color of the output text.
        """
        self.color = COLORS[color]

    def __call__(self, *args, **kwargs) -> None:
        """
        Prints the content in the agent's color and returns it.

        Args:
            content (T): The content to be printed.

        Returns:
            T: The content.
        """
        print(f"{self.color}", end="")
        print(*args, **kwargs)
        print(f"{colorama.Style.RESET_ALL}", end="", flush=True)
