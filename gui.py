"""All tkinter UI: CSV picker, the settings window, and the result popup."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import (
    DECIMAL_CHOICES,
    DEFAULT_SETTINGS_FILE,
    TARGET_CERT,
    TARGET_TRAVELER,
    ensure_default_settings,
    list_setting_files,
    load_settings,
)
from signatures import load_signatures


def pick_csv_file():
    """Pop up a file-open dialog and return the chosen CSV path, or "" if the
    dialog was cancelled. Uses its own hidden root so it can run before the main
    GUI window is created."""
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
    )
    root.destroy()
    return path


def get_settings(csv_path):
    """Show the GUI for the already-selected ``csv_path``, return a settings
    dict, or None if the window was closed without pressing "Create documents".
    The in-window message area is used for input-validation errors."""
    result = {"submitted": False}

    # Settings files: make sure default.json exists, list the available files and load the default one to seed every input field below.
    ensure_default_settings()
    setting_files = list_setting_files() or [DEFAULT_SETTINGS_FILE]
    initial_setting = (
        DEFAULT_SETTINGS_FILE
        if DEFAULT_SETTINGS_FILE in setting_files
        else setting_files[0]
    )
    initial_data = load_settings(initial_setting)

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

    # --- CSV file (selected at startup) ---------------------------------
    r = next_row(mainframe)
    ttk.Label(mainframe, text="CSV file").grid(
        column=0, row=r, sticky=tk.W, padx=5, pady=5
    )
    ttk.Label(
        mainframe, text=os.path.basename(csv_path), foreground="green"
    ).grid(column=1, row=r, columnspan=2, sticky=tk.W, padx=5, pady=5)

    # --- Target selection (which sheet to create) -----------------------
    # A single dropdown replaces the old per-section checkboxes; exactly one
    # sheet is created per run. Switching to the Certificate Sheet first asks
    # the user to confirm they have reviewed the Traveler Sheet.
    target = tk.StringVar(value=TARGET_TRAVELER)
    prev_target = [TARGET_TRAVELER]  # last confirmed value, for reverting

    def confirm_cert():
        """Native Yes/No dialog (same style as the result popup). Returns True
        if the user is sure, False otherwise."""
        return messagebox.askyesno(
            "Confirm",
            "I have reviewed the generated Traveler Sheet and confirmed "
            "that everything is correct.",
            icon="warning",
            parent=root,
        )

    def on_target_selected(_event=None):
        if target.get() == TARGET_CERT and prev_target[0] != TARGET_CERT:
            if not confirm_cert():
                target.set(prev_target[0])  # revert
                return
        prev_target[0] = target.get()

    # --- Settings file selection ----------------------------------------
    # Lists the JSON files in the settings folder; picking one reloads every
    # input field from that file. The handler is bound later, once all the
    # fields it needs to update have been created (see apply_settings below).
    setting_name = tk.StringVar(value=initial_setting)
    r = next_row(mainframe)
    ttk.Label(mainframe, text="Setting").grid(
        column=0, row=r, sticky=tk.W, padx=5, pady=5
    )
    setting_combo = ttk.Combobox(
        mainframe,
        textvariable=setting_name,
        values=setting_files,
        state="readonly",
        width=20,
    )
    setting_combo.grid(column=1, row=r, sticky=tk.W, padx=5, pady=5)

    r = next_row(mainframe)
    ttk.Label(mainframe, text="Target").grid(
        column=0, row=r, sticky=tk.W, padx=5, pady=5
    )
    target_combo = ttk.Combobox(
        mainframe,
        textvariable=target,
        values=[TARGET_TRAVELER, TARGET_CERT],
        state="readonly",
        width=20,
    )
    target_combo.grid(column=1, row=r, sticky=tk.W, padx=5, pady=5)
    target_combo.bind("<<ComboboxSelected>>", on_target_selected)

    # --- Text inputs ----------------------------------------------------
    part_num = tk.StringVar(value="")
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
        entry._ph_show = show  # used by apply_settings to reset an empty field
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
    def add_decimals_section(parent, title, defaults, output_default, after_header=None):
        """Add a titled section with an output-filename field and four decimal
        dropdowns. ``after_header`` is an optional callable(parent) used to add
        extra rows right below the section header. Returns
        (filename_var, decimals_dict)."""
        add_section_header(parent, title)
        if after_header:
            after_header(parent)

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

    # "Certified by" dropdown: names parsed from the sigs/ folder, nothing
    # selected by default (validated on Create).
    signatures = load_signatures()
    certified_by = tk.StringVar(value="")

    def add_certified_by(parent):
        r = next_row(parent)
        ttk.Label(parent, text="Certified by").grid(
            column=0, row=r, sticky=tk.W, padx=5, pady=3
        )
        ttk.Combobox(
            parent,
            textvariable=certified_by,
            values=list(signatures),
            state="readonly",
            width=30,
        ).grid(column=1, row=r, columnspan=2, sticky=tk.W, padx=5, pady=3)

    traveler_filename, traveler_vars = add_decimals_section(
        left_col,
        "Traveler Sheet",
        {"wavelength": 2, "il": 1, "depth": 2, "width": 1},
        "traveler_sheet_filled.docx",
    )
    cert_filename, cert_vars = add_decimals_section(
        right_col,
        "Certificate Sheet",
        {"wavelength": 1, "il": 1, "depth": 1, "width": 1},
        "certificate_sheet_filled.docx",
        after_header=add_certified_by,
    )

    # Wider entries in the certificate column so long placeholders fit.
    cert_field_width = 50

    # --- Model and wavelength for insertion loss (certificate fields) ---
    part_num_entry = add_text_field(
        right_col, "Part Number", part_num,
        placeholder="(Required) e.g. C2H2-12-H(5.5)-50-FCAPC", width=cert_field_width,
    )
    il_wavelength = tk.StringVar(value="")
    il_wavelength_entry = add_text_field(
        right_col,
        "Wavelength for I.L.",
        il_wavelength,
        placeholder="(Optional) e.g. 1550 (in nm)",
        width=cert_field_width,
    )

    # --- Extra text inputs ----------------------------------------------
    extra_vars = []
    extra_entries = []
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
        extra_entries.append(entry)

    # --- Apply a settings dict to every input field ---------------------
    def set_placeholder_field(entry, var, value):
        """Set a placeholder-backed field: show the real value, or restore the
        greyed-out hint when the value is empty."""
        value = "" if value is None else str(value)
        if value:
            entry._placeholder_on = False
            entry.configure(foreground=default_fg)
            var.set(value)
        else:
            var.set("")
            entry._ph_show()

    def apply_settings(data):
        """Populate every input field from a loaded settings dict."""
        source.set(data["source"])
        detector.set(data["detector"])
        traveler_filename.set(data["traveler_filename"])
        cert_filename.set(data["cert_filename"])
        for key, var in traveler_vars.items():
            var.set(str(data["traveler_decimals"].get(key, var.get())))
        for key, var in cert_vars.items():
            var.set(str(data["cert_decimals"].get(key, var.get())))
        # Only accept a "Certified by" name that matches a known signature.
        cb = data.get("certified_by", "")
        certified_by.set(cb if cb in signatures else "")
        set_placeholder_field(part_num_entry, part_num, data.get("part_num", ""))
        set_placeholder_field(
            il_wavelength_entry, il_wavelength, data.get("il_wavelength", "")
        )
        extras = data.get("extras", [])
        for i, entry in enumerate(extra_entries):
            set_placeholder_field(
                entry, extra_vars[i], extras[i] if i < len(extras) else ""
            )

    def on_setting_selected(_event=None):
        apply_settings(load_settings(setting_name.get()))

    setting_combo.bind("<<ComboboxSelected>>", on_setting_selected)
    apply_settings(initial_data)  # seed all fields from the default settings file

    # --- Create documents button ----------------------------------------
    message_var = tk.StringVar(value="")

    def set_message(text, color):
        message_var.set(text)
        message_label.configure(foreground=color)

    def create_documents():
        strip_placeholders()  # ensure hint text is never read as real input
        if target.get() == TARGET_CERT and not part_num.get().strip():
            set_message(
                'The "Part Number" field cannot be empty when the '
                'Certificate Sheet target is selected.',
                "red",
            )
            restore_placeholders()  # bring back hint text after stripping
            return
        if target.get() == TARGET_CERT and not certified_by.get():
            set_message(
                'Please select a "Certified by" name for the Certificate Sheet.',
                "red",
            )
            restore_placeholders()
            return
        set_message("", "red")
        result["submitted"] = True
        result["csv_path"] = csv_path
        result["target"] = target.get()
        result["certified_by"] = certified_by.get()
        result["part_num"] = part_num.get()
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
        foreground="red",
        wraplength=400,
        justify=tk.CENTER,
    )
    message_label.grid(column=0, row=next_row(mainframe), columnspan=3, padx=5, pady=(0, 5))

    root.mainloop()

    return result if result["submitted"] else None


def show_result(message, color):
    """Show the outcome of the run in a small popup window, then return so the
    program can exit. ``color`` is "red" for errors, anything else for success."""
    root = tk.Tk()
    root.withdraw()
    if color == "red":
        messagebox.showerror("Result", message)
    else:
        messagebox.showinfo("Result", message)
    root.destroy()
