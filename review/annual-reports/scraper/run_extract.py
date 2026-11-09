"""Scrape every target PDF, writing per-row results and a triage report."""
import json, os, pickle, sys, time
import pipeline

# Working directory for the run: the review folder that contains this package.
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def unreadable(path):
    """True when the file cannot be read.

    OneDrive leaves the dataless flag set on files it still serves on demand,
    so the flag rejects reports that open fine; a short read decides it.
    """
    try:
        with open(path, "rb") as fh:
            return len(fh.read(65536)) == 0
    except OSError:
        return True


def main(limit=None, out="results.pkl"):
    # list_targets.txt holds report paths relative to the repository root.
    targets = [os.path.join(pipeline.REPO, l.strip())
               for l in open(f"{S}/list_targets.txt") if l.strip()]
    if limit:
        targets = targets[:limit]
    rows, t0 = [], time.time()
    for i, p in enumerate(targets, 1):
        rec = {"path": p, "Source PDF": os.path.basename(p)}
        if not os.path.exists(p):
            rec.update(status="missing")
        elif unreadable(p):
            rec.update(status="unreadable")
        else:
            try:
                row, meta = pipeline.scrape(p)
                rec.update(status="error" if meta.get("error") else "ok",
                           row=row, meta=meta)
            except Exception as e:
                rec.update(status="exception", error=f"{type(e).__name__}: {e}")
        rows.append(rec)
        if i % 20 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(targets)}  {el:.0f}s  ({el/i:.1f}s/file)", flush=True)
    with open(f"{S}/{out}", "wb") as f:
        pickle.dump(rows, f)
    print(f"wrote {S}/{out}  ({len(rows)} records, {time.time()-t0:.0f}s)")
    return rows


if __name__ == "__main__":
    main(limit=int(sys.argv[1]) if len(sys.argv) > 1 else None,
         out=sys.argv[2] if len(sys.argv) > 2 else "results.pkl")
