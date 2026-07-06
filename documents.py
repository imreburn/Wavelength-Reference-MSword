"""CSV -> docx generation engine (pandas + docxtpl, no GUI)."""

import os
import re

import pandas as pd
from docxtpl import DocxTemplate, RichText, InlineImage
from docx.shared import Mm

from config import TARGET_TRAVELER
from paths import app_dir
from signatures import load_signatures, signature_width_mm


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
        
        if pd.notna(closest["I.L."]) and params["il_wavelength"] != 0:
            loss = f"{closest['I.L.']:.{params['il']}f} dB"
            il_wl = f"@ {closest['Wavelength (nm)']:.{params['wavelength']}f} nm"
        elif len(il_vals):
            loss = f"{il_vals.max():.{params['il']}f} dB"
            il_wl = f"@ {group.loc[il_vals.idxmax()]['Wavelength (nm)']:.{params['wavelength']}f} nm"
        else:
            loss, il_wl = "NA", ""

        temp_vals = group["Temperature"].dropna()

        extra_txts = []
        for txt in params['extras']:
            if txt != "":
                txt = f"({txt})"
            extra_txts.append(parse_rich(txt))

        certs.append({
            "date": closest["Date"],
            "serial": prefix,
            "ilwavelength": il_wl,
            "loss": loss,
            "temperature": f"{temp_vals.iloc[0]:.1f}" if len(temp_vals) else "23.0",
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


def run_once(settings):
    """Generate the requested sheets. Returns (message, color, paths): the
    outcome message/colour for the result popup and the list of generated files
    to open afterwards (empty on error or when nothing was created)."""
    if not settings["csv_path"]:
        return "No CSV file selected.", "red", []

    try:
        message, paths = _generate(settings)
        return message, "green", paths
    except Exception as exc:  # no console, so surface failures in the popup
        return f"Error: {exc}", "red", []


def _generate(settings):
    df = pd.read_csv(settings["csv_path"], dtype={"Label (SN)": str})
    df = df.sort_values(["Label (SN)", "Wavelength (nm)"])

    source = settings["source"]
    detector = settings["detector"]

    # Make sure the output folder exists (anchored to the app, not the CWD).
    output_dir = os.path.join(app_dir(), "output_sheets")
    os.makedirs(output_dir, exist_ok=True)

    paths = []  # generated files, in the order they should be opened

    # Traveler sheet
    if settings["target"] == TARGET_TRAVELER:
        traveler_rows = build_rows(df, settings["traveler"])
        doc_travel = DocxTemplate(os.path.join(app_dir(), "traveler_template.docx"))
        doc_travel.render({
            "source": source,
            "detector": detector,
            "rows": traveler_rows,
        })
        traveler_out = os.path.join(output_dir, settings["traveler_filename"])
        doc_travel.save(traveler_out)
        paths.append(traveler_out)
        return "Traveler sheet created.", paths

    # Certificate sheet (one per group), using the certificate decimal settings.
    cert_rows = build_rows_cert(df, settings["cert"])
    doc_cert = DocxTemplate(os.path.join(app_dir(), "cert_template.docx"))

    # Signature: look up the chosen name's image and scale it down for insertion.
    sig_name = settings["signed_by"]
    sig_path = load_signatures().get(sig_name)
    sig_image = InlineImage(doc_cert, sig_path, width=Mm(signature_width_mm(sig_path))) if sig_path else ""

    doc_cert.render({
        "model": settings["part_num"],
        "source": source,
        "detector": detector,
        "rows": cert_rows,
        "signame": sig_name,
        "sigimage": sig_image,
    })
    cert_out = os.path.join(output_dir, settings["cert_filename"])
    doc_cert.save(cert_out)
    paths.append(cert_out)
    return "Certificate sheet created.", paths
