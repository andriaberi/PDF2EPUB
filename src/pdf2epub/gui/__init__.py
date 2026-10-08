def main() -> int:
    """Open the window. Its web view is imported here, so the command line never needs it."""
    from .window import main as open_window

    return open_window()
