"""Signature image discovery and sizing (no Pillow dependency)."""

import os
import re
import struct

from paths import app_dir


# Matches "signature-<name>.<ext>"; the captured group is the person's name.
_SIGNATURE_RE = re.compile(r"signature-(.+)\.(?:png|jpe?g)$", re.IGNORECASE)

# Signature sizing
SIG_HEIGHT_MM = 25
SIG_MAX_WIDTH_MM = 40


def load_signatures():
    """Return an ordered {name: image_path} dict for the signature images in the
    sibling ``sigs`` folder, where the name is the part of the filename after
    "signature-". Empty if the folder is missing."""
    sig_dir = os.path.join(app_dir(), "sigs")
    sigs = {}
    if os.path.isdir(sig_dir):
        for fname in sorted(os.listdir(sig_dir)):
            m = _SIGNATURE_RE.match(fname)
            if m:
                sigs[m.group(1)] = os.path.join(sig_dir, fname)
    return sigs


def _image_pixel_size(path):
    """Return (width_px, height_px) for a PNG or JPEG by reading only its header, so we don't need a Pillow dependency. Returns None if the size can't be read."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
            # PNG: 8-byte signature, then IHDR with width/height as big-endian uint32.
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
                return w, h
            # JPEG: walk the marker segments to the Start-Of-Frame (SOFn).
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                b = f.read(1)
                while b and b == b"\xff":
                    marker = f.read(1)
                    while marker == b"\xff":  # skip fill bytes
                        marker = f.read(1)
                    # SOF0..SOF15 hold the dimensions (excluding non-frame markers).
                    if 0xC0 <= marker[0] <= 0xCF and marker[0] not in (0xC4, 0xC8, 0xCC):
                        f.read(3)  # segment length (2) + precision (1)
                        h, w = struct.unpack(">HH", f.read(4))
                        return w, h
                    seg_len = struct.unpack(">H", f.read(2))[0]
                    f.seek(seg_len - 2, 1)
                    b = f.read(1)
    except (OSError, struct.error):
        pass
    return None


def signature_width_mm(path):
    """Width (in mm) to render a signature at, chosen so its rendered HEIGHT is
    SIG_HEIGHT_MM, then clamped to SIG_MAX_WIDTH_MM. Falls back to the cap if the
    image dimensions can't be read."""
    size = _image_pixel_size(path)
    if not size:
        return SIG_MAX_WIDTH_MM
    w_px, h_px = size
    width = SIG_HEIGHT_MM * (w_px / h_px)
    return min(width, SIG_MAX_WIDTH_MM)
