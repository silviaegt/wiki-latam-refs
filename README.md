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
  - [Domain Suffix Classification](#domain-suffix-classification)
- [Visualizations](#visualizations)
  - [Top domains](#top-domains)
  - [Top domains by entity type](#top-domains-by-entity-type)
  - [Top pages](#top-pages)
  - [Notes on the visualizations](#notes-on-the-visualizations)
- [Relationship to *Untangling Wikipedia's Sources*](#relationship-to-untangling-wikipedias-sources)
- [Key Findings](#key-findings)
- [How to Reproduce](#how-to-reproduce)
  - [Scripts](#scripts)
- [References](#references)
- [License](#license)

## Data Source

The underlying data comes from the **Cultural Context Content (CCC) Datasets** published by Miquel-Ribé and Laniado (2019). Specifically, this project uses the **Spanish Wikipedia dataset**, which identifies articles with a strong cultural context for the Spanish-speaking world—including a large number of Latin American topics.

The dataset is available on figshare:

> Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Process

The pipeline builds on the methodology developed in the *Untangling Wikipedia's Sources* research project:

1. **Reference Extraction** — References are extracted from the Spanish Wikipedia articles in the CCC dataset, parsing both structured template citations (e.g., `cite web`, `cite news`) and unstructured "text" references.

2. **URL Normalization & Resolution** — URLs are normalized to base domains, archive wrappers are resolved to original sources (e.g., `web.archive.org/*/http://original.com`), and redirects are handled to create a clean mapping between Wikipedia references and the actual sources being cited.

3. **URL Enrichment** — Domains will be enriched with metadata layers including:
   - **Domain Suffix Classification** — (see [section below](#domain-suffix-classification)) :white_check_mark:
   - **Media Bias Fact Check (MBFC)** — political bias, factual reporting, media type, and country of origin :hourglass:
   - **GDELT & Wikidata** — ownership, funding, and transparency information :hourglass:
   - **IP geolocation & WHOIS** — geographic location of sources :hourglass:
   - **OpenAlex & Crossref** — scholarly citation metadata for academic URLs :hourglass:

4. **Aggregation & Visualization** — Reference counts are aggregated by `page_id` and `page_title`, then filtered and sorted to identify the top cited pages. The treemaps visualize the distribution of references across articles and domains.

### Domain Suffix Classification

Domain suffixes are extracted using the R package [`pslr`](https://cran.r-project.org/package=pslr), which relies on the [Public Suffix List](https://publicsuffix.org/) to identify the effective public suffix of each URL (e.g., `com`, `com.mx`, `gov.br`). The resulting suffixes are then classified using a **layered methodology** designed to separate semantic domain types from geographic information.

#### Classification Layers

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

## Visualizations

The treemaps are published as interactive HTML files via GitHub Pages. Each country has three views:

- **Top domains** — most-cited domains in articles about the country, aggregated by number of distinct pages.
- **Top domains by entity type** — same, but broken down by the type of entity the article describes (municipality, football club, diocese, etc.), using Wikidata's `instance of` hierarchy.
- **Top pages** — Wikipedia articles with the highest number of references.

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
