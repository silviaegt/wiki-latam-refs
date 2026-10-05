# =============================================================================
# Domain Suffix Classification for the Wikipedia LatAm Corpus
#
# Description:
#   Classifies the suffixes of domains cited in Spanish Wikipedia articles
#   about Latin America and the Caribbean according to their functional
#   category: governmental, academic, commercial, organizational, ccTLD, etc.
#
#   Combines three sources:
#     1. Public Suffix List (via pslr)      -> registrable suffixes
#     2. GovEduDomains                      -> explicit gov/edu catalog
#     3. Wikimedia Movement Insights        -> country and region metadata
#
#   Adds compositional and regional rules on top:
#     - com.ar     -> commercial + Argentina
#     - ac.gov.br  -> Acre + governmental + Brazil
#     - gub.uy     -> governmental + Uruguay
#
# Input:
#   data/long_domains.csv  (one row per unique domain, column `domain`)
#
# Output:
#   data/dominios_latam_clasificado.csv
#
# Author:    Silvia Gutiérrez De la Torre
# Contact:   silviaegt@wikimedia.org
# Date:      2026-10-04
# License:   CC BY 4.0
#
# AI note:
#   The structure, comment style, and documentation of this script were
#   reviewed with assistance from DeepSeek and ChatGPT
#   The methodological design, source selection, classification logic,
#   and compositional rules are original work by the author.
# =============================================================================


# 1. Dependencies -------------------------------------------------------------

library(tidyverse)   # data manipulation and the %>% pipe
library(pslr)        # suffix extraction from the Public Suffix List


# 2. Configuration ------------------------------------------------------------
# Paths and URLs centralized for easy modification.

input_domains_path  <- "../data/long_domains.csv"
output_path         <- "../data/dominios_latam_clasificado.csv"

# Government and education domain catalog (community-maintained)
govedu_url <- paste0(
  "https://raw.githubusercontent.com/",
  "thu-jzl/GovEduDomains/main/data/domain_suffixes.csv"
)

# Canonical country table from Wikimedia Movement Insights
countries_url <- paste0(
  "https://gitlab.wikimedia.org/",
  "repos/movement-insights/canonical-data/",
  "-/raw/main/country/countries.tsv"
)


# 3. Suffix extraction --------------------------------------------------------
# Each domain is decomposed into (subdomain, domain, suffix) using the
# Public Suffix List. For example:
#   www.unam.mx    -> subdomain = "www", domain = "unam", suffix = "mx"
#   www.gov.br     -> subdomain = "www", domain = "gov",  suffix = "br"

long_domains <- read_csv(input_domains_path, show_col_types = FALSE)
domains      <- unique(long_domains$domain)
ext          <- pslr::suffix_extract(domains)


# 4. Load GovEduDomains catalog ----------------------------------------------
# Translates the `category` field and normalizes ISO country codes.
#
# Note: some suffixes appear in multiple countries; we keep the first
# occurrence (distinct by suffix). If country-specific granularity is ever
# needed, this step should be revised.

govedu_lookup <- read_csv(govedu_url, show_col_types = FALSE) %>%
  transmute(
    suffix          = str_to_lower(str_remove(suffix, "^\\.")),
    govedu_category = case_when(
      category == "government" ~ "governmental",
      category == "education"  ~ "academic",
      TRUE                     ~ NA_character_
    ),
    govedu_country  = country_or_region,
    govedu_iso2     = str_to_upper(iso2)
  ) %>%
  distinct(suffix, .keep_all = TRUE)


# 5. Load Wikimedia country table ---------------------------------------------
# Used as the authoritative source for country names, subcontinent, and
# economic region.

countries_lookup <- read_tsv(countries_url, show_col_types = FALSE) %>%
  transmute(
    iso_code        = str_to_upper(iso_code),
    country_name    = name,
    un_subcontinent = un_subcontinent,
    economic_region = economic_region
  ) %>%
  filter(!is.na(iso_code), iso_code != "") %>%
  distinct(iso_code, .keep_all = TRUE)


# 6. Generic suffix taxonomy --------------------------------------------------
# Semantic categories for gTLDs and for labels that may appear before a
# ccTLD (e.g. "com" in "com.ar").
#
# Important: do NOT include gov / gob / gouv / go / edu / ac here.
# Those are resolved via GovEduDomains because their meaning depends on
# the country (for example, "ac" means academic in Costa Rica, but is the
# ccTLD for Ascension Island; "go" is governmental in some countries, but
# can be a subdomain in others).

generic_lookup <- tribble(
  ~suffix,           ~category,
  
  # Organizations and commercial
  "com",             "commercial",
  "org",             "organization",
  "net",             "network",
  "info",            "informational",
  "biz",             "business",
  
  # Special purpose
  "int",             "international",
  "mil",             "military",
  "aero",            "aviation",
  "coop",            "cooperative",
  "museum",          "museum",
  
  # Media and content
  "news",            "media",
  "tv",              "media",
  "media",           "media",
  "press",           "media",
  "blog",            "blog",
  
  # Travel
  "travel",          "tourism",
  
  # Generic gTLDs
  "online",          "generic",
  "pro",             "professional",
  "app",             "generic",
  "site",            "generic",
  "website",         "generic",
  "digital",         "generic",
  "today",           "generic",
  "live",            "generic",
  "cloud",           "generic",
  "global",          "generic",
  "world",           "generic",
  "international",   "generic",
  "top",             "generic",
  "club",            "generic",
  "tips",            "generic",
  "bio",             "generic",
  
  # Regional and linguistic
  "cat",             "regional",
  "eus",             "regional"
) %>%
  distinct(suffix, .keep_all = TRUE)


# 7. ccTLD lookup -------------------------------------------------------------
# Derived from the Wikimedia country table.
# Special case: "uk" is a DNS ccTLD, but the ISO code for the United Kingdom
# is "GB". Added explicitly.

cctld_lookup <- countries_lookup %>%
  transmute(
    tld             = str_to_lower(iso_code),
    cctld_iso_code  = iso_code
  ) %>%
  distinct(tld, .keep_all = TRUE) %>%
  bind_rows(tibble(tld = "uk", cctld_iso_code = "GB")) %>%
  distinct(tld, .keep_all = TRUE)


# 8. Brazilian regional government suffixes -----------------------------------
# In Brazil, suffixes of the form <state>.gov.br do NOT mean
# "academic + governmental + Brazil". They mean <state> + governmental + Brazil.
# For example:
#   ac.gov.br  -> Acre
#   sp.gov.br  -> São Paulo
#   mg.gov.br  -> Minas Gerais

br_states_lookup <- tribble(
  ~region, ~region_name,
  "ac", "Acre",
  "al", "Alagoas",
  "ap", "Amapá",
  "am", "Amazonas",
  "ba", "Bahia",
  "ce", "Ceará",
  "df", "Distrito Federal",
  "es", "Espírito Santo",
  "go", "Goiás",
  "ma", "Maranhão",
  "mt", "Mato Grosso",
  "ms", "Mato Grosso do Sul",
  "mg", "Minas Gerais",
  "pa", "Pará",
  "pb", "Paraíba",
  "pr", "Paraná",
  "pe", "Pernambuco",
  "pi", "Piauí",
  "rj", "Rio de Janeiro",
  "rn", "Rio Grande do Norte",
  "rs", "Rio Grande do Sul",
  "ro", "Rondônia",
  "rr", "Roraima",
  "sc", "Santa Catarina",
  "se", "Sergipe",
  "sp", "São Paulo",
  "to", "Tocantins"
)

br_gov_lookup <- br_states_lookup %>%
  mutate(suffix = paste0(region, ".gov.br"))


# 9. Semantic map for compound suffixes ---------------------------------------
# Labels that may appear before a ccTLD, with their semantic category.
# Examples:
#   com.ar  -> commercial
#   org.mx  -> organization
#   ac.cr   -> academic
#   gob.pe  -> governmental

compound_lookup <- tribble(
  ~label,    ~category,
  
  # Commercial
  "com",     "commercial",
  "co",      "commercial",
  
  # Organizations
  "org",     "organization",
  "ong",     "organization",
  
  # Networks
  "net",     "network",
  
  # Information
  "info",    "informational",
  "inf",     "informational",
  
  # Education
  "edu",     "academic",
  "ac",      "academic",
  
  # Government
  "gov",     "governmental",
  "gob",     "governmental",
  "gouv",    "governmental",
  "go",      "governmental",
  "gub",     "governmental",
  
  # Military
  "mil",     "military",
  
  # Justice
  "jus",     "judicial",
  
  # Professional
  "pro",     "professional",
  
  # Other
  "art",     "art",
  "travel",  "tourism",
  "tur",     "tourism",
  "web",     "generic",
  "jor",     "press",
  "pub",     "publication"
)


# 10. Classification function -------------------------------------------------
# Takes the output of pslr::suffix_extract() and returns an enriched data
# frame with the category of each suffix.
#
# Priority order (highest to lowest):
#   1. Regional rule (Brazil: <state>.gov.br)
#   2. Explicit GovEduDomains catalog
#   3. Generic taxonomy (exact match)
#   4. Compositional rule (label + ccTLD: com.ar, org.mx, ac.cr)
#   5. Pure ccTLD (mx, ar, br)
#   6. "other" (unclassified)

classify_suffix <- function(ext) {
  
  # ---------------------------------------------------------------------------
  # 10.1 Normalize and decompose each suffix
  # ---------------------------------------------------------------------------
  
  out <- ext %>%
    mutate(
      suffix        = str_to_lower(str_remove(suffix, "^\\.")),
      tld           = str_extract(suffix, "[^.]+$"),         # last label
      first_label   = str_extract(suffix, "^[^.]+"),         # first label
      n_labels      = str_count(suffix, fixed(".")) + 1      # number of labels
    )
  
  # ---------------------------------------------------------------------------
  # 10.2 Enrich with the different sources
  # ---------------------------------------------------------------------------
  
  out <- out %>%
    left_join(govedu_lookup, by = "suffix") %>%
    left_join(
      generic_lookup %>% rename(generic_category = category),
      by = "suffix"
    ) %>%
    left_join(cctld_lookup, by = "tld") %>%
    left_join(
      br_gov_lookup %>% select(suffix, region, region_name),
      by = "suffix"
    ) %>%
    left_join(
      compound_lookup,
      by = c("first_label" = "label")
    ) %>%
    rename(component_category = category)
  
  # ---------------------------------------------------------------------------
  # 10.3 Resolve ISO country code
  # ---------------------------------------------------------------------------
  # Priority: GovEduDomains (if it carries a country) > ccTLD lookup (if applicable)
  
  out <- out %>%
    mutate(iso_code = coalesce(govedu_iso2, cctld_iso_code)) %>%
    left_join(countries_lookup, by = "iso_code")
  
  # ---------------------------------------------------------------------------
  # 10.4 Apply classification rules
  # ---------------------------------------------------------------------------
  
  out <- out %>%
    mutate(
      
      # Functional category of the suffix
      category = case_when(
        
        # 1. Regional rule (Brazil)
        suffix %in% br_gov_lookup$suffix ~
          "governmental",
        
        # 2. GovEduDomains catalog (explicit gov, edu)
        !is.na(govedu_category) ~
          govedu_category,
        
        # 3. Exact generic taxonomy
        !is.na(generic_category) ~
          generic_category,
        
        # 4. Compositional rule (label + ccTLD)
        #    Only when there are exactly 2 labels, the first is semantic,
        #    and the second is a known ccTLD.
        n_labels == 2 &
          !is.na(component_category) &
          !is.na(cctld_iso_code) ~
          component_category,
        
        # 5. Pure ccTLD
        !is.na(cctld_iso_code) &
          suffix == str_to_lower(cctld_iso_code) ~
          "cctld",
        
        # 6. Unclassified
        TRUE ~
          "other"
      ),
      
      # Source of the classification (traceability)
      category_source = case_when(
        suffix %in% br_gov_lookup$suffix                            ~ "regional_rule",
        !is.na(govedu_category)                                     ~ "GovEduDomains",
        !is.na(generic_category)                                    ~ "taxonomy",
        n_labels == 2 &
          !is.na(component_category) &
          !is.na(cctld_iso_code)                                    ~ "compositional_rule",
        !is.na(cctld_iso_code) &
          suffix == str_to_lower(cctld_iso_code)                    ~ "Wikimedia_country_table",
        TRUE                                                        ~ "unknown"
      ),
      
      # Structural type (useful for auditing and debugging)
      suffix_type = case_when(
        suffix %in% br_gov_lookup$suffix                            ~ "regional_government",
        !is.na(govedu_category) &
          govedu_category == "governmental"                         ~ "government",
        !is.na(govedu_category) &
          govedu_category == "academic"                             ~ "education",
        !is.na(generic_category)                                    ~ "generic_semantic",
        n_labels == 2 &
          !is.na(component_category) &
          !is.na(cctld_iso_code)                                    ~ "semantic_plus_ccTLD",
        !is.na(cctld_iso_code) &
          suffix == str_to_lower(cctld_iso_code)                    ~ "ccTLD",
        TRUE                                                        ~ "unknown"
      )
    )
  
  # ---------------------------------------------------------------------------
  # 10.5 Select and order output columns
  # ---------------------------------------------------------------------------
  
  out %>%
    select(
      suffix,
      category,
      suffix_type,
      iso_code,
      country_name,
      un_subcontinent,
      economic_region,
      region,
      region_name,
      category_source,
      everything()
    ) %>%
    select(
      -any_of(c(
        "govedu_category", "govedu_country", "govedu_iso2",
        "generic_category", "cctld_iso_code", "tld", "first_label",
        "n_labels", "component_category"
      ))
    )
}


# 11. Run classification ------------------------------------------------------

ext_classified <- classify_suffix(ext)


# 12. Diagnostics -------------------------------------------------------------
# How many suffixes remain unclassified and which are the most frequent.
# These cases should feed new rules into `generic_lookup` or
# `compound_lookup` in future iterations.

unclassified <- ext_classified %>%
  filter(category == "other") %>%
  count(suffix, sort = TRUE)

message("Unclassified suffixes: ", nrow(unclassified))
print(unclassified, n = 20)


# 13. Export ------------------------------------------------------------------

write_csv(ext_classified, output_path)
message("Saved: ", output_path)