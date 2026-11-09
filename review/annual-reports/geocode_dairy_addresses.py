"""Geocode the Dairy Address column of the annual report summary.

Writes Geospatial_Data/Dairy_Report_Geocodes.csv, which the visualization
notebook reads as a cache so that no figure build touches the network. Run this
once, or again when the report file's addresses change.

Coordinates produced here are used only for the Figure 1 locator map. The
routing, network and exposure analyses keep the geocodes already stored in the
manifest files.

Geocoders, in the order tried:
  1. US Census Bureau, Public_AR_Current benchmark, batch endpoint
       https://geocoding.geo.census.gov/geocoder/locations/addressbatch
  2. the same service's single-address endpoint, which parses free-form input
       https://geocoding.geo.census.gov/geocoder/locations/onelineaddress
  3. Nominatim (OpenStreetMap), for rural addresses absent from TIGER address
     ranges, rate-limited to one request per second as its policy requires
       https://nominatim.openstreetmap.org/search

Run with --nominatim-only to fill gaps in an existing cache without repeating
the Census pass.
"""
import csv
import io
import os
import re
import sys
import time

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + os.sep
REPORT_FILE = (ROOT + "outputs/review/annual-reports/"
               "Dairy_Report_Summary_Region_5_2024_with_source_pdf_scraping.csv")
PLACE_SHP = (ROOT + "data/geospatial-data/CA_Census_Place/"
             "cb_2024_06_place_500k.shp")
MANIFEST_FILE = ROOT + "outputs/results/routing/processed_manure_manifests_analysis.geojson"
BG_SHP_GLOB = ROOT + "data/geospatial-data/CA_BGs/nhgis0015_shape*/*.shp"
OUT_FILE = ROOT + "outputs/review/annual-reports/Dairy_Report_Geocodes.csv"

BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
ONELINE_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim requires a User-Agent identifying the application.
NOMINATIM_UA = "manure-trucking-research/1.0 (dairy manure transport study)"
NOMINATIM_DELAY_S = 1.1
BENCHMARK = "Public_AR_Current"
BATCH_LIMIT = 10000

# All 58 California counties. The address strings place the county after the
# city, so a trailing county name is stripped before the city is identified.
CA_COUNTY_NAMES = [
    "Alameda", "Alpine", "Amador", "Butte", "Calaveras", "Colusa",
    "Contra Costa", "Del Norte", "El Dorado", "Fresno", "Glenn", "Humboldt",
    "Imperial", "Inyo", "Kern", "Kings", "Lake", "Lassen", "Los Angeles",
    "Madera", "Marin", "Mariposa", "Mendocino", "Merced", "Modoc", "Mono",
    "Monterey", "Napa", "Nevada", "Orange", "Placer", "Plumas", "Riverside",
    "Sacramento", "San Benito", "San Bernardino", "San Diego",
    "San Francisco", "San Joaquin", "San Luis Obispo", "San Mateo",
    "Santa Barbara", "Santa Clara", "Santa Cruz", "Shasta", "Sierra",
    "Siskiyou", "Solano", "Sonoma", "Stanislaus", "Sutter", "Tehama",
    "Trinity", "Tulare", "Tuolumne", "Ventura", "Yolo", "Yuba",
]
# California county FIPS codes are the odd numbers 001 to 115 assigned in
# alphabetical order, which is how they appear in the block-group shapefile.
COUNTY_FIPS = {f"{2 * i + 1:03d}": n for i, n in enumerate(CA_COUNTY_NAMES)}
CA_COUNTIES = {n.lower() for n in CA_COUNTY_NAMES}
# Written without the county word, so both "San Joaquin" and "Joaquin" strip.
COUNTY_TAILS = CA_COUNTIES | {c.split()[-1] for c in CA_COUNTIES if " " in c}

_ZIP = re.compile(r"\b(9\d{4})(?:-\d{4})?\b")
# Street-type words, so the positional fallback below cannot mistake the tail of
# a street name for the city: "20334 S Polk Ave Fresno" must not yield "Ave".
_STREET_WORD = re.compile(
    r"^(?:av|ave|avenue|rd|road|st|street|hwy|highway|blvd|boulevard|ln|lane"
    r"|dr|drive|way|ct|court|pl|place|cir|circle|trl|trail|pkwy|parkway|bvd)$",
    re.I)
_PUNCT = re.compile(r"[^\w/\s]")


def check_nominatim(out):
    """Reject Nominatim hits that landed on a same-named road elsewhere.

    Nominatim matches a road name without holding it to the rest of the
    address, so "8001 Road 104 Tulare" resolves to Road 104 in Yolo County,
    300 km north, and that error survives a test against the regional boundary
    because the Water Board covers both. Where a city was parsed, requiring it
    in the returned display name catches this; where none was, the county named
    in the address is the only handle left.

    Applied to Nominatim rows only. Census matches are held to a TIGER address
    range and a ZIP, and where they disagree with the county field it is the
    report that is wrong: Laton is in Fresno and Hilmar in Merced, whatever the
    filing says, so testing those would discard sound coordinates.
    """
    import glob

    import geopandas as gpd
    rows = out.index[(out["provider"] == "nominatim") & out["lat"].notna()]
    if not len(rows):
        return out

    city = out.loc[rows, "city_parsed"].astype(str).str.lower().str.strip()
    shown = out.loc[rows, "matched_address"].astype(str).str.lower()
    has_city = city.ne("") & city.ne("nan")
    # Whole-word, since "ave" is a substring of "avenue" and would let a match
    # in the wrong city pass.
    bad = has_city & pd.Series(
        [re.search(rf"\b{re.escape(c)}\b", d) is None
         for c, d in zip(city, shown)], index=rows)

    no_city = rows[~has_city]
    shp = glob.glob(BG_SHP_GLOB)
    if len(no_city) and shp:
        stated = (out.loc[no_city, "county_parsed"].astype(str)
                  .str.lower().str.strip())
        # A bare "Joaquin" or "Dorado" is how the two-word counties appear.
        stated = stated.replace({n.split()[-1].lower(): n.lower()
                                 for n in CA_COUNTY_NAMES if " " in n})
        cty = (gpd.read_file(shp[0])[["COUNTYFP", "geometry"]]
               .dissolve("COUNTYFP").to_crs("EPSG:4326").reset_index())
        pts = gpd.GeoDataFrame(
            {"i": no_city},
            geometry=gpd.points_from_xy(out.loc[no_city, "lon"],
                                        out.loc[no_city, "lat"]),
            crs="EPSG:4326")
        landed = (gpd.sjoin(pts, cty, how="left", predicate="within")
                  .set_index("i")["COUNTYFP"].map(COUNTY_FIPS).str.lower())
        mism = landed.reindex(no_city).notna() & stated.isin(CA_COUNTIES) & (
            landed.reindex(no_city) != stated)
        bad = bad.reindex(rows, fill_value=False)
        bad.loc[no_city] = bad.loc[no_city] | mism.to_numpy()

    print(f"  Nominatim check: {len(rows)} hits, {int(bad.sum())} rejected "
          "for landing outside the city or county the address names")
    if bad.any():
        print(out.loc[bad[bad].index, ["Dairy Address", "matched_address"]]
              .to_string(index=False))
        out.loc[bad[bad].index, ["lat", "lon"]] = np.nan
        out.loc[bad[bad].index, ["provider", "match_precision"]] = ""
    return out


def load_city_names():
    """Place names from the 2024 Census cartographic boundary file.

    Used as a gazetteer to split the city off the end of the address, since
    multi-word names such as Los Banos and Elk Grove cannot be found by
    splitting on whitespace.
    """
    import geopandas as gpd
    names = gpd.read_file(PLACE_SHP)["NAME"].dropna().astype(str)
    return {n.lower() for n in names}


def parse_address(raw, cities):
    """Split 'street city county ZIP' into Census batch fields.

    The column is inconsistent: some rows carry a ZIP+4, some an explicit CA,
    some no county, and some no ZIP at all. ZIP is taken wherever it appears,
    the county is stripped from the tail, and the city is the longest remaining
    suffix that matches a California place name.
    """
    s = str(raw).strip()
    zipc = ""
    m = _ZIP.search(s)
    if m:
        zipc = m.group(1)
        s = s[:m.start()] + " " + s[m.end():]
    s = _PUNCT.sub(" ", s)
    toks = [t for t in s.split() if t.lower() != "ca"]

    county = ""
    while len(toks) > 1 and " ".join(toks[-2:]).lower() in COUNTY_TAILS:
        county = county or " ".join(toks[-2:])
        toks = toks[:-2]
    if len(toks) > 1 and toks[-1].lower() in COUNTY_TAILS:
        county = county or toks[-1]
        toks = toks[:-1]

    city = ""
    for take in (3, 2, 1):
        if len(toks) > take and " ".join(toks[-take:]).lower() in cities:
            city = " ".join(toks[-take:])
            toks = toks[:-take]
            break
    # Small unincorporated communities (Helm, Hilmar, Burrel) are absent from the
    # place file, and misspellings such as "Crowslanding" never match it. The
    # county having been stripped, the city sits in the last position by
    # construction, so take it there rather than leave it glued to the street.
    if (not city and len(toks) > 2 and not toks[-1][:1].isdigit()
            and not _STREET_WORD.match(toks[-1])):
        city = toks[-1]
        toks = toks[:-1]
    return " ".join(toks), city, "CA", zipc, county


def post_batch(rows):
    """One batch request. rows is a list of (id, street, city, state, zip)."""
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    resp = requests.post(
        BATCH_URL,
        files={"addressFile": ("addresses.csv", buf.getvalue(), "text/csv")},
        data={"benchmark": BENCHMARK, "returntype": "locations"},
        timeout=1800)
    resp.raise_for_status()
    # Response columns: id, input, match status, match type, matched address,
    # "lon,lat", TIGER line id, side. Match type is Exact or Non_Exact, the
    # latter meaning the house number was interpolated along the block.
    out = {}
    for rec in csv.reader(io.StringIO(resp.text)):
        if len(rec) < 3:
            continue
        rid, status = rec[0], rec[2]
        if status == "Match" and len(rec) >= 6:
            lon, lat = rec[5].split(",")
            out[rid] = (float(lat), float(lon), rec[4], rec[3])
        else:
            out[rid] = None
    return out


def get_oneline(address):
    """Single-address fallback, which parses free-form input server-side."""
    resp = requests.get(ONELINE_URL, params={
        "address": address, "benchmark": BENCHMARK, "format": "json"},
        timeout=60)
    resp.raise_for_status()
    matches = resp.json().get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    c = matches[0]["coordinates"]
    return (float(c["y"]), float(c["x"]),
            matches[0].get("matchedAddress", ""), "oneline")


def get_nominatim(street, city, zipc, raw):
    """OpenStreetMap fallback for addresses TIGER cannot resolve.

    Queried from the parsed fields rather than the raw string, because the raw
    string carries the county after the city and Nominatim reads that as part of
    the place name. Results are confined to the United States and to the first
    candidate, which Nominatim ranks by importance.
    """
    q = ", ".join(x for x in (street, city, f"CA {zipc}".strip(), "USA") if x)
    resp = requests.get(NOMINATIM_URL, params={
        "q": q or str(raw), "format": "jsonv2", "countrycodes": "us",
        "limit": 1, "addressdetails": 0},
        headers={"User-Agent": NOMINATIM_UA}, timeout=60)
    resp.raise_for_status()
    hits = resp.json()
    if not hits:
        return None
    # addresstype separates a house-number hit from a road-centreline hit, which
    # on a rural avenue can sit kilometres from the dairy.
    return (float(hits[0]["lat"]), float(hits[0]["lon"]),
            hits[0].get("display_name", ""),
            "osm_" + str(hits[0].get("addresstype", "")))


def _s(v):
    """CSV round-trips leave blanks as NaN and ZIPs as floats."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, float):
        return f"{int(v):05d}"
    return str(v).strip()


def fill_nominatim(out):
    """Fill rows still missing coordinates, one request per second."""
    todo = out.index[out["lat"].isna()].tolist()
    if not todo:
        return out
    print(f"  querying Nominatim for {len(todo):,} unmatched, "
          f"{NOMINATIM_DELAY_S:.1f}s apart "
          f"({len(todo) * NOMINATIM_DELAY_S / 60:.1f} min) ...")
    got = 0
    for n, i in enumerate(todo, 1):
        r = None
        try:
            r = get_nominatim(_s(out.at[i, "street_parsed"]),
                              _s(out.at[i, "city_parsed"]),
                              _s(out.at[i, "zip_parsed"]),
                              out.at[i, "Dairy Address"])
        except Exception as exc:
            print(f"    row {i}: {type(exc).__name__}")
        if r:
            out.loc[i, ["lat", "lon"]] = [r[0], r[1]]
            out.at[i, "matched_address"] = r[2]
            out.at[i, "match_precision"] = r[3]
            out.at[i, "provider"] = "nominatim"
            got += 1
        if n % 20 == 0:
            print(f"    {n}/{len(todo)}  matched {got}")
        time.sleep(NOMINATIM_DELAY_S)
    print(f"  Nominatim matched {got:,} of {len(todo):,}")
    return out


def offset_check(df):
    """Median and 90th-percentile distance to the existing manifest geocodes.

    The report and manifest address strings share a format, so the dairies
    appearing in both give an independent read on whether this parse is sound.
    """
    import geopandas as gpd
    man = gpd.read_file(MANIFEST_FILE)
    key = (man["Origin Dairy Address"].astype(str).str.lower().str.strip())
    ref = (pd.DataFrame({
        "k": key,
        "lat": pd.to_numeric(man["Origin Dairy Latitude (Geocoded)"], errors="coerce"),
        "lon": pd.to_numeric(man["Origin Dairy Longitude (Geocoded)"], errors="coerce")})
        .dropna().drop_duplicates("k").set_index("k"))
    j = df.assign(k=df["Dairy Address"].astype(str).str.lower().str.strip()).join(
        ref, on="k", rsuffix="_ref").dropna(subset=["lat", "lon", "lat_ref"])
    if j.empty:
        return 0, np.nan, np.nan
    dy = (j["lat"] - j["lat_ref"]) * 111_320.0
    dx = ((j["lon"] - j["lon_ref"]) * 111_320.0
          * np.cos(np.radians(j["lat"].to_numpy())))
    d = np.hypot(dx, dy)
    return len(j), float(np.median(d)), float(np.percentile(d, 90))


def clean_and_report(out, label):
    """Guard against out-of-state coordinates, then report coverage."""
    n_ok = int(out["lat"].notna().sum())
    counts = out["provider"].value_counts().to_dict()
    print(f"\n{label}: {n_ok:,} of {len(out):,} "
          f"({100 * n_ok / len(out):.1f}%)   "
          + "  ".join(f"{k} {v:,}" for k, v in counts.items() if k))
    # California's bounding box, as a coarse guard against a mis-parse or a
    # Nominatim hit landing in another state.
    inbox = (out["lat"].between(32.4, 42.1) & out["lon"].between(-124.5, -114.1))
    bad = out["lat"].notna() & ~inbox
    if bad.any():
        print(f"  {int(bad.sum())} outside California, dropped:")
        print(out.loc[bad, ["Dairy Address", "lat", "lon", "provider",
                            "matched_address"]].to_string(index=False))
        out.loc[bad, ["lat", "lon"]] = np.nan
        out.loc[bad, "provider"] = ""
    out = check_nominatim(out)
    _p = out.loc[out["lat"].notna(), "match_precision"].value_counts()
    print("  match precision: "
          + ",  ".join(f"{k} {v:,}" for k, v in _p.items() if k))
    n_ov, med, p90 = offset_check(out)
    print(f"  offset against the manifest geocodes on {n_ov} shared addresses: "
          f"median {med:,.0f} m, 90th percentile {p90:,.0f} m")
    return out


def main():
    if "--nominatim-only" in sys.argv:
        out = pd.read_csv(OUT_FILE, low_memory=False)
        for _c in ("provider", "matched_address", "match_precision"):
            out[_c] = out.get(_c, pd.Series("", index=out.index)).fillna("")
        print(f"loaded cache: {out['lat'].notna().sum():,} of {len(out):,} "
              "already geocoded")
        out = fill_nominatim(out)
        out = clean_and_report(out, "geocoded")
        out.to_csv(OUT_FILE, index=False)
        print(f"wrote {OUT_FILE}")
        return 0

    rep = pd.read_csv(REPORT_FILE, low_memory=False)
    cities = load_city_names()
    print(f"report rows: {len(rep):,}   place-name gazetteer: {len(cities):,}")

    parsed = [parse_address(a, cities) for a in rep["Dairy Address"]]
    print(f"parsed: {sum(1 for p in parsed if p[1]):,} with a city, "
          f"{sum(1 for p in parsed if p[3]):,} with a ZIP, "
          f"{sum(1 for p in parsed if p[4]):,} naming a county, "
          f"{sum(1 for p in parsed if not p[1] and not p[3]):,} with neither "
          "city nor ZIP")

    rows = [(str(i), p[0], p[1], p[2], p[3]) for i, p in enumerate(parsed)]
    assert len(rows) <= BATCH_LIMIT, "batch limit exceeded; split the upload"
    print(f"posting {len(rows):,} addresses to the Census batch geocoder ...")
    t0 = time.time()
    res = post_batch(rows)
    print(f"  batch returned in {time.time() - t0:.0f}s: "
          f"{sum(1 for v in res.values() if v):,} matched")

    prov = ["census_batch" if res.get(str(i)) else "" for i in range(len(rep))]
    unmatched = [i for i in range(len(rep)) if not res.get(str(i))]
    if unmatched:
        print(f"  retrying {len(unmatched):,} unmatched via one-line ...")
        for n, i in enumerate(unmatched, 1):
            try:
                r = get_oneline(str(rep["Dairy Address"].iloc[i]))
            except Exception as exc:
                print(f"    row {i}: {type(exc).__name__}")
                r = None
            if r:
                res[str(i)] = r
                prov[i] = "census_oneline"
            if n % 25 == 0:
                print(f"    {n}/{len(unmatched)}")
            time.sleep(0.1)

    out = pd.DataFrame({
        "Source PDF": rep["Source PDF"],
        "Dairy Name": rep["Dairy Name"],
        "Dairy Address": rep["Dairy Address"],
        "street_parsed": [p[0] for p in parsed],
        "city_parsed": [p[1] for p in parsed],
        "zip_parsed": [p[3] for p in parsed],   # kept as text, not a number
        "county_parsed": [p[4] for p in parsed],
        "lat": [res.get(str(i))[0] if res.get(str(i)) else np.nan
                for i in range(len(rep))],
        "lon": [res.get(str(i))[1] if res.get(str(i)) else np.nan
                for i in range(len(rep))],
        "matched_address": [res.get(str(i))[2] if res.get(str(i)) else ""
                            for i in range(len(rep))],
        "match_precision": [res.get(str(i))[3] if res.get(str(i)) else ""
                            for i in range(len(rep))],
        "provider": prov,
    })
    out = clean_and_report(out, "geocoded by Census")
    out = fill_nominatim(out)
    out = clean_and_report(out, "geocoded")

    out.to_csv(OUT_FILE, index=False)
    print(f"wrote {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
