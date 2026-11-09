"""Measure how much of the manifest export tonnage the report CSV covers.

The point of adding rows is to shrink a non-random coverage gap: dairies that
appear in the manifests but not in the annual-report summary account for a
disproportionate share of exported manure.
"""
import os, sys
import pandas as pd
from build_review import canon_name, street_key

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MANIFESTS = f"{REPO}/outputs/review/manifests/processed_manure_manifests.csv"


def coverage(report_csv, label):
    rep = pd.read_csv(report_csv)
    man = pd.read_csv(MANIFESTS)
    r_street = {street_key(a) for a in rep["Dairy Address"].dropna()} - {None}
    r_name = {canon_name(n) for n in rep["Dairy Name"].dropna()} - {""}

    man["_tons"] = pd.to_numeric(man["Total Manure Amount (tons)"], errors="coerce").fillna(0)
    man["_sk"] = man["Origin Dairy Address"].map(street_key)
    man["_nk"] = man["Origin Dairy Name"].map(canon_name)
    man["_matched"] = man["_sk"].isin(r_street) | man["_nk"].isin(r_name)

    dairies = man.groupby(["_nk", "_sk"], dropna=False).agg(
        tons=("_tons", "sum"), matched=("_matched", "max")).reset_index()
    tot = dairies["tons"].sum()
    unm = dairies.loc[~dairies["matched"], "tons"].sum()
    n_unm = int((~dairies["matched"]).sum())
    print(f"\n{label}")
    print(f"  report rows                         {len(rep):,}")
    print(f"  manifest origin dairies             {len(dairies):,}")
    print(f"  ...not found in the report CSV      {n_unm:,} "
          f"({n_unm/max(1,len(dairies)):.0%})")
    print(f"  manifest tonnage                    {tot:,.0f} wet tons")
    print(f"  ...from unmatched dairies           {unm:,.0f} ({unm/max(1,tot):.1%})")
    return {"rows": len(rep), "dairies": len(dairies), "unmatched": n_unm,
            "tons": tot, "unmatched_tons": unm}


if __name__ == "__main__":
    before = coverage(sys.argv[1], "BEFORE (existing summary)")
    if len(sys.argv) > 2:
        after = coverage(sys.argv[2], "AFTER (with scraped rows)")
        d = before["unmatched_tons"] - after["unmatched_tons"]
        print(f"\n  export tonnage brought into coverage: {d:,.0f} wet tons "
              f"({d/max(1,before['tons']):.1%} of all manifest tonnage)")
        print(f"  unmatched share: {before['unmatched_tons']/before['tons']:.1%} "
              f"-> {after['unmatched_tons']/after['tons']:.1%}")
