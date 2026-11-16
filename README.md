# Waste Data: Operational Dairy Records for Pollution Accounting

Code and data for Bick, Wettermark, Hervey, Eneva and Ho, *Waste Data: Operational Dairy Records for Pollution Accounting*. The analysis uses 2024 dairy annual reports and manure and wastewater transport manifests filed with California's Central Valley Regional Water Quality Control Board (Region 5). It builds a nitrogen balance for each dairy, models the manure trucking network and who lives near it, and compares the reported manure management with the California Air Resources Board's greenhouse gas inventory.

## Quick start

All figures and tables can be reproduced by running one notebook, `analysis/Analysis.ipynb`:

conda env create -f environment/environment.yml
conda activate ca-dairy-accounting
conda install -n ca-dairy-accounting jupyterlab   # or open the notebook in VS Code with this environment's kernel
cd analysis
jupyter lab Analysis.ipynb                        # then Restart & Run All, runs in ~one minute


It writes every generated figure in `outputs/results/figures/` (PNG and EPS), every table in `outputs/results/tables/` (including the SI tables in LaTeX, `SI_Tables.md`), and the manuscript's numbers as LaTeX macros (`outputs/results/Manuscript_Parameters.tex`), from the review outputs in `outputs/review/` and the routing files in `outputs/results/routing/`. To regenerate those inputs as well, from the annual-report and manifest PDFs through the routing, follow the detailed directions in [Reproducing the results, step by step](reproduction_and_outputs.md#reproducing-the-results-step-by-step).

Extracted data from 2024 annual reports (dairy names, source PDFs, herd size, and nitrogen generation, application and exports are available in `outputs/review/annual-reports/Dairy_Annual_Report_Summary_Table_Region_5_2024.csv`. 

Extracted data from 2024 manure and wastewater transport manifests (origin dairy, destination, quantity) are available in `outputs/review/annual-reports/processed_manure_manifests.csv` and `outputs/review/annual-reports/processed_wastewater_manifests.csv`, respectively.

## Contents

- [Quick start](#quick-start)
- [Pipeline overview](#pipeline-overview)
- [Repository layout](#repository-layout)
- [Setup](#setup)
- [Reproducing the results, step by step](reproduction_and_outputs.md#reproducing-the-results-step-by-step) (in `reproduction_and_outputs.md`)
- [Outputs and the manuscript](reproduction_and_outputs.md#outputs-and-the-manuscript) (in `reproduction_and_outputs.md`)
- [File and field reference](reproduction_and_outputs.md#file-and-field-reference) (in `reproduction_and_outputs.md`)
- [Data sources and attribution](reproduction_and_outputs.md#data-sources-and-attribution) (in `reproduction_and_outputs.md`)
- [License](reproduction_and_outputs.md#license) (in `reproduction_and_outputs.md`)

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
├── README.md
└── reproduction_and_outputs.md  Step-by-step reproduction, outputs, file and field reference
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
