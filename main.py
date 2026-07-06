import dpi_awareness  # noqa: F401  (process-wide DPI awareness, import-time side effect)

import os
import subprocess
import sys

from documents import run_once
from gui import get_settings, pick_csv_file, show_result


def open_file(path):
    """Hand a file to the OS default app (Word for .docx) as a detached process,
    so it stays open after this program exits."""
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])  # fire-and-forget
    else:
        subprocess.Popen(["xdg-open", path])


def main():
    csv_path = pick_csv_file()
    if not csv_path:  # dialog cancelled: nothing to do
        return

    while True:
        settings = get_settings(csv_path)
        if settings is None:  # window closed without pressing "Create"
            return

        message, color, paths = run_once(settings)
        show_result(message, color)
        for path in paths:
            open_file(path)


if __name__ == "__main__":
    main()
