"""Assemble scraped rows, grade them, render evidence, and emit the review page."""
import json, os, pickle, random, re, sys, urllib.parse
import pandas as pd
import apply_rows, crop_removal, crops, pipeline
from review_html import TEMPLATE

# Working directory for the run: the review folder that contains this package.
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = pipeline.REPO
TARGET = f"{REPO}/outputs/review/annual-reports/Dairy_Report_Summary_Region_5_2024_with_source_pdf_scraping.csv"
OUT = S

FIELDS = [("Dairy Name", False), ("Dairy Address", False)] + \
         [(c, True) for c in pipeline.HERD] + \
         [(c, True) for c in [
             "Total Herd Size", "Total Manure Excreted (tons)",
             "Total Dry Manure Generated N (lbs)",
             "Total Dry Manure Generated N After Ammonia Losses (lbs)",
             "Total Process Wastewater Generated (gals)",
             "Total Process Wastewater Generated N (lbs)",
             "Applied N Dry Manure (lbs)", "Applied Process Wastewater N (lbs)",
             "Total Exports N (lbs)", "Total Applied N (lbs)",
             "Unaccounted-for N (lbs)",
             "UCCE Nitrogen from Manure (lbs)", "Ratio of UCCE N to Reported N",
             "Applied to Remove Ratio N", "Total Crop-Removed N"]]
PASS_SAMPLE = 0.10
# The facility-wide applied-to-removed ratio, reviewed on its own filter. Only
# the standard and IAS forms print one.
RATIO_KEY = "Applied to Remove Ratio N"
RATIO_FORMS = ["Standard", "IAS"]
# The page tag whose crop carries the ratio, per form.
RATIO_TAG = {"Standard": "applied", "IAS": "attachment_b"}
# Facility-wide crop N removal, reviewed on its own filter for every summary
# report on the standard or IAS form, including those parsed before this study.
CROP_KEY = "Total Crop-Removed N"
CROP_CSV = crop_removal.OUT_CSV
# Offered in the report-type dropdown. The first entry means "not yet judged",
# so an untouched report is distinguishable from one confirmed as Standard.
FORM_TYPES = ["", "Standard", "IAS", "Livingston", "ProvostPritchard",
              "Standard + IAS", "Standard + Livingston",
              "Standard + ProvostPritchard", "No form markers", "Other"]


def pdf_url(path):
    """URL of a source report relative to the review page, with spaces and # escaped."""
    return urllib.parse.quote(os.path.relpath(pipeline.local_pdf(path), OUT))


def load_seed():
    """Prior decisions in the shape the review page keeps in localStorage.

    Numeric corrections are emitted as numbers so an unedited value compares
    equal to the scraped one and is dropped rather than stored as a diff. A
    report whose ratio was corrected counts as already examined.
    """
    numeric = {k for k, n in FIELDS if n}
    verdicts, ratio_ok, form_type, crop_ok = {}, {}, {}, {}
    for pdf, e in apply_rows.load_review().items():
        fields = {}
        for k, v in e["fields"].items():
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            if k in numeric:
                v = pd.to_numeric(v, errors="coerce")
                if pd.isna(v):
                    continue
                v = float(v)
            else:
                v = str(v)
            fields[k] = v
        verdicts[pdf] = {"verdict": e["verdict"], "fields": fields,
                         "note": " | ".join(e["notes"])}
        if e.get("ratio_ok") or RATIO_KEY in fields:
            ratio_ok[pdf] = True
        if e.get("form_type"):
            form_type[pdf] = e["form_type"]
        if e.get("crop_ok") or CROP_KEY in fields:
            crop_ok[pdf] = True
    return {"verdicts": verdicts, "ratioOK": ratio_ok, "formType": form_type,
            "cropOK": crop_ok}


def load_crop():
    """Source PDF -> extracted crop removal record, or {} before extraction has run."""
    if not os.path.exists(CROP_CSV):
        print(f"  {CROP_CSV} not found; the crop N filter will be empty")
        return {}
    ex = pd.read_csv(CROP_CSV)
    ex = ex[ex["Status"] != "no PDF"].drop_duplicates("Source PDF")
    return {r["Source PDF"]: r for _, r in ex.iterrows()}


def crop_info(c):
    """What the review page needs to show and check one crop removal value."""
    v = lambda k: None if pd.isna(c[k]) else float(c[k])
    page = None if pd.isna(c["Page"]) else int(c["Page"])
    return {"status": c["Status"], "rank": crop_removal.STATUS_ORDER.index(c["Status"]),
            "T": v("Total N Applied (all sources)"), "Q": v("Printed Ratio"),
            "S": v("Summary Ratio"), "page": page, "method": c["Method"],
            "reader": c["Reader"]}


def canon_street(a):
    a = str(a or "").lower()
    a = re.sub(r"\b(ave|avenue)\b", "av", a)
    a = re.sub(r"\b(rd|road)\b", "rd", a)
    a = re.sub(r"\b(st|street)\b", "st", a)
    a = re.sub(r"[^a-z0-9]+", " ", a)
    return " ".join(a.split())


def canon_name(n):
    n = str(n or "").lower()
    n = re.sub(r"\b(dairy|dairies|farms?|llc|inc|ranch(es)?|and|&|the|#\d+|no\s*\d+)\b", " ", n)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", n).split())


def street_key(addr):
    """Leading house number plus the next two words: enough to spot a repeat."""
    c = canon_street(addr)
    m = re.match(r"^(\d+)\s+(\S+)(?:\s+(\S+))?", c)
    return None if not m else " ".join(x for x in m.groups() if x)


def main(pkl="results.pkl", out=None):
    global OUT
    if out:
        OUT = out
    rows = pickle.load(open(f"{S}/{pkl}", "rb"))
    # Duplicate detection must compare against the state of the file before any
    # scraped rows were appended, otherwise every appended row matches itself.
    baseline = f"{OUT}/backup_before_append.csv"
    have = pd.read_csv(baseline if os.path.exists(baseline) else TARGET)
    ex_street = {street_key(a) for a in have["Dairy Address"].dropna()} - {None}
    ex_name = {canon_name(n) for n in have["Dairy Name"].dropna()} - {""}

    recs, triage = [], []
    for r in rows:
        pdf = r["Source PDF"]
        base = {"Source PDF": pdf, "status": r["status"]}
        if r["status"] != "ok":
            triage.append({**base, "form": "", "method": "", "grade": "",
                           "note": r.get("error", r["status"])})
            continue
        row, meta = r["row"], r["meta"]
        sk, nk = street_key(row.get("Dairy Address")), canon_name(row.get("Dairy Name"))
        # Only a street match blocks the append. Family surnames recur across
        # different dairies in this region, so a name match on its own is an
        # advisory note rather than evidence of a duplicate.
        dup = f"street {sk} already in the CSV" if (sk and sk in ex_street) else ""
        name_note = (f"same surname as an existing row ({nk}); different address"
                     if (not dup and nk and nk in ex_name) else "")
        grade = meta["grade"]
        if name_note:
            meta["notes"] = list(meta["notes"]) + [name_note]
        recs.append({"pdf": pdf, "path": pipeline.local_pdf(r["path"]), "row": row, "meta": meta,
                     "grade": grade, "dup": dup, "name_note": name_note})
        triage.append({**base, "form": meta["form"], "method": meta["method"],
                       "grade": grade, "n_pages": meta.get("n_pages"),
                       "duplicate_risk": dup, "name_note": name_note,
                       "fails": "; ".join(meta["fails"]),
                       "warns": "; ".join(meta["warns"]),
                       "note": " | ".join(meta["notes"])})

    # Queue order: hard failures first, then warnings, then OCR-read rows, then a
    # sample of clean rows for spot checking, then the rest.
    rnd = random.Random(0)
    def rank(rec):
        if rec["grade"] == "FAIL":
            return 0
        if rec["grade"] == "WARN":
            return 1
        if rec["meta"]["method"] == "ocr":
            return 2
        return 3 if rnd.random() < PASS_SAMPLE else 4
    recs.sort(key=lambda r: (rank(r), r["pdf"]))

    crop = load_crop()
    for rec in recs:
        c = crop.get(rec["pdf"])
        if c is not None and pd.notna(c[CROP_KEY]):
            rec["row"][CROP_KEY] = float(c[CROP_KEY])

    os.makedirs(f"{OUT}/crops", exist_ok=True)
    payload = []
    for i, rec in enumerate(recs, 1):
        made = crops.render(rec["path"], rec["meta"].get("pages"),
                            f"{OUT}/crops", method=rec["meta"]["method"])
        c = crop.get(rec["pdf"])
        if c is not None and isinstance(c["Crop File"], str) \
                and c["Crop File"] not in [f for _t, _p, f in made]:
            made.append(("crop_removal", int(c["Page"]), c["Crop File"]))
        payload.append({
            "pdf": rec["pdf"], "grade": rec["grade"], "form": rec["meta"]["form"],
            "method": rec["meta"]["method"], "npages": rec["meta"].get("n_pages"),
            "dup": rec["dup"], "notes": rec["meta"]["notes"],
            "crops": [[t, p, f] for t, p, f in made],
            "f": {k: rec["row"].get(k) for k, _ in FIELDS},
            "url": pdf_url(rec["path"]),
            "ratiopage": rec["meta"].get("pages", {}).get(
                RATIO_TAG.get(rec["meta"]["form"])),
            "crop": None if c is None else crop_info(c),
        })
        if i % 50 == 0:
            print(f"  crops {i}/{len(recs)}", flush=True)

    # Reports parsed before this study have no scraped row, so they join the
    # page carrying only the crop removal value and its page image.
    summ = pd.read_csv(TARGET, low_memory=False).drop_duplicates("Source PDF")
    summ = summ.set_index("Source PDF")
    have_pdf = {p["pdf"] for p in payload}
    extra = []
    for pdf, c in crop.items():
        if pdf in have_pdf:
            continue
        s_row = summ.loc[pdf] if pdf in summ.index else None
        txt = lambda k: None if s_row is None or pd.isna(s_row[k]) else str(s_row[k])
        ratio = None if s_row is None else pd.to_numeric(s_row[RATIO_KEY], errors="coerce")
        info = crop_info(c)
        extra.append({
            "pdf": pdf, "grade": "CROP", "form": c["Reader"] if isinstance(c["Reader"], str)
            and c["Reader"] else "Standard",
            "method": c["Method"] if isinstance(c["Method"], str) else "text",
            "npages": None if pd.isna(c["Pages"]) else int(c["Pages"]), "dup": "",
            "notes": ["Parsed before this study (Robertson et al.); only the "
                      "facility-wide crop N removal is reviewed here"]
                     + ([c["Notes"]] if isinstance(c["Notes"], str) and c["Notes"] else []),
            "crops": ([["crop_removal", info["page"], c["Crop File"]]]
                      if info["page"] and isinstance(c["Crop File"], str) else []),
            "f": {"Dairy Name": txt("Dairy Name"), "Dairy Address": txt("Dairy Address"),
                  RATIO_KEY: None if ratio is None or pd.isna(ratio) else float(ratio),
                  CROP_KEY: None if pd.isna(c[CROP_KEY]) else float(c[CROP_KEY])},
            "url": pdf_url(c["Source Path"]), "ratiopage": info["page"],
            "cropOnly": True, "crop": info,
        })
    extra.sort(key=lambda r: (r["crop"]["rank"], str(r["f"]["Dairy Name"] or r["pdf"])))
    payload += extra

    seed = load_seed()
    html = (TEMPLATE
            .replace("__ROWS__", json.dumps(payload))
            .replace("__FIELDS__", json.dumps([{"k": k, "num": n} for k, n in FIELDS]))
            .replace("__HERD__", json.dumps(pipeline.HERD))
            .replace("__SEED__", json.dumps(seed))
            .replace("__RATIO_KEY__", json.dumps(RATIO_KEY))
            .replace("__RATIO_FORMS__", json.dumps(RATIO_FORMS))
            .replace("__FORM_TYPES__", json.dumps(FORM_TYPES))
            .replace("__CROP_KEY__", json.dumps(CROP_KEY)))
    print(f"  seeded {len(seed['verdicts'])} prior decisions into the page "
          f"({len(seed['ratioOK'])} with the ratio already examined, "
          f"{len(seed['cropOK'])} with crop N removal already examined)")
    n_crop = sum(1 for p in payload if p.get("crop"))
    print(f"  crop N removal: {n_crop} reports in the Crop N filter "
          f"({len(extra)} of them parsed before this study, added as crop-only rows)")
    with open(f"{OUT}/Dairy_Report_Scrape_Review.html", "w") as f:
        f.write(html)

    pd.DataFrame(triage).to_csv(f"{OUT}/triage_report.csv", index=False)
    flat = []
    for rec in recs:
        d = {"Source PDF": rec["pdf"], "_grade": rec["grade"],
             "_form": rec["meta"]["form"], "_method": rec["meta"]["method"],
             "_duplicate_risk": rec["dup"],
             "_name_note": rec.get("name_note", ""),
             "_basis": rec["meta"].get("basis_override", ""),
             "_notes": " | ".join(rec["meta"]["notes"])}
        d.update({k: rec["row"].get(k) for k, _ in FIELDS})
        flat.append(d)
    pd.DataFrame(flat).to_csv(f"{OUT}/scraped_rows.csv", index=False)

    print(f"\n{len(recs)} rows staged for review")
    print(f"  grades: " + ", ".join(
        f"{g}={sum(1 for r in recs if r['grade']==g)}" for g in ("FAIL", "WARN", "PASS")))
    print(f"  duplicate risk flagged: {sum(1 for r in recs if r['dup'])}")
    print(f"  wrote {OUT}/Dairy_Report_Scrape_Review.html")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results.pkl",
         sys.argv[2] if len(sys.argv) > 2 else None)
