"""Word-geometry helpers shared by every form-type extractor.

Annual report PDFs place a label and its value on the same visual row but as
separate text objects, and often put a second label/value pair further right on
that same row. Reading the flowed text therefore pairs labels with the wrong
numbers, so every value here is located by coordinate.
"""
import re
from collections import defaultdict

NUM = re.compile(r"^\(?-?[\d,]+\.?\d*\)?$")
Y_BAND = 1.8          # a label and its value sit within this many points vertically
_band = Y_BAND        # active tolerance; OCR baselines jitter more than native text


def set_band(v):
    """Widen the row tolerance for OCR'd pages, where baselines are noisier."""
    global _band
    _band = float(v)


def get_band():
    return _band


def num(tok):
    """'1,234.5'->1234.5, '(198.7)'->-198.7, '-'/''/non-numeric->None."""
    t = str(tok).strip()
    if t in ("-", "", "–", "—"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "").replace("$", "")
    if not re.fullmatch(r"-?\d*\.?\d+", t):
        return None
    v = float(t)
    return -v if neg else v


def words(page):
    """[(x0, y0, x1, y1, text)] for one page, with split figures rejoined.

    Some forms emit a figure as two adjacent text runs, split at the decimal
    point ("21,811" then ".85") or at a thousands separator ("81" then
    ",099.08"), which would otherwise be read as two separate numbers.
    """
    raw = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
    raw.sort(key=lambda t: (round(t[1], 1), t[0]))
    out = []
    for t in raw:
        if out:
            p = out[-1]
            if (t[4][:1] in ".," and re.fullmatch(r"[\d,.]+", t[4])
                    and re.search(r"\d", t[4])
                    and re.search(r"\d$", p[4]) and abs(t[1] - p[1]) <= 1.0
                    and -1.5 <= t[0] - p[2] <= 2.5):
                out[-1] = (p[0], p[1], t[2], max(p[3], t[3]), p[4] + t[4])
                continue
        out.append(t)
    return out


def bands(page, tol=None):
    """Group words into visual rows keyed by representative y."""
    tol = _band if tol is None else tol
    out = defaultdict(list)
    for x0, y0, x1, y1, t in words(page):
        out[round(y0 / tol) * tol].append((x0, x1, y0, t))
    return {y: sorted(v) for y, v in sorted(out.items())}


def find_labels(page, label, max_x=None):
    """Every position where a label phrase occurs: [(y0, left_edge, right_edge), ...].

    Section headings repeat the wording of the field labels beneath them
    ("C. PROCESS WASTEWATER GENERATED" above "Process wastewater generated:"),
    so callers must be able to try each occurrence rather than just the first.
    """
    want = re.sub(r"\s+", " ", label).strip().lower().rstrip(":")
    hits = []
    for y0, row in bands(page).items():
        toks = [(x0, x1, yy, t) for x0, x1, yy, t in row
                if max_x is None or x0 < max_x]
        for i in range(len(toks)):
            acc = ""
            for j in range(i, min(i + 14, len(toks))):
                acc = (acc + " " + toks[j][3]).strip()
                norm = re.sub(r"\s+", " ", acc).lower().rstrip(":")
                if norm == want:
                    hits.append((toks[j][2], toks[i][0], toks[j][1]))
                    break
                if len(norm) > len(want) + 4:
                    break
    return hits


def find_label(page, label, max_x=None):
    """First position of a label phrase, or None."""
    h = find_labels(page, label, max_x)
    return h[0] if h else None


def value_right_of(page, label, band=None, skip=0):
    """First numeric token to the right of `label`, on the same visual row.

    This is what keeps 'After ammonia losses' from picking up the phosphorus
    figure that precedes it in reading order: that value lies left of the label.
    Each occurrence of the label is tried in turn, so a section heading with the
    same wording and no value beside it does not mask the real field.
    """
    band = _band if band is None else band
    for ly, _lleft, lright in find_labels(page, label):
        cands = sorted((x0, num(t)) for x0, y0, x1, y1, t in words(page)
                       if abs(y0 - ly) <= band and x0 > lright
                       and NUM.match(t) and num(t) is not None)
        if len(cands) > skip:
            return cands[skip][1]
    return None


def row_values(page, label, band=None, min_x=None):
    """All numerics on the label's visual row, left to right."""
    band = _band if band is None else band
    for ly, _lleft, lright in find_labels(page, label):
        lo = lright if min_x is None else min_x
        vals = sorted((x0, num(t)) for x0, y0, x1, y1, t in words(page)
                      if abs(y0 - ly) <= band and x0 > lo
                      and NUM.match(t) and num(t) is not None)
        if vals:
            return [v for _, v in vals]
    return []


def find_page(doc, *needles, limit=None):
    """First page whose text contains every needle."""
    for i, pg in enumerate(doc if limit is None else doc[:limit]):
        t = pg.get_text()
        if all(n.lower() in t.lower() for n in needles):
            return i, pg
    return None, None


def value_below(page, header, y_lo=None, y_hi=None, max_dy=80):
    """Numeric beneath a column header, matched by horizontal overlap.

    Provost & Pritchard tables emit their header cells and value cells in
    opposite orders, so pairing by reading order is wrong; the value is the
    numeric below the header whose x-range overlaps it most.
    """
    hits = find_labels(page, header)
    if not hits:
        return None
    best = None
    for hy, hleft, hright in hits:
        hw = (hleft, hright)
        for x0, y0, x1, y1, t in words(page):
            if y0 <= hy + 1 or y0 - hy > max_dy:
                continue
            if y_lo is not None and y0 < y_lo:
                continue
            if y_hi is not None and y0 > y_hi:
                continue
            v = num(t)
            if v is None or not NUM.match(t):
                continue
            ov = min(x1, hw[1]) - max(x0, hw[0])
            if ov > 0:
                cand = (y0 - hy, -ov, v)
                if best is None or cand[:2] < best[:2]:
                    best = cand
    return None if best is None else best[2]


def section_bounds(page, heading, next_headings=()):
    """(y_start, y_end) for a titled block, so lookups stay inside one table."""
    h = find_label(page, heading)
    if not h:
        return None, None
    y0 = h[0]
    y1 = None
    for nh in next_headings:
        n = find_label(page, nh)
        if n and n[0] > y0 and (y1 is None or n[0] < y1):
            y1 = n[0]
    return y0, y1


def header_block(page, x_min=100, x_max=None, y_max=100,
                 skip_words=("Period", "Jan")):
    """Left-labelled header values (name, street, city) in top-to-bottom order."""
    out = []
    for y, row in bands(page).items():
        if y > y_max:
            continue
        full = " ".join(t for _, _, _, t in row)
        if any(s in full for s in skip_words):
            continue
        val = " ".join(t for x0, x1, yy, t in row
                       if x0 >= x_min and (x_max is None or x1 <= x_max))
        if val.strip():
            out.append(val.strip())
    return out
