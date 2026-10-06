<div style="text-align: right;">
  <a href="README.md">English</a> | <a href="README.es.md">Español</a>
</div>

# wiki-latam-refs

This repository contains the pipeline to [obtain](#data-source), [enrich](#domain-suffix-classification), and [visualize](#visualizations) the reference sources cited in Spanish Wikipedia articles related to Latin America. The goal is to reveal which domains, publications, and institutions dominate the sourcing of knowledge about the region, and to make visible the geographic and linguistic patterns hidden in Wikipedia's citations.

This work is part of **Silvia Gutiérrez'** PhD under the supervision of **Prof. Dr. Manuel Burghardt** at the University of Leipzig. To learn more about how it relates to my overall project, go to [Relationship to *Untangling Wikipedia's Sources*](#relationship-to-untangling-wikipedias-sources).

## Table of Contents

- [Overview](#overview)
- [Data Source](#data-source)
- [Process](#process)
  - [Reference Extraction](#reference-extraction)
  - [Enrichment](#enrichment)
    - [Domain Suffix Classification](#domain-suffix-classification)
      - [Classification Layers](#classification-layers)
    - [Key Principles](#key-principles)
  - [Aggregation and Visualization](#aggregation-and-visualization)
- [Visualizations](#visualizations)
  - [Top domains](#top-domains)
  - [Top domains by entity type](#top-domains-by-entity-type)
  - [Top pages](#top-pages)
  - [Notes on the visualizations](#notes-on-the-visualizations)
- [Relationship to *Untangling Wikipedia's Sources*](#relationship-to-untangling-wikipedias-sources)
- [Key Findings](#key-findings)
- [How to Reproduce](#how-to-reproduce)
  - [Scripts](#scripts)
    - [`classify_suffixes.R`](#classify_suffixesr)
- [References](#references)
- [License](#license)


## Data Source

The underlying data comes from the **Cultural Context Content (CCC) Datasets** published by Miquel-Ribé and Laniado (2019). Specifically, this project uses the **Spanish Wikipedia dataset**, which identifies articles with a strong cultural context for the Spanish-speaking world—including a large number of Latin American topics.

The dataset is available on figshare:

> Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. Figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Process

The pipeline builds on the methodology developed in the *Untangling Wikipedia's Sources* research project:

1. [**Reference Extraction**](#reference-extraction) — References are extracted from the Spanish Wikipedia articles in the CCC dataset, parsing both structured template citations (e.g., `cite web`, `cite news`) and unstructured "text" references.

2. **URL Normalization & Resolution** — URLs are normalized to base domains, archive wrappers are resolved to original sources (e.g., `web.archive.org/*/http://original.com`), and redirects are handled to create a clean mapping between Wikipedia references and the actual sources being cited.

3. **URL Enrichment** — Domains will be enriched with metadata layers including:
   - **Domain Suffix Classification** — (see [section below](#domain-suffix-classification)) ✅
   - **Media Bias Fact Check (MBFC)** — political bias, factual reporting, media type, and country of origin ⏳
   - **GDELT & Wikidata** — ownership, funding, and transparency information ⏳
   - **IP geolocation & WHOIS** — geographic location of sources ⏳
   - **OpenAlex & Crossref** — scholarly citation metadata for academic URLs ⏳

4. **Aggregation & Visualization** — Reference counts are aggregated by `page_id` and `page_title`, then filtered and sorted to identify the top cited pages. The treemaps visualize the distribution of references across articles and domains.


### Reference extraction

Extraction is handled by two modules that work together:

- **`refdb.py`** — extracts structured reference data from a single Wikipedia article.
- **`fetch_refs.py`** — orchestrates the extraction across thousands of articles and writes the results to disk.

#### `refdb.py`

Given a Wikipedia page (by title or page ID), `refdb.py`:

1. Fetches the article's wikitext via the Wikimedia API (`action=query`, `prop=revisions`).
2. Parses the wikitext with [`mwparserfromhell`](https://github.com/earwig/mwparserfromhell) and filters `<ref>...</ref>` tags, skipping self-closing or empty ones.
3. For each reference:
   - Identifies the main citation template (e.g. `cita web`, `cita libro`, `cita noticia`).
   - Captures nested templates, if any.
   - Resolves the URL, including fallback cascades for parameter names and archive wrappers (e.g. `urlarchivo=`, `archiveurl=`, or snapshot URLs from `web.archive.org`).
   - Extracts every non-empty template parameter.

The output is a tidy DataFrame with **one row per reference** and the following base columns:

| Column | Description |
| :--- | :--- |
| `page_id` | Wikipedia page ID |
| `page_title` | Article title |
| `ref_index` | Ordinal position of the reference within the article |
| `template` | Main citation template name (lowercase) |
| `nested_templates` | Pipe-separated list of nested templates, if any |
| `url` | Resolved URL (original, not snapshot) |
| `url_archivo` | Archived URL, if present |
| `raw_string` | Raw wikitext of the reference |
| `text` | Plain-text rendering of the reference |

Any additional template parameters (e.g. `título`, `fecha`, `autor`, `editorial`) become additional columns. Because templates are heterogeneous, the DataFrame is **wide and sparse**: a row from `{{cita web}}` will have `editorial` empty, while a row from `{{cita libro}}` will have `url` empty.

#### `fetch_refs.py`

`fetch_refs.py` orchestrates extraction across the full corpus:

1. Reads a CSV (`latam.csv`) with one row per article (`page_id`, `iso3166`).
2. Groups articles by country.
3. For each article, calls `refdb.extract()` and accumulates results in an in-memory buffer.
4. When the buffer exceeds 2,000 rows, concatenates and writes a parquet chunk to `refs/<ISO>/part-NNNNN.parquet`.
5. Maintains a **resume ledger** (`fetch_state.csv`) with the status of every (page, country) pair, so the process can be resumed if interrupted.
6. Writes per-country failure logs to `failures/<ISO>.csv`.
7. Prints a summary of rows per country at the end.

Output layout:

```
refs/
├── AR/
│   ├── part-00001.parquet
│   ├── part-00002.parquet
│   └── ...
├── BR/
│   └── ...
├── MX/
│   └── ...
failures/
├── AR.csv
└── ...
fetch_state.csv
```

#### Design decisions

| Decision | Rationale |
| :--- | :--- |
| **One row per reference** | Preserves the fine-grained structure needed for template and archive analysis. |
| **Wide and sparse tables** | Templates are heterogeneous; a fixed schema would force information loss. |
| **Parquet chunks of ~2,000 rows** | Balances memory usage and I/O overhead on a laptop. |
| **Resume ledger** | The pipeline runs for hours; interruption should not require restarting. |
| **No API rate limit bypass** | `SLEEP = 0.1` between requests respects Wikimedia's terms of service. |

#### Known limitations

- **One API call per page.** The Wikimedia API allows batching up to 50 titles per request. Migrating to batch requests would reduce runtime by roughly 30×, but requires refactoring `fetch_page()` to handle multi-page responses and split the results per page.
- **Wide parquet files.** Because every template parameter becomes a column, the parquet files are wider than necessary. An alternative would be to serialize non-base parameters as a JSON column, at the cost of parsing on read.
- **Python string storage workaround.** The pipeline disables pyarrow-backed strings (`pd.set_option("mode.string_storage", "python")`) to avoid a schema-inference failure when writing heterogeneous DataFrames to parquet. This is an environment-specific workaround, not a design choice.

### Enrichment

Once the reference parquets exist, the pipeline enriches them with external metadata:

1. **Domain normalization** — URLs are normalized to registered domains, and archive wrappers are resolved to original sources.
2. **Domain suffix classification** — Suffixes are extracted with [`pslr`](https://cran.r-project.org/package=pslr) (Public Suffix List) and classified using the layered methodology described in the **Domain Suffix Classification** section above.
3. **Wikidata enrichment** — Each article's Wikidata QID is retrieved, along with its `instance of` (P31) and `subclass of` (P279) properties. This produces the `instance_of_parent_label` used in the by-entity-type visualizations.
4. **Country and region mapping** — Country metadata (ISO code, UN subcontinent, economic region) is joined from the [Wikimedia Movement Insights](https://gitlab.wikimedia.org/repos/movement-insights/canonical-data) canonical country table.

#### Domain Suffix Classification

Domain suffixes are extracted using the R package [`pslr`](https://cran.r-project.org/package=pslr), which relies on the [Public Suffix List](https://publicsuffix.org/) to identify the effective public suffix of each URL (e.g., `com`, `com.mx`, `gov.br`). The resulting suffixes are then classified using a **layered methodology** designed to separate semantic domain types from geographic information.

##### Classification Layers

| Layer | Description | Source |
| :--- | :--- | :--- |
| **Government & Education** | Government and educational namespaces are identified using a manually curated catalog of government and education suffixes across countries and regions. | [`GovEduDomains`](https://github.com/thu-jzl/GovEduDomains) |
| **Generic Namespaces** | Generic namespaces such as `com`, `org`, `net`, `mil`, and `news` are classified using a predefined semantic taxonomy. | Predefined semantic taxonomy |
| **Compound Country-Code Namespaces** | Compound country-code namespaces (e.g., `com.mx`, `org.ar`, `net.br`, `ac.cr`) are classified compositionally by combining the semantic meaning of the namespace with the country identified by its final country-code label. | Compositional rule |
| **Country Metadata** | Country metadata—including ISO code, country name, UN subcontinent, and economic region—is derived from the canonical country dataset. | [Wikimedia Movement Insights](https://gitlab.wikimedia.org/repos/movement-insights/canonical-data/-/raw/main/country/countries.tsv) |
| **Regional Exceptions** | Country-specific exceptions and regional namespaces, such as Brazilian state government domains (`ac.gov.br`, `sp.gov.br`), are handled through explicit rules to avoid incorrectly interpreting regional codes as semantic labels. | Explicit rules |

#### Key Principles

- **Separation of concerns:** Semantic domain types are distinguished from geographic information.
- **Auditability & reproducibility:** The classification distinguishes between categories explicitly documented in external catalogs and categories inferred from domain structure, while **preserving the classification source** for auditability and reproducibility.

### Aggregation and visualization

Enriched references are aggregated at the (country, domain, entity type) level to produce:

- **Top domains** — Most-cited domains per country, weighted by distinct pages.
- **Top domains by entity type** — Same, broken down by the Wikidata `instance of` hierarchy.
- **Top pages** — Articles with the highest number of references.

These aggregations feed the treemaps published in the `dataviz/` folder.

### Top domains

Most-cited domains in Wikipedia articles about each country.

| Country | ISO | Visualization |
| :--- | :---: | :--- |
| Chile | CL | [top_domains_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_cl.html) |
| Colombia | CO | [top_domains_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_co.html) |
| Ecuador | EC | [top_domains_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ec.html) |
| Mexico | MX | [top_domains_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_mx.html) |
| Nicaragua | NI | [top_domains_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ni.html) |
| Peru | PE | [top_domains_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_pe.html) |
| Puerto Rico | PR | [top_domains_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_pr.html) |
| Paraguay | PY | [top_domains_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_py.html) |
| El Salvador | SV | [top_domains_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_sv.html) |
| Venezuela | VE | [top_domains_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ve.html) |

### Top domains by entity type

Most-cited domains in articles about each country, broken down by the type of entity the article describes. Entity types come from Wikidata's `instance of` (P31) and `subclass of` (P279) properties.

| Country | ISO | Visualization |
| :--- | :---: | :--- |
| Chile | CL | [top_domains_bytype_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_cl.html) |
| Colombia | CO | [top_domains_bytype_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_co.html) |
| Ecuador | EC | [top_domains_bytype_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ec.html) |
| Mexico | MX | [top_domains_bytype_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_mx.html) |
| Nicaragua | NI | [top_domains_bytype_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ni.html) |
| Peru | PE | [top_domains_bytype_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_pe.html) |
| Puerto Rico | PR | [top_domains_bytype_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_pr.html) |
| Paraguay | PY | [top_domains_bytype_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_py.html) |
| El Salvador | SV | [top_domains_bytype_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_sv.html) |
| Venezuela | VE | [top_domains_bytype_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ve.html) |

### Top pages

Wikipedia articles with the highest number of references, per country.

| Country | ISO | Visualization |
| :--- | :---: | :--- |
| Chile | CL | [top_pages_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_cl.html) |
| Colombia | CO | [top_pages_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_co.html) |
| Ecuador | EC | [top_pages_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ec.html) |
| Mexico | MX | [top_pages_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_mx.html) |
| Nicaragua | NI | [top_pages_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ni.html) |
| Peru | PE | [top_pages_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_pe.html) |
| Puerto Rico | PR | [top_pages_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_pr.html) |
| Paraguay | PY | [top_pages_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_py.html) |
| El Salvador | SV | [top_pages_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_sv.html) |
| Venezuela | VE | [top_pages_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ve.html) |

### Notes on the visualizations

- All HTML files are self-contained and interactive (hover, zoom, drill-down).
- Treemaps are built with [Plotly Express](https://plotly.com/python/treemaps/).
- Countries are ordered alphabetically. Codes follow ISO 3166-1 alpha-2.

## Relationship to *Untangling Wikipedia's Sources*

This work is directly connected to the Wikimedia research project **[Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge](https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge)** (2024–2026), supervised by Prof. Dr. Manuel Burghardt at the University of Leipzig.

That project develops methodologies to unlock the latent information in Wikipedia's URLs, treating them not as endpoints but as gateways to understanding the encyclopedia's intellectual lineage, geographic reach, and epistemic diversity. It addresses a persistent blind spot in citation research: while prior work focused heavily on structured identifiers (DOIs, ISBNs, PMIDs), URLs—the most widely used citation format—remain analytically opaque.

The treemaps in this repository contribute to that mission by providing a **visual, Latin America–focused lens** on the URL sourcing patterns the project seeks to reveal. Specifically, they help explore questions such as:

- **Which sources dominate Latin American topics?** The treemaps show the concentration of references across pages like *Paraguay*, *Estado de Hidalgo*, etc.
- **Do Spanish Wikipedia's URLs point to more U.S. sources than Latin American ones?** This is one of the comparative questions the research project poses.
- **What does the "text" URL goldmine reveal?** The project found that a large share of "text" references contain at least one non-Wikipedia URL, and that Spanish Wikipedia's URLs often point to geographic data (e.g., `geonames.usgs.gov`), suggesting translation from English sources.

By visualizing these patterns for Latin America specifically, this repository offers a regional case study that complements the project's cross-linguistic analyses.

## Key Findings

*To be added.*

## How to Reproduce

*To be completed.*

### Scripts

#### `classify_suffixes.R`

Classifies the domain suffixes of the corpus according to their functional category (governmental, academic, commercial, etc.), see more in the [Domain Suffix Classification](#domain-suffix-classification) section of this README. The code combines three data sources:

- **Public Suffix List** (via the R package `pslr`)
- **GovEduDomains** (community catalog of government and education domains)
- **Wikimedia Movement Insights** (canonical country and region metadata)

**Input:** `data/long_domains.csv` (one row per unique domain).
**Output:** `data/dominios_latam_clasificado.csv`.

**Authorship:** The structure and documentation were reviewed with assistance from a language model (DeepSeek and ChatGPT). The methodological design and classification rules are original work by the author.

## References

- Gutiérrez, Silvia (2024–ongoing). *Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge*. Wikimedia Research. https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge
- Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
