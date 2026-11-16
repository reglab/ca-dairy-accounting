# Waste Data: Operational Dairy Records for Pollution Accounting

Code and data for Bick, Wettermark, Hervey, Eneva and Ho, *Waste Data: Operational Dairy Records for Pollution Accounting*. The analysis uses 2024 dairy annual reports and manure and wastewater transport manifests filed with California's Central Valley Regional Water Quality Control Board (Region 5). It builds a nitrogen balance for each dairy, models the manure trucking network and who lives near it, and compares the reported manure management with the California Air Resources Board's greenhouse gas inventory.

## Quick start

All figures and tables can be reproduced by running one notebook, `analysis/Analysis.ipynb`:

conda env create -f environment/environment.yml
conda activate ca-dairy-accounting
conda install -n ca-dairy-accounting jupyterlab   # or open the notebook in VS Code with this environment's kernel
cd analysis
jupyter lab Analysis.ipynb                        # then Restart & Run All, runs in ~one minute


It writes every generated figure in `outputs/results/figures/` (PNG and EPS), every table in `outputs/results/tables/` (including the SI tables in LaTeX, `SI_Tables.md`), and the manuscript's numbers as LaTeX macros (`outputs/results/Manuscript_Parameters.tex`), from the review outputs in `outputs/review/` and the routing files in `outputs/results/routing/`. To regenerate those inputs as well, from the annual-report and manifest PDFs through the routing, follow the detailed directions in [Reproducing the results, step by step](#reproducing-the-results-step-by-step).

Extracted data from 2024 annual reports (dairy names, source PDFs, herd size, and nitrogen generation, application and exports are available in `outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv`. 

Extracted data from 2024 manure and wastewater transport manifests (origin dairy, destination, quantity) are available in `outputs/review/annual-reports/processed_manure_manifests.csv` and `outputs/review/annual-reports/processed_wastewater_manifests.csv`, respectively.

## Contents

- [Quick start]
- [Pipeline overview]
- [Repository layout]
- [Setup]
- [Reproducing the results, step by step]
- [Outputs and the manuscript]
- [File and field reference]
- [Data sources and attribution]
- [License]

## Pipeline overview

```
data/annual-reports/ (858 PDFs) ──► review/annual-reports/  (scrape + manual review) ──► outputs/review/annual-reports/
data/manifests/R5/  (OCR text)  ──► review/manifests/extraction/ (extract + manual validation)
                                        └─► outputs/review/manifests/processed_*_manifests.csv
outputs/review/manifests/processed_manure_manifests.csv + data/routing-data/ ──► analysis/Routing.ipynb ──► outputs/results/routing/
outputs/results/routing/ + outputs/review/manifests/geocode_review.csv ──► review/manifests/geocode-review/ (applies the verdicts in place)
outputs/review/* + outputs/results/routing/ + data/ ──► analysis/Analysis.ipynb ──► outputs/results/figures/, outputs/results/tables/
```

The two review stages (annual reports and manifests) mix code with human review. Their results ship as files in `outputs/review/`, and the analysis reads those files. They are documented here so the steps can be followed, not because they must be rerun. Some steps called live services (OCR and geocoding APIs) or ran on a compute cluster; they are marked **frozen** below.

## Repository layout

```
ca-dairy-accounting/
├── analysis/
│   ├── Analysis.ipynb          Final analysis: Figures 2–5, S1, S4–S10, Tables S5–S11, the SI tables in LaTeX
│   │                           and the manuscript parameters (Manuscript_Parameters.tex)
│   └── Routing.ipynb           Routes each manure manifest over the OpenStreetMap road network
├── review/
│   ├── annual-reports/         Annual-report extraction and review (scraper/, reviewer HTML + crops/, orchestrator notebook,
│   │                           build_report_formats.py, geocode_dairy_addresses.py, and the scraper's working files)
│   └── manifests/
│       ├── extraction/         Manifest OCR, field extraction and validation (manifest_preparation.ipynb)
│       ├── helpers/            Configuration tables and the dairy-summary copy read by the extraction notebook
│       └── geocode-review/     Geocode and route review tool (Manure_Manifest_Review.ipynb, geocode_review.html)
├── data/
│   ├── annual-reports/         2024 Region 5 dairy annual reports, <office>/{Correct_Forms,Consulting_and_Error_Causing_Forms}/  [Hugging Face]
│   ├── manifests/R5/           Manifest pages and OCR text by region and form template                                           [Hugging Face]
│   ├── geospatial-data/        Water Board boundary, California state and counties, block groups and Census places
│   ├── routing-data/           Processed OpenStreetMap road network (study_area_network_processed_v13.pkl)                       [Hugging Face]
│   └── tabular-data/           Original report summary, EMFAC emission rates, ZIP-to-county table
├── outputs/
│   ├── review/annual-reports/  Products of the annual-report review (the report table the analysis reads)
│   ├── review/manifests/       Products of the manifest extraction and review (the manifest tables the analysis reads)
│   └── results/
│       ├── figures/            Manuscript figures (PNG and EPS for each generated figure)
│       ├── tables/             Manuscript tables and tables whose values the text quotes
│       └── routing/            Routing outputs, with the review verdicts applied (pair_cache/ holds two exposure caches)
├── environment/
│   ├── environment.yml         Analysis environment (also the geocode review and the annual-report scraper)
│   ├── environment-routing.yml Routing environment
│   ├── environment-manifest-extraction.yml  Manifest extraction environment (manifest_preparation.ipynb)
│   └── environment-lock-osx-arm64.txt  Exact conda package list of the analysis environment
├── LICENSE.txt
└── README.md
```

## Setup

### Data download

The repository holds everything `analysis/Analysis.ipynb` needs, and the page images for the annual-report reviewer (`review/annual-reports/crops/`). The annual-report PDFs, the manifest files and the processed road network are in the Hugging Face dataset [reglab/ca-dairy-accounting](https://huggingface.co/datasets/reglab/ca-dairy-accounting). Download them only to rerun the review or routing stages:

| File on Hugging Face | Goes to | Download size | Needed by |
|---|---|---|---|
| `annual-reports.zip` | `data/annual-reports/`: the 858 annual-report PDFs (3.8 GB unzipped) | 3.4 GB | annual-report scraper |
| `manifests.zip` | `data/manifests/R5/` (4.7 GB unzipped): the same 858 reports filed by form template (`*/*/original/`); the manifests split out of them (`*/all_manifests/`, `manifest_<i>.pdf` and `manifest_<i>.txt`); and the OCR text of the manifest pages (`*/*/{fitz,tesseract,llmwhisperer}_output/`, 1,767 files) | 4.2 GB | manifest extraction. It reads the OCR text as a cache; the LLMWhisperer text can only be regenerated with an LLMWhisperer API key. |
| `study_area_network_processed_v13.pkl` | `data/routing-data/` | 1.6 GB | `analysis/Routing.ipynb` |

From the repository root, download the files and put them in place. The download needs the Hugging Face command-line tool (`pip install -U huggingface_hub`):

```bash
huggingface-cli download reglab/ca-dairy-accounting annual-reports.zip manifests.zip study_area_network_processed_v13.pkl --repo-type dataset --local-dir data
unzip -q data/annual-reports.zip -d data -x "__MACOSX/*" "*.DS_Store"
unzip -q data/manifests.zip -d data -x "__MACOSX/*" "*.DS_Store"
mkdir -p data/routing-data && mv data/study_area_network_processed_v13.pkl data/routing-data/
```

The dataset can also be downloaded file by file from its web page. The zip files can be deleted after unzipping. Git ignores the zip files, the folders they unpack to, the road network and the download cache in `data/.cache/`.

The road network was built from the Geofabrik OpenStreetMap extract for California (https://download.geofabrik.de/north-america/us/california.html). The raw `.osm` file is **not** needed: `Routing.ipynb` reads the processed pickle, and only reads `data/routing-data/california-260318_study_area.osm` when the pickle is missing. To rebuild the network from scratch, download the extract from Geofabrik, clip it to the study area, and save it under that name.

### Environments

```bash
conda env create -f environment/environment.yml                      # analysis, geocode review, annual-report scraper
conda env create -f environment/environment-routing.yml              # routing (Linux or macOS, large memory)
conda env create -f environment/environment-manifest-extraction.yml  # manifest extraction (plus Tesseract, Poppler, libpostal)
```

`environment/environment.yml` pins the versions that produced the published outputs on macOS (arm64); `environment/environment-lock-osx-arm64.txt` lists every conda package exactly. The environment includes poppler, whose `pdftocairo` converts each figure that `Analysis.ipynb` saves to EPS. **Run the analysis in the activated environment** (`conda activate ca-dairy-accounting`, or select that environment's kernel). Activation sets `PROJ_NETWORK=ON`, so pyproj downloads the NOAA HARN datum grids from cdn.proj.org on the first run. Without them the reprojection to California Albers (EPSG:3310) uses a coarser transformation, and `BlockGroup_Exposure.csv` and Figure 4 come out slightly different. To open the notebooks, use JupyterLab (`conda install -n ca-dairy-accounting jupyterlab`) or an editor such as VS Code with the environment's kernel.

## Reproducing the results, step by step

Run each notebook from top to bottom in a fresh kernel (Restart & Run All), from its own folder. `Analysis.ipynb`, `Routing.ipynb` and `Manure_Manifest_Review.ipynb` find the repository root by walking up from the working directory. `manifest_preparation.ipynb` and `Dairy_Report_Scrape_Review.ipynb` must be started from their own folders, because they locate the repository relative to it.

### 1. Annual-report extraction and review (frozen; macOS only)

`review/annual-reports/Dairy_Report_Scrape_Review.ipynb` documents how the 215 annual reports that were not parsed by Robertson et al. (2026) were added to the report table:

1. scrape the PDFs with PyMuPDF and Apple Vision OCR (`results.pkl`);
2. post-process (`results_final.pkl`);
3. read facility-wide crop nitrogen removal (`crop_removal_extracted.csv`);
4. build the interactive review page (`Dairy_Report_Scrape_Review.html`, Figure S2) and review every row by hand (`outputs/review/annual-reports/scrape_review.csv`);
5. apply the reviewed rows to `outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv`;
6. tally the form each report used (`Annual_Report_Formats.csv`, Figure S1a).

The published files are already in place. Do not use Run All: the scrape cells rewrite the shipped intermediates, and the apply cell rewrites the analysis input. Several steps read the CSV that step 5 writes, so the published files came from repeating steps 5 → 6 → 3 → 4 → 5. The pickles and `crop_removal_extracted.csv` record each PDF under its original OneDrive path; `scraper/pipeline.local_pdf` maps those paths onto `data/annual-reports/`.

`review/annual-reports/geocode_dairy_addresses.py` geocoded the dairy addresses for the Figure 4a map with the US Census geocoder and Nominatim, writing `outputs/review/annual-reports/Dairy_Report_Geocodes.csv`. It is kept as a record; rerunning it queries live services and can change Figure 4a.

### 2. Manifest extraction and validation (frozen: cached OCR, LLMWhisperer and geocoder calls)

`review/manifests/extraction/manifest_preparation.ipynb` (by D. Wettermark) finds the transport manifests inside the annual reports, OCRs them (PyMuPDF, Tesseract, LLMWhisperer), extracts each field and geocodes the destinations. Its outputs:

- `outputs/review/manifests/all_manifests_as_written_automatic.csv`: automatic extraction;
- `outputs/review/manifests/all_manifests_as_written_validated.csv`: the same records after manual validation (a hand-made input to the later cells);
- `outputs/review/manifests/processed_manure_manifests.csv` and `processed_wastewater_manifests.csv` (839 and 427 records), which the analysis reads;
- `outputs/review/manifests/extraction_errors_by_field.csv`: errors corrected per field in the extraction accuracy comparison behind Figure S10;
- `outputs/review/manifests/geocode_cache.json`: cached geocoder responses;
- `outputs/review/manifests/2024_manifest_template_counts.csv`: manifests per form template, behind Table S1 and Figure S1b;
- `outputs/review/manifests/2024_files_by_template.csv`: manifest count and pages for each annual-report PDF, which the notebook reads and rewrites;
- `outputs/results/figures/Figure_S10_Manifest_Extraction_Accuracy.png` and `outputs/review/manifests/Haul_Size_Breakdown.png`.

Rerunning it needs the PDFs and the OCR text folders in `data/manifests/R5/` from Hugging Face (see Data download), the `cafo-manifests` environment and the system libraries in `environment/environment-manifest-extraction.yml`. With the OCR text and the geocode cache, no API key is needed unless new files are added. On 12 November 2026 the two haul columns of `processed_manure_manifests.csv` were rebuilt with the notebook's own functions from cells 4, 9 and 11 (`backfill_quantities`, `prepare_manifests` and `add_haul_estimates` with the 20-ton bin open-ended), applied to the validated table. The origin-address backfill and geocoding steps, which need libpostal and do not touch the haul inputs, were skipped. Every other column is unchanged, and the counts equal those `Routing.ipynb` computes.

### 3. Analysis inputs

The analysis reads `outputs/review/manifests/processed_manure_manifests.csv` and `processed_wastewater_manifests.csv` exactly as step 2 writes them (839 and 427 records). The routing files in `outputs/results/routing/`, the verdicts in `outputs/review/manifests/geocode_review.csv` and the figures and tables in `outputs/results/` were all made from these two files. Do not edit the processed files by hand: routing assigns route IDs by row order, and the geocode verdicts are keyed on address and coordinates.

### 4. Routing (optional; large memory)

`analysis/Routing.ipynb` (environment `manure_trucking_routing`) snaps every manure manifest's origin and destination to the road network, routes each pair by travel time in parallel, and writes the five files in `outputs/results/routing/` (plus `od_table_processed_v13.pkl`, an intermediate that nothing reads). It loads the 1.6 GB processed network, so it needs a machine with well over 16 GB of RAM (the published run used a Linux cluster). Rerunning it **overwrites the reviewed routing files**; run step 5 afterwards to re-apply the geocode verdicts.

### 5. Geocode and route review

`review/manifests/geocode-review/Manure_Manifest_Review.ipynb` writes the interactive reviewer `geocode_review.html` (Figure S3), in which every origin, destination and route was judged by hand against satellite imagery. The verdicts are in `outputs/review/manifests/geocode_review.csv`. Its section 5 (cell 6) applies them to `processed_manure_manifests_analysis.geojson`, `od_lines_with_status.geojson` and `od_pairs_with_status.geojson`, marking 190 more manifests as invalid (Bad Origin Geocode 14, Bad Destination Geocode 95, Routing Incorrect 81) and leaving 559 valid routes. To reproduce the shipped files, run cells 0–2 and section 5. Section 4 (cell 5) merges a decisions file exported from the reviewer and does nothing when there is none.

### 6. Analysis

```bash
conda activate ca-dairy-accounting
cd analysis
jupyter lab Analysis.ipynb     # JupyterLab: see Setup. Then Restart & Run All
```

`analysis/Analysis.ipynb` takes about 80 seconds with the exposure caches. It writes every file in `outputs/results/figures/` except Figures 1, S2, S3 and S6 (each figure as a PNG and an EPS), every file in `outputs/results/tables/`, and `outputs/results/Manuscript_Parameters.tex` and `.csv`. It stops with an error if any input is missing, rather than skipping a figure.

The two files in `outputs/results/routing/pair_cache/` cache the most expensive step, the intersection of the 500 m road buffers with block groups and Census places. They are used only while they are newer than `network_with_hauls_v13.gpkg`; otherwise they are rebuilt (several minutes). Because the folder name sorts after the network file, a git checkout writes them later and keeps them valid. All outputs are identical between runs in the pinned environment.

## Outputs and the manuscript

Every figure that `Analysis.ipynb` produces is also saved as an `.eps` file with the same name, converted from a PDF of the figure by poppler's `pdftocairo`. Text, lines and shapes stay vector. EPS has no transparency, so semi-transparent elements are embedded as 300 dpi images. In Figure 4 the map layers of panels a–c are embedded as images at the PNG's 200 dpi, which keeps the file at 4 MB instead of about 100 MB; the panel text, legends and colour bars stay vector. The conversion timestamp is removed, so reruns give identical files.

| File (outputs/results/figures/) | Manuscript | Produced by |
|---|---|---|
| `Figure_1_Data_Flow.jpg` | Figure 1 | drawn in draw.io (static) |
| `Figure_2_Manifest_Characteristics.png` | Figure 2 | Analysis.ipynb, cell 5 |
| `Figure_3_Nitrogen_Accounting.png` | Figure 3 | Analysis.ipynb, cell 5 |
| `Figure_4_Network_And_Exposure.png` | Figure 4 | Analysis.ipynb, cell 5 |
| `Figure_5_CARB_Manure_Management.png` | Figure 5 | Analysis.ipynb, cell 3 |
| `Figure_S1_Reporting_Formats.png` | Figure S1 | Analysis.ipynb, cell 5 |
| `Figure_S2_Annual_Report_Review_Example.png` | Figure S2 | screenshot of `review/annual-reports/Dairy_Report_Scrape_Review.html` (static) |
| `Figure_S3_Geocoding_Routing_Review_Example.png` | Figure S3 | screenshot of `review/manifests/geocode-review/geocode_review.html` (static) |
| `Figure_S4_Manure_Trucked_Per_Month.png` | Figure S4 | Analysis.ipynb, cell 5 |
| `Figure_S5_Applied_Ratio.png` | Figure S5 | Analysis.ipynb, cell 5 |
| `Figure_S6_Manifest_Flowchart.jpg` (source: `.drawio`) | Figure S6 | drawn in draw.io (static) from the drop counts printed by Analysis.ipynb, cell 0 |
| `Figure_S7_Routing_Failure_Modes.png` | Figure S7 | Analysis.ipynb, cell 4 |
| `Figure_S8_Routing_Zooms.png` | Figure S8 | Analysis.ipynb, cell 0 |
| `Figure_S9_Unaccounted_Nitrogen.png` | Figure S9 | Analysis.ipynb, cell 5 |
| `Figure_S10_Manifest_Extraction_Accuracy.png` | Figure S10 | Analysis.ipynb, cell 6, from the extraction outputs in `outputs/review/manifests/` (manifest_preparation.ipynb, cell 21, draws the same figure) |

| File (outputs/results/tables/) | Manuscript | Produced by |
|---|---|---|
| `Table_S5_Dropped_Route_Comparison.csv` | Table S5 | Analysis.ipynb, cell 1 |
| `Table_S6_Top_Receivers.csv` | Table S6 | Analysis.ipynb, cell 5 |
| `Table_S7_Longest_Routes.csv` | Table S7 | Analysis.ipynb, cell 0 |
| `Table_S8_Place_VMT_Total.csv` | Table S8 | Analysis.ipynb, cell 2 |
| `Table_S9_Place_VMT_Per_Capita.csv` | Table S9 | Analysis.ipynb, cell 2 |
| `Table_S10_Place_VMT_Per_Area.csv` | Table S10 | Analysis.ipynb, cell 2 |
| `Table_S11_Place_Exposure_Summary.csv` | values quoted in the text | Analysis.ipynb, cell 2 |
| `BlockGroup_Exposure.csv` | values quoted in the text | Analysis.ipynb, cell 2 |
| `Exposure_by_Income_Quintile.csv` | Figure 4e and values in the text | Analysis.ipynb, cell 2 |
| `SI_Tables.md` | Tables S1–S10 in LaTeX, with captions | Analysis.ipynb, cell 7 |
| `SI_Tables_S2_S4.tex` | Tables S2–S4 in LaTeX | Analysis.ipynb, cell 7 |

`SI_Tables.md` holds every SI table as a `longtable` block (`\usepackage{array,longtable}`). Table S1's percentages are `analysis_pct` (shares of the 1,198 analysed manifests) in `outputs/review/manifests/2024_manifest_template_counts.csv`, and its attachment, order, page-count and file-example columns come from `outputs/review/manifests/Manifest_Formats.csv`. Tables S2–S4 describe the extraction notebook's fields and rules, so their text is set in cell 7 (`SI_TABLES_S2_S4`), which also writes it on its own to `SI_Tables_S2_S4.tex`. Tables S5–S10 are formatted from the same results as the CSV files above.

`outputs/results/Manuscript_Parameters.tex` (cell 7) defines one LaTeX macro for each number the manuscript quotes from these results, and for each analysis setting it quotes (for example `\UnaccNMillionLb` for the unaccounted-for nitrogen in the abstract, or `\pDroppedTons` for a p-value with its relation). Add `\input{Manuscript_Parameters}` to the manuscript preamble; the `SI_Tables.md` captions use the same macros. `Manuscript_Parameters.csv` lists each macro with its value, unrounded value and the cell and variable it comes from. A few counts that no file records (the manual-screening counts in SI Methods 0.1.1, and software versions and routing settings that live in `Routing.ipynb`) are entered in cell 7 as literals and marked as such.

## File and field reference

### Result tables (`outputs/results/tables/`)

#### outputs/results/tables/Table_S5_Dropped_Route_Comparison.csv

Each row is one variable (manifest tonnage or origin-dairy herd size) summarised for one group of manure manifests. The groups are: routed, each drop reason, and all dropped combined. The universe is the 839 manure manifests.

- **Producer:** `analysis/Analysis.ipynb`, cell 1.
- **Manuscript:** Table S5 (cited as Table S5 in §2.3 and §3.3; goes with Fig. S7). The Mann-Whitney results are quoted in §3.3.

| Field | Description |
|---|---|
| variable | Either `Total manure (tons)` or `Herd size (animal units)`. Tonnage is `Total Manure Amount (tons)` as reported on the manifest (`processed_manure_manifests.csv`, carried into `processed_manure_manifests_analysis.geojson`). Herd size is the origin dairy's animal units: the six herd classes on its 2024 annual report, weighted by the Order R5-2008-0066 Table 1 factors (milk cows 1.40, dry cows 1.12, bred heifers 1.02, heifers 0.49, both calf classes 0.29). It is missing if any herd class is blank. Herd size belongs to the dairy, so it repeats across that dairy's manifests. |
| group | `Routed` means `valid route` is true. `Dropped: <reason>` is the first check the manifest failed, taken from `validation reason`. The reasons are No destination address, Outside water board, Failed geocode, Cross-county APN, Routing Failed, Bad Origin Geocode, Bad Destination Geocode and Routing Incorrect. The last three are verdicts from the manual geocode review. A reason with no manifests gets no row. `Routing Failed` has a single manifest, so its sd and test columns are blank. `Dropped: ALL` pools every dropped manifest. |
| n | Number of manifests in the group with a non-missing value. |
| n_missing | Number of manifests in the group with a missing value. |
| pct_missing | n_missing as a percentage of the group (%). |
| mean | Mean of the variable (tons, or animal units). |
| sd | Sample standard deviation (ddof = 1), same units as mean. |
| median | Median, same units as mean. |
| median_diff_vs_routed | Group median minus the Routed median, same units. Blank for Routed. |
| rank_biserial | Rank-biserial correlation, 2U/(n_group × n_routed) − 1, where U is the Mann-Whitney U of the group against Routed. Ranges from −1 to +1; positive means the group's values tend to be higher than routed values. Blank for Routed. |
| p_value | Two-sided Mann-Whitney U p-value against Routed, with no multiplicity correction. Rounded to 6 decimals, so 0.0 means p < 5×10⁻⁷. Blank for Routed. |

#### outputs/results/tables/Table_S6_Top_Receivers.csv

Each row is one of the 20 destinations that received the most manure. Destinations are identified by a normalised destination address. All 839 manure manifests count, not only the routed ones.

- **Producer:** `analysis/Analysis.ipynb`, cell 5.
- **Manuscript:** Table S6. Rank 2, a P.O. Box, is quoted in §3.1 (163,632 tons, 18 records). The manuscript table leaves out `Nitrogen (lb)` and `In report set`, and labels `Address form` as "Address type".

| Field | Description |
|---|---|
| Rank | Rank by tonnage received, 1–20. |
| Destination (normalised) | The manifest's `Destination Address Final`, normalised in five steps: (1) uppercased; (2) non-alphanumeric characters removed; (3) "CA"/"CALIFORNIA", California ZIP / ZIP+4 codes, and county names at the end of the address removed (the extraction appends the manifest's destination county, which is often wrong); (4) leading words such as a person's or business name removed before the house number; (5) PO boxes, and addresses where a road word comes before the number, are left alone in step 4. Manifests are grouped on this key. |
| Tons | Sum of `Total Manure Amount (tons)` as reported on the manifests, in short tons, rounded to whole tons. |
| Manifests | Number of manifest records sent to this destination. |
| Origin dairies | Number of distinct origin dairies, counted as distinct `Source PDF` annual-report files. |
| Nitrogen (lb) | Estimated nitrogen sent, in lb, rounded. Calculated as dry tons × 2.1% N × 2,000 lb/ton, the mid value from the UC Davis Manure Technical Guide. Dry tons = Tons × the manifest's `Manure Solids (%)`. Where a manifest gives no solids value, the tonnage-weighted mean of the manifests that do is used. |
| % of tonnage | Tons as a percentage of all tonnage on manifests with a non-blank destination key (%). |
| Cumulative % | Running total of `% of tonnage` from rank 1 down (%). |
| Address form | The Figure 2b address class of the receiver's records, by tonnage: `street`, `PO box`, or `place` for a key with no house number, such as "EL NIDO COYOTE RD". |
| In report set | `yes` if, for any manifest under this key, the destination street key (house number plus the next two words, normalised) matches the address of a dairy that filed a 2024 annual report (`Dairy_Annual_Report_Summary_Table_Region_5_2024.csv`). Otherwise `no`. |

#### outputs/results/tables/Table_S7_Longest_Routes.csv

Each row is one validated manure route (one manifest record). Only the 10 longest are kept, ranked by one-way road distance. The same origin-destination pair can appear on several rows under different RouteIDs.

- **Producer:** `analysis/Analysis.ipynb`, cell 0, which reads `outputs/results/routing/od_lines_with_status.geojson` and keeps rows where `valid route` is true.
- **Manuscript:** Table S7. Cited in §3.3, which names the longest trip (104.0 mi, Dutch Door Dairy to Stockton) and gives the top-10 shares. The manuscript table leaves out the 10-ton trips, 20-ton trips and capacity columns.

| Field | Description |
|---|---|
| Rank | Rank by one-way route distance, 1–10. |
| RouteID | Manifest record identifier, assigned by `analysis/Routing.ipynb` as the row position in the processed manure manifests (+1). It is the join key for all routing outputs. |
| Origin dairy | `Origin Dairy Name` from the processed manifests. |
| Origin address | `Origin Dairy Address` from the processed manifests: the manifest text, filled in from the dairy summary or PDF file name during extraction where the manifest left it blank. |
| Origin county | County polygon (`data/geospatial-data/CA_Counties`) that contains the geocoded origin point. |
| Destination address | `Destination Address Final`: the destination text used for geocoding, as written on the manifest. It may be the address with the cross street and county appended, a parcel number, a cross street, a contact address or a hauler address. |
| Destination type | `Destination Type (Standardized)`: Farmer, Broker, Composting Facility, Other or Blank. |
| Destination county | County polygon that contains the geocoded destination point. |
| Route distance one way (mi) | Length of the fastest (least travel-time) path over the OSM road network, computed in `analysis/Routing.ipynb`. Converted from km to miles, 1 decimal. |
| 10-ton truck trips | Number of 10-ton hauls, as rebuilt in `analysis/Routing.ipynb`. If the manifest gives a mass per haul of 5–15 t, its reported haul count is used. Otherwise tonnage is split by the regional 10-ton/20-ton tonnage share. A manifest under 10 t gets one 10-ton trip. |
| 20-ton truck trips | Number of 20-ton hauls, by the same rule; a reported haul count is used when mass per haul is ≥ 15 t. |
| Total truck trips | 10-ton trips + 20-ton trips (loaded trips). |
| Manure shipped, reported (tons) | `Total Manure Amount (tons)` as reported on the manifest, 1 decimal. |
| Truck capacity implied (tons) | 10 × 10-ton trips + 20 × 20-ton trips, whole tons. |
| Loaded truck-mi over all hauls | Route distance × total truck trips (mi), whole miles. Counts loaded travel only; the empty return would double it. |

#### outputs/results/tables/Table_S8_Place_VMT_Total.csv

Each row is one Census place (city, town or CDP) among the 20 with the most manure-truck miles allocated to it. A place qualifies if more than half its area lies in the Central Valley Water Board region and its truck-mi is above zero.

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Table S8 (Rank, Place, Truck-mi only). Tulare, Visalia and Shafter are quoted in §3.3.

| Field | Description |
|---|---|
| Rank | Rank by Truck-mi, 1–20. |
| Place | `NAMELSAD` from the 2024 Census place cartographic boundary file (`cb_2024_06_place_500k`). |
| Type | `city`, `town` or `CDP`, from the place's `LSAD` code (25, 43 or 57). |
| Population | Total population from the 2020–2024 ACS five-year estimates (table B01003, NHGIS `AUO6E001`), in persons. |
| Land area (mi2) | TIGER `ALAND` converted to mi² (excludes water), 2 decimals. |
| Truck-mi | Truck vehicle-miles allocated to the place, rounded to whole miles; empty returns are included (loaded mi × 2). Each road segment carrying validated hauls is buffered by 500 m (EPSG:3310). Its truck-mi are spread evenly over its buffer, and the place receives the share of each buffer that falls inside its boundary. |
| Truck-mi per capita | Truck-mi / Population (mi per resident), 2 decimals. |
| Truck-mi per mi2 | Truck-mi / Land area (mi per mi² of land), whole numbers. |

#### outputs/results/tables/Table_S9_Place_VMT_Per_Capita.csv

Each row is one Census place among the 20 with the highest truck-mi per resident. The places, columns and calculations are the same as Table S8. Several of these places have fewer than 500 residents, so their rates rest on small denominators.

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Table S9 (Rank, Place, Truck-mi per capita only). Lakeside CDP (24.23) is quoted in §3.3; cited with Table S10 in §3.3 and §4.

| Field | Description |
|---|---|
| Rank | Rank by Truck-mi per capita, 1–20. |
| Place | `NAMELSAD` from `cb_2024_06_place_500k`. |
| Type | `city`, `town` or `CDP`, from `LSAD`. |
| Population | ACS 2020–2024 total population (B01003, `AUO6E001`), in persons. |
| Land area (mi2) | TIGER `ALAND` in mi² (excludes water), 2 decimals. |
| Truck-mi | Truck-mi allocated to the place from the 500 m buffers, empty returns included, whole miles. See Table S8. |
| Truck-mi per capita | Truck-mi / Population (mi per resident), 2 decimals. |
| Truck-mi per mi2 | Truck-mi / Land area (mi per mi²), whole numbers. |

#### outputs/results/tables/Table_S10_Place_VMT_Per_Area.csv

Each row is one Census place among the 20 with the highest truck-mi per square mile of land. The places, columns and calculations are the same as Table S8.

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Table S10 (Rank, Place, Truck-mi per mi² only). Tipton CDP (10,908) is quoted in §3.3; cited in §3.3 and §4.

| Field | Description |
|---|---|
| Rank | Rank by Truck-mi per mi2, 1–20. |
| Place | `NAMELSAD` from `cb_2024_06_place_500k`. |
| Type | `city`, `town` or `CDP`, from `LSAD`. |
| Population | ACS 2020–2024 total population (B01003, `AUO6E001`), in persons. |
| Land area (mi2) | TIGER `ALAND` in mi² (excludes water), 2 decimals. |
| Truck-mi | Truck-mi allocated to the place from the 500 m buffers, empty returns included, whole miles. See Table S8. |
| Truck-mi per capita | Truck-mi / Population (mi per resident), 2 decimals. |
| Truck-mi per mi2 | Truck-mi / Land area (mi per mi²), whole numbers. |

#### outputs/results/tables/Table_S11_Place_Exposure_Summary.csv

Each row is one group of Census places: a community type (CDP, city, town) or a population size class. It covers every place with more than half its area in the Water Board region. Rates are pooled (group totals divided by group totals), not averages of place-level rates.

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Not in the manuscript. There is no Table S11.

| Field | Description |
|---|---|
| Grouping | `Community type` or `Population size`. |
| Group | For community type: `CDP`, `city` or `town`. For population size, by ACS population: `<0.5k` (<500), `0.5-2.5k` (500–2,499), `2.5-10k` (2,500–9,999), `10-50k` (10,000–49,999), `>=50k` (≥50,000). |
| Places in region | Number of places in the group. |
| Places exposed | Number of places with allocated truck-mi above zero. |
| Incidence (%) | Places exposed / Places in region × 100. |
| Population | Total ACS 2020–2024 population of all places in the group, in persons. |
| Population in exposed places (%) | Population of the exposed places as a share of the group's Population (%). |
| Truck-mi | Total truck-mi allocated to the group's places from the 500 m buffers, empty returns included, whole miles. |
| Share of truck-mi (%) | The group's Truck-mi as a share of the total across all groups in the same Grouping (%). |
| Share of exposed population (%) | The group's population in exposed places as a share of all exposed-place population in the same Grouping (%). |
| Trucking exposure ratio | Share of truck-mi / Share of exposed population. Above 1 means the group's exposed residents carry more than their proportional share. |
| Truck-mi per capita | Truck-mi / population of the exposed places (mi per resident), 3 decimals. |
| Truck-mi per mi2 | Truck-mi / land area (`ALAND`) of the exposed places (mi per mi²), 1 decimal. |
| People per mi2 | Population of the exposed places / land area of the exposed places (persons per mi²), 1 decimal. |
| Mean share of area within 500 m (%) | Unweighted mean over the exposed places of the share of each place's area (polygon area in EPSG:3310) lying within 500 m of any road segment carrying validated hauls (%). Blank when the group has no exposed places. |

#### outputs/results/tables/BlockGroup_Exposure.csv

Each row is one 2024 Census block group whose area lies more than half inside the Central Valley Water Board boundary (5,246 rows). The full, unclipped polygon is used for areas and allocation.

The file has no geometry. Join it on `GISJOIN` to `data/geospatial-data/CA_BGs/nhgis0015_shape-nhgis0015_shapefile_tl2024_060_blck_grp_2024/CA_blck_grp_2024.shp`. Areas and buffers were computed in EPSG:3310 (California Albers).

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Not a manuscript table. It holds the block-group values behind Fig. 4e and the §3.3 income statistics, which use the 4,851 rows with `AURUE001` > 0.

| Field | Description |
|---|---|
| GISJOIN | NHGIS block-group identifier. |
| AURUE001 | Median household income in 2024 inflation-adjusted dollars (ACS 2020–2024 table B19013, NHGIS code). `-666666666` means the value is suppressed (395 rows); these rows are left out of the income analysis. |
| bg_pop | Total population, ACS 2020–2024 (table B01003), in persons. |
| unit_area_mi2 | Polygon area in EPSG:3310 (mi²). |
| land_area_mi2 | TIGER `ALAND` in mi² (excludes water); equals `unit_area_mi2` where `ALAND` is missing. |
| VMT10_j | 10-ton truck vehicle-miles allocated to the block group, empty returns included (mi). Each road segment carrying validated hauls is buffered by 500 m. Its truck-mi are spread evenly over its buffer, and the block group receives the share of each buffer inside it. |
| VMT20_j | The same, for 20-ton trucks (mi). |
| VMT_j | VMT10_j + VMT20_j (mi). |
| PM2.5_g_j | PM2.5 from the allocated truck-mi (g). Uses EMFAC2025 v2.1.1 rates for San Joaquin Valley APCD, calendar year 2024: T7 Single Dump Class 8 for 10-ton trucks and T7 Tractor Class 8 for 20-ton trucks. Includes running exhaust, tire wear and brake wear. |
| NOx_g_j | NOx running exhaust from the allocated truck-mi, same EMFAC rates (g). |
| ROG_g_j | ROG running exhaust from the allocated truck-mi, same EMFAC rates (g). |
| exposed_mi2 | Area of the block group within 500 m of any road segment carrying hauls, using the union of all buffers (mi²). |
| frac_exposed | exposed_mi2 / unit_area_mi2 (fraction, 0–1). |
| VMT_per_mi2 | VMT_j / land_area_mi2 (truck-mi per mi² of land). |
| VMT_per_capita | VMT_j / bg_pop (truck-mi per resident). Blank where bg_pop is 0 (6 rows). |
| PM25_per_capita | PM2.5_g_j / bg_pop (g per resident). Blank where bg_pop is 0. |

#### outputs/results/tables/Exposure_by_Income_Quintile.csv

Each row is one population-weighted median-household-income quintile of block groups, Q1 (lowest income) to Q5. Only block groups with reported income are included (4,851). Cut points are set so each quintile holds about a fifth of residents.

The `rho_*` correlation columns are the same on every row, because they are computed over all block groups rather than per quintile.

- **Producer:** `analysis/Analysis.ipynb`, cell 2.
- **Manuscript:** Fig. 4e (bars and 95% CIs) and values quoted in §3.3: 0.38 vs 0.11 truck-mi per person for Q1 vs Q5; Spearman ρ = −0.187 per resident and −0.199 per mi² over 4,851 block groups.

| Field | Description |
|---|---|
| quintile | `Q1` (lowest median household income) to `Q5` (highest). |
| n_bg | Number of block groups in the quintile. |
| income_min, income_max | Lowest and highest block-group median household income in the quintile (2024 dollars). 2,499 and 250,001 are the ACS bottom and top codes. |
| pop | Total residents of the quintile (sum of `bg_pop`). |
| mean_exposure | Population-weighted mean of `VMT_per_capita` (truck-mi within 500 m per resident). This is the primary metric. |
| ci_lo, ci_hi | 95% bootstrap percentile interval for mean_exposure. 2,000 draws, resampling block groups with replacement within the quintile, seed 0. |
| alt_mean | Population-weighted mean of `VMT_per_mi2` (truck-mi per mi² of land). |
| alt_ci_lo, alt_ci_hi | 95% bootstrap percentile interval for alt_mean, using the same method. |
| total_VMT | Sum of `VMT_j` over the quintile (truck-mi, empty returns included). |
| total_PM25_g | Sum of `PM2.5_g_j` over the quintile (g). |
| pop_share_pct | pop as a share of the total over all five quintiles (%). |
| vmt_share_pct | total_VMT as a share of the total over all five quintiles (%). |
| rho_mhi_all, rho_mhi_all_p, rho_mhi_all_ci_lo, rho_mhi_all_ci_hi | Spearman ρ between median household income (`AURUE001`) and truck-mi per resident, over all block groups with income > 0. Unweighted. The four columns are: ρ; its two-sided p-value; and the 2.5th and 97.5th percentiles of 2,000 bootstrap draws (seed 0). |
| rho_mhi_exposed, rho_mhi_exposed_p, rho_mhi_exposed_ci_lo, rho_mhi_exposed_ci_hi | The same, restricted to block groups with truck-mi per resident > 0. |
| rho_pc_all, rho_pc_all_p, rho_pc_all_ci_lo, rho_pc_all_ci_hi | The same as `rho_mhi_all*`, but using per capita income (ACS B19301, NHGIS `AUSYE001`) in place of median household income. |
| rho_pc_exposed, rho_pc_exposed_p, rho_pc_exposed_ci_lo, rho_pc_exposed_ci_hi | Per capita income, block groups with truck-mi per resident > 0. |
| rho_alt_mhi_all, rho_alt_mhi_all_p, rho_alt_mhi_all_ci_lo, rho_alt_mhi_all_ci_hi | The same as `rho_mhi_all*`, but using the alternative metric, truck-mi per mi² (`VMT_per_mi2`). |
| rho_alt_mhi_exposed, rho_alt_mhi_exposed_p, rho_alt_mhi_exposed_ci_lo, rho_alt_mhi_exposed_ci_hi | Median household income vs truck-mi per mi², block groups with truck-mi per mi² > 0. |
| rho_alt_pc_all, rho_alt_pc_all_p, rho_alt_pc_all_ci_lo, rho_alt_pc_all_ci_hi | Per capita income vs truck-mi per mi², all block groups with income > 0. |
| rho_alt_pc_exposed, rho_alt_pc_exposed_p, rho_alt_pc_exposed_ci_lo, rho_alt_pc_exposed_ci_hi | Per capita income vs truck-mi per mi², block groups with truck-mi per mi² > 0. |

### Routing outputs (`outputs/results/routing/`)

#### `outputs/results/routing/network_with_hauls_v13.gpkg`

Each row is one directed road segment (OSMnx edge `u → v`, `key`) that at least one routed origin–destination pair travels over. There are 23,147 rows. Produced by `analysis/Routing.ipynb`, cell 0 (cells 1–2 are empty), function `export_network_with_hauls_shapefile`. It backs Fig. 4b, Fig. S8, the trip-mileage, emissions and fuel totals in §3.3 and SI 0.1.3, and, through the exposure cache, Fig. 4e–f and Tables S8–S10. The stored haul columns cover all 749 routed pairs. `Analysis.ipynb` cell 0 (`network_hauls_from_routes`) replaces them with a re-sum of `route_edge_usage_v13.csv.gz` over routes where `valid route` is true.

Geometry: LineString, EPSG:32610 (WGS 84 / UTM zone 10N, metres), single layer `network_with_hauls_v13`.

| Field | Description |
|---|---|
| `u` | Start node ID. OSM node ID, or a negative ID for a point inserted where a geocode was snapped onto an edge: −(10,000,000 + RouteID) for an origin, −(20,000,000 + RouteID) for a destination. A snap within 0.5 m of an existing node reuses that node. |
| `v` | End node ID (same scheme as `u`). |
| `key` | Key that tells apart parallel edges between the same `u` and `v` in the OSMnx MultiDiGraph (0–2). |
| `length_m` | Edge length in metres from OSMnx. For segments created by snap-splitting it is the planar length in EPSG:32610. It differs from the geometry length by up to about 53 m on single edges. |
| `speed_kph` | Speed used for routing, km/h. Set by OSMnx `add_edge_speeds`: the OSM `maxspeed` tag where present, otherwise the notebook's default for the highway type (motorway 100, primary 80, residential 30, …), otherwise 40. Split segments take the parent edge's speed. |
| `travel_time_sec` | Travel time in seconds = `length_m` / (`speed_kph` / 3.6). This is the routing weight. |
| `name` | OSM `name` tag. Where OSMnx merged ways with different names, it is a Python list written as a string (e.g. `"['Road 27', 'Madera Avenue']"`). Null on split segments and unnamed ways. |
| `highway` | OSM `highway` tag (same list-as-string convention). Null on the 1,542 snap-split segments and on 3,232 OSM ways that have no `highway` tag. |
| `h10` | Loaded (one-way) 10-ton hauls crossing the segment in the `u → v` direction, summed over all routed pairs. Return trips are not included; the analysis multiplies by 2. |
| `h20` | Same as `h10` for 20-ton hauls. |
| `km10` | Loaded 10-ton truck-km on the segment = `h10` × `length_m` / 1000. |
| `km20` | Loaded 20-ton truck-km = `h20` × `length_m` / 1000. |
| `kmtot` | `km10` + `km20`, in km. |

Caveat: the 3,232 rows with no `highway` tag that are not snap-split segments are mostly named after rail lines and waterways (e.g. "BNSF Bakersfield Subdivision", "UP Fresno Subdivision", "Construction Package 1", "Fairfield Canal"). Some have `maxspeed`-derived speeds up to 402 km/h. Together they carry 25.0% of `kmtot`, and 16.2% of loaded truck-km on routes where `valid route` is true.

#### `outputs/results/routing/route_edge_usage_v13.csv.gz`

Each row is one routed pair's use of one directed network segment. There are 58,615 rows covering 749 routes and 23,147 segments; there is no geometry. Produced by `analysis/Routing.ipynb`, cell 0, function `export_route_edge_usage`. Summing over `RouteID` by (`u`, `v`, `key`) reproduces `h10`, `h20`, `km10`, `km20` and `kmtot` in `network_with_hauls_v13.gpkg` exactly. This is checked when the file is written and again in `Analysis.ipynb` cell 0. The table is not cited directly in the manuscript. `Analysis.ipynb` cell 0 (`network_hauls_from_routes`) uses it to limit the network to routes where `valid route` is true. That backs Fig. 4b, Fig. S8, the mileage, emissions and fuel totals in §3.3 and SI 0.1.3, and the exposure results (Fig. 4e–f, Tables S8–S10). It joins to the network file on `u`, `v`, `key` and to the OD and manifest files on `RouteID`.

| Field | Description |
|---|---|
| `RouteID` | Route ID: the 1-based row number of the manifest in `processed_manure_manifests.csv`. |
| `u` | Start node ID of the segment (same scheme as the network file). |
| `v` | End node ID of the segment. |
| `key` | Parallel-edge key of the segment. |
| `hauls_10ton` | The route's loaded 10-ton haul count (`Hauls_10ton` of the OD pair), repeated on every segment of the route. |
| `hauls_20ton` | The route's loaded 20-ton haul count, repeated on every segment. |
| `km_10` | Loaded 10-ton truck-km this route adds to the segment = segment `length_m` / 1000 × `hauls_10ton`. |
| `km_20` | Loaded 20-ton truck-km = segment `length_m` / 1000 × `hauls_20ton`. |
| `km_tot` | `km_10` + `km_20`, in km. |

#### `outputs/results/routing/od_lines_with_status.geojson`

Each row is one origin–destination pair (one manifest) that was sent to routing. There are 750 rows: 749 with `routing_status` = `success`, and 1 with `same_node` (its origin and destination snap to the same node, so it has no path). Produced by `analysis/Routing.ipynb`, cell 0, function `export_od_lines_with_status`. `review/manifests/geocode-review/Manure_Manifest_Review.ipynb` cell 6 ("5) Apply the verdicts") then rewrites the file in place: it adds the three review-verdict columns and updates `valid route` and `validation reason`. It backs Fig. 4d, Table S7, and the route-distance values quoted in §3.3: 90.0% of trips under 25 mi, longest trip 104.0 mi, mean 10.0 mi one way, and the ten longest routes holding 10.2% of truck-miles and 1.8% of tonnage. Its `valid route` flag also picks which routes `Analysis.ipynb` cell 0 keeps in the network. The review tool shown in Fig. S3 draws these lines.

Geometry: LineString, EPSG:4326 (written as OGC:CRS84, lon/lat). It is the routed path in travel order, built from network edge geometries and reprojected from EPSG:32610. It starts and ends at the snap points on the network, not at the geocodes. Pairs that failed to route get null geometry (the 1 `same_node` row in the current file).

| Field | Description |
|---|---|
| `RouteID` | Route ID: the 1-based row number of the manifest in `processed_manure_manifests.csv`. |
| `routing_status` | Routing result: `success`, `same_node` (both ends snapped to the same node), `no_path`, `error_<message>` or `not_processed`. Only `success` and `same_node` appear now. |
| `origin_name` | Origin dairy name, as reported on the manifest (`Origin Dairy Name`). Null on 4 rows. |
| `origin_address` | Origin dairy address (`Origin Dairy Address`), as reported on the manifest. Where blank, it was filled from the annual-report summary or the PDF file name during extraction. |
| `dest_address` | Destination text that was geocoded (`Destination Address Final`), copied from the manifest field chosen by the extraction's priority order. |
| `dest_type` | Destination type, standardized from the manifest text by keyword (`Destination Type (Standardized)`): Farmer, Broker, Composting Facility, Other, Blank. |
| `source_pdf` | File stem of the annual-report PDF the manifest was extracted from. |
| `orig_lat` | Geocoded origin latitude, decimal degrees (WGS84). |
| `orig_lon` | Geocoded origin longitude, decimal degrees (WGS84). |
| `dest_lat` | Geocoded destination latitude, decimal degrees (WGS84). |
| `dest_lon` | Geocoded destination longitude, decimal degrees (WGS84). |
| `Hauls_10ton` | Loaded one-way 10-ton hauls for the pair: `Number of 10-ton Hauls for Analysis`, with null set to 0. |
| `Hauls_20ton` | Loaded one-way 20-ton hauls for the pair: `Number of 20-ton Hauls for Analysis`, with null set to 0. |
| `Origin County` | County containing the origin point (spatial join with `data/geospatial-data/CA_Counties`). |
| `Destination County` | County containing the destination point. |
| `route_km` | One-way length of the least-travel-time path between the snapped origin and destination nodes, in km (sum of edge `length_m` / 1000). Null if not routed. |
| `total_truck_km` | `route_km` × (`Hauls_10ton` + `Hauls_20ton`): loaded truck-km for the pair, without return trips. |
| `valid route` | True if the pair passed every routing check and every manual-review verdict. |
| `validation reason` | First check the pair failed; null when valid. Values in this file: `Routing Failed`, `Bad Origin Geocode`, `Bad Destination Geocode`, `Routing Incorrect`. |
| `Origin Geocode Correct` | Manual verdict on the origin point from `outputs/review/manifests/geocode_review.csv`: true, false, or null if not judged. |
| `Destination Geocode Correct` | Manual verdict on the destination point (true / false / null). |
| `Route Correct` | Manual verdict on the routed path, keyed by the coordinates of both endpoints. False means flagged as a bad route; null means not judged. |

#### `outputs/results/routing/od_pairs_with_status.geojson`

Each row is one endpoint of a routed origin–destination pair, two points per pair. There are 1,500 rows (750 origins, 750 destinations). Produced by `analysis/Routing.ipynb`, cell 0, function `export_od_pairs_with_status`. `Manure_Manifest_Review.ipynb` cell 6 rewrites it in place, the same way as the OD lines. Not in the manuscript: no analysis code reads it, and it serves as a GIS point layer.

Geometry: Point, EPSG:4326 (OGC:CRS84), placed at the geocoded origin or destination coordinate (not snapped).

| Field | Description |
|---|---|
| `point_type` | `origin` or `destination`: which endpoint the point is. |
| `RouteID`, `routing_status`, `origin_name`, `origin_address`, `dest_address`, `dest_type`, `source_pdf`, `orig_lat`, `orig_lon`, `dest_lat`, `dest_lon`, `Hauls_10ton`, `Hauls_20ton`, `Origin County`, `Destination County`, `route_km`, `total_truck_km`, `valid route`, `validation reason`, `Origin Geocode Correct`, `Destination Geocode Correct`, `Route Correct` | Same definitions and units as in `od_lines_with_status.geojson`. The values repeat on both points of a pair. |

#### `outputs/results/routing/processed_manure_manifests_analysis.geojson`

Each row is one manure manifest record. There are 839 rows, the full `processed_manure_manifests.csv`, with no rows dropped. Written by `analysis/Routing.ipynb`, cell 0: `add_haul_estimates` and `add_validation_columns`, then saved in the main block. `Manure_Manifest_Review.ipynb` cell 6 rewrites it in place: it adds the verdict columns and appends the review reasons to `valid route` and `validation reason`. It backs the Fig. S6 drop counts, Fig. S7, Table S5, the tonnage join in Table S7, and Fig. S4. It also backs the record counts in §2.3 and §3.3: 89 dropped before routing, 1 that failed to route, and 559 validated (66.6%) with 76,166 10-ton hauls, 29,083 20-ton hauls and 1,350,324 t (56.1%). `Analysis.ipynb` cell 0 loads it as `manure_df`.

Geometry: Point, EPSG:4326 (OGC:CRS84), at the geocoded destination. Null on the 68 records that have no destination geocode.

| Field | Description |
|---|---|
| `Source PDF` | File stem of the annual-report PDF holding the manifest. |
| `Manifest Number` | Order of the manifest within its PDF, as assigned during extraction. A letter suffix (`1a`, `1b`, …) marks the separate rows of a multi-row hauling table. |
| `Start Page` | PDF page number where the manifest starts. |
| `End Page` | PDF page number where the manifest ends. |
| `Origin Dairy Name` | As reported on the manifest. |
| `Origin Dairy Address` | As reported on the manifest. Where blank, filled from the annual-report summary or the PDF file name. |
| `Origin Dairy Latitude (Geocoded)` | Origin latitude, decimal degrees (WGS84). Geocoded by the ArcGIS World geocoder (Google as fallback); may have been corrected by hand. |
| `Origin Dairy Longitude (Geocoded)` | Origin longitude, decimal degrees (WGS84). |
| `Destination Address Final` | Destination text chosen for geocoding by priority order: parcel number, coordinates written in the cross-street field, address (plus cross street and county), a two-street intersection, contact address, hauler address. Copied from the manifest. |
| `Destination Address Final Source` | Manifest field that supplied it: `Destination Address`, `Destination Contact Address`, `Destination Assessor Parcel Number`, `Hauler Address`, `Destination Nearest Cross Street`. Null when there is no destination. |
| `Destination Type (Standardized)` | Manifest destination type matched by keyword to Composting Facility (compost / kellogg / hyponex / fertilizer / supply), Farmer (farm) or Broker (broker). Blank if empty; Other otherwise. |
| `Destination Latitude (Geocoded)` | Destination latitude, decimal degrees (WGS84). Comes from the DWR parcel locator for parcel numbers, ArcGIS/Google for addresses, or coordinates written on the manifest. Null when not geocodable (e.g. PO boxes, city-only addresses). |
| `Destination Longitude (Geocoded)` | Destination longitude, decimal degrees (WGS84). |
| `First Haul Date` | Earliest date parsed from the manifest's haul-date text, formatted YYYY-MM-DD. Null when only one date was reported. |
| `Last Haul Date` | Latest (or only) haul date, formatted YYYY-MM-DD. |
| `Is Pipeline` | String `"True"` / `"False"`: true if "pipeline" appears in the manifest text. |
| `Is Trucked` | Always true for manure manifests (set during extraction). |
| `Manure Mass per Haul (tons)` | Tons per load, parsed from the manifest's load text (e.g. "N loads x M tons"), or converted from cubic yards per load using the reported density. |
| `Manure Number of Hauls` | Number of loads parsed from the manifest's load text. |
| `Total Manure Amount (tons)` | Total manure shipped, as reported on the manifest. If reported in cubic yards, converted as yards / reported density. Rounded to 0.1 t. |
| `Manure Solids (%)` | Percent solids as reported, or 100 − reported moisture %. Values above 100 are set to null. |
| `RouteID` | 1-based row number; the join key to the OD files and `route_edge_usage_v13.csv.gz`. |
| `Number of 10-ton Hauls for Analysis` | Loaded 10-ton trips, recomputed by `Routing.ipynb` `add_haul_estimates`. This overwrites the column in the input CSV. Rules: the reported number of hauls if mass per haul is in [5, 15) t; 0 if mass per haul is ≥ 15 t; otherwise round(total t × p10 / 10), where p10 is the 10-ton tonnage share among manifests whose class is known. Records under 10 t get 1. Null when no tonnage is given. |
| `Number of 20-ton Hauls for Analysis` | Loaded 20-ton trips: the reported number of hauls if mass per haul is ≥ 15 t; 0 if in [5, 15) t or under 10 t total; otherwise round(total t × (1 − p10) / 20). |
| `valid route` | True if the record passed every check below. |
| `validation reason` | First failed check, in this order: `No destination address`, `Outside water board` (origin or destination outside the Central Valley Water Board boundary), `Failed geocode`, `Cross-county APN` (destination geocoded from a parcel number lies in a different county from the origin), `Routing Failed`, then the manual-review reasons `Bad Origin Geocode`, `Bad Destination Geocode`, `Routing Incorrect`. Null when valid. |
| `routing_status` | `success` for the 749 routed records and `same_node` for 1. Null for the 89 records never sent to routing. `snapping_failed`, `no_path` and `error_*` are possible but do not appear. |
| `Origin Geocode Correct` | Manual verdict on the origin point (true / false / null if not judged). |
| `Destination Geocode Correct` | Manual verdict on the destination point (true / false / null). |
| `Route Correct` | Manual verdict on the routed path (true / false / null). |

Note: across all 839 records, this file's haul columns sum to 134,180 10-ton and 52,853 20-ton hauls (§2.3). `Routing.ipynb` recomputes them with the same rule `manifest_preparation.ipynb` uses, so they equal the haul columns of `processed_manure_manifests.csv`. The validated subtotals (76,166 and 29,083) come from this file.

#### `outputs/results/routing/pair_cache/exposure_pairs_500m.pkl`

A pickled pandas DataFrame with no geometry. Each row is one pair of (road segment's 500 m buffer, census block group) that overlap with area greater than zero. There are 48,717 rows covering 19,833 segments and 1,361 block groups. Produced by `analysis/Analysis.ipynb` cell 2 (the third cell, the buffer-exposure block): `build_exposure_pairs(exp_net, bg_units)`, saved by `_cache_write`, which tries parquet first and falls back to pickle. The cache is reused while it is newer than `network_with_hauls_v13.gpkg`. It stores only geometry-derived columns. Truck-miles are joined on each run by `attach_edge_vmt`, so changing which routes are selected does not invalidate it. It backs Fig. 4e, Fig. 4c via the same block-group set, and the block-group values in §3.3: Spearman ρ = −0.187 per resident and −0.199 per mi², and 0.38 vs 0.11 truck-mi per person. It also feeds `BlockGroup_Exposure.csv` and `Exposure_by_Income_Quintile.csv`.

| Field | Description |
|---|---|
| `edge_idx` | 0-based position of the segment in the exposure network that `prepare_exposure_network(network)` builds in cell 2. That network is the gpkg (after cell 0's valid-route re-sum) reprojected to EPSG:3310, with zero-length and empty edges dropped and reciprocal `u→v` / `v→u` edges of equal length merged into one undirected segment. It is not a gpkg row number. |
| `buffer_area` | Area of the segment's 500 m round-capped buffer, m² (EPSG:3310, California Albers). |
| `GISJOIN` | NHGIS block-group identifier (15 characters) for 2024 TIGER/Line block groups. The block-group set is those with ACS 2020–2024 income records and more than 50% of their area inside the Water Board boundary; their full unclipped polygons are used. |
| `inter_area` | Area where the buffer overlaps the block group, m² (EPSG:3310). |
| `area_frac` | `inter_area` / `buffer_area` (0–1): the share of the segment's truck-miles assigned to the block group. Exposure for a block group = Σ segment VMT × `area_frac`, then × 2 for return trips. |

#### `outputs/results/routing/pair_cache/exposure_pairs_place_500m.pkl`

A pickled pandas DataFrame with no geometry. Each row is one pair of (road segment's 500 m buffer, Census Place) that overlap with area greater than zero. There are 10,118 rows covering 9,164 segments and 163 places. Produced by `analysis/Analysis.ipynb` cell 2, in the Census Place block (`build_exposure_pairs(exp_net, _pl, unit_id="GEOID")`). It uses the same cache rules as the block-group file, plus a check that every `GEOID` is in the current set of retained places. It backs Tables S8, S9 and S10, Fig. 4f, and the place values in §3.3: Tulare 49,299 mi, Visalia, Shafter, Lakeside at 24.23 truck-mi per resident, Tipton at 10,908 truck-mi per mi², and the top 5% of residents bearing 48.7% of truck-miles. It also feeds `Table_S11_Place_Exposure_Summary.csv`, which is not in the manuscript.

| Field | Description |
|---|---|
| `edge_idx` | 0-based segment position in the cell 2 exposure network (same as in `exposure_pairs_500m.pkl`). |
| `buffer_area` | Area of the segment's 500 m buffer, m² (EPSG:3310). |
| `GEOID` | 7-character Census Place GEOID (state FIPS `06` + 5-digit place code) from the 2024 Census Place shapefile. Only places with more than 50% of their area inside the Water Board are included; their full polygons are used. |
| `inter_area` | Area where the buffer overlaps the place, m² (EPSG:3310). |
| `area_frac` | `inter_area` / `buffer_area` (0–1): the share of the segment's truck-miles assigned to the place. |

### Manifest tables read by the analysis (`outputs/review/manifests/`)

#### outputs/review/manifests/processed_manure_manifests.csv

Each row is one manure transport record: one haul entry on a manifest attached to a 2024 annual report. A manifest that lists several hauls or destinations gives several rows. The file has 839 rows and 23 columns.

- **Producer:** `review/manifests/extraction/manifest_preparation.ipynb`. Cell 11 defines the geocoders, `prepare_manifests` and `save_manifest_type`. Cell 17 drops the rows marked `Is Duplicate` in the hand-validated `all_manifests_as_written_validated.csv`, then runs `backfill_origin_addresses` → `geocode_manifests` → `backfill_quantities` → `prepare_manifests` → `save_manifest_type`. `analysis/Routing.ipynb` and `analysis/Analysis.ipynb` read it.
- **Manuscript:**
  - the manure records (§2.1)
  - 2,406,173 tons and the destination-type shares (§3.1, Fig. 2a)
  - destination address forms (Fig. 2b)
  - 134,180 10-ton and 52,853 20-ton hauls in the haul columns (§2.3)
  - the 10-ton share, and the 828 dated / 567 last-date-only records (SI 0.1.1)
  - Fig. S4 and Table S6
  - records linked to dairies (SI 0.1.4, Fig. 5)
  - through `Routing.ipynb`, all routing results (Fig. 4, Figs. S6–S8, Tables S5 and S7–S10)

| Field | Description |
|---|---|
| Source PDF | File name of the annual-report PDF the manifest is attached to, without the extension. |
| Manifest Number | Position of the manifest within that PDF (1, 2, …). A letter suffix (`3a`, `3b`, …) marks separate records taken from one manifest document, such as the rows of a hauling table. |
| Start Page | First page of the manifest in the source PDF (counted from 1). |
| End Page | Last page of the manifest in the source PDF (counted from 1). |
| Origin Dairy Name | Name of the exporting dairy as written on the manifest. Blank on 6 rows. |
| Origin Dairy Address | Exporting dairy address as written on the manifest. When it is blank or names no city or ZIP code, it is replaced by the report's `Dairy Address` in `review/manifests/helpers/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv`, matched on `Source PDF`. Blank on 5 rows. |
| Origin Dairy Latitude (Geocoded) | Origin latitude in decimal degrees (WGS84). Comes from the ArcGIS World geocoder (Google as fallback) run on the origin address, kept only for street-level matches. Blank on 6 rows, which `Routing.ipynb` drops as failed geocodes. |
| Origin Dairy Longitude (Geocoded) | Origin longitude in decimal degrees (WGS84), produced the same way. |
| Destination Address Final | Text used to locate the destination: the first of these manifest fields that geocodes, in priority order: Destination Assessor Parcel Number; coordinates written in Destination Nearest Cross Street; Destination Address (tried first with cross street and county appended); a cross street naming two streets; Destination Contact Address; Hauler Address (only if the hauler text contains farm, compost or fertilizer). If none geocodes, or the manifest gives its own latitude and longitude, it is the highest-priority non-blank text. It is copied as written, so it can include names, phone numbers or a comma-separated list of APNs. Blank on 12 rows. |
| Destination Address Final Source | Name of the manifest field that `Destination Address Final` came from (e.g. `Destination Address`, `Destination Assessor Parcel Number`, `Destination Contact Address`, `Destination Nearest Cross Street`, `Hauler Address`). |
| Destination Type (Standardized) | Destination type ticked or written on the manifest, mapped by keyword: compost/kellogg/hyponex/fertilizer/supply → `Composting Facility`; farm → `Farmer`; broker → `Broker`; any other text → `Other`; blank → `Blank`. A manifest that names two types gets both, comma-separated (e.g. `Broker, Composting Facility`, 3 rows). |
| Destination Latitude (Geocoded) | Destination latitude in decimal degrees (WGS84). Taken from the manifest's own latitude/longitude if given; otherwise, for an APN, the DWR statewide parcel locator's match closest to the geocoded destination address, contact address or origin, used only when one of the APN's matches lies in a county covered by a ZIP code in the origin, destination or contact address; otherwise coordinates written in the cross-street field, or a street-level ArcGIS/Google match of the fields listed under `Destination Address Final`. Blank on 68 rows where nothing matched at street level. |
| Destination Longitude (Geocoded) | Destination longitude in decimal degrees (WGS84), produced the same way. |
| First Haul Date | Earliest date parsed from the manifest's haul-date text, formatted YYYY-MM-DD. Blank when only one date is given (567 of the 828 dated rows). |
| Last Haul Date | Latest (or only) date parsed from the haul-date text, formatted YYYY-MM-DD. Blank on 11 rows. A few parsed values fall outside 2024. |
| Is Pipeline | `True` if the manifest text mentions a pipeline or ditch (a keyword rule, checked during manual validation). `True` on 1 row; blank on 2 rows. |
| Is Trucked | Always TRUE, because all manure transport is assumed to be by truck. |
| Manure Mass per Haul (tons) | Tons per load, parsed from the manifest's "Method Used to Determine Volume of Manure" text (e.g. "42 loads x 10 tons"), or converted from cubic yards per load ÷ manure density (yd³ per ton). Blank on 719 rows. |
| Manure Number of Hauls | Number of loads, parsed from the same text. Blank on 745 rows. |
| Total Manure Amount (tons) | Total manure hauled on the record, in US short tons, as reported on the manifest, rounded to 0.1 t. Converted from cubic yards ÷ density when only a volume is reported. Filled on every row. |
| Manure Solids (%) | Solids content (%) as reported on the manifest. Values above 100 are removed. When only moisture is reported, this is 100 − moisture %. Blank on 130 rows. |
| Number of 10-ton Hauls for Analysis | One-way loaded hauls assigned to 10-ton trucks. If the manifest reports both haul size and haul count, this is the reported count when the size is 5 to under 15 t, and 0 when it is 15 t or more. Otherwise it is estimated as round(total tons × p / 10), where p ≈ 0.56 is the 10-ton bin's share of tonnage on manifests that report a haul size. A manifest of under 10 t in total is one 10-ton haul. |
| Number of 20-ton Hauls for Analysis | The same for 20-ton trucks (15 t or more per load). The estimate is round(total tons × (1 − p) / 20), and 0 for a manifest under 10 t. |

#### outputs/review/manifests/processed_wastewater_manifests.csv

Each row is one process-wastewater transport record from a manifest attached to a 2024 annual report. The file has 427 rows and 24 columns.

- **Producer:** the same notebook cells as the manure file (cells 11 and 17 of `manifest_preparation.ipynb`). `Is Trucked` comes from the validated input, and `wastewater_is_trucked()` fills it where that is blank. Only `analysis/Analysis.ipynb` reads this file, because wastewater is not routed.
- **Manuscript:**
  - the wastewater records (§2.1)
  - 914.8 million gallons, 78.3% to farmers and 21.7% blank (§3.1, Fig. 2c)
  - the transport modes: 73.3% of the volume unknown, 22.6% by pipeline and 4.1% trucked (§3.1, Fig. 2d)
  - records linked to dairies (SI 0.1.4, Fig. 5)

| Field | Description |
|---|---|
| Source PDF | File name of the annual-report PDF, without the extension. |
| Manifest Number | Position of the manifest within the PDF. A letter suffix marks several records taken from one manifest. |
| Start Page | First page of the manifest in the source PDF (counted from 1). |
| End Page | Last page of the manifest in the source PDF (counted from 1). |
| Origin Dairy Name | Exporting dairy name as written on the manifest. |
| Origin Dairy Address | Exporting dairy address as written on the manifest, filled in the same way as in the manure file. |
| Origin Dairy Latitude (Geocoded) | Origin latitude in decimal degrees (WGS84), geocoded as in the manure file. |
| Origin Dairy Longitude (Geocoded) | Origin longitude in decimal degrees (WGS84). |
| Destination Address Final | Destination text chosen with the same priority order as the manure file. Blank on 2 rows. |
| Destination Address Final Source | Name of the manifest field that `Destination Address Final` came from. |
| Destination Type (Standardized) | Same keyword mapping as the manure file (`Blank`, `Farmer`, `Broker`, `Composting Facility`, `Other`). |
| Destination Latitude (Geocoded) | Destination latitude in decimal degrees (WGS84), same method as the manure file. Blank on 7 rows. |
| Destination Longitude (Geocoded) | Destination longitude in decimal degrees (WGS84). Blank on 7 rows. |
| First Haul Date | Earliest parsed haul date, formatted YYYY-MM-DD. Blank when only one date is given. |
| Last Haul Date | Latest (or only) parsed haul date, formatted YYYY-MM-DD. Blank on 4 rows. |
| Is Pipeline | `True` if the manifest text mentions a pipeline or ditch (checked during manual validation). `True` on 131 rows; blank on 3. The analysis classes a row as Trucked if `Is Trucked` is `True`, as Pipeline if this is `True`, and as Unsure otherwise. |
| Is Trucked | `True` (22 rows), `False` (131) or `UNSURE` (274), as checked by hand in the validated file. Where that is blank, `wastewater_is_trucked()` gives `False` for pipelines, `True` when the hauler name or wastewater method mentions a load, haul or tank and not apply or applied, and `UNSURE` otherwise. |
| Wastewater Volume per Haul (Gallons) | Gallons per load, parsed from the "Method Used to Determine Volume of Wastewater" text (e.g. "247 Loads @ 9500 Gallons Per Load"). |
| Wastewater Number of Hauls | Number of loads, parsed from that text. |
| Wastewater Hours Pumped (Hours) | Pumping time in hours, parsed from that text. |
| Wastewater Pumping Rate (GPM) | Pump rate in gallons per minute, parsed from that text. |
| Total Process Wastewater Exports (Gallons) | Total wastewater exported on the record, in US gallons, as reported on the manifest. Blank on 4 rows. |
| Number of <8,000 gal Hauls for Analysis | Hauls assigned to the under-8,000-gallon bin. If both volume per haul and load count are reported, this is the reported count when the volume is under 8,000 gal (0 otherwise). If not, it is estimated as round(total gallons × p / 2,000), where p ≈ 0.31 is this bin's share of volume on manifests that report a per-haul volume. Computed for every row whatever the transport mode. The analysis does not use it. |
| Number of >=8,000 gal Hauls for Analysis | The same for the 8,000-gallon-and-over bin, estimated as round(total gallons × (1 − p) / 10,000). The analysis does not use it. |

#### outputs/review/manifests/Manifest_Formats.csv

Each row is one manifest template (form variant) found among the 2024 manifests. The file has 18 rows.

- **Producer:** compiled by hand; no script writes it. `Analysis.ipynb` cell 6 reads its descriptive columns for Table S1, which cell 7 writes to `SI_Tables.md`. Fig. S1b is drawn from `2024_manifest_template_counts.csv`.
- **Manuscript:** the attachment letter, general order, page count and file example columns of Table S1. Its `Number of manifests 2024` counts are an earlier hand tally (1,244 documents over 14 templates) and are superseded by `2024_manifest_template_counts.csv`. Table S1 leaves out `Template “name”`, `Number of manifests 2024`, `Percent of 2024 manifests`, `Notes` and `URL of template`, and drops the R5-2017-0058 General Order row, which has no 2024 manifests.

| Field | Description |
|---|---|
| Template “name” | Working name of the template (e.g. `R5-2007-0035 Alternate 1`). The column header itself contains curly quotes. |
| Template ID | Template label used in Table S1 and on the Fig. S1b bars. |
| Attachment Letter | Attachment letter of the form in its general order (`D`, `F`, `G`; `4` for CAG018001 Form 4). `N/A` or blank where there is none. |
| General Order Referenced | Water Board order printed on the form, recorded as found (`R5-2010-XXXX` and `R5-2017-0000` are kept as recorded). `N/A` or blank for forms not tied to an order. |
| Page Count | Pages per manifest in this template. |
| Number of manifests 2024 | Hand count of 2024 manifest documents that use the template. Blank where not counted. The 14 non-zero counts add up to 1,244. |
| Percent of 2024 manifests | Share of manifests, entered by hand as text (e.g. `31.20%`). The values imply a total of about 1,289 manifests, not the 1,244 that the count column adds up to. Templates with no count show `0.00%`. |
| File example | `Source PDF` name of an annual report that contains an example of the template. |
| Notes | Free-text notes on the form's regulatory basis. |
| URL of template | Link to the blank form in the published order or reporting tool, where known. |

#### outputs/review/manifests/geocode_review.csv

Each row is one manual verdict from the geocode review. It covers either one geocoded point (an origin dairy or a destination) or one routed origin–destination path. The file has 2,265 rows: 529 origin, 1,033 destination and 703 route.

- **Producer:** the browser reviewer `review/manifests/geocode-review/geocode_review.html`, which section 3 of `Manure_Manifest_Review.ipynb` generates.
  - **Writing:** after "Link CSV" is pressed, the reviewer rewrites this file a moment after each verdict. If decisions were exported instead, section 4 merges the export into the file.
  - **Applying:** section 5 reads the file and writes `Origin Geocode Correct`, `Destination Geocode Correct`, `Route Correct`, `valid route` and `validation reason` into `outputs/results/routing/processed_manure_manifests_analysis.geojson`, `od_lines_with_status.geojson` and `od_pairs_with_status.geojson`.
  - **Keys:** verdicts are keyed by address and coordinates, so they survive a re-run of `Routing.ipynb`. Rows whose key no longer matches any manifest stay in the file but have no effect.
- **Manuscript:** the manual review of every origin, destination and route (§2.3; the tool is shown in Fig. S3). Its `False` verdicts produce the "Bad Origin Geocode", "Bad Destination Geocode" and "Routing Incorrect" drops in Fig. S6 and Table S5, and so determine the 559 validated routes (§3.3).

| Field | Description |
|---|---|
| key | Join key. For points: `side\|address\|lat\|lon`, with the address lower-cased, whitespace collapsed and coordinates to 6 decimals. For routes: `route\|origin lat,lon\|destination lat,lon`. |
| side | `origin`, `destination` or `route`. |
| address | Address shown in the reviewer: `Origin Dairy Address` or `Destination Address Final`; for routes, `origin address -> destination address`. For verdicts on points no longer in the routing output, it is recovered from the key and is lower-case. On 524 such route rows it is blank. |
| lat | Latitude of the point in decimal degrees (WGS84); for route rows, the origin latitude. On the 524 route rows recovered from the key, it holds the origin as text `lat,lon`. |
| lon | Longitude of the point in decimal degrees (WGS84); for route rows, the origin longitude. On the 524 recovered route rows, it holds the destination as text `lat,lon`. |
| verdict | `True` means the geocode is correct or the route is OK. `False` means the geocode is wrong or the routing failed: 13 origin, 192 destination and 153 route rows are `False`. |
| reviewed_utc | Time the verdict was recorded, as an ISO 8601 UTC timestamp (e.g. `2026-09-26T06:10:08.163Z`). |

### Manifest extraction files (`outputs/review/manifests/`, `review/manifests/helpers/`, `data/manifests/`)

#### outputs/review/manifests/2024_files_by_template.csv

Each row is one annual-report PDF in `data/manifests/R5/<region>/<template>/original/`. There are 858 rows. The file records how many manifests the PDF holds and on which pages.

- **Producer:** cell 13 of `review/manifests/extraction/manifest_preparation.ipynb`. It lists every PDF under `original/` and counts its manifests and their pages in the PDF's OCR text with `identify_manifest_pages()`, keeping the `manifest_count`, `manifest_pages` and `detected_pages` values already in the file, so this file is both an input and an output. The same cell compares `detected_pages` against `manifest_pages` and prints page-level false-positive and false-negative rates for the detector.
- **Manuscript:** matches the manifest counts in SI Methods 0.1.1. `manifest_count` adds up to 1,226, which is 1,169 found automatically, minus 2 false positives, plus 59 missed, before duplicates are removed. The page-level detector rates are not quoted.

| Field | Description |
|---|---|
| county | Name of the data folder (`<region>`): `fresno_madera`, `kern`, `kings`, `rancho_cordova`, `tulare_east` or `tulare_west`. This is a Water Board office or area, not a single county. `rancho_cordova` covers Stanislaus, Merced, San Joaquin, Sacramento and other northern counties. |
| template | Subfolder (`<template>`) that groups the PDFs by annual-report format or consulting firm: `generic_r5`, `innovative_ag`, `cas`, `livingston`, `provost_pritchard`, `dellaville`, `full_coverage`, `ghd`, `vestra`. This is **not** the manifest template (see `Parameter Template`). |
| filename | PDF file name with its extension (`.pdf` or `.PDF`). |
| manifest_count | Number of manifests in the PDF. When the file has no value yet, it is the number of manifests that `identify_manifest_pages()` finds in the PDF's OCR text. 0 means the PDF has no manifests. |
| manifest_pages | Comma-separated page numbers (1-based) that make up the manifests. This is the reference set for the detector check. When the file has no value yet, it comes from the page ranges grouped from the OCR text. Blank when there are no manifests. |
| detected_pages | Comma-separated page numbers (1-based) flagged by the keyword detector `detect_manifest_pages_in_pdf`. The search starts at the report's "Required Attachments" list, and each page that matches a keyword is listed together with the page after it. Only recomputed when `detect_pages=True`, which takes about 6 hours. Blank when nothing was flagged. |

#### outputs/review/manifests/all_manifests_as_written_automatic.csv

Each row is one manifest record extracted automatically from the OCR text, before any manual validation. A manifest with a multi-row hauling table (template `R5-2007-0035_one_page_2`) gives one row per table row. There are 1,292 rows.

- **Producer:** cell 15 of `manifest_preparation.ipynb`, which calls `extract_manifests_from_txt()` from cell 9 on each report's text from `ocr_txt_paths()` (cell 7). It prefers `llmwhisperer_output/<stem>.txt` and falls back to `tesseract_output/<stem>.txt`. Cell 17 reads the file back and processes it without saving, and cell 23 reads its `Form Template` column. The result is the "automatic" side of the accuracy comparison.
- **Manuscript:** not quoted directly. It is the automatic input to Fig. S10 and to the accuracy figures in SI Methods 0.1.1.
- Text values are title-cased OCR output. They often contain OCR errors, for example `© Farmer` or solids values above 100.

| Field | Description |
|---|---|
| Origin Dairy Name, Origin Dairy Address | Name and address of the origin dairy, as written on the manifest (OCR). |
| Origin Dairy Latitude (Geocoded), Origin Dairy Longitude (Geocoded) | Empty placeholders. Geocoding only happens in the processed outputs. |
| Hauler Name, Hauler Address | Hauling company or person and their address, as written on the manifest. |
| Destination Name | Name of the destination, as written on the manifest. |
| Destination Contact Address | Destination contact address as written. The phone number is removed, and any text before the first number of two or more digits is dropped. |
| Destination Address | Destination address as written. The last assessor parcel number (APN) in it is cut out and, if the APN field is blank, moved to `Destination Assessor Parcel Number`. |
| Destination Nearest Cross Street | Cross-street text, as written on the manifest. |
| Destination Type | Raw text of the destination-type checkbox (Farmer, Broker, Composting Facility, …), as read by OCR. |
| Destination Type (Standardized) | Empty placeholder. |
| Destination Assessor Parcel Number | APN as written, either from the APN field or split off the address. Whitespace is removed, `.` becomes `-`, and `X`/`x` becomes `0`. Any county name is split off into `Destination County`. |
| Destination County | County name written after the APN, if there is one. |
| Destination Address Final, Destination Address Final Source | Empty placeholders. |
| Destination Latitude (Geocoded), Destination Longitude (Geocoded) | Empty placeholders. |
| Destination Latitude, Destination Longitude | Coordinates in decimal degrees, as written. Only the `CAG018001` form has these fields (11 rows). OCR sometimes drops the decimal point, e.g. `360607199.0`. |
| Haul Date | Haul date or date range, as written. |
| First Haul Date | Earliest date parsed from `Haul Date` (YYYY-MM-DD). Only filled when more than one date was parsed. Dates without a year are set to 2024. |
| Last Haul Date | Latest date parsed from `Haul Date`, or the only date (YYYY-MM-DD). |
| Is Pipeline | `True` if "pipeline" or "ditch" appears anywhere in the manifest text. |
| Is Trucked | `False` if pipeline. `True` if the hauler name or wastewater method text mentions load, haul or tank and does not mention apply or applied. Otherwise `UNSURE`. |
| Wastewater Volume per Haul (Gallons), Wastewater Number of Hauls | Gallons per load and number of loads, parsed from the wastewater method text (e.g. "60 Loads … @ 9500 Gallons Per Load"). |
| Wastewater Hours Pumped (Hours), Wastewater Pumping Rate (GPM) | Pumping hours (fractions converted to decimals) and gallons per minute, parsed from the wastewater method text. |
| Total Process Wastewater Exports (Gallons) | Total wastewater exported, in gallons, as written on the manifest. |
| Manure Mass per Haul (tons), Manure Number of Hauls | Tons per load and number of loads, parsed from the manure method text. |
| Manure Volume per Haul (cubic yards) | Cubic yards per load, parsed from the method text when the unit is yards. Empty in this file. |
| Total Manure Amount (tons) | Total manure exported, in tons, as written. For hauling-table rows, it is that row's amount. |
| Total Manure Amount (cubic yards), Manure Density | Not extracted automatically. Empty in this file. |
| Manure Solids (%) | Solids content in percent, as written. If the text reads "N % moisture", the value is moved to `Manure Moisture (%)`. Values above 100 are OCR errors (18 rows); the notebook removes such values from the validated records only. |
| Manure Moisture (%) | Moisture content in percent, as written. |
| Method Used to Determine Volume of Manure, Method Used to Determine Volume of Wastewater | Free-text method statements, as written on the manifest. |
| Parameter Template | Field layout used to read the manifest: the `parameter_template` of its `Form Template` in `review/manifests/helpers/templates.csv`, or `R5-2007-0035_general_order` when the form template is `unknown`. |
| Source PDF | File name of the annual-report PDF without its extension. |
| Start Page, End Page | Page range of the manifest in the source PDF (1-based, inclusive). |
| Manifest Number | Order of the manifest within the PDF (1…n). A letter suffix (`1a`, `1b`, …) marks each hauling-table row of a `R5-2007-0035_one_page_2` manifest. |
| County | Data-folder name (`<region>` in `data/manifests/R5/<region>/`) that holds the report's OCR text. |
| Manifest Type | `manure`, `wastewater` or `both`, depending on which of the two total-amount fields has a value. `unknown` if neither does. |
| Form Template | Form template (`template_key` in `templates.csv`) of the first row whose keywords match the manifest text and whose `page_count` is blank or equals the manifest's page count; `unknown` if none does. |

#### outputs/review/manifests/all_manifests_as_written_validated.csv

Each row is one manifest record, checked and corrected by hand against the source PDF. There are 1,293 rows, 27 of them flagged as duplicates.

- **Producer:** not written by code. This is the collaborator's hand-validated copy of the automatic extraction. Cell 17 of `manifest_preparation.ipynb` reads it, drops the duplicates, fills origin addresses from the dairy summary, geocodes the rows, backfills quantities, and writes the `processed_{manure,wastewater}_manifests.csv` that the analysis reads. Cell 23 reads it to count manifests per form template.
- **Manuscript:** the validated source behind all manifest results, through `processed_*_manifests.csv`. It is also the "manual" side of Fig. S10 and of the accuracy figures in SI Methods 0.1.1.

| Field | Description |
|---|---|
| Source PDF | File name of the annual-report PDF without its extension. |
| Street no | House number at the start of `Source PDF`, for file names that begin with an address. Blank otherwise. Spreadsheet helper, not read by the notebook. |
| Rest of PDF | `Source PDF` with the leading house number removed. Same as `Source PDF` when there is no number. Not read by the notebook. |
| County | Data-folder name (`fresno_madera`, `kern`, `kings`, `rancho_cordova`, `tulare_east`, `tulare_west`). |
| Manifest Number | Order of the manifest within the PDF. A letter suffix (`1a`, `1b`, …) marks one record per row of a multi-row hauling table. |
| Is Duplicate | `x` marks a manifest that duplicates another one (27 rows, 11 of them manifests 2–12 of `3355 Virginia Rd Wheatland 2024 Dairy AR`). Cell 17 drops these rows. |
| Start Page, End Page | Page range of the manifest in the source PDF (1-based, inclusive). |
| Manifest Type | `manure`, `wastewater`, `both` or `unknown`. |
| Origin Dairy Name, Origin Dairy Address | Origin dairy name and address, as written on the manifest (validated). |
| Hauler Name, Hauler Address | Hauler name and address, as written on the manifest (validated). |
| Destination Name | Destination name as written. Sometimes includes a phone number. |
| Destination Contact Address, Destination Address | Destination contact address and destination address, as written on the manifest (validated). |
| Destination Nearest Cross Street | Cross-street text as written. Sometimes ends with a county name. |
| Destination Assessor Parcel Number | APN or APNs as written. Sometimes followed by a county name, e.g. `015-091-045` or `0001-0001-0001-0001 Fresno`. |
| Destination County | County named next to the APN on the manifest. |
| Destination Latitude, Destination Longitude | Coordinates in decimal degrees as written on the form. Blank on every row in the current file; the collaborator's latest update removed the 11 values from `CAG018001` forms. |
| Destination Type | Destination type as written or checked on the manifest (Farmer, Broker, Composting Facility, …). |
| First Haul Date, Last Haul Date | First (only when a range is given) and last haul date, entered by hand as m/d/yy. |
| Unique Hauling Days Mentioned | Count of distinct haul dates listed on the manifest, entered by hand (29 rows). Not read by the notebook. Manifests 1–3 of `21670 W Bloss Ave, Hilmar` hold gallon-sized numbers here (1,125,000–1,440,000). Those rows have an empty wastewater total and no last haul date, so they look shifted by one column. |
| Total Process Wastewater Exports (Gallons) | Total wastewater exported, in gallons, as written on the manifest. |
| Total Manure Amount (tons) | Total manure exported, in tons, as written on the manifest. |
| Manure Solids (%), Manure Moisture (%) | Solids and moisture content in percent, as written. Processing converts moisture to solids as 100 − moisture. |
| Total Manure Amount (cubic yards) | Total manure in cubic yards, as written (13 rows). Converted to tons by dividing by `Manure Density`. |
| Manure Density | Density in cubic yards per ton, as written on the form ("yards per ton"). The only value is 1.63. |
| Method Used to Determine Volume of Manure, Method Used to Determine Volume of Wastewater | Free-text method statements, as written on the manifest. |
| Manure Number of Hauls, Manure Mass per Haul (tons), Manure Volume per Haul (cubic yards) | Number of loads, tons per load and cubic yards per load, taken from the manure method text. |
| Wastewater Volume per Haul (Gallons), Wastewater Number of Hauls | Gallons per load and number of loads, taken from the wastewater method text. |
| Wastewater Hours Pumped (Hours), Wastewater Pumping Rate (GPM) | Pumping hours and gallons per minute, taken from the wastewater method text. |
| Is Pipeline | `True` or `False`: whether the wastewater was moved by pipeline (validated). |
| Is Trucked | `TRUE`, `FALSE` or `UNSURE` on wastewater and `both` records, checked by hand; blank on the others. |
| Parameter Template | Manifest template key (see `templates.csv`). Blank for 97 rows. |
| Page Source | `automatic` (1,237 rows) or `manual` (56 rows), set by the collaborator. Not read by the notebook. |

#### outputs/review/manifests/extraction_errors_by_field.csv

Each row is one manifest field, followed by two summary rows. The value is the number of records where the automatic value disagrees with the validated value.

- **Producer:** cell 21 of `manifest_preparation.ipynb`.
- **How records are compared:**
  - Validated and automatic processed records are matched on `Source PDF` + `Manifest Number`.
  - Only rows where at least one side has a value are compared.
  - Two values agree if any libpostal spelling of one, reduced to lowercase letters and digits, equals a spelling of the other.
  - A field is listed only if it has at least 50 non-blank values on both sides. These are the same fields shown in Fig. S10.
  - `Is Trucked` is compared on wastewater records only, because every manure record is trucked on both sides.
- **Manuscript:** the correction counts in SI Methods 0.1.1. The per-field accuracy percentages in Fig. S10 come from the same comparison but are not stored here; `Analysis.ipynb` cell 6 recomputes them from these counts and the number of records compared per field.

| Field | Description |
|---|---|
| Field | Name of the manifest field (a `parameter_name` from `parameters.csv`), or one of two summary labels. `Manifests with at least one error` counts distinct records with a disagreement in any listed field. `Manifests with a result-impacting correction` does the same, but only for fields whose names contain Date, Address, Parcel, Cross Street, (tons), (Gallons) or Hauls. |
| Errors Corrected | Number of records where the automatic value had to be corrected in that field. For the summary rows, the number of distinct manifest records. |

#### outputs/review/manifests/geocode_cache.json

A geocoding cache that persists between runs. It is a single JSON object with 1,746 entries. Each key is a lookup query and each value is that query's result.

- **Producer:** cell 11 of `manifest_preparation.ipynb`, which loads the file into `cache`. `cache_put()` adds each new lookup and rewrites the whole file. Lookups happen in `geocode_address()` and `parcel_candidates()`, which run during cell 17.
- **Manuscript:** not in the manuscript. It speeds up and supports the geocoding described in SI Methods 0.1.3.

**Keys**

- **Address lookups** (1,486 keys): `"<normalized address>|<county hint>"`, written by `geocode_address()`.
  - The address is the first libpostal expansion of the input, lowercased.
  - The county hint is the lowercase data-folder name (e.g. `fresno_madera`) or the county written next to the APN (e.g. `merced`). It is left out, with its `|`, when there is none.
  - Example: `"625 east coleman avenue laton fresno 93242|fresno_madera"`.
- **Parcel lookups** (260 keys): `"parcels|<APN>"`, written by `parcel_candidates()` for each number it looks up from `Destination Assessor Parcel Number` (split at commas), with the APN as `normalize_apn()` writes it (e.g. `"parcels|015-091-045"`). `nearest_parcel()` skips numbers made only of 0s, 1s and hyphens, so the 5 such keys in the file (e.g. `"parcels|0001-0001-0001-0001"`) are not read.

**Values of address lookups:** a 3-element array `[lat, lng, meta]`.

| Element | Description |
|---|---|
| `lat`, `lng` | Latitude and longitude in decimal degrees. `geocode_address()` rounds them to 5 decimals; some cached entries hold unrounded values. `null` when the lookup failed or the match was not at street level (191 entries). |
| `meta.source` | Where the result came from:<br>• `arcgis` (1,289): ArcGIS World geocoder, limited to California<br>• `google` (162): Google geocoder, used when ArcGIS gave no street-level match<br>• `not_street_level` (21): a match coarser than a street address<br>• `not_an_intersection` (13): an intersection query that did not return a street intersection<br>• `all_failed` (1): not written by `geocode_address()` |
| `meta.address` | Matched address returned by the service. `geocode_address()` stores it with street-level `arcgis` and `google` matches; some entries with `null` coordinates also carry it, showing the coarse match (absent on 35 entries). |
| `meta.out_of_bounds` | `true` on 50 `arcgis` entries whose match fell outside the study area. Coordinates are `null`. `geocode_address()` does not write this key. |

**Values of parcel lookups:** the parcels that the DWR statewide parcel locator lists under the number, each `[lat, lng, county, parcel text]`. `parcel_candidates()` searches several spellings of the number and keeps each distinct candidate whose parcel digits begin with one of the number's digit readings. Coordinates are rounded to 5 decimals, the county is the locator's `Subregion`, and the parcel text is the APN plus the situs address when there is one (e.g. `[37.48647, -120.79195, "Stanislaus", "024009033, 519 S STORY RD, TURLOCK, CA, 95380"]`). There are 556 candidates over the 260 keys; 54 keys have an empty list (no parcel found).

#### outputs/review/manifests/Haul_Size_Breakdown.png

A 2×2 figure. It shows haul sizes and per-facility export totals from the validated, processed manifests.

- **Producer:** cell 19 of `manifest_preparation.ipynb` (200 dpi).
- **Manuscript:** not in the manuscript. It gives context for the 10-ton and 20-ton haul bins described in SI Methods 0.1.1.

**Top row: haul-size distributions**

- Left panel: manure, in tons per haul.
- Right panel: wastewater, in gallons per haul. Pipeline manifests are excluded.
- Each panel is a histogram with 10 equal-width bins. It shows each facility's mean per-haul size, using records that report both size per haul and number of hauls. The left axis is the number of facilities.
- Black dots on the right axis show the total hauls of the facilities in each bin.
- The solid line is the mean of the facility averages: 13.4 t for manure and 9,490 gal for wastewater.
- The dotted line is the mean weighted by hauls: 12.9 t for manure and 9,466 gal for wastewater.

**Bottom row: facility exports**

- Each point is one facility (`Source PDF`).
- The x-axis is total exports in tons or gallons. The y-axis is the number of manifests.
- The wastewater panel includes pipeline manifests.

#### outputs/review/manifests/2024_manifest_template_counts.csv

Each row is one manifest form template, with a final `Total` row (19 rows).

- **Producer:** cell 23 of `manifest_preparation.ipynb`. It takes one row per `Source PDF` and `Start Page` from `all_manifests_as_written_validated.csv` and gives each the `Form Template` of the automatic manifest that starts on the same page. `analysis_manifests` counts the manifests not marked `Is Duplicate`; `forms_submitted` also counts the duplicates of `CAG018001` forms.
- **Manuscript:** Table S1 (`analysis_pct`) and Fig. S1b. `analysis/Analysis.ipynb` cell 5 (Figure S1 block) draws Fig. S1b from `template_id` and `analysis_manifests`, dropping the `Total` row and templates with a count of 0, which leaves 17 templates.

| Field | Description |
|---|---|
| template_id | Form template (`template_key` in `templates.csv`), or `Total`. |
| analysis_manifests | Manifests of this template in the analysis (1,198 in all). |
| analysis_pct | Share of `analysis_manifests`, in percent. |
| forms_submitted | Manifest forms submitted of this template (1,211 in all). It differs from `analysis_manifests` only for `CAG018001` (15 forms, 2 in the analysis). |
| forms_submitted_pct | Share of `forms_submitted`, in percent. |

#### review/manifests/helpers/parameters.csv

Each row is one manifest field (40 rows). The `parameter_name` values are the column headers used in every manifest CSV.

- **Producer:** written by hand. Cell 4 of `manifest_preparation.ipynb` reads it.
- **Manuscript:** Table S2 (its Parameter Name, Data Type and Manifest Type columns).

| Field | Description |
|---|---|
| parameter_key | Identifier in snake_case used in code and in `parameter_locations.csv`, e.g. `destination_parcel_number`. |
| parameter_name | Column header used in the manifest CSVs, e.g. `Destination Assessor Parcel Number`. Units are in parentheses. |
| data_type | `text`, `numeric`, `date` or `boolean`. Controls how the column is typed (`coerce_columns`) and whether extracted values are parsed as numbers. |
| default | `NA`, or blank for `is_trucked`. Loaded but not used. |
| description | Short note, mostly blank, e.g. "Parsed from haul_date". Not read by the notebook. |
| manifest_type | `both`, `manure` or `wastewater`. Manure-only columns are dropped from the wastewater output and the other way round. |
| source | `pdf` (field on the form) or `calculation` (derived). For documentation only; not read by the notebook. |

#### review/manifests/helpers/parameter_locations.csv

Each row is one extraction rule (115 rows). A rule says where to find one field on one manifest template in the cleaned OCR text.

- **Producer:** written by hand. Cell 4 reads it, and `find_parameter_value()` in cell 9 applies it.
- **Manuscript:** not in the manuscript as a table. It is the "keyword-based text extraction based on form field titles" described in SI Methods 0.1.1.
- All text matching is case-insensitive.

| Field | Description |
|---|---|
| region | Water Board region. Always 5; not read. |
| template | `parameter_template` from `templates.csv` that the rule applies to. |
| parameter_key | Field to extract (`parameter_key` in `parameters.csv`). |
| page_search_text | Anchor text. If given, the search starts after its first occurrence, and the field is left blank if the anchor is missing. `NA` means search the whole text. |
| search_direction | Where the value sits relative to the line that matches `row_search_text`:<br>• `right`: rest of that line<br>• `right_below`: rest of the line plus the next line, unless the next line starts a new section<br>• `below`: next line<br>• `above`: previous line |
| row_search_text | Label text that finds the line: the first line containing it. |
| column_search_text | Always `NA`; not read. |
| item_order | If set, keep only the Nth word of the value (0-based). |
| ignore_before | Drop everything up to and including this text. With `below`, the field is left blank if the next line starts with this text. |
| ignore_after | One or more markers separated by `\|`. The value is cut at the earliest marker. `first_number` means the first run of 2 or more digits. |

#### review/manifests/helpers/templates.csv

Each row is one manifest form template (18 rows), with the keyword rule used to assign manifests to it and the field layout used to read them.

- **Producer:** written by hand. Cell 4 reads it, and `find_template()` in cell 9 uses it to assign each manifest's `Form Template`.
- **How a template is assigned:** rows are tested in file order and the first match wins. If nothing matches, the `Form Template` is `unknown` and the manifest is read with the `R5-2007-0035_general_order` layout.
- **Manuscript:** the template classification in SI Methods 0.1.1 that underlies Table S1. The number of distinct `layout` values among the templates with 2024 forms is `\NManifestLayouts` (14), counted by `Analysis.ipynb` cell 6.

| Field | Description |
|---|---|
| template_key | Form template identifier, e.g. `R5-2007-0035 Variant 2`. The same names are used in `2024_manifest_template_counts.csv`. |
| template_name | Readable name, e.g. "R5-2013-0122 Attachment D". Not read by the notebook. |
| keywords | Rule tested against the upper-cased, cleaned manifest text. `\|` separates alternatives, `&&` separates groups that must all match, and a group starting with `!` must be absent, e.g. `INNOVATIVE AG && !ATTACHMENT D`. |
| page_count | Number of pages the manifest must span for the template to match. Blank matches any length. |
| parameter_template | The field layout in `parameter_locations.csv` that the template shares. It is written to `Parameter Template`. |
| layout | Page layout of the template: the `template_key` of the template whose pages it matches apart from the header, otherwise its own `template_key`. The three retyped copies of Attachment D (`R5-2007-0035 Variant 1`–`3`) have `R5-2007-0035 General Order`. Not read by the extraction notebook. |

#### review/manifests/helpers/common_errors.csv

Each row is one OCR text correction (42 rows). The corrections are applied to each manifest's text before fields are extracted.

- **Producer:** written by hand. Cell 4 reads it, and `clean_common_errors()` in cell 9 applies it.
- **Manuscript:** the "common OCR errors" cleaning in SI Methods 0.1.1. Not a table.

| Field | Description |
|---|---|
| error | OCR text to replace. Leading and trailing spaces count, e.g. `" tous"`. |
| correct | Replacement text. The one row where this is blank (`"; "`) is dropped when the file is loaded, so it is never applied. |
| cs | `False`: replace regardless of case. `True`: replace the exact text, case-sensitive. |

#### review/manifests/helpers/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv

A copy of `data/tabular-data/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv` with the same 588 rows and columns, in which 71 `Source PDF` values are edited to match the annual-report file names in `data/manifests/R5/` (3 of them are blank in the original). All other values are identical.

- **Producer:** the collaborator. No code in this repository writes it.
- **Read by:** `backfill_origin_addresses()` in cell 11 of `manifest_preparation.ipynb`, run in cell 17. It looks up `Dairy Address` by the `Source PDF` name without its extension and uses it as `Origin Dairy Address` when a validated manifest's origin address is blank or names no city or ZIP code.
- **Manuscript:** not in the manuscript.

#### data/manifests/R5/ folder layout

This folder holds the source annual reports, the extracted text and the individual manifests. None of it is in git: `original/`, the three `*_output/` text folders and `all_manifests/` are all on Hugging Face (see Data download). Cell 13 of `manifest_preparation.ipynb` writes the OCR text of reports that have no `fitz_output` or `tesseract_output` file yet, cell 15 writes `manifest_<i>.txt`, and `save_manifest_pdfs()` (defined in cell 9 and run separately) writes the manifest PDFs. The counts below are for the full data set.

```
data/manifests/R5/
  <region>/                      fresno_madera | kern | kings | rancho_cordova | tulare_east | tulare_west
    <template>/                  generic_r5 | innovative_ag | cas | livingston | provost_pritchard |
                                 dellaville | full_coverage | ghd | vestra
      original/                  annual-report PDFs (858 in total)
      fitz_output/<stem>.txt
      tesseract_output/<stem>.txt
      llmwhisperer_output/<stem>.txt
    all_manifests/<pdf stem>/
      manifest_<i>.txt
      manifest_<i>.pdf
      all_manifests.pdf
```

| Path | Contents |
|---|---|
| `<region>/` | Water Board office or area folder. Same values as `county` in `2024_files_by_template.csv`. |
| `<region>/<template>/` | Annual-report format or consulting-firm folder. Same values as `template` in `2024_files_by_template.csv`. Not every folder has all three text subfolders. |
| `original/` | Source annual-report PDFs (`.pdf` or `.PDF`). The file stem is used as `Source PDF`. |
| `fitz_output/<stem>.txt` | Embedded text from PyMuPDF for the detected manifest pages, with `=== Page N ===` markers between pages (785 files). For 62 PDFs the file holds only `no_manifests_found`: the keyword detector found no manifest pages. |
| `tesseract_output/<stem>.txt` | Tesseract OCR of the same pages, with the same page markers (735 files). Settings: 350 dpi (250 dpi for scans too large at 350 dpi), orientation correction, contrast enhancement and thresholding, `--oem 1 --psm 4 -c preserve_interword_spaces=1`. |
| `llmwhisperer_output/<stem>.txt` | Text from the LLMWhisperer API (form mode, line-printer layout) with page markers (247 files). Only made when the Tesseract mean confidence is below 60, or the text contains `R5-2013-0122` or `CUBIC YARDS`. Extraction uses this file when it exists, and otherwise uses `tesseract_output`. |
| `all_manifests/<pdf stem>/` | One folder per PDF that has manifests (378 folders). |
| `manifest_<i>.txt` | Text of manifest *i* after OCR cleaning, without page markers (1,225 files). |
| `manifest_<i>.pdf` | The pages of manifest *i* (`Start Page`–`End Page`), cut from the original PDF (1,225 files). |
| `all_manifests.pdf` | All manifest pages of that PDF, joined into one file. |

### Annual-report review files (`outputs/review/annual-reports/`, `review/annual-reports/`)

#### outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv

Each row is one 2024 dairy annual report (one facility) in the 795-report analysis sample, keyed on `Source PDF`. 580 rows come from the earlier parse by Robertson et al. 2026 (`Scraped August 2026 = False`). The other 215 were scraped and hand-reviewed in this repository (`True`).

**Producer:** `review/annual-reports/scraper/apply_rows.py --write` (`Dairy_Report_Scrape_Review.ipynb` §5). The script works in three steps:
1. It rebuilds the table from `backup_before_append.csv` and repairs it from 588 to 580 rows. It drops 7 rows whose identity was overwritten with the "1008 N. Verduga Rd" letterhead and 1 exact duplicate, and fills 3 blank `Source PDF` values.
2. It appends the accepted rows from `scraped_rows.csv`, applying the corrections in `scrape_review.csv`.
3. It adds `Total Crop-Removed N` from `crop_removal_extracted.csv`.

**Read by:** `analysis/Analysis.ipynb` cells 1 and 4. `build_report_formats.py`, `geocode_dairy_addresses.py`, `scraper/crop_removal.py` and `scraper/build_review.py` also read it.

**Manuscript:** the 795-report sample (§2.1, SI 0.1.1); Figs. 3a–d, 4a (herd table converted to animal units), 5b, S5, S7d–f and S9; Table S5 (herd size of the origin dairy). It also backs values quoted in §3.1 (complete reports, herd, manure and wastewater totals), §3.2, and SI 0.1.2 and 0.1.4; the current values are in `outputs/results/Manuscript_Parameters.csv`. Rows with `Source Form Type` = `Livingston` are left out of the nitrogen accounting (Figs. 3a and 5 and the unaccounted-for total; `Analysis.ipynb` cell 3) but stay in the herd, manure and wastewater totals. Those totals count every dairy report with at least 2 cattle and a dry-manure nitrogen figure (735), and sum wastewater over the 718 that state it.

All quantities are 2024 annual totals. "Earlier-parse only" means the column is filled for the 580 Robertson et al. rows and blank for the 215 scraped rows.

| Field | Description |
|---|---|
| `Source PDF` | File name of the annual-report PDF under `data/annual-reports/<office>/<folder>/`. Unique row key. |
| `Dairy Name` | Facility name as printed on the report. For 4 scraped reports that print no name, it is taken from the PDF file name. |
| `Dairy Address` | Facility address as `<street> <city> <county> <ZIP>`, as reported; parts that are not printed are left out. For scraped rows it is built from the form's address fields. If those are missing, it falls back to the street in the file name and the county of the office folder. |
| `Milk Cows`, `Dry Cows`, `Bred Heifers`, `Heifers`, `Calves (4-6 mo.)`, `Calves (0-3 mo.)` | Average head count by herd class (head), as reported. On the standard form this is the "Average number" row of the herd table. Blank where the form has no such class; Livingston forms have no 4–6-month calf column. |
| `Total Herd Size` | Sum of the six herd classes (head). |
| `Total Manure Excreted (tons)` | Manure excreted by the herd (tons/yr), as reported. Treat it as as-excreted unless `Manure Basis` says otherwise. |
| `Total Dry Manure Generated N (lbs)` | Nitrogen in manure generated (lb N/yr), as reported ("Total nitrogen from manure"). Despite the name, this is whole-herd manure N. |
| `Total Dry Manure Generated N After Ammonia Losses (lbs)` | Manure N after the form's flat 30% ammonia loss (lb N/yr), as reported. It equals 0.70 × the previous column on every row. For scraped forms that print no value, it is calculated that way. |
| `Total Dry Manure Generated P (lbs)`, `Total Dry Manure Generated K (lbs)`, `Total Dry Manure Generated Salt (lbs)` | Phosphorus, potassium and salt in manure generated (lb/yr), as reported. Earlier-parse only. |
| `Total Process Wastewater Generated (gals)` | Process wastewater generated (US gal/yr), as reported. |
| `Total Process Wastewater Generated N (lbs)` | Nitrogen in process wastewater generated (lb N/yr), as reported. |
| `Total Process Wastewater Generated P (lbs)`, `Total Process Wastewater Generated K (lbs)`, `Total Process Wastewater Generated Salt (lbs)` | Phosphorus, potassium and salt in process wastewater (lb/yr), as reported. Earlier-parse only. |
| `Average Milk Production (lb per cow per day)` | As reported. Earlier-parse only. |
| `Applied N Dry Manure (lbs)`, `Applied P Dry Manure (lbs)`, `Applied K Dry Manure (lbs)`, `Applied Salt Dry Manure (lbs)` | Nutrients applied to the dairy's own cropland in solid manure (lb/yr), as reported in the summary of nutrient applications. Livingston N is summed over that form's per-field application pages. P, K and salt are earlier-parse only. |
| `Applied Process Wastewater N (lbs)`, `Applied Process Wastewater P (lbs)`, `Applied Process Wastewater K (lbs)`, `Applied Process Wastewater Salt (lbs)` | Nutrients applied to the dairy's own cropland in process wastewater (lb/yr), as reported. P, K and salt are earlier-parse only. |
| `Applied to Remove Ratio N`, `Applied to Remove Ratio P`, `Applied to Remove Ratio K`, `Applied to Remove Ratio Salt` | Facility-wide ratio of nutrient applied to nutrient removed by crops (unitless), as reported: "Applied to removed ratio" on the standard form, "Nitrogen Ratio" on the IAS form. Blank for Livingston rows. P, K and salt are earlier-parse only. |
| `Total Exports N (lbs)`, `Total Exports P (lbs)`, `Total Exports K (lbs)`, `Total Exports Salt (lbs)` | Nutrients exported off-site (lb/yr), as reported ("Total exports for all materials"). For scraped rows, N is set to 0 where the form states that no exports were entered. Livingston forms report exported mass only, so N = exported tons × (manure N ÷ manure tons) + exported gal × (wastewater N ÷ wastewater gal). P, K and salt are earlier-parse only. |
| `Total Applied N (lbs)`, `Total Applied P (lbs)`, `Total Applied K (lbs)`, `Total Applied Salt (lbs)` | Applied solid manure plus applied process wastewater (lb/yr). P, K and salt are earlier-parse only. |
| `Unaccounted-for N (lbs)` | After-ammonia manure N + wastewater N − `Total Applied N` − `Total Exports N` (lb N/yr). Can be negative. Counts wastewater N as a separate source, following the convention of Robertson et al. |
| `Unaccounted-for P (lbs)`, `Unaccounted-for K (lbs)`, `Unaccounted-for Salt (lbs)` | Manure generated + wastewater generated − total applied − total exports (lb/yr), with no loss term. Earlier-parse only. |
| `Average Milk Production (kg per cow)` | lb per cow per day × 0.453592, giving kg per cow **per day**. Earlier-parse only. |
| `Average Milk Production (L per cow)` | kg per cow per day × 0.971, giving L per cow **per day**. Earlier-parse only. |
| `Total Annual Milk Production (L)` | L per cow per day × (`Milk Cows` + `Dry Cows`) × 365, in L/yr. Earlier-parse only. |
| `Total Process Wastewater Generated (L)` | gal × 3.78541, in L/yr. Earlier-parse only. |
| `Ratio of Wastewater to Milk (L/L)` | Wastewater L ÷ annual milk L. Blank where either is 0. Earlier-parse only. |
| `USDA Nitrogen from Manure (lbs)` | Herd-based manure-N estimate labelled USDA (lb N/yr), carried over from Robertson et al. 2026. The computation is not in this repository. Earlier-parse only; blank where the herd is 0. |
| `Ratio of USDA N to Reported N` | `USDA Nitrogen from Manure` ÷ `Total Dry Manure Generated N`. Earlier-parse only. |
| `UCCE Nitrogen from Manure (lbs)` | Herd-based manure-N estimate (lb N/yr): head × 365 for milk and dry cows, × 133.54 for bred heifers and heifers, and × 44.51 for calves of either age (lb N per head per year). For scraped rows, `scraper/finalize.py` fills it using rates refitted from the earlier-parse rows, counting unlisted classes as 0. |
| `Ratio of UCCE N to Reported N` | `UCCE Nitrogen from Manure` ÷ `Total Dry Manure Generated N`. |
| `Manure Conversion Factor (tons per cow per year)` | `Total Manure Excreted` ÷ (`Milk Cows` + `Dry Cows` + 15/41 × [`Bred Heifers` + `Heifers` + both calf classes]), in tons per cow-equivalent per year. This formula was worked out from the data: it reproduces every filled row. Earlier-parse only. |
| `Scraped August 2026` | `True` for the 215 rows extracted and reviewed in this repository; `False` for the 580 rows from Robertson et al. 2026. |
| `Source Form Type` | Report layout the scraper read: `Standard` (Water Board form), `IAS` (Innovative Ag Services) or `Livingston` (Livingston Dairy Consulting). Blank for earlier-parse rows. |
| `Manure Basis` | Moisture basis of the form's manure tonnage: `as-excreted` (Standard, IAS) or `40pct-moisture` (Livingston). Blank for earlier-parse rows. |
| `Extraction Method` | `text` (PDF text layer) or `ocr` (Apple Vision OCR). Blank for earlier-parse rows. |
| `Extraction Notes` | Starts with `QA <PASS/WARN/FAIL>; review accepted`. Then, separated by `\|`: extraction notes (fallbacks, calculated values), `review corrected: <fields>`, and any note the reviewer wrote. Blank for earlier-parse rows. |
| `Total Crop-Removed N` | Facility-wide N removed by crops (lb N/yr): "Actual crop nutrient removal" on the standard form, "Crop Nitrogen Removal" on the IAS form. `scraper/crop_removal.py` reads it for both row sets. It is written when the page check passes (total N applied ÷ removal = printed ratio, within 0.01) or when a reviewer confirmed or corrected it; otherwise blank. Always blank for Livingston forms. |

Caveats:
- **UCCE N is stale for 19 scraped rows.** Their herd counts were corrected in review, but `apply_rows.py` does not recompute `UCCE Nitrogen from Manure` or its ratio.
- **25 scraped rows have no street in `Dairy Address`.** 3 are blank, 19 contain only `Kern`, and 3 contain a name fragment.

#### outputs/review/annual-reports/scrape_review.csv

Each row is one review decision for one report. A report with field corrections gets one row per corrected field, with its verdict and flags repeated; a report with no corrections gets one row with `field` blank. There are 1,125 rows covering 923 reports:
- 361 scraped reports with a verdict: 296 accepted, 65 unusable.
- 562 earlier-parse reports that were reviewed only for crop N removal.

**Producer:** the review page `review/annual-reports/Dairy_Report_Scrape_Review.html` (built by `scraper/build_review.py` and `scraper/review_html.py`), through its "Link CSV" or "Export decisions" button (notebook §4). **Read by:** `apply_rows.py` (§5), and by `build_review.py` to reload earlier decisions into the page. **Manuscript:** not in the manuscript; it is the record of the manual review shown in Fig. S2.

| Field | Description |
|---|---|
| `Source PDF` | Report reviewed. Key into the summary and `scraped_rows.csv`. |
| `verdict` | `accepted`, `unusable` (row left out of the summary) or blank (report reviewed only for crop N removal). The page also offers `flagged`, but no row uses it. |
| `field` | Summary column that was corrected. Blank on rows with no correction. |
| `scraped_value` | Value the scraper extracted for that field, as shown on the review page. Blank when nothing was extracted. |
| `corrected_value` | Value the reviewer entered from the PDF. Blank on a row that names a field means the reviewer cleared the value. |
| `reviewed_utc` | ISO 8601 UTC time the decision was recorded or exported. |
| `note` | Free-text reason for a later correction (2 distinct notes, on 29 rows). |
| `ratio_ok` | `1` when the reviewer checked the facility-wide applied-to-removed N ratio against the PDF; otherwise blank. |
| `form_type` | Report layout confirmed by the reviewer, which would override the detector. Blank on every row of this file. |
| `crop_ok` | `1` when the reviewer confirmed `Total Crop-Removed N` against the PDF page; otherwise blank. |

#### outputs/review/annual-reports/Annual_Report_Formats.csv

Each row is one row of the report summary (795 rows, same order, keyed on `Source PDF`), giving the report form that dairy filed.

**Producer:** `review/annual-reports/build_report_formats.py` (notebook §5b). It classifies every PDF under `data/annual-reports/` with `scraper/detect.py`, scanning the first 25 pages. It then links files to summary rows by file name in three passes: exact token match, then close-string match, then street-number match. **Read by:** `Analysis.ipynb` cell 6, and `scraper/crop_removal.py` to pick the Standard and IAS reports. **Manuscript:** Fig. S1a; the "4 types of annual reports" and "690 (87%) used the standard Water Board form … remaining 105 used a consultant format" in §3.1; the 4 annual-report formats in Fig. 1a.

| Field | Description |
|---|---|
| `Source PDF` | Summary row key. |
| `Form Type` | Values: `Standard form` (692), `Innovative Ag Services form` (83), `Livingston Dairy Consulting form` (18), and `Standard + Innovative Ag Services` (2; a packet with both standard pages and IAS markers). |
| `Source` | How `Form Type` was decided. `detector` (760): form markers were found in the matched PDF. `report summary` (20): the detector found nothing, so the summary's `Source Form Type` was used. `earlier parse inclusion criterion` (15): no PDF was matched, so the row is assigned `Standard form` because Robertson et al. admitted only standard-form reports. |
| `Consultant` | Consultant firm named in the first 25 pages of the matched PDF: `IAS`, `Livingston` or blank. |
| `Has Standard Pages` | `1` if standard-form markers ("General Order No. R5-2007-0035", "DAIRY FACILITY INFORMATION", "AVAILABLE NUTRIENTS") appear in the first 25 pages, else `0`. Blank when no file was matched. |
| `Scanned Image Only` | `1` if none of the first 25 pages has a text layer, else `0`. Also `0` when no file was matched. |
| `Matched File` | File name of the PDF linked to the row. May differ in spelling from `Source PDF` (81 rows). Blank for the 15 unmatched rows. |

#### outputs/review/annual-reports/Dairy_Report_Geocodes.csv

Each row is one row of the report summary as it stood when geocoded (797 rows, built 30 Aug 2026), with coordinates for its `Dairy Address`. It is a CSV with point coordinates in `lon`/`lat` (decimal degrees), which `Analysis.ipynb` reads as EPSG:4326.

**Producer:** `review/annual-reports/geocode_dairy_addresses.py`, run on its own because it needs the network. It tries the US Census batch geocoder, then the Census one-line geocoder, then Nominatim. **Read by:** `Analysis.ipynb` cell 6, joined on `Source PDF`. **Manuscript:** Fig. 4a and "Of 795 dairies, 767 were geocoded" (SI 0.1.1).

| Field | Description |
|---|---|
| `Source PDF`, `Dairy Name`, `Dairy Address` | Copied from the report summary at build time. |
| `street_parsed` | Street part of `Dairy Address`, with ZIP, county and city removed. |
| `city_parsed` | City: the longest trailing match to a 2024 Census place name, otherwise the last non-street word. Blank if none. |
| `zip_parsed` | 5-digit ZIP found in the address. Blank if none. |
| `county_parsed` | California county name removed from the end of the address. Blank if none. |
| `lat`, `lon` | Latitude and longitude in decimal degrees. Blank when there was no match, the point fell outside California's bounding box, or a Nominatim hit landed outside the city or county the address names. |
| `matched_address` | Address string returned by the geocoder (Census matched address or Nominatim display name). It is kept for 9 rejected Nominatim hits whose coordinates were cleared. |
| `match_precision` | `Exact` or `Non_Exact` (Census batch; `Non_Exact` means the house number was interpolated along the block), `oneline` (Census one-line endpoint), or `osm_<addresstype>` (Nominatim, e.g. `osm_road` for a road-centreline hit, `osm_place`). Blank when no match was accepted. |
| `provider` | `census_batch`, `census_oneline`, `nominatim` or blank. |

Caveat: this file was built from an earlier version of the summary, so it no longer lines up exactly:
- It has 3 `Source PDF` values that are not in the current summary, and lacks 1 current row (Open Sky Dairy).
- 27 addresses differ from the current summary.
- The manuscript's 767 geocoded dairies are counted over this file's 797 rows; 765 of the current 795 rows have coordinates.

#### review/annual-reports/backup_before_append.csv

Each row is one annual report from Robertson et al. 2026's parse (588 rows × 56 columns): the state of the summary before any scraped rows were added.

**Producer:** `apply_rows.py --write` copies the summary to this file on its first run and never overwrites it. **Read by:** `apply_rows.py` (the baseline every rebuild starts from), `build_review.py` (duplicate check), `finalize.py` (fits the UCCE rates) and `coverage.py` (the "BEFORE" figures in notebook §6).

**How it relates to `data/tabular-data/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv`:** same rows, same columns, same values. The only differences are formatting: herd counts are written as `425.0` rather than `425`, and 3 floats differ in their last printed digit.

It still contains the defects that `apply_rows.py` repairs:
- 7 rows with `Source PDF` "1008 N. Verduga Rd, Turlock 2024 Dairy AR.pdf" whose identity fields were overwritten.
- 2 identical rows for "26290 S Union Rd Manteca 2024 Dairy AR.pdf".
- 3 rows with a blank `Source PDF`.

**Manuscript:** not cited directly; 580 of its rows make up the earlier-parse part of the analysis sample.

| Field | Description |
|---|---|
| `Source PDF`, `Dairy Name`, `Dairy Address` | Report file name, facility name and address, as in the summary. |
| `Milk Cows`, `Dry Cows`, `Bred Heifers`, `Heifers`, `Calves (4-6 mo.)`, `Calves (0-3 mo.)`, `Total Herd Size` | Average head counts by class, and their sum (head). |
| `Total Manure Excreted (tons)`, `Total Dry Manure Generated N (lbs)`, `Total Dry Manure Generated N After Ammonia Losses (lbs)`, `Total Dry Manure Generated P (lbs)`, `Total Dry Manure Generated K (lbs)`, `Total Dry Manure Generated Salt (lbs)` | Manure generated (tons/yr) and its nutrients (lb/yr), as reported. |
| `Total Process Wastewater Generated (gals)`, `Total Process Wastewater Generated N (lbs)`, `Total Process Wastewater Generated P (lbs)`, `Total Process Wastewater Generated K (lbs)`, `Total Process Wastewater Generated Salt (lbs)` | Wastewater generated (gal/yr) and its nutrients (lb/yr), as reported. |
| `Average Milk Production (lb per cow per day)` | As reported. |
| `Applied N Dry Manure (lbs)`, `Applied P Dry Manure (lbs)`, `Applied K Dry Manure (lbs)`, `Applied Salt Dry Manure (lbs)`, `Applied Process Wastewater N (lbs)`, `Applied Process Wastewater P (lbs)`, `Applied Process Wastewater K (lbs)`, `Applied Process Wastewater Salt (lbs)` | Nutrients applied on the dairy's own land (lb/yr), as reported. |
| `Applied to Remove Ratio N`, `Applied to Remove Ratio P`, `Applied to Remove Ratio K`, `Applied to Remove Ratio Salt` | Facility-wide applied-to-removed ratios (unitless), as reported. |
| `Total Exports N (lbs)`, `Total Exports P (lbs)`, `Total Exports K (lbs)`, `Total Exports Salt (lbs)` | Exports (lb/yr), as reported. |
| `Total Applied N (lbs)`, `Total Applied P (lbs)`, `Total Applied K (lbs)`, `Total Applied Salt (lbs)` | Applied solid manure + applied wastewater (lb/yr). |
| `Unaccounted-for N (lbs)`, `Unaccounted-for P (lbs)`, `Unaccounted-for K (lbs)`, `Unaccounted-for Salt (lbs)` | Nutrient balance residuals (lb/yr), defined as in the summary. |
| `Average Milk Production (kg per cow)`, `Average Milk Production (L per cow)`, `Total Annual Milk Production (L)`, `Total Process Wastewater Generated (L)`, `Ratio of Wastewater to Milk (L/L)` | Unit conversions and the wastewater-to-milk ratio. Per-cow values are per day. Formulas as in the summary. |
| `USDA Nitrogen from Manure (lbs)`, `Ratio of USDA N to Reported N`, `UCCE Nitrogen from Manure (lbs)`, `Ratio of UCCE N to Reported N`, `Manure Conversion Factor (tons per cow per year)` | Herd-based N estimates, their ratios to reported N, and the manure conversion factor, as in the summary. |

#### review/annual-reports/scraped_rows.csv

Each row is one scraped report (361 rows): the 360 reports in `list_targets.txt` plus the Verduga report that `finalize.py` scrapes separately. Values are as extracted and post-processed, **before** review corrections.

**Producer:** `scraper/build_review.py`, run as `main("results_final.pkl")` (notebook §3); `Total Crop-Removed N` is joined from `crop_removal_extracted.csv`. **Read by:** `apply_rows.py`. Of the 361 rows, 215 were appended to the summary, 65 were marked unusable, and 81 accepted rows were held back as duplicate risks. **Manuscript:** not in the manuscript.

| Field | Description |
|---|---|
| `Source PDF` | Report file name (unique). |
| `_grade` | Automatic QA grade from `pipeline.qa`: `FAIL`, `WARN` or `PASS`. `FAIL` means the herd total does not match the sum of classes, after-ammonia N ≠ 0.70 × gross N, or a required field is missing. `WARN` means a per-head or per-ton ratio falls outside the 5th–95th-percentile band of the 588 existing rows, applied N plus exports exceeds available N, or the manure basis is not as-excreted. |
| `_form` | Layout read: `Standard`, `IAS`, `Livingston` or `ProvostPritchard`. |
| `_method` | `text` or `ocr`. |
| `_duplicate_risk` | `street <key> already in the CSV` when the house number plus the next two words of the address match a row of `backup_before_append.csv`. `apply_rows.py` holds such rows back unless run with `--include-duplicates`. |
| `_name_note` | Advisory only: the row has the same normalized name as an existing row but a different address. |
| `_basis` | Per-row override of the manure basis: `asae-total-solids` for the 6 Provost & Pritchard rows, which are read from the ASAE D384.2 whole-herd table. Blank means the form's default basis. |
| `_notes` | Extraction notes, separated by `\|`. |
| `Dairy Name`, `Dairy Address`, `Milk Cows`, `Dry Cows`, `Bred Heifers`, `Heifers`, `Calves (4-6 mo.)`, `Calves (0-3 mo.)`, `Total Herd Size`, `Total Manure Excreted (tons)`, `Total Dry Manure Generated N (lbs)`, `Total Dry Manure Generated N After Ammonia Losses (lbs)`, `Total Process Wastewater Generated (gals)`, `Total Process Wastewater Generated N (lbs)`, `Applied N Dry Manure (lbs)`, `Applied Process Wastewater N (lbs)`, `Total Exports N (lbs)`, `Total Applied N (lbs)`, `Unaccounted-for N (lbs)`, `UCCE Nitrogen from Manure (lbs)`, `Ratio of UCCE N to Reported N`, `Applied to Remove Ratio N`, `Total Crop-Removed N` | Same meanings and units as the summary columns of the same name, with pre-review values. |

#### review/annual-reports/crop_removal_extracted.csv

Each row is one summary report filed on the Standard or IAS form according to `Annual_Report_Formats.csv` (775 rows: 580 from the earlier parse, 195 scraped), with its facility-wide crop N removal and the check on it.

**Producer:** `scraper/crop_removal.py` (notebook §2b), which also renders the source page into `crops/`. **Read by:** `apply_rows.py`, which fills the summary's `Total Crop-Removed N`, and `build_review.py`. **Manuscript:** source of the crop-removed N used for nitrogen pressure (§2.2, §3.2, SI 0.1.2; Figs. 3b, 3d and S5), through the summary column.

| Field | Description |
|---|---|
| `Source PDF` | Summary row key. |
| `Dairy Name` | From the summary. |
| `Form Type` | From `Annual_Report_Formats.csv`: `Standard form`, `Innovative Ag Services form` or `Standard + Innovative Ag Services`. |
| `Set` | `scraped` (scraped in this repository) or `earlier parse` (Robertson et al. 2026). |
| `Reader` | Page reader that found the value: `Standard` or `IAS`. Blank when no page was found. |
| `Method` | `text` or `ocr` (only the relevant page is OCR'd). Blank when there is no PDF. |
| `Page` | 1-based page number the value was read from. |
| `Total Crop-Removed N` | Facility-wide crop N removal (lb N/yr): "Actual crop nutrient removal" on the standard form, "Crop Nitrogen Removal" on the IAS form. |
| `Total N Applied (all sources)` | Total N applied from all sources, printed on the same page (lb N/yr): "Total nutrients applied" on the standard form, "Total Nitrogen Applied" on the IAS form. |
| `Printed Ratio` | Applied-to-removed N ratio printed on that page (unitless). |
| `Summary Ratio` | `Applied to Remove Ratio N` from the summary at run time. |
| `Ratio Agrees` | `True` when \|`Printed Ratio` − `Summary Ratio`\| ≤ 0.01. Blank when either is missing. |
| `Status` | `check passes` (720): \|total applied ÷ removal − printed ratio\| ≤ 0.01. The other values are `zero removal` (29), `no PDF` (15), `page not found` (6), `removal not read` (3) and `check unavailable` (2). `check fails` is possible but does not occur. |
| `Crop File` | JPEG of the page in `review/annual-reports/crops/`. |
| `Source Path` | Absolute path of the PDF at run time, under its original OneDrive folder. `pipeline.local_pdf` maps it to `data/annual-reports/`. |
| `Pages` | Page count of the PDF. |
| `Notes` | `read by OCR`, `IAS summary page used` or `Standard summary page used` (for combined packets), a printed ratio that disagrees with the summary's, or a read error. |

#### review/annual-reports/results.pkl, review/annual-reports/results_final.pkl

Each is a Python `list` of dicts, one per scraped report. `results.pkl` holds 360 records: the raw output of `scraper/run_extract.py` (notebook §1), one per line of `list_targets.txt`. `results_final.pkl` holds 361: the same records after `scraper/finalize.py` (§2), plus the Verduga report scraped fresh. `finalize.py` makes these changes:
- Switches Provost & Pritchard rows to the ASAE table.
- Sets blank exports to 0 where the form states there were none.
- Recomputes the calculated N fields.
- Adds UCCE N.
- Re-grades every record.

`results_final.pkl` is read by `crop_removal.py` and `build_review.py`. **Manuscript:** not in the manuscript.

| Field | Description |
|---|---|
| `path` | Absolute path of the PDF when it was scraped (original OneDrive folder; mapped to `data/annual-reports/` by `pipeline.local_pdf`). |
| `Source PDF` | PDF file name. |
| `status` | `ok`, `missing`, `unreadable`, `error` or `exception`. All records are `ok` in the shipped files. |
| `row` | Dict mapping summary column names to extracted values (herd counts as `int`, others as `float` or `str`). Keys: `Dairy Name`, `Dairy Address`, the six herd classes, `Total Herd Size`, `Total Manure Excreted (tons)`, `Total Dry Manure Generated N (lbs)`, `Total Dry Manure Generated N After Ammonia Losses (lbs)`, `Total Process Wastewater Generated (gals)`, `Total Process Wastewater Generated N (lbs)`, `Applied N Dry Manure (lbs)`, `Applied Process Wastewater N (lbs)`, `Applied to Remove Ratio N`, `Total Exports N (lbs)`, `Total Applied N (lbs)`, `Unaccounted-for N (lbs)`. `results_final.pkl` adds `UCCE Nitrogen from Manure (lbs)` and `Ratio of UCCE N to Reported N`. A key is missing when nothing was found. Units are as in the summary. |
| `meta.form` | `Standard`, `IAS`, `Livingston` or `ProvostPritchard`. |
| `meta.method` | `text` or `ocr`. |
| `meta.n_pages` | Page count of the PDF. |
| `meta.pages` | Dict mapping a section tag to its 1-based page number. Standard: `herd`, `nutrients`, `applied`, `exports`. IAS: `attachment_a` (herd and generated), `attachment_b` (applications), `attachment_c` (exports). Livingston: `herd`, `nutrients`, `exports`. Provost & Pritchard: `identity`, `herd`, `generated`, `applied`, `exports`, plus `asae` in `results_final.pkl`. |
| `meta.notes` | List of extraction notes (these become `Extraction Notes`). |
| `meta.grade`, `meta.fails`, `meta.warns` | QA grade (`PASS`/`WARN`/`FAIL`) and the lists of failure and warning reasons. |
| `meta.ratios` | Plausibility ratios: `tons_per_head` (tons manure per head), `n_per_ton` (lb N per ton), `n_per_head` (lb N per head), `wwn_per_kgal` (lb wastewater N per 1,000 gal). |
| `meta.basis_override` | `results_final.pkl` only: `asae-total-solids` on the 6 Provost & Pritchard records. |
| `meta.Source PDF`, `meta.path` | Copies of the top-level values. |
| `error`, `meta.error` | Present only on failed records; there are none in the shipped files. |

#### review/annual-reports/list_targets.txt

Each line is the path of one annual-report PDF, relative to the repository root (`data/annual-reports/<office>/<folder>/<file>`). Together the 360 lines are the candidate reports not covered by the earlier parse, which the scraper reads.

By office: Fresno Madera 19, Kern 26, Kings 30, Rancho Cordova 110, Tulare East 125, Tulare West 50. By folder: 269 in `Consulting_and_Error_Causing_Forms`, 91 in `Correct_Forms`. All 360 files are present.

**Producer:** an input list; no script in the repository writes it. **Read by:** `scraper/run_extract.py` (notebook §1). The Verduga report is not listed; `finalize.py` scrapes it directly. **Manuscript:** not in the manuscript.

| Field | Description |
|---|---|
| (one path per line) | PDF path relative to the repository root. Blank lines are skipped. |

### Input data (`data/`)

#### data/tabular-data/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv

This is the earlier parse of 2024 Region 5 dairy annual reports by Robertson et al. 2026 [20]. Each of the 588 rows is one annual report on the standard Water Board form (Order R5-2007-0035).

- **Producer:** external (Robertson et al. 2026). No code in this repository writes it.
- **Read by:**
  - `review/manifests/helpers/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv` is a copy with 71 `Source PDF` names edited to match the PDF file names. `manifest_preparation.ipynb` reads that copy, not this file.
  - `review/annual-reports/backup_before_append.csv` is a copy with identical values. `scraper/apply_rows.py` rebuilds `outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv` from that copy. It drops the 7 broken rows and 1 duplicate described below, then appends 215 newly scraped reports. `scraper/finalize.py` fits its UCCE per-head factors on the same copy. The analysis reads the extended file, not this one.
- **Manuscript:** this is the source of the "580 dairies parsed by Robertson et al 2026" in §2.1 and SI Methods 0.1.1 (588 rows − 7 − 1 = 580). It is not cited as a table.
- **Known defects:**
  - 7 rows reuse `Source PDF` = `1008 N. Verduga Rd, Turlock 2024 Dairy AR.pdf`, have `Dairy Name` = "CENTRAL VALLEY REGION" and have no address.
  - The 2 rows for `26290 S Union Rd Manteca 2024 Dairy AR.pdf` are identical (one is a duplicate).
  - 3 rows have no `Source PDF`.
  - 42 rows have a herd of 0 and `Total Manure Excreted` = 1.
- **How the derived columns were checked:** "as reported" means the value is copied from the report. Derived columns were computed by Robertson et al. The formulas given below reproduce every non-blank value. The sources of their factors are not documented in this repository.

| Field | Description |
|---|---|
| Source PDF | File name of the report PDF. 497 of the 578 distinct values match a file under `data/annual-reports/` exactly. |
| Dairy Name | Facility name, as reported |
| Dairy Address | Address formatted `<street> <city> <county> <ZIP>`, as reported. Blank in 7 rows. |
| Milk Cows, Dry Cows, Bred Heifers, Heifers, Calves (4-6 mo.), Calves (0-3 mo.) | Average head count by herd class, from the form's herd table (head) |
| Total Herd Size | Sum of the six herd classes (head) |
| Total Manure Excreted (tons) | "Total manure excreted by the herd", as reported (US tons/yr, as excreted) |
| Total Dry Manure Generated N (lbs) | "Total nitrogen from manure", as reported (lb N/yr) |
| Total Dry Manure Generated N After Ammonia Losses (lbs) | "After ammonia losses (30% loss applied)", as reported (lb N/yr). Equals 0.70 × the column above. |
| Total Dry Manure Generated P (lbs), Total Dry Manure Generated K (lbs), Total Dry Manure Generated Salt (lbs) | P, K and salt in manure generated, as reported (lb/yr) |
| Total Process Wastewater Generated (gals) | "Process wastewater generated", as reported (US gal/yr). 81 rows are 0 and 1 is negative. |
| Total Process Wastewater Generated N (lbs), Total Process Wastewater Generated P (lbs), Total Process Wastewater Generated K (lbs), Total Process Wastewater Generated Salt (lbs) | Nutrients in the process wastewater generated, as reported (lb/yr) |
| Average Milk Production (lb per cow per day) | As reported (lb/cow/day) |
| Applied N Dry Manure (lbs), Applied P Dry Manure (lbs), Applied K Dry Manure (lbs), Applied Salt Dry Manure (lbs) | Manure nutrients applied to the dairy's own cropland, as reported (lb/yr) |
| Applied Process Wastewater N (lbs), Applied Process Wastewater P (lbs), Applied Process Wastewater K (lbs), Applied Process Wastewater Salt (lbs) | Wastewater nutrients applied to the dairy's own cropland, as reported (lb/yr) |
| Applied to Remove Ratio N, Applied to Remove Ratio P, Applied to Remove Ratio K, Applied to Remove Ratio Salt | The form's "Applied to removed ratio": nutrient applied from all sources divided by crop removal, as reported (unitless) |
| Total Exports N (lbs), Total Exports P (lbs), Total Exports K (lbs), Total Exports Salt (lbs) | "Total exports for all materials", as reported (lb/yr) |
| Total Applied N (lbs), Total Applied P (lbs), Total Applied K (lbs), Total Applied Salt (lbs) | Derived: applied dry manure + applied process wastewater (lb/yr). Fertilizer is not included. |
| Unaccounted-for N (lbs) | Derived: manure N after ammonia losses + wastewater N − Total Applied N − Total Exports N (lb/yr). Negative in 67 rows. |
| Unaccounted-for P (lbs), Unaccounted-for K (lbs), Unaccounted-for Salt (lbs) | Derived: manure generated + wastewater generated − total applied − total exports, with no loss factor (lb/yr) |
| Average Milk Production (kg per cow) | Derived: lb/cow/day × 0.453592 (kg per cow per day) |
| Average Milk Production (L per cow) | Derived: kg/cow/day × 0.971 (L per cow per day) |
| Total Annual Milk Production (L) | Derived: L/cow/day × (Milk Cows + Dry Cows) × 365 (L/yr) |
| Total Process Wastewater Generated (L) | Derived: gal × 3.78541 (L/yr) |
| Ratio of Wastewater to Milk (L/L) | Derived: wastewater L / annual milk L. Blank in the 126 rows where either value is ≤ 0. |
| USDA Nitrogen from Manure (lbs) | Derived: Total Manure Excreted × 12.92 lb N/ton (lb N/yr). Blank in the 42 zero-herd rows. |
| Ratio of USDA N to Reported N | Derived: USDA N / Total Dry Manure Generated N |
| UCCE Nitrogen from Manure (lbs) | Derived: 365 × (milk + dry cows) + 133.54 × (bred heifers + heifers) + 44.51 × (both calf classes) (lb N/yr). Blank in the zero-herd rows. |
| Ratio of UCCE N to Reported N | Derived: UCCE N / Total Dry Manure Generated N |
| Manure Conversion Factor (tons per cow per year) | Derived: Total Manure Excreted / (milk + dry cows + 0.36585 × all heifers and calves) (tons per cow-equivalent per year) |

**Citation:** Robertson Z, Lehmann E, Zerbe A, Bick I A and Sivas D A 2026, *Confined Animal Facility Permitting and Reporting Under the Porter-Cologne Water Quality Control Act*, Stanford ENRLP [20].

#### data/tabular-data/EMFAC2025ER-EMFAC202YClass-SanJoaquinValleyAPCD-2024-Annual-20260827132803.csv

This is the raw CARB EMFAC2025 (v2.1.1) Emission Rates export. Settings: region type Air District; San Joaquin Valley APCD; calendar year 2024; Annual season; EMFAC202Y categories; exported 27 Aug 2026. Each of the 52 rows is one diesel vehicle category, aggregated over all model years and speeds.

- **Format:** the file opens with 7 metadata lines and a blank line, so read it with `skiprows=8`.
- **Producer:** CARB EMFAC web tool.
- **Read by:** no code reads it. It is the documented source of `EMFAC_Rates_2024.csv`.
- **Manuscript:** ref [40]. It underlies the rates quoted in SI Methods 0.1.3.

| Field | Description |
|---|---|
| Region | "San Joaquin Valley APCD" |
| Calendar Year | 2024 |
| Vehicle Category | EMFAC202Y vehicle category. The analysis uses `T7 Single Dump Class 8` and `T7 Tractor Class 8`. |
| Model Year | "Aggregate" (all model years) |
| Speed | "Aggregate" (all speeds) |
| Fuel | "Diesel" |
| Population | Vehicle population (vehicles) |
| Total VMT, CVMT, EVMT | Total, combustion and electric vehicle-miles travelled (miles/day) |
| Trips | Trips per day |
| NOx_RUNEX, PM2.5_RUNEX, PM10_RUNEX, CO2_RUNEX, CH4_RUNEX, N2O_RUNEX, ROG_RUNEX, TOG_RUNEX, NH3_RUNEX, CO_RUNEX, SOx_RUNEX | Running-exhaust emission rates (g/mile) |
| NOx_IDLEX, PM2.5_IDLEX, PM10_IDLEX, CO2_IDLEX, CH4_IDLEX, N2O_IDLEX, ROG_IDLEX, TOG_IDLEX, CO_IDLEX, SOx_IDLEX | Idle-exhaust emission rates (g/vehicle/day) |
| NOx_STREX, PM2.5_STREX, PM10_STREX, CO2_STREX, CH4_STREX, N2O_STREX, ROG_STREX, TOG_STREX, CO_STREX, SOx_STREX | Start-exhaust emission rates (g/trip) |
| PM2.5_PMTW, PM10_PMTW | Tire-wear particulate (g/mile) |
| PM2.5_PMBW, PM10_PMBW | Brake-wear particulate (g/mile) |
| ROG_HOTSOAK, TOG_HOTSOAK, ROG_RUNLOSS, TOG_RUNLOSS | Hot-soak and running-loss evaporative emissions (g/trip) |
| ROG_DIURN, TOG_DIURN | Diurnal evaporative emissions (g/vehicle/day) |

**Citation:** California Air Resources Board, EMFAC2025 v2.1.1 [40] (https://arb.ca.gov/emfac/).

#### data/tabular-data/EMFAC_Rates_2024.csv

These are the per-mile rates used by the analysis. Each row is one truck class: `10t` (10-ton hauls) and `20t` (20-ton hauls).

- **Producer:** no script in the repository writes this file. Every rate equals the matching row of the EMFAC export above to full precision, and `gal_per_mi` equals `CO2_g_per_mi / co2_g_per_gal`.
- **Read by:**
  - `analysis/Analysis.ipynb` cell 1. It multiplies the rates by per-edge truck-miles to get `PM2.5_emissions`, `NOx_emissions`, `ROG_emissions`, `diesel_gal` and `CO2_kg`, and prints the summary totals.
  - `analysis/Analysis.ipynb` cell 3, `aggregate_exposure()`. It produces `PM2.5_g_j`, `NOx_g_j` and `ROG_g_j` in `BlockGroup_Exposure.csv`.
- **Manuscript:**
  - Rates quoted in SI Methods 0.1.3: NOx 1.21/1.47 g/mi, CO2 1,621.27/1,497.15 g/mi, PM2.5 0.0516/0.0545 g/mi, 6.29/6.81 mpg.
  - Totals in §3.3: 118.8 kg PM2.5, 2,909.4 kg NOx, 353,376 gal diesel, 3,601 t CO2.
  - The diesel figure is repeated in §4.

| Field | Description |
|---|---|
| class | Truck class key (`10t` or `20t`), used as the index |
| emfac_category | EMFAC202Y category the class is mapped to: `T7 Single Dump Class 8` or `T7 Tractor Class 8` |
| gal_per_mi | Diesel use (gal/mile) = CO2_g_per_mi / co2_g_per_gal |
| CO2_g_per_mi | CO2_RUNEX (g/mile) |
| NOx_g_per_mi | NOx_RUNEX (g/mile) |
| PM25_g_per_mi | PM2.5_RUNEX + PM2.5_PMTW + PM2.5_PMBW (g/mile) |
| ROG_g_per_mi | ROG_RUNEX (g/mile) |
| NOx_g_per_veh_day_idle | NOx_IDLEX (g/vehicle/day). Not used by the analysis. |
| emfac_version | "EMFAC2025 v2.1.1, Emission Rates" |
| region | "San Joaquin Valley APCD" |
| calendar_year | 2024 |
| season | "Annual" |
| fuel | "Diesel" |
| model_year | "Aggregate" |
| speed | "Aggregate" |
| pm25_components | Processes summed into PM25_g_per_mi ("RUNEX+PMTW+PMBW") |
| co2_g_per_gal | 10,190 g CO2 per gallon of diesel |
| co2_g_per_gal_source | Citation for co2_g_per_gal (EIA CO2 emissions coefficients, distillate fuel oil) |
| source_export | File name of the EMFAC export the rates were taken from |

**Citation:** CARB EMFAC2025 [40]; US EIA CO2 coefficients [63].

#### data/tabular-data/zipcode_to_county.csv

This is a California ZIP-code-to-county table. Each of the 1,801 rows is one California ZIP code.

- **Producer:** external. The source is not recorded in the repository. The columns match the SimpleMaps US ZIP Codes database (https://simplemaps.com/data/us-zips), cut to California rows with the state, ZCTA, timezone and flag columns removed.
- **Read by:** `review/manifests/extraction/manifest_preparation.ipynb` cell 11. It reads only `zip` and `county_names_all`. `zip_counties()` lists the counties covered by the ZIP codes in a manifest's origin, destination and contact addresses, and `nearest_parcel()` accepts an APN only if one of its parcels lies in one of them. The set of all county names builds `COUNTY_SUFFIX_RE`, which strips a trailing "<county>" or "<county> County" from intersection-style destination addresses in `format_intersection()`.
- **Manuscript:** not in the manuscript.

| Field | Description |
|---|---|
| zip | 5-digit ZIP code (read as text) |
| lat | ZIP latitude (decimal degrees), as published |
| lng | ZIP longitude (decimal degrees), as published |
| city | City name, as published |
| population | Estimated population (persons), as published |
| density | Population per km², as published |
| county_fips | FIPS code (state + county) of the primary county. The leading zero is dropped, e.g. `6037`. |
| county_name | Primary county name. Not used by the code. |
| county_weights | JSON object mapping 5-digit county FIPS to the percent of the ZIP's population in that county |
| county_names_all | All counties the ZIP falls in, separated by "\|". With `zip`, the only field the code uses. |
| county_fips_all | Their FIPS codes, separated by "\|". Single-county rows lost the leading zero. |

**Attribution (if SimpleMaps):** the Basic database is licensed CC BY 4.0. Credit "SimpleMaps.com, US Zip Codes Database" with a link to https://simplemaps.com/data/us-zips.

#### data/geospatial-data/CA_Water_Board_Boundary/CentralValleyRegionalWaterBoard_EPSG4326.geojson

This is the study-area boundary: one MultiPolygon feature for the Central Valley Regional Water Quality Control Board (Region 5). CRS is EPSG:4326.

- **Source:** California State Water Resources Control Board, "Regional Board Boundaries" feature service [39]. The Region 5 polygon was saved in EPSG:4326.
- **Read by:**
  - `analysis/Routing.ipynb` cell 1:
    - clips the road graph to the boundary plus a 25 km buffer, but only when it builds the pickle;
    - `filter_od_to_boundary()`;
    - validation check 2, "Outside water board".
  - `analysis/Analysis.ipynb`:
    - cell 1: wastewater origin/destination check, and the Figure S8 outline and city clipping;
    - cell 3: block groups and places are kept when more than 50% of their area is inside;
    - cell 6: Figure 4a–c outline.
- **Manuscript:** Figure S6 (the "outside the Water Board" drop), Figures 4 and S8, Tables S8–S10, and §3.3 (the 4,851 block groups).

| Field | Description |
|---|---|
| objectid | Feature ID from the source layer (5) |
| rb | Regional board number (5) |
| rb_name | "Central Valley" |
| st_area_sh, st_length_ | Area and perimeter carried over from the source layer in its projected units. Not used. |
| geometry | MultiPolygon. Only the geometry is used. |

**Citation:** SWRCB Regional Board Boundaries [39].

#### data/geospatial-data/CA_State/CA_State.geojson

This is the California state outline: one MultiPolygon feature. CRS is EPSG:4326.

- **Source:** `info.txt` gives "2023 CA TIGER outline" from data.ca.gov "CA Geographic Boundaries" (https://data.ca.gov/dataset/ca-geographic-boundaries), which is derived from US Census TIGER/Line.
- **Read by:** `analysis/Analysis.ipynb` cell 6. It is the Figure 4a background, and only the geometry is used.
- **Manuscript:** Figure 4a.

| Field | Description |
|---|---|
| OBJECTID | Feature ID from the source layer |
| REGION, DIVISION | Census region (4) and division (9) codes |
| STATEFP, STATENS, GEOID | State FIPS code, ANSI code and GEOID (06) |
| STUSPS, NAME | "CA", "California" |
| LSAD, MTFCC, FUNCSTAT | TIGER legal/statistical area code, feature class code (G4000) and functional status |
| ALAND, AWATER | Land and water area (m²) |
| INTPTLAT, INTPTLON | Internal point latitude and longitude |
| Shape_Leng, Shape_Le_1, Shape_Area | Perimeter and area from the source layer's projection. Not used. |

**Citation:** US Census Bureau TIGER/Line (public domain), via the California Department of Technology's data.ca.gov dataset.

#### data/geospatial-data/CA_Counties/CA_Counties.shp (.shx, .dbf, .prj, .cpg)

These are the 58 California county polygons. CRS is EPSG:3857 (WGS 84 / Web Mercator), and the code reprojects them to EPSG:4326.

- **Source:** California Department of Technology, data.ca.gov "CA Geographic Boundaries". The ArcGIS metadata that shipped with the file (still in git history, commit 43ad4d9) shows it was exported on 2024-05-03 from Census `tl_2019_us_county`.
- **Read by:**
  - `analysis/Routing.ipynb` cell 1. `load_od_table()` uses `NAME` to set Origin County and Destination County, and validation check 4 uses them ("cross-county destination APN").
  - `analysis/Analysis.ipynb` cell 1. It finds the origin county of dropped manifests (printed only).
  - `analysis/Analysis.ipynb` cell 3. It finds the county of each exposed Census place (printed only).
- **Manuscript:** the drop step in §2.3 and Figure S6 for APN geocodes outside the origin county. The county borders in Figure 4a come from the block-group file, not this one.

| Field | Description |
|---|---|
| STATEFP, COUNTYFP, COUNTYNS, GEOID | State FIPS, county FIPS, county ANSI code, and 5-digit county GEOID |
| NAME | County name. This is the field the code uses. |
| NAMELSAD | Name with legal/statistical description ("Fresno County") |
| LSAD, CLASSFP, MTFCC, FUNCSTAT | TIGER legal/statistical area, class, feature class (G4020) and functional status codes |
| CSAFP, CBSAFP, METDIVFP | Combined statistical area, CBSA and metropolitan division codes |
| ALAND, AWATER | Land and water area (m²) |
| INTPTLAT, INTPTLON | Internal point latitude and longitude |
| Shape_Leng, Shape_Area | Perimeter and area in Web Mercator units. Not used. |

Geometry is Polygon.

**Citation:** US Census Bureau TIGER/Line 2019 (public domain), via data.ca.gov.

#### data/geospatial-data/CA_BGs/nhgis0015_shape-nhgis0015_shapefile_tl2024_060_blck_grp_2024/CA_blck_grp_2024.shp

These are the 2024 California census block group polygons from the IPUMS NHGIS extract nhgis0015 (2024 TIGER/Line block groups): 25,588 features.

- **CRS:** ESRI:102003, USA Contiguous Albers Equal Area Conic (NAD83). The analysis reprojects to EPSG:3310.
- **Read by:**
  - `analysis/Analysis.ipynb` cell 3, `load_block_groups()`. It joins `GISJOIN` to the two CSVs below and uses `ALAND` as the land-area denominator.
  - `analysis/Analysis.ipynb` cell 6. It dissolves on `COUNTYFP` to draw the Figure 4a county outlines.
  - `review/annual-reports/geocode_dairy_addresses.py`. It dissolves on `COUNTYFP` to check which county each Nominatim hit falls in.
- **Manuscript:** Figure 4a (county borders), 4c and 4e; §2.3 and §3.3 (4,851 block groups, Spearman ρ, quintile truck-miles per person).

| Field | Description |
|---|---|
| GISJOIN | NHGIS join code. This is the key to the CSVs. |
| STATEFP, COUNTYFP, TRACTCE, BLKGRPCE | State, county, tract and block-group codes. `COUNTYFP` is used. |
| GEOID, GEOIDFQ | 12-digit block-group GEOID and its fully qualified form |
| NAMELSAD | "Block Group N" |
| MTFCC, FUNCSTAT | Feature class (G5030) and functional status |
| ALAND, AWATER | Land and water area (m²). `ALAND` is used. |
| INTPTLAT, INTPTLON | Internal point latitude and longitude |
| Shape_Leng, Shape_Area | Perimeter (m) and area (m²) in the file's CRS. Not used. |

Geometry is Polygon.

**Citation:** NHGIS [41] (see the terms below).

#### data/geospatial-data/CA_BGs/nhgis0017_ds272_20245_blck_grp.csv (+ _codebook.txt)

This is block-group income from the 2020–2024 ACS 5-year estimates (NHGIS dataset ds272, tables B19001, B19013 and B19301). Each of the 25,607 rows is one California block group.

- **Read by:** `analysis/Analysis.ipynb` cell 3, `load_block_groups()`. It uses `GISJOIN`, `AURUE001`, `AURUM001`, `AUSYE001` and `AUSYM001`. Only `AURUE001` > 0 enters the quintiles and correlations.
- **Manuscript:** Figure 4c and 4e; §2.3 and §3.3 (income quintiles, Spearman ρ = −0.187 and −0.199).
- **Special values:** negative codes such as −666666666, −333333333 and −222222222 are ACS annotation codes, meaning no estimate or MOE is available or appropriate. A median of 250001 means "$250,000 or more".

| Field | Description |
|---|---|
| GISJOIN | NHGIS join code (joins to the shapefile) |
| YEAR | "2020-2024" |
| STUSAB, STATE, STATEA | "CA", "California", "06" |
| COUNTY, COUNTYA | County name and code |
| TRACTA, BLKGRPA | Tract and block-group codes |
| GEO_ID, TL_GEO_ID | Census geographic ID and TIGER/Line GEOID |
| REGIONA, DIVISIONA, COUSUBA, PLACEA, CONCITA, AIANHHA, RES_ONLYA, TRUSTA, AIHHTLI, AITSA, ANRCA, CBSAA, CSAA, METDIVA, UAA, CDCURRA, SLDUA, SLDLA, ZCTA5A, SUBMCDA, SDELMA, SDSECA, SDUNIA, PCI, PUMAA, BTTRA, BTBGA | NHGIS context codes. All are empty at this geographic level. |
| NAME_E, NAME_M | Area name (estimate and MOE blocks) |
| AURTE001–AURTE017 | B19001 household counts: total, then 16 income brackets from "< $10,000" to "$200,000 or more" (households) |
| AURUE001 | B19013 median household income (2024 dollars). Used. |
| AUSYE001 | B19301 per capita income (2024 dollars). Used. |
| AURTM001–AURTM017, AURUM001, AUSYM001 | Margins of error for the estimates above. `AURUM001` and `AUSYM001` are read. |

#### data/geospatial-data/CA_BGs/nhgis0016_ds272_20245_blck_grp.csv (+ _codebook.txt)

This is block-group total population from the 2020–2024 ACS 5-year estimates (NHGIS ds272, table B01003). Each of the 25,607 rows is one block group.

- **Read by:** `analysis/Analysis.ipynb` cell 3. It joins on `GISJOIN`, and `AUO6E001` (auto-detected) becomes `bg_pop`.
- **Manuscript:** per-resident exposure in Figure 4e and §3.3 (0.38 vs 0.11 truck-miles per person).

| Field | Description |
|---|---|
| GISJOIN | NHGIS join code |
| YEAR | "2020-2024" |
| STUSAB, STATE, STATEA | "CA", "California", "06" |
| COUNTY, COUNTYA | County name and code |
| TRACTA, BLKGRPA | Tract and block-group codes |
| GEO_ID, TL_GEO_ID | Census geographic ID and TIGER/Line GEOID |
| REGIONA, DIVISIONA, COUSUBA, PLACEA, CONCITA, AIANHHA, RES_ONLYA, TRUSTA, AIHHTLI, AITSA, ANRCA, CBSAA, CSAA, METDIVA, UAA, CDCURRA, SLDUA, SLDLA, ZCTA5A, SUBMCDA, SDELMA, SDSECA, SDUNIA, PCI, PUMAA, BTTRA, BTBGA | NHGIS context codes. All are empty. |
| NAME_E, NAME_M | Area name |
| AUO6E001 | Total population (persons). Used. |
| AUO6M001 | Its margin of error (persons) |

#### data/geospatial-data/CA_Census_Place/cb_2024_06_place_500k.shp (.shx, .dbf, .prj, .cpg)

This is the US Census Bureau 2024 cartographic boundary file of California places (cities, towns and CDPs) at 1:500,000: 1,618 features.

- **CRS:** EPSG:4269 (NAD83). The analysis reprojects to EPSG:3310.
- **Read by:**
  - `analysis/Analysis.ipynb` cell 3. It keeps places with more than 50% of their area inside the Water Board, joins population on `GEOID`, and writes the Table S8–S11 CSVs. It uses `GEOID`, `LSAD` (25 = city, 43 = town, 57 = CDP), `ALAND` and `NAMELSAD`.
  - `analysis/Analysis.ipynb` cell 6: Figure 4f.
  - `review/annual-reports/geocode_dairy_addresses.py`. It uses `NAME` as a city gazetteer.
- **Manuscript:** Tables S8–S10; Figure 4f; values in §3.3 (Tulare 49,299 mi, Lakeside, Tipton, 48.7%).

| Field | Description |
|---|---|
| STATEFP, PLACEFP, PLACENS | State FIPS, place FIPS and place ANSI codes |
| GEOID, GEOIDFQ | 7-digit place GEOID (the join key) and its fully qualified form |
| NAME | Place name |
| NAMELSAD | Name with type ("Tulare city") |
| STUSPS, STATE_NAME | "CA", "California" |
| LSAD | Legal/statistical area description code |
| ALAND, AWATER | Land and water area (m²) |

Geometry is Polygon.

**Citation:** US Census Bureau 2024 Cartographic Boundary File [46] (public domain).

#### data/geospatial-data/CA_Census_Place/place acs pop data 2020-2024/nhgis0018_ds272_20245_place.csv (+ _codebook.txt)

This is place total population from the 2020–2024 ACS 5-year estimates (NHGIS extract nhgis0018, ds272, table B01003). Each of the 1,618 rows is one California Census place.

- **Read by:** `analysis/Analysis.ipynb` cell 3. It builds `GEOID` = `STATEA` (2 digits) + `PLACEA` (5 digits) and reads `AUO6E001` into `place_pop`.
- **Manuscript:** Table S9 (per resident), Figure 4f, §3.3; ref [45].

| Field | Description |
|---|---|
| GISJOIN | NHGIS join code |
| YEAR | "2020-2024" |
| STUSAB, STATE, STATEA | "CA", "California", "06" |
| PLACE, PLACEA | Place name and 5-digit place code |
| GEO_ID, TL_GEO_ID | Census geographic ID and TIGER/Line GEOID |
| REGIONA, DIVISIONA, COUNTYA, COUSUBA, TRACTA, BLKGRPA, CONCITA, AIANHHA, RES_ONLYA, TRUSTA, AIHHTLI, AITSA, ANRCA, CBSAA, CSAA, METDIVA, UAA, CDCURRA, SLDUA, SLDLA, ZCTA5A, SUBMCDA, SDELMA, SDSECA, SDUNIA, PCI, PUMAA, BTTRA, BTBGA | NHGIS context codes. All are empty. |
| NAME_E, NAME_M | Area name |
| AUO6E001 | Total population (persons). Used. |
| AUO6M001 | Its margin of error (persons) |

**NHGIS terms (all three CSVs and the block-group shapefile):**
- Cite: Schroeder J, Van Riper D, Manson S, Cooper G, Krause Z, Kugler T, Zhu T and Ruggles S. *IPUMS National Historical Geographic Information System: Version 21.0* [dataset]. Minneapolis, MN: IPUMS. 2026. https://doi.org/10.18128/D050.V21.0
- Redistribution needs IPUMS permission. Publishing a subset to meet journal data requirements is allowed, which covers these California extracts.

#### data/routing-data/study_area_network_processed_v13.pkl

This is the drivable road network used for routing: a pickled `networkx.MultiDiGraph` built with OSMnx 2.1.0 from a Geofabrik OpenStreetMap extract of California.

- **Size:** 1.68 GB on disk; 2.69 million nodes and 8.16 million edges, according to `environment/environment-routing.yml`.
- **What it contains:** the graph is simplified, clipped to the Water Board boundary plus a 25 km buffer, projected to EPSG:32610 (UTM 10N; confirmed from `network_with_hauls_v13.gpkg`, which is written from it), and has speeds and travel times added. It does not contain the origin and destination nodes, which `add_od_nodes_by_splitting()` inserts in memory after loading.
- **Producer:** `analysis/Routing.ipynb` cell 1, main block, step 1. This runs only when the pickle is missing. In that case the notebook:
  1. reads `data/routing-data/california-260318_study_area.osm` (not distributed) with `ox.graph_from_xml(simplify=True, retain_all=False)`, caching it as `study_area_network.pkl`;
  2. runs `clip_graph_to_buffered_boundary(buffer_km=25)` and `ox.project_graph`;
  3. runs `ox.add_edge_speeds()` with per-type defaults: motorway 100, motorway_link 70, trunk 90, trunk_link 60, primary 80, primary_link 50, secondary 60, secondary_link 40, tertiary 50, tertiary_link 30, unclassified 40, residential 30, living_street 20, service 20, pedestrian 5, track 20, road 40 km/h, with a 40 km/h fallback. Tagged OSM `maxspeed` values are kept.
  4. fills missing lengths from planar geometry, fills missing speeds with 40 km/h, then runs `ox.add_edge_travel_times()`.
- **Read by:** `analysis/Routing.ipynb` cell 1. `analysis/Analysis.ipynb` does not read it.
- **Manuscript:** SI Methods 0.1.3 (network preprocessing), and through the routing outputs §3.3, Figure 4b/4d, Figures S6–S8 and Tables S5 and S7–S10.
- **Loading:** it needs the `environment/environment-routing.yml` environment (Python 3.12, OSMnx 2.1.0) and well over 16 GB of RAM. Unpickle only a copy from the project's Hugging Face repository (see Data download).

| Element | Attribute | Description (as used by Routing.ipynb) |
|---|---|---|
| graph | `crs` | Projected CRS (EPSG:32610). Used to project origin/destination points and route lines. |
| node | `x`, `y` | Easting and northing (m, UTM 10N). Used for edge splitting and as a fallback straight-segment geometry. |
| edge | `length` | Segment length (m). Gives route distance and truck-km. |
| edge | `speed_kph` | Free-flow speed (km/h), imputed as described above |
| edge | `travel_time` | Traversal time (s). This is the shortest-path weight. |
| edge | `geometry` | Shapely LineString in EPSG:32610. Missing on straight edges, where the u–v segment is used. |
| edge | `name`, `highway` | OSM street name and road class. Copied into `outputs/results/routing/network_with_hauls_v13.gpkg`. |
| node/edge | other OSM tags kept by OSMnx (e.g. `osmid`, `oneway`, `maxspeed`, `lanes`, `ref`, `street_count`) | Present but not read once the pickle exists |

**Attribution:** map data © OpenStreetMap contributors, available under the Open Database License (ODbL) 1.0 (https://www.openstreetmap.org/copyright), distributed by Geofabrik GmbH [35]. The pickle is a Derivative Database, so it must be distributed under ODbL 1.0. Also cite OSMnx [61] and NetworkX [62].

#### data/annual-reports/

These are the 2024 dairy annual report PDFs submitted to the Central Valley Regional Water Quality Control Board, as received by Robertson et al. 2026 [20]. There are 858 PDFs (3.8 GB). The folder is not in git; it is on Hugging Face (see Data download).

- **Layout:** `data/annual-reports/<office>/<Correct_Forms | Consulting_and_Error_Causing_Forms>/<report>.pdf`. The office folders and file counts are in the table below.
- **Folder meaning:** the folder names are as received. Every Robertson et al. row whose PDF matches a file name exactly (497 of 578) is in a `Correct_Forms` folder. `Consulting_and_Error_Causing_Forms` holds consultant-format or problem reports.
- **File names:**
  - Fresno-office folders mostly use `2024AR_<Dairy Name>_<street>_<county>.pdf`.
  - Rancho Cordova uses `<street> <city> 2024 Dairy AR.pdf`.
  - There are variants (e.g. `2024AR Faial Farms Dairy.pdf`, `... GoatDairy AR.pdf`), and 192 files use the `.PDF` extension.
  - The file name is the `Source PDF` key in the report summaries.
- **Read by:**
  - `review/annual-reports/Dairy_Report_Scrape_Review.ipynb` and `scraper/*.py` scrape the 360 reports listed in `list_targets.txt` (269 Consulting, 91 Correct).
  - `build_report_formats.py` walks all PDFs to write `Annual_Report_Formats.csv`.
  - The review page links to the PDFs.
- **Manuscript:** §2.1 and SI Methods 0.1.1 (annual reports), Figure S1a (report formats), Figure S2 (review tool).

| Office folder | Correct_Forms | Consulting_and_Error_Causing_Forms | Total |
|---|---|---|---|
| Fresno Madera | 62 | 19 | 81 |
| Kern | 16 | 26 | 42 |
| Kings | 46 | 30 | 76 |
| Rancho Cordova | 399 | 85 | 484 |
| Tulare East | 38 | 87 | 125 |
| Tulare West | 28 | 22 | 50 |

## Data sources and attribution

- **Dairy annual reports and manifests:** public records of the Central Valley Regional Water Quality Control Board, 2024 reporting year. The original report summary (`data/tabular-data/Dairy_Report_Summary_Region_5_2024_with_source_pdf.csv`) is the earlier parse by Robertson et al. (2026), *Confined Animal Facility Permitting and Reporting Under the Porter-Cologne Water Quality Control Act*, Stanford Environmental & Natural Resources Law and Policy Program. The records contain names and addresses of dairy operators, haulers and receiving parties as filed.
- **Road network:** © OpenStreetMap contributors, California extract distributed by Geofabrik GmbH, available under the Open Database License (ODbL) v1.0. The processed network in `data/routing-data/` is a derived database under the same license.
- **Census data:** IPUMS NHGIS, University of Minnesota (www.nhgis.org): 2020–2024 American Community Survey 5-year estimates (dataset ds272) for block groups (extracts nhgis0015–nhgis0017) and places (nhgis0018). Cite as: Schroeder J, Van Riper D, Manson S, Cooper G, Krause Z, Kugler T, Zhu T and Ruggles S. *IPUMS National Historical Geographic Information System: Version 21.0* [dataset]. Minneapolis, MN: IPUMS, 2026. https://doi.org/10.18128/D050.V21.0. Place boundaries: US Census Bureau 2024 cartographic boundary file `cb_2024_06_place_500k` (public domain).
- **Boundaries:** Central Valley Regional Water Board boundary from the California State Water Resources Control Board's Regional Board Boundaries feature service; California state and county outlines from US Census TIGER/Line (public domain).
- **Emission rates:** California Air Resources Board, EMFAC2025 emission rates for the San Joaquin Valley APCD, calendar year 2024 (`data/tabular-data/EMFAC2025ER-…csv`); `EMFAC_Rates_2024.csv` holds the rates the analysis uses, taken from that export by hand.
- **ZIP code to county table** (`data/tabular-data/zipcode_to_county.csv`): used by the manifest extraction to infer counties. Check its source's license (it follows the SimpleMaps US ZIP database layout, whose free version requires attribution) before redistribution.

## License

Code is released under the MIT License (see `LICENSE.txt`), © 2026 Ian Avery Bick and Daly Wettermark. Third-party data keep their own licenses, listed above.
