"""Apple Vision OCR presented as a pymupdf-compatible page.

Scanned packets have no text layer, but every extractor here works purely from
word tuples. Emitting OCR results in the same (x0, y0, x1, y1, text) shape and
in PDF point coordinates lets the same form parsers run unchanged.
"""
import Quartz
import Vision
from Foundation import NSData

DPI = 300


def _cgimage_from_png(png_bytes):
    src = Quartz.CGImageSourceCreateWithData(NSData.dataWithBytes_length_(
        png_bytes, len(png_bytes)), None)
    return Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)


def ocr_words(page, dpi=DPI, min_conf=0.30):
    """OCR one rendered page, returning word tuples in PDF points."""
    pm = page.get_pixmap(dpi=dpi)
    img = _cgimage_from_png(pm.tobytes("png"))
    if img is None:
        return []
    W, H = page.rect.width, page.rect.height

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(False)          # numbers, not prose
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        return []

    out = []
    for obs in (req.results() or []):
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        cand = cand[0]
        if cand.confidence() < min_conf:
            continue
        text = cand.string()
        pos = 0
        for tok in text.split():
            start = text.find(tok, pos)
            pos = start + len(tok)
            rng = Vision.NSMakeRange(start, len(tok))
            box, e = cand.boundingBoxForRange_error_(rng, None)
            bb = box.boundingBox() if box is not None else obs.boundingBox()
            x, y, w, h = bb.origin.x, bb.origin.y, bb.size.width, bb.size.height
            out.append((x * W, (1.0 - (y + h)) * H, (x + w) * W, (1.0 - y) * H, tok))
    out.sort(key=lambda t: (round(t[1], 1), t[0]))
    return out


class OcrPage:
    """Minimal stand-in for a pymupdf page, backed by OCR output."""

    def __init__(self, page, dpi=DPI):
        self._words = ocr_words(page, dpi=dpi)
        self.rect = page.rect
        self.number = page.number
        self._src = page

    def get_text(self, kind=None):
        if kind == "words":
            return [(x0, y0, x1, y1, t, 0, 0, 0) for x0, y0, x1, y1, t in self._words]
        rows, cur, last = [], [], None
        for x0, y0, x1, y1, t in self._words:
            if last is not None and abs(y0 - last) > 3:
                rows.append(" ".join(cur)); cur = []
            cur.append(t); last = y0
        if cur:
            rows.append(" ".join(cur))
        return "\n".join(rows)

    def get_pixmap(self, **kw):
        return self._src.get_pixmap(**kw)


class OcrDoc:
    """Lazily OCR'd document, indexable and iterable like pymupdf's Document."""

    def __init__(self, doc, dpi=DPI, max_pages=None):
        self._doc = doc
        self._cache = {}
        self._dpi = dpi
        self._n = len(doc) if max_pages is None else min(len(doc), max_pages)

    def __len__(self):
        return self._n

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(self._n))]
        if i < 0:
            i += self._n
        if i not in self._cache:
            self._cache[i] = OcrPage(self._doc[i], dpi=self._dpi)
        return self._cache[i]

    def __iter__(self):
        for i in range(self._n):
            yield self[i]
