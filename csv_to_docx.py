import dpi_awareness  # noqa: F401  (process-wide DPI awareness, import-time side effect)

import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog

import pandas as pd
from datetime import datetime
from docxtpl import DocxTemplate, RichText


def app_dir():
    """Directory the app lives in: the .exe's folder when frozen by PyInstaller,
    otherwise this script's folder. Templates are read from here and output is
    written here, so the app works regardless of the current working directory
    (e.g. when launched from a Windows shortcut, where the CWD may be elsewhere).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# Allowed choices for every "number of decimals" dropdown.
DECIMAL_CHOICES = ["0", "1", "2", "3", "4", "5"]


def get_settings():
    """Show the GUI, return a settings dict, or None if the window was closed
    without pressing "Create documents"."""
    result = {"submitted": False}

    root = tk.Tk()
    root.title("Create traveler and certificate sheets")

    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    mainframe.columnconfigure(1, weight=1)

    row = 0

    # --- CSV file selection ---------------------------------------------
    csv_path = tk.StringVar()

    def pick_csv():
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            csv_path.set(path)

    ttk.Button(mainframe, text="Select CSV file", command=pick_csv).grid(
        column=0, row=row, sticky=tk.W, padx=5, pady=5
    )
    ttk.Label(mainframe, textvariable=csv_path, foreground="#444").grid(
        column=1, row=row, columnspan=2, sticky=tk.W, padx=5, pady=5
    )
    row += 1

    # --- Sheet selection ------------------------------------------------
    gen_traveler = tk.BooleanVar(value=True)
    gen_cert = tk.BooleanVar(value=True)
    sheet_frame = ttk.Frame(mainframe)
    sheet_frame.grid(column=0, row=row, columnspan=3, sticky=tk.W, padx=5, pady=5)
    ttk.Checkbutton(
        sheet_frame, text="Traveler Sheet", variable=gen_traveler
    ).grid(column=0, row=0, sticky=tk.W, padx=(0, 20))
    ttk.Checkbutton(
        sheet_frame, text="Certificate Sheet", variable=gen_cert
    ).grid(column=1, row=0, sticky=tk.W)
    row += 1

    # --- Text inputs ----------------------------------------------------
    model = tk.StringVar(value="")
    source = tk.StringVar(value="Keysight N7778C")
    detector = tk.StringVar(value="Keysight N7748A")

    def add_text_field(label, var):
        nonlocal row
        ttk.Label(mainframe, text=label).grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=5
        )
        ttk.Entry(mainframe, width=40, textvariable=var).grid(
            column=1, row=row, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        row += 1

    add_text_field("Model", model)
    add_text_field("Source", source)
    add_text_field("Detector", detector)

    # --- Decimal-count section builder ----------------------------------
    def add_decimals_section(title, defaults, output_default):
        """Add a titled section with an output-filename field followed by four
        decimal dropdowns. Returns (filename_var, decimals_dict)."""
        nonlocal row
        ttk.Separator(mainframe, orient=tk.HORIZONTAL).grid(
            column=0, row=row, columnspan=3, sticky=(tk.W, tk.E), pady=(12, 4)
        )
        row += 1
        ttk.Label(mainframe, text=title, font=("TkDefaultFont", 10, "bold")).grid(
            column=0, row=row, columnspan=3, sticky=tk.W, padx=5, pady=(0, 4)
        )
        row += 1

        filename_var = tk.StringVar(value=output_default)
        ttk.Label(mainframe, text="Output filename").grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=3
        )
        ttk.Entry(mainframe, width=40, textvariable=filename_var).grid(
            column=1, row=row, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=3
        )
        row += 1

        vars_ = {}
        labels = [
            ("wavelength", "Wavelength decimals"),
            ("il", "I.L. decimals"),
            ("depth", "Depth decimals"),
            ("width", "Width decimals"),
        ]
        for key, label in labels:
            var = tk.StringVar(value=str(defaults[key]))
            ttk.Label(mainframe, text=label).grid(
                column=0, row=row, sticky=tk.W, padx=5, pady=3
            )
            ttk.Combobox(
                mainframe,
                width=5,
                textvariable=var,
                values=DECIMAL_CHOICES,
                state="readonly",
            ).grid(column=1, row=row, sticky=tk.W, padx=5, pady=3)
            vars_[key] = var
            row += 1
        return filename_var, vars_

    traveler_filename, traveler_vars = add_decimals_section(
        "Traveler sheet",
        {"wavelength": 2, "il": 1, "depth": 2, "width": 1},
        "traveler_sheet_filled.docx",
    )
    cert_filename, cert_vars = add_decimals_section(
        "Certificate sheet",
        {"wavelength": 1, "il": 1, "depth": 1, "width": 1},
        "certificate_sheet_filled.docx",
    )

    # --- Wavelength for insertion loss ----------------------------------
    il_wavelength = tk.StringVar(value="")
    add_text_field("Wavelength for insertion loss", il_wavelength)

    # --- Extra text inputs ----------------------------------------------
    extra_vars = []
    for i in range(1, 6):
        var = tk.StringVar(value="")
        ttk.Label(mainframe, text=f"Extra input {i}").grid(
            column=0, row=row, sticky=tk.W, padx=5, pady=3
        )
        ttk.Entry(mainframe, width=40, textvariable=var).grid(
            column=1, row=row, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=3
        )
        extra_vars.append(var)
        row += 1

    # --- Create documents button ----------------------------------------
    def create_documents():
        result["submitted"] = True
        result["csv_path"] = csv_path.get()
        result["gen_traveler"] = gen_traveler.get()
        result["gen_cert"] = gen_cert.get()
        result["model"] = model.get()
        result["source"] = source.get()
        result["detector"] = detector.get()
        result["traveler"] = {k: int(v.get()) for k, v in traveler_vars.items()}
        result["traveler_filename"] = traveler_filename.get()
        result["cert"] = {k: int(v.get()) for k, v in cert_vars.items()}
        try:
            result["cert"]["il_wavelength"] = float(il_wavelength.get())
        except ValueError:
            result["cert"]["il_wavelength"] = 0.0
        result["cert"]["extras"] = [v.get() for v in extra_vars]
        result["cert_filename"] = cert_filename.get()
        root.destroy()

    ttk.Button(mainframe, text="Create documents", command=create_documents).grid(
        column=0, row=row, columnspan=3, sticky=tk.E, padx=5, pady=(12, 5)
    )

    root.mainloop()

    return result if result["submitted"] else None


def build_rows(df, decimals):
    """Format each CSV row into the dict the templates expect, using the given
    per-field decimal counts."""
    return [
        {
            "date": r.Date,
            "wavelength": f"{r._2:.{decimals['wavelength']}f}",
            "serial": f"{r._3}",
            "depth": f"{r.Depth:.{decimals['depth']}f}",
            "width": f"{r._6:.{decimals['width']}f}",
            "loss": f"{r._4:.{decimals['il']}f}" if pd.notna(r._4) else "-",
            "temperature": f"{r.Temperature}" if pd.notna(r.Temperature) else "-",
            "ripple": "-",
        }
        for r in df.itertuples()
    ]

# Matches _{...} or ^{...}; the braces are literal, the contents are captured.
_SUBSUP_RE = re.compile(r'([_^])\{([^}]*)\}')


def parse_rich(txt):
    """Turn a string into a RichText, rendering _{x} as subscript and ^{x} as
    superscript (e.g. 'H_{2}O' or '1550^{th}'). Plain strings pass through
    unchanged, just wrapped in a RichText."""
    rt = RichText()
    pos = 0
    for m in _SUBSUP_RE.finditer(txt):
        if m.start() > pos:
            rt.add(txt[pos:m.start()])
        kind, inner = m.group(1), m.group(2)
        rt.add(inner, subscript=(kind == '_'), superscript=(kind == '^'))
        pos = m.end()
    if pos < len(txt):
        rt.add(txt[pos:])
    return rt


def build_rows_cert(df, params):
    """Build one certificate per group, where the group is the part of the
    'Label (SN)' before the dash (e.g. 1-1, 1-2, ... -> group "1").

    Each certificate dict carries header fields (date, serial, temperature,
    loss) taken from the group, plus a "cells" list with one entry per CSV row
    in the group for the inner table (wavelength + depth)."""
    group_key = df["Label (SN)"].astype(str)

    certs = []
    for prefix, group in df.groupby(group_key, sort=False):

        # Pick the I.L. from the row whose wavelength is closest to the
        # requested insertion-loss wavelength (only rows that have an I.L.).
        
        distances = (group["Wavelength (nm)"] - params["il_wavelength"]).abs()
        closest = group.loc[distances.idxmin()]
        il_vals = group["I.L."].dropna()
        if pd.notna(closest["I.L."]):
            loss = f"{closest['I.L.']:.{params['il']}f} dB"
        elif len(il_vals):
            loss = f"{il_vals.max():.{params['il']}f} dB"
        else:
            loss = "NA"

        temp_vals = group["Temperature"].dropna()

        extra_txts = []
        for txt in params['extras']:
            if txt != "":
                txt = f"({txt})"
            extra_txts.append(parse_rich(txt))
        
        certs.append({
            "date": closest["Date"],
            "serial": prefix,
            "loss": loss,
            "temperature": f"{temp_vals.iloc[0]}" if len(temp_vals) else "",
            "cells": [
                {
                    "wavelength": f"{row['Wavelength (nm)']:.{params['wavelength']}f}",
                    "depth": f"{row['Depth']:.{params['depth']}f}",
                    "extra": txt,
                }
                for (_, row), txt in zip(group.iterrows(), extra_txts)
            ],
        })
    return certs


def main():
    settings = get_settings()
    if settings is None:
        print("Cancelled.")
        return

    if not settings["csv_path"]:
        print("No CSV file selected.")
        return

    df = pd.read_csv(settings["csv_path"], dtype={"Label (SN)": str})
    df = df.sort_values(["Label (SN)", "Wavelength (nm)"])

    source = settings["source"]
    detector = settings["detector"]

    # Make sure the output folder exists (anchored to the app, not the CWD).
    output_dir = os.path.join(app_dir(), "msword_output")
    os.makedirs(output_dir, exist_ok=True)

    # Traveler sheet
    if settings["gen_traveler"]:
        traveler_rows = build_rows(df, settings["traveler"])
        doc_travel = DocxTemplate(os.path.join(app_dir(), "traveler_template.docx"))
        doc_travel.render({
            "source": source,
            "detector": detector,
            "rows": traveler_rows,
        })
        doc_travel.save(os.path.join(output_dir, settings["traveler_filename"]))

    # Certificate sheet (one per group), using the certificate decimal settings.
    if settings["gen_cert"]:
        cert_rows = build_rows_cert(df, settings["cert"])
        doc_cert = DocxTemplate(os.path.join(app_dir(), "cert_template.docx"))
        doc_cert.render({
            "model": settings["model"],
            "source": source,
            "detector": detector,
            "rows": cert_rows,
        })
        doc_cert.save(os.path.join(output_dir, settings["cert_filename"]))

    if settings["gen_traveler"] and settings["gen_cert"]:
        print("Done: traveler and certificate sheets created.")
    elif settings["gen_traveler"]:
        print("Done: traveler sheet created.")
    elif settings["gen_cert"]:
        print("Done: certificate sheet created.")
    else:
        print("Nothing selected: no sheets created.")


if __name__ == "__main__":
    main()
