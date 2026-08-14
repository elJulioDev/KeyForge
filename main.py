"""
KeyForge - Key remapping tool
Main application entry point
"""
import sys
import logging

def main():
    try:
        from src.gui import KeyForgeApp
        app = KeyForgeApp()
        app.run()
    except Exception as e:
        logging.getLogger(__name__).critical(f"Fatal error: {e}", exc_info=True)
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "KeyForge - Error",
                f"An unexpected error occurred:\n\n{type(e).__name__}: {e}\n\n"
                "The application will close."
            )
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
