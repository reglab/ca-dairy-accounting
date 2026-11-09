"""Identify which annual-report form a packet uses."""
import re

CONSULTANTS = [
    ("Livingston", r"Livingston\s+Dairy\s+Consulting"),
    ("IAS",        r"Innovative\s+Ag(?:riculture)?\s+Services|Innovative\s+Ag\b"),
    # Provost & Pritchard cover pages carry only the firm's address and website,
    # not its name, so ppeng.com is the reliable signal.
    ("ProvostPritchard", r"Provost\s*&?\s*Pritchard|ppeng\.com|"
                         r"130\s+N\.?\s+Garden\s+Street"),
]
# The official form, which is preferred whenever a packet contains it.
STANDARD = r"General Order No\. R5-2007-0035|DAIRY FACILITY INFORMATION|AVAILABLE NUTRIENTS"


def scan(doc, pages=25):
    """Return (consultant, has_standard_pages, text_pages, blank_pages)."""
    consultant, has_std = None, False
    text_pages = blank = 0
    for pg in doc[:pages]:
        t = pg.get_text()
        (text_pages := text_pages + 1) if t.strip() else (blank := blank + 1)
        if re.search(STANDARD, t, re.I):
            has_std = True
        if consultant is None:
            for nm, pat in CONSULTANTS:
                if re.search(pat, t, re.I):
                    consultant = nm
                    break
    return consultant, has_std, text_pages, blank


def form_type(doc, pages=25):
    """'Standard' when the official pages are present, else the consultant form."""
    consultant, has_std, *_ = scan(doc, pages)
    if has_std:
        return "Standard"
    return consultant or "Unknown"
