# Portfolio Metrics Extraction

Automates extraction of financial metrics from non-standardized management PDF
reports, deterministically processing them into a clean metrics table for
further business / portfolio-level analysis.

## Setup

```bash
pip install -r requirements.txt
```
Requires Python 3.10+ (developed on 3.10.9).

## Input

Place the source PDF reports in `pdfs/`.

## Run Book

1. Run the extract.ipynb notebook to extract the metrics with minimal preprocessing, this is the most manual intensive notebook with granularity of logic to make the logic as permissive or conservative as possible.

1.a. Run the build_label_metric.ipynb notebook to generate a base mapping file, which is used by the silver notebook to create the silver layer of data. The generated mapping is a starting point and can be edited directly to add or adjust entries for future metrics.

2. Run the silver.ipynb notebook which processes the bronze layer, and cleans/dedupes the data and create a clean conformed metrics table which can be used for creating views or further analysis.
The silver.csv is the table with data which has been identified as high degree of confidence.


See [NOTES.md](NOTES.md) for approach, assumptions, limitations, and next steps.