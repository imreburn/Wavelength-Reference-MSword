# -*- mode: python ; coding: utf-8 -*-
#
# Build a single-FOLDER Windows distribution:
#
#     pyinstaller csv_to_docx.spec
#
# Output: dist/csv_to_docx/   <- distribute this whole folder.
#         dist/csv_to_docx/csv_to_docx.exe   <- double-click to run.
#
# contents_directory='.' keeps the classic flat layout (PyInstaller < 6
# behaviour): the exe, its support files, AND the two .docx templates all sit
# side by side in dist/csv_to_docx/. The script locates the templates (and
# writes 'msword_output/') via app_dir(), which resolves to the .exe's own
# folder when frozen -- so it works no matter the current working directory,
# including when launched from a Windows shortcut.

block_cipher = None


a = Analysis(
    ['csv_to_docx.py'],
    pathex=[],
    binaries=[],
    # Ship the Word templates next to the exe (dest '.') so the script's plain
    # relative-path open() calls find them.
    datas=[
        ('traveler_template.docx', '.'),
        ('cert_template.docx', '.'),
    ],
    hiddenimports=[
        'docxtpl',
        'docx',
        'jinja2',
        'lxml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim weight: these pandas optional backends aren't used here.
    excludes=['matplotlib', 'PyQt5', 'PySide2', 'IPython', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,        # onedir: binaries go in COLLECT, not the exe
    name='csv_to_docx',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    # GUI app: no console window. Set to True to see print()/tracebacks.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='csv_to_docx',
    # Flat layout: put everything (incl. templates) beside the exe instead of
    # in an '_internal' subfolder. This is what lets the relative paths work.
    contents_directory='.',
)
