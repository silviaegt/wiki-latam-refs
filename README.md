# wiki-latam-refs

Treemaps visualizing the sources cited in Wikipedia articles about Latin America.

## Overview

This repository contains treemap visualizations that map the reference sources cited in Wikipedia articles related to Latin America. The goal is to reveal which domains, publications, and institutions dominate the sourcing of knowledge about the region, and to make visible the geographic and linguistic patterns hidden in Wikipedia's citations.

This work is a supervised project by **Silvia Gutiérrez**, under the supervision of **Prof. Dr. Manuel Burghardt** at the University of Leipzig.

## Data Source

The underlying data comes from the **Cultural Context Content (CCC) Datasets** published by Miquel-Ribé and Laniado (2019). Specifically, this project uses the **Spanish Wikipedia dataset**, which identifies articles with a strong cultural context for the Spanish-speaking world—including a large number of Latin American topics.

The dataset is available on figshare:

> Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Process

The pipeline builds on the methodology developed in the *Untangling Wikipedia's Sources* research project:

1. **Reference Extraction** — References are extracted from the Spanish Wikipedia articles in the CCC dataset, parsing both structured template citations (e.g., `cite web`, `cite news`) and unstructured "text" references.

2. **URL Normalization & Resolution** — URLs are normalized to base domains, archive wrappers are resolved to original sources (e.g., `web.archive.org/*/http://original.com`), and redirects are handled to create a clean mapping between Wikipedia references and the actual sources being cited.

3. **URL Enrichment** — Domains will be enriched with metadata layers including:
   - **Media Bias Fact Check (MBFC)** — political bias, factual reporting, media type, and country of origin
   - **GDELT & Wikidata** — ownership, funding, and transparency information
   - **IP geolocation & WHOIS** — geographic location of sources
   - **OpenAlex & Crossref** — scholarly citation metadata for academic URLs

4. **Aggregation & Visualization** — Reference counts are aggregated by `page_id` and `page_title`, then filtered and sorted to identify the top cited pages. The treemaps visualize the distribution of references across articles and domains.

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

*To be added.*

## References

- Gutiérrez, Silvia (2024–ongoing). *Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge*. Wikimedia Research. https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge
- Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
