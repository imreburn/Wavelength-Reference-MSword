"""Filesystem locations for the app, resolved relative to the app/script so the
program works regardless of the current working directory."""

import os
import sys


def app_dir():
    """Directory the app lives in: the .exe's folder when frozen by PyInstaller,
    otherwise this script's folder. Templates are read from here and output is
    written here, so the app works regardless of the current working directory
    (e.g. when launched from a Windows shortcut, where the CWD may be elsewhere).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def settings_dir():
    """Folder that holds the JSON settings files, next to the app/script."""
    return os.path.join(app_dir(), "settings")
