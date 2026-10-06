<div style="text-align: right;">
  <a href="README.md">English</a> | <a href="README.es.md">Español</a>
</div>

# wiki-latam-refs

Treemaps que visualizan las fuentes citadas en artículos de Wikipedia sobre América Latina.

## Descripción general

Este repositorio contiene el pipeline para obtener, enriquecer y visualizar las fuentes de referencia citadas en artículos de Wikipedia en español relacionados con América Latina. El objetivo es revelar qué dominios, publicaciones e instituciones dominan las fuentes de conocimiento sobre la región, y hacer visibles los patrones geográficos y lingüísticos ocultos en las citas de Wikipedia.

Este trabajo es parte del doctorado de **Silvia Gutiérrez**, bajo la supervisión del **Prof. Dr. Manuel Burghardt** en la Universidad de Leipzig. Para saber más sobre cómo se relaciona con mi proyecto general, ve a [Relación con *Untangling Wikipedia's Sources*](#relación-con-untangling-wikipedias-sources).

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Fuente de datos](#fuente-de-datos)
- [Proceso](#proceso)
  - [Clasificación de sufijos de dominio](#clasificación-de-sufijos-de-dominio)
- [Visualizaciones](#visualizaciones)
  - [Dominios principales](#dominios-principales)
  - [Dominios principales por tipo de entidad](#dominios-principales-por-tipo-de-entidad)
  - [Páginas principales](#páginas-principales)
  - [Notas sobre las visualizaciones](#notas-sobre-las-visualizaciones)
- [Relación con *Untangling Wikipedia's Sources*](#relación-con-untangling-wikipedias-sources)
- [Hallazgos clave](#hallazgos-clave)
- [Cómo reproducir](#cómo-reproducir)
  - [Scripts](#scripts)
- [Referencias](#referencias)
- [Licencia](#licencia)

## Fuente de datos

Los datos subyacentes provienen de los **Conjuntos de Datos de Contenido de Contexto Cultural (CCC)** publicados por Miquel-Ribé y Laniado (2019). Específicamente, este proyecto utiliza el **conjunto de datos de Wikipedia en español**, que identifica artículos con un fuerte contexto cultural para el mundo hispanohablante, incluida una gran cantidad de temas latinoamericanos.

El conjunto de datos está disponible en figshare:

> Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Proceso

El pipeline se basa en la metodología desarrollada en el proyecto de investigación *Untangling Wikipedia's Sources*:

1. **Extracción de referencias** — Las referencias se extraen de los artículos de Wikipedia en español del conjunto de datos CCC, analizando tanto citas estructuradas de plantillas (p. ej., `cite web`, `cite news`) como referencias "de texto" no estructuradas.

2. **Normalización y resolución de URL** — Las URL se normalizan a dominios base, los envoltorios de archivo se resuelven a las fuentes originales (p. ej., `web.archive.org/*/http://original.com`), y se gestionan las redirecciones para crear un mapeo limpio entre las referencias de Wikipedia y las fuentes reales citadas.

3. **Enriquecimiento de URL** — Los dominios se enriquecerán con capas de metadatos que incluyen:
   - **Clasificación de sufijos de dominio** — (ver [sección más abajo](#clasificación-de-sufijos-de-dominio)) :white_check_mark:
   - **Media Bias Fact Check (MBFC)** — sesgo político, verificación de hechos, tipo de medio y país de origen :hourglass:
   - **GDELT y Wikidata** — información sobre propiedad, financiación y transparencia :hourglass:
   - **Geolocalización IP y WHOIS** — ubicación geográfica de las fuentes :hourglass:
   - **OpenAlex y Crossref** — metadatos de citas académicas para URL académicas :hourglass:

4. **Agregación y visualización** — Los recuentos de referencias se agregan por `page_id` y `page_title`, luego se filtran y ordenan para identificar las páginas más citadas. Los treemaps visualizan la distribución de referencias entre artículos y dominios.

### Clasificación de sufijos de dominio

Los sufijos de dominio se extraen utilizando el paquete de R [`pslr`](https://cran.r-project.org/package=pslr), que se basa en la [Lista de Sufijos Públicos](https://publicsuffix.org/) para identificar el sufijo público efectivo de cada URL (p. ej., `com`, `com.mx`, `gov.br`). Los sufijos resultantes se clasifican utilizando una **metodología por capas** diseñada para separar los tipos de dominio semánticos de la información geográfica.

#### Capas de clasificación

| Capa | Descripción | Fuente |
| :--- | :--- | :--- |
| **Gobierno y Educación** | Los espacios de nombres gubernamentales y educativos se identifican mediante un catálogo curado manualmente de sufijos gubernamentales y educativos de países y regiones. | [`GovEduDomains`](https://github.com/thu-jzl/GovEduDomains) |
| **Espacios de nombres genéricos** | Los espacios de nombres genéricos como `com`, `org`, `net`, `mil` y `news` se clasifican utilizando una taxonomía semántica predefinida. | Taxonomía semántica predefinida |
| **Espacios de nombres compuestos de código de país** | Los espacios de nombres compuestos de código de país (p. ej., `com.mx`, `org.ar`, `net.br`, `ac.cr`) se clasifican composicionalmente combinando el significado semántico del espacio de nombres con el país identificado por su etiqueta final de código de país. | Regla composicional |
| **Metadatos de país** | Los metadatos de país —incluyendo código ISO, nombre del país, subcontinente de la ONU y región económica— se derivan del conjunto de datos canónico de países. | [Wikimedia Movement Insights](https://gitlab.wikimedia.org/repos/movement-insights/canonical-data/-/raw/main/country/countries.tsv) |
| **Excepciones regionales** | Las excepciones específicas de cada país y los espacios de nombres regionales, como los dominios gubernamentales de los estados brasileños (`ac.gov.br`, `sp.gov.br`), se gestionan mediante reglas explícitas para evitar interpretar incorrectamente los códigos regionales como etiquetas semánticas. | Reglas explícitas |

#### Principios clave

- **Separación de responsabilidades:** los tipos de dominio semánticos se distinguen de la información geográfica.
- **Auditabilidad y reproducibilidad:** la clasificación distingue entre categorías documentadas explícitamente en catálogos externos y categorías inferidas de la estructura del dominio, mientras **preserva la fuente de clasificación** para auditabilidad y reproducibilidad.

## Visualizaciones

Los treemaps se publican como archivos HTML interactivos a través de GitHub Pages. Cada país tiene tres vistas:

- **Dominios principales** — dominios más citados en artículos sobre el país, agregados por número de páginas distintas.
- **Dominios principales por tipo de entidad** — lo mismo, pero desglosado por el tipo de entidad que describe el artículo (municipio, club de fútbol, diócesis, etc.), utilizando la jerarquía `instance of` de Wikidata.
- **Páginas principales** — artículos de Wikipedia con el mayor número de referencias.

### Dominios principales

Dominios más citados en artículos de Wikipedia sobre cada país.

| País | ISO | Visualización |
| :--- | :---: | :--- |
| Chile | CL | [top_domains_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_cl.html) |
| Colombia | CO | [top_domains_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_co.html) |
| Ecuador | EC | [top_domains_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ec.html) |
| México | MX | [top_domains_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_mx.html) |
| Nicaragua | NI | [top_domains_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ni.html) |
| Perú | PE | [top_domains_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_pe.html) |
| Puerto Rico | PR | [top_domains_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_pr.html) |
| Paraguay | PY | [top_domains_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_py.html) |
| El Salvador | SV | [top_domains_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_sv.html) |
| Venezuela | VE | [top_domains_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_ve.html) |

### Dominios principales por tipo de entidad

Dominios más citados en artículos sobre cada país, desglosados por el tipo de entidad que describe el artículo. Los tipos de entidad provienen de las propiedades `instance of` (P31) y `subclass of` (P279) de Wikidata.

| País | ISO | Visualización |
| :--- | :---: | :--- |
| Chile | CL | [top_domains_bytype_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_cl.html) |
| Colombia | CO | [top_domains_bytype_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_co.html) |
| Ecuador | EC | [top_domains_bytype_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ec.html) |
| México | MX | [top_domains_bytype_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_mx.html) |
| Nicaragua | NI | [top_domains_bytype_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ni.html) |
| Perú | PE | [top_domains_bytype_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_pe.html) |
| Puerto Rico | PR | [top_domains_bytype_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_pr.html) |
| Paraguay | PY | [top_domains_bytype_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_py.html) |
| El Salvador | SV | [top_domains_bytype_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_sv.html) |
| Venezuela | VE | [top_domains_bytype_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_domains_bytype_ve.html) |

### Páginas principales

Artículos de Wikipedia con el mayor número de referencias, por país.

| País | ISO | Visualización |
| :--- | :---: | :--- |
| Chile | CL | [top_pages_cl.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_cl.html) |
| Colombia | CO | [top_pages_co.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_co.html) |
| Ecuador | EC | [top_pages_ec.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ec.html) |
| México | MX | [top_pages_mx.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_mx.html) |
| Nicaragua | NI | [top_pages_ni.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ni.html) |
| Perú | PE | [top_pages_pe.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_pe.html) |
| Puerto Rico | PR | [top_pages_pr.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_pr.html) |
| Paraguay | PY | [top_pages_py.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_py.html) |
| El Salvador | SV | [top_pages_sv.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_sv.html) |
| Venezuela | VE | [top_pages_ve.html](https://silviaegt.github.io/wiki-latam-refs/dataviz/top_pages_ve.html) |

### Notas sobre las visualizaciones

- Todos los archivos HTML son autocontenidos e interactivos (hover, zoom, drill-down).
- Los treemaps están construidos con [Plotly Express](https://plotly.com/python/treemaps/).
- Los países están ordenados alfabéticamente. Los códigos siguen ISO 3166-1 alpha-2.

## Relación con *Untangling Wikipedia's Sources*

Este trabajo está directamente relacionado con el proyecto de investigación de Wikimedia **[Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge](https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge)** (2024–2026), supervisado por el Prof. Dr. Manuel Burghardt en la Universidad de Leipzig.

Ese proyecto desarrolla metodologías para desbloquear la información latente en las URL de Wikipedia, tratándolas no como puntos finales sino como puertas de entrada para comprender el linaje intelectual, el alcance geográfico y la diversidad epistémica de la enciclopedia. Aborda un punto ciego persistente en la investigación de citas: mientras que trabajos previos se centraron fuertemente en identificadores estructurados (DOI, ISBN, PMID), las URL —el formato de cita más utilizado— permanecen analíticamente opacas.

Los treemaps de este repositorio contribuyen a esa misión proporcionando una **lente visual centrada en América Latina** sobre los patrones de fuentes de URL que el proyecto busca revelar. Específicamente, ayudan a explorar preguntas como:

- **¿Qué fuentes dominan los temas latinoamericanos?** Los treemaps muestran la concentración de referencias en páginas como *Paraguay*, *Estado de Hidalgo*, etc.
- **¿Las URL de Wikipedia en español apuntan a más fuentes estadounidenses que latinoamericanas?** Esta es una de las preguntas comparativas que plantea el proyecto de investigación.
- **¿Qué revela la mina de oro de las URL "de texto"?** El proyecto encontró que una gran parte de las referencias "de texto" contienen al menos una URL no perteneciente a Wikipedia, y que las URL de Wikipedia en español a menudo apuntan a datos geográficos (p. ej., `geonames.usgs.gov`), lo que sugiere una traducción desde fuentes en inglés.

Al visualizar estos patrones específicamente para América Latina, este repositorio ofrece un estudio de caso regional que complementa los análisis interlingüísticos del proyecto.

## Hallazgos clave

*Por añadir.*

## Cómo reproducir

*Por completar.*

### Scripts

#### `classify_suffixes.R`

Clasifica los sufijos de dominio del corpus según su categoría funcional (gubernamental, académica, comercial, etc.); ver más en la sección [Clasificación de sufijos de dominio](#clasificación-de-sufijos-de-dominio) de este README. El código combina tres fuentes de datos:

- **Lista de Sufijos Públicos** (a través del paquete de R `pslr`)
- **GovEduDomains** (catálogo comunitario de dominios gubernamentales y educativos)
- **Wikimedia Movement Insights** (metadatos canónicos de países y regiones)

**Entrada:** `data/long_domains.csv` (una fila por dominio único).
**Salida:** `data/dominios_latam_clasificado.csv`.

**Autoría:** La estructura y la documentación fueron revisadas con la asistencia de un modelo de lenguaje (DeepSeek y ChatGPT). El diseño metodológico y las reglas de clasificación son trabajo original del autor.

## Referencias

- Gutiérrez, Silvia (2024–en curso). *Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge*. Wikimedia Research. https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge
- Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Licencia

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)