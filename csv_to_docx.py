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


def get_settings(initial_message="", initial_message_color="green"):
    """Show the GUI, return a settings dict, or None if the window was closed
    without pressing "Create documents". ``initial_message`` is shown in the
    message area (e.g. the result of the previous run, since there is no
    console to print to)."""
    result = {"submitted": False}

    root = tk.Tk()
    root.title("Create Traveler and Certificate Sheets")
    root.geometry("+50+10")  # fix top-left position on every loop

    mainframe = ttk.Frame(root, padding="10 10 10 10")
    mainframe.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    mainframe.columnconfigure(1, weight=1)

    # Larger style for the action buttons. For ttk buttons, size comes from the
    # font and internal padding=(x, y) rather than a height option.
    ttk.Style().configure(
        "Big.TButton",
        font=("TkDefaultFont", 11),
        padding=(14, 8),
        anchor="center",
    )

    # Per-frame grid cursor: returns the next free row for the given frame so
    # each column/section can be laid out independently.
    grid_row = {}

    def next_row(frame):
        r = grid_row.get(frame, 0)
        grid_row[frame] = r + 1
        return r

    # --- CSV file selection ---------------------------------------------
    csv_path = tk.StringVar()
    csv_status = tk.StringVar(value="No file selected")

    def pick_csv():
        path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            csv_path.set(path)
            csv_status.set(f"Selected: {os.path.basename(path)}")
            csv_status_label.configure(foreground="green")

    r = next_row(mainframe)
    ttk.Button(
        mainframe, text="Select CSV file", command=pick_csv, style="Big.TButton"
    ).grid(column=0, row=r, sticky=tk.W, padx=5, pady=5)
    csv_status_label = ttk.Label(mainframe, textvariable=csv_status, foreground="#b00")
    csv_status_label.grid(
        column=1, row=r, columnspan=2, sticky=tk.W, padx=5, pady=5
    )

    # --- Sheet selection (checkboxes live in each section below) --------
    gen_traveler = tk.BooleanVar(value=False)
    gen_cert = tk.BooleanVar(value=False)

    # --- Text inputs ----------------------------------------------------
    model = tk.StringVar(value="")
    source = tk.StringVar(value="Keysight N7778C Tunable Laser Source")
    detector = tk.StringVar(value="Keysight N7748A Power Meter")

    # --- Placeholder (hint) text support --------------------------------
    # tkinter has no native placeholder, so we show greyed-out example text
    # in empty fields and clear it on focus. Registered entries are stripped
    # before their values are read, so a placeholder never becomes real input.
    default_fg = ttk.Style().lookup("TEntry", "foreground") or "black"
    placeholder_entries = []  # (entry, var, placeholder)

    def add_placeholder(entry, var, placeholder):
        def show():
            if not var.get():
                entry._placeholder_on = True
                entry.configure(foreground="grey")
                var.set(placeholder)

        def clear():
            if getattr(entry, "_placeholder_on", False):
                entry._placeholder_on = False
                var.set("")
                entry.configure(foreground=default_fg)

        entry.bind("<FocusIn>", lambda _e: clear())
        entry.bind("<FocusOut>", lambda _e: show())
        show()
        placeholder_entries.append((entry, show, clear))

    def strip_placeholders():
        for _entry, _show, clear in placeholder_entries:
            clear()

    def restore_placeholders():
        for _entry, show, _clear in placeholder_entries:
            show()

    def add_text_field(parent, label, var, placeholder=None, width=40):
        r = next_row(parent)
        ttk.Label(parent, text=label).grid(
            column=0, row=r, sticky=tk.W, padx=5, pady=5
        )
        entry = ttk.Entry(parent, width=width, textvariable=var)
        entry.grid(
            column=1, row=r, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        if placeholder:
            add_placeholder(entry, var, placeholder)
        return entry

    def add_section_header(parent, title):
        r = next_row(parent)
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(
            column=0, row=r, columnspan=3, sticky=(tk.W, tk.E), pady=(12, 4)
        )
        r = next_row(parent)
        ttk.Label(parent, text=title, font=("TkDefaultFont", 10, "bold")).grid(
            column=0, row=r, columnspan=3, sticky=tk.W, padx=5, pady=(0, 4)
        )

    # --- Two-column body: Traveler on the left, Certificate on the right -
    body = ttk.Frame(mainframe)
    body.grid(
        column=0, row=next_row(mainframe), columnspan=3,
        sticky=(tk.N, tk.W, tk.E, tk.S),
    )
    body.columnconfigure(0, weight=1, uniform="cols")
    body.columnconfigure(1, weight=1, uniform="cols")

    left_col = ttk.Frame(body)
    left_col.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))
    left_col.columnconfigure(1, weight=1)

    right_col = ttk.Frame(body)
    right_col.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(10, 0))
    right_col.columnconfigure(1, weight=1)

    # --- Test Equipment section (left column only) ----------------------
    add_section_header(left_col, "Test Equipment")
    add_text_field(left_col, "Source", source)
    add_text_field(left_col, "Detector", detector)

    # --- Decimal-count section builder ----------------------------------
    def add_decimals_section(parent, title, defaults, output_default, gen_var, checkbox_label):
        """Add a titled section beginning with an enable checkbox, followed by
        an output-filename field and four decimal dropdowns. Returns
        (filename_var, decimals_dict)."""
        add_section_header(parent, title)

        r = next_row(parent)
        ttk.Label(parent, text=checkbox_label).grid(
            column=0, row=r, sticky=tk.W, padx=5, pady=(0, 4)
        )
        ttk.Checkbutton(parent, variable=gen_var).grid(
            column=1, row=r, columnspan=2, sticky=tk.W, padx=5, pady=(0, 4)
        )

        filename_var = tk.StringVar(value=output_default)
        r = next_row(parent)
        ttk.Label(parent, text="Output filename").grid(
            column=0, row=r, sticky=tk.W, padx=5, pady=3
        )
        ttk.Entry(parent, width=40, textvariable=filename_var).grid(
            column=1, row=r, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=3
        )

        vars_ = {}
        labels = [
            ("wavelength", "Wavelength Decimals"),
            ("il", "I.L. Decimals"),
            ("depth", "Depth Decimals"),
            ("width", "Width Decimals"),
        ]
        for key, label in labels:
            var = tk.StringVar(value=str(defaults[key]))
            r = next_row(parent)
            ttk.Label(parent, text=label).grid(
                column=0, row=r, sticky=tk.W, padx=5, pady=3
            )
            ttk.Combobox(
                parent,
                width=5,
                textvariable=var,
                values=DECIMAL_CHOICES,
                state="readonly",
            ).grid(column=1, row=r, sticky=tk.W, padx=5, pady=3)
            vars_[key] = var
        return filename_var, vars_

    traveler_filename, traveler_vars = add_decimals_section(
        left_col,
        "Traveler Sheet",
        {"wavelength": 2, "il": 1, "depth": 2, "width": 1},
        "traveler_sheet_filled.docx",
        gen_traveler,
        "Create Traveler Sheet?",
    )
    cert_filename, cert_vars = add_decimals_section(
        right_col,
        "Certificate Sheet",
        {"wavelength": 1, "il": 1, "depth": 1, "width": 1},
        "certificate_sheet_filled.docx",
        gen_cert,
        "Create Certificate Sheet?",
    )

    # Wider entries in the certificate column so long placeholders fit.
    cert_field_width = 50

    # --- Model and wavelength for insertion loss (certificate fields) ---
    add_text_field(
        right_col, "Part Number", model,
        placeholder="(Required) e.g. C2H2-12-H(5.5)-50-FCAPC", width=cert_field_width,
    )
    il_wavelength = tk.StringVar(value="")
    add_text_field(
        right_col,
        "Wavelength for I.L.",
        il_wavelength,
        placeholder="(Optional) e.g. 1550 (in nm)",
        width=cert_field_width,
    )

    # --- Extra text inputs ----------------------------------------------
    extra_vars = []
    for i in range(1, 6):
        var = tk.StringVar(value="")
        r = next_row(right_col)
        ttk.Label(right_col, text=f"Extra input {i}").grid(
            column=0, row=r, sticky=tk.W, padx=5, pady=3
        )
        entry = ttk.Entry(right_col, width=cert_field_width, textvariable=var)
        entry.grid(
            column=1, row=r, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=3
        )
        add_placeholder(entry, var, f"(Optional) Note for {i}-th absorption. e.g. H^{{12}}CN, H_{{2}}O")
        extra_vars.append(var)

    # --- Create documents button ----------------------------------------
    message_var = tk.StringVar(value=initial_message)

    def set_message(text, color):
        message_var.set(text)
        message_label.configure(foreground=color)

    def create_documents():
        strip_placeholders()  # ensure hint text is never read as real input
        if gen_cert.get() and not model.get().strip():
            set_message(
                'The "Model" field cannot be empty when '
                '"Create Certificate Sheet?" is checked.',
                "red",
            )
            restore_placeholders()  # bring back hint text after stripping
            return
        set_message("", "red")
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

    # Exit leaves result["submitted"] False, so get_settings returns None and
    # the main loop stops.
    button_frame = ttk.Frame(mainframe)
    button_frame.grid(column=0, row=next_row(mainframe), columnspan=3, pady=(12, 5))
    ttk.Button(
        button_frame, text="Create", command=create_documents, style="Big.TButton"
    ).grid(column=0, row=0, padx=5)
    ttk.Button(
        button_frame, text="Exit", command=root.destroy, style="Big.TButton"
    ).grid(column=1, row=0, padx=5)
    message_label = ttk.Label(
        mainframe,
        textvariable=message_var,
        foreground=initial_message_color,
        wraplength=400,
        justify=tk.CENTER,
    )
    message_label.grid(column=0, row=next_row(mainframe), columnspan=3, padx=5, pady=(0, 5))

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
    # Loop so the user can create sheets repeatedly; closing/cancelling the
    # window (get_settings returns None) ends the program. The status message
    # from each run is shown in the next window, since there is no console.
    message, color = "", "green"
    while True:
        settings = get_settings(message, color)
        if settings is None:
            return
        message, color = run_once(settings)


def run_once(settings):
    """Generate the requested sheets. Returns (message, color) describing the
    outcome, to be displayed in the GUI on the next loop."""
    if not settings["csv_path"]:
        return "No CSV file selected.", "red"

    try:
        return _generate(settings), "green"
    except Exception as exc:  # no console, so surface failures in the GUI
        return f"Error: {exc}", "red"


def _generate(settings):
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
        return "Done: traveler and certificate sheets created."
    elif settings["gen_traveler"]:
        return "Done: traveler sheet created."
    elif settings["gen_cert"]:
        return "Done: certificate sheet created."
    else:
        return "Nothing selected: no sheets created."


if __name__ == "__main__":
    main()
