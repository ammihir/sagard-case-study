# Notes
 
## Approach

The goal was to pull financial metrics out of a set of management PDF reports that
don't follow any shared template, and turn them into one clean table I can actually
analyze across the portfolio. I split this into layers so each stage does one job
and I can see where things go wrong.

**Bronze — extraction (`extract.ipynb`).**
I read each PDF as text with `pdfplumber` and process it line by line. Each line is
triaged: bullet-style lines are treated as prose and set aside, header lines tell me
which time periods the columns represent, and everything else is treated as a data
row. For a data row I peel the numeric values off the right-hand side, treat what's
left as the metric label, and pair each value with the period sitting above it. Every
extracted value becomes one record with its company, period, value, unit, a source
snippet (so I can always trace a number back to the line it came from), and a
confidence flag. Output is one JSONL file per company.
 
I kept this stage deliberately rule-based rather than reaching for an LLM. It's
transparent, deterministic, and easy to debug — when a number is wrong I can point at
the exact line and rule that produced it.
 
**Mapping — controlled vocabulary (`build_label_metric.ipynb` + `canonical.py`).**
The same metric shows up under many names ("Contracted ARR", "Annual Recurring
Revenue", etc.). Rather than resolve every row, I collect the ~35 *distinct* labels
across the whole portfolio and map each one once to a canonical metric. The resolver
works in trust layers: an exact match against a hand-maintained synonym dictionary is
high-confidence and auto-accepted; a looser keyword match is medium-confidence and
flagged for review; anything unmatched is left explicitly unmapped rather than
guessed. The result is written to `label_metric_map.json` as a review table — high
-confidence rows are ready to go, the rest are meant to be eyeballed and edited by
hand. This is where a human (or an LLM proposing mappings for a human to approve)
would step in.
 
**Silver — conform (`silver.ipynb`).**
This takes the bronze records, applies the mapping, cleans and dedupes, and produces
`silver.csv` — the conformed, high +confidence metrics table that downstream analysis
or views would sit on top of.The mapping step only ingests records the
  extractor marked "high", so anything the extractor wasn't sure about is excluded
  from the conformed layer by design, not by accident.

## Assumptions
 
A few things I'm assuming about the source documents. They hold for the sample set,
but they're worth stating because they're where the extractor is fragile:
 
- **Headers sit directly above their tables**, and the value columns are in the same
  left-to-right order as the period columns in the header. Values are matched to
  periods by position, so if a table's columns were in a different order than its
  header, the numbers would attach to the wrong quarter without any error.
- **One reporting currency per document.** I detect it once (from a declaration, a
  footnote, or a symbol) and apply it to the whole file.
- **A line that mentions a quarter is a column header.** This is the shakiest
  assumption — a prose sentence like "revenue grew in Q2 2025…" looks the same to the
  code as a real header, so prose can occasionally disturb the period context.

## Current Limitations:

Metrics disclosed only in written commentary rather than the metrics table (e.g. PeopleFlow Q2 Gross Margin, stated in prose) are not captured in this phase. Prose extraction is a natural next step, but it requires period/metric disambiguation — the Q2 commentary states both the current and prior-quarter margin in one sentence — so I scoped it out to keep extracted values high-precision. An LLM pass over commentary, validated against the source text, is the intended extension

Canonicalization runs at the distinct-label level. A curated dictionary auto-accepts high +confidence matches. Fuzzy and LLM matching handle the residual as proposals routed to a human-review queue, never auto-accepted. Approved proposals are folded back into the dictionary, so the deterministic layer keeps growing and the fuzzy/LLM layers shrink over time.

## Future State:

- **Idempotent runs.** Make the extractor safe to re-run — dedupe or overwrite on
  write instead of pure append.

- **Gold layer.** A per-company / per-metric (or other comparison) layer feeding a
  visualization view for historical analysis.

- **Mappings in a store.** Keep the mappings in a relational database or tabular
  structure the scripts reference directly, for version controllability.