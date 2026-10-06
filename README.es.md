<div style="text-align: right;">
  <a href="README.md">English</a> | <a href="README.es.md">Español</a>
</div>

# wiki-latam-refs

Este repositorio contiene el pipeline para [obtener](#fuente-de-datos), [enriquecer](#clasificación-de-sufijos-de-dominio) y [visualizar](#visualizaciones) las fuentes de referencia citadas en artículos de la Wikipedia en español relacionados con América Latina. El objetivo es revelar qué dominios, publicaciones e instituciones dominan las fuentes de conocimiento sobre la región, y visibilizar los patrones geográficos y lingüísticos ocultos en las citas de Wikipedia.

Este trabajo forma parte del doctorado de **Silvia Gutiérrez** bajo la supervisión del **Prof. Dr. Manuel Burghardt** en la Universidad de Leipzig. Para saber más sobre cómo se relaciona con mi proyecto general, ve a [Relación con *Untangling Wikipedia's Sources*](#relación-con-untangling-wikipedias-sources).

## Índice

- [Descripción general](#descripción-general)
- [Fuente de datos](#fuente-de-datos)
- [Proceso](#proceso)
  - [Extracción de referencias](#extracción-de-referencias)
  - [Enriquecimiento](#enriquecimiento)
    - [Clasificación de sufijos de dominio](#clasificación-de-sufijos-de-dominio)
      - [Capas de clasificación](#capas-de-clasificación)
    - [Principios clave](#principios-clave)
  - [Agregación y visualización](#agregación-y-visualización)
- [Visualizaciones](#visualizaciones)
  - [Dominios más citados](#dominios-más-citados)
  - [Dominios más citados por tipo de entidad](#dominios-más-citados-por-tipo-de-entidad)
  - [Páginas más citadas](#páginas-más-citadas)
  - [Notas sobre las visualizaciones](#notas-sobre-las-visualizaciones)
- [Relación con *Untangling Wikipedia's Sources*](#relación-con-untangling-wikipedias-sources)
- [Hallazgos clave](#hallazgos-clave)
- [Cómo reproducir](#cómo-reproducir)
  - [Scripts](#scripts)
    - [`classify_suffixes.R`](#classify_suffixesr)
- [Referencias](#referencias)
- [Licencia](#licencia)

## Fuente de datos

Los datos subyacentes provienen de los **Cultural Context Content (CCC) Datasets** publicados por Miquel-Ribé y Laniado (2019). En concreto, este proyecto utiliza el **dataset de la Wikipedia en español**, que identifica artículos con un fuerte contexto cultural para el mundo hispanohablante—incluyendo un gran número de temas latinoamericanos.

El dataset está disponible en figshare:

> Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. Figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Proceso

El pipeline se basa en la metodología desarrollada en el proyecto de investigación *Untangling Wikipedia's Sources*:

1. [**Extracción de referencias**](#extracción-de-referencias) — Las referencias se extraen de los artículos de la Wikipedia en español del dataset CCC, analizando tanto citas estructuradas con plantillas (p. ej., `cite web`, `cite news`) como referencias "text" no estructuradas.

2. **Normalización y resolución de URLs** — Las URLs se normalizan a dominios base, se resuelven los envoltorios de archivo a las fuentes originales (p. ej., `web.archive.org/*/http://original.com`), y se gestionan las redirecciones para crear un mapeo limpio entre las referencias de Wikipedia y las fuentes reales citadas.

3. **Enriquecimiento de URLs** — Los dominios se enriquecerán con capas de metadatos que incluyen:
   - **Clasificación de sufijos de dominio** — (ver [sección más abajo](#clasificación-de-sufijos-de-dominio)) ✅
   - **Media Bias Fact Check (MBFC)** — sesgo político, rigor informativo, tipo de medio y país de origen ⏳
   - **GDELT y Wikidata** — información sobre propiedad, financiación y transparencia ⏳
   - **Geolocalización IP y WHOIS** — ubicación geográfica de las fuentes ⏳
   - **OpenAlex y Crossref** — metadatos de citas académicas para URLs académicas ⏳

4. **Agregación y visualización** — Los recuentos de referencias se agregan por `page_id` y `page_title`, y luego se filtran y ordenan para identificar las páginas más citadas. Los treemaps visualizan la distribución de referencias entre artículos y dominios.

### Extracción de referencias

La extracción se gestiona mediante dos módulos que trabajan juntos:

- **`refdb.py`** — extrae datos estructurados de referencias de un único artículo de Wikipedia.
- **`fetch_refs.py`** — orquesta la extracción en miles de artículos y escribe los resultados en disco.

#### `refdb.py`

Dada una página de Wikipedia (por título o ID de página), `refdb.py`:

1. Obtiene el wikitexto del artículo a través de la API de Wikimedia (`action=query`, `prop=revisions`).
2. Analiza el wikitexto con [`mwparserfromhell`](https://github.com/earwig/mwparserfromhell) y filtra las etiquetas `<ref>...</ref>`, omitiendo las auto-cerradas o vacías.
3. Para cada referencia:
   - Identifica la plantilla de cita principal (p. ej., `cita web`, `cita libro`, `cita noticia`).
   - Captura plantillas anidadas, si las hay.
   - Resuelve la URL, incluyendo cascadas de respaldo para nombres de parámetros y envoltorios de archivo (p. ej., `urlarchivo=`, `archiveurl=`, o URLs de instantáneas de `web.archive.org`).
   - Extrae todos los parámetros no vacíos de la plantilla.

La salida es un DataFrame ordenado con **una fila por referencia** y las siguientes columnas base:

| Columna | Descripción |
| :--- | :--- |
| `page_id` | ID de la página de Wikipedia |
| `page_title` | Título del artículo |
| `ref_index` | Posición ordinal de la referencia dentro del artículo |
| `template` | Nombre de la plantilla de cita principal (minúsculas) |
| `nested_templates` | Lista de plantillas anidadas separadas por pipes, si las hay |
| `url` | URL resuelta (original, no instantánea) |
| `url_archivo` | URL archivada, si existe |
| `raw_string` | Wikitexto crudo de la referencia |
| `text` | Representación en texto plano de la referencia |

Cualquier parámetro adicional de la plantilla (p. ej., `título`, `fecha`, `autor`, `editorial`) se convierte en columnas adicionales. Debido a que las plantillas son heterogéneas, el DataFrame es **ancho y disperso**: una fila de `{{cita web}}` tendrá `editorial` vacía, mientras que una fila de `{{cita libro}}` tendrá `url` vacía.

#### `fetch_refs.py`

`fetch_refs.py` orquesta la extracción en todo el corpus:

1. Lee un CSV (`latam.csv`) con una fila por artículo (`page_id`, `iso3166`).
2. Agrupa los artículos por país.
3. Para cada artículo, llama a `refdb.extract()` y acumula los resultados en un búfer en memoria.
4. Cuando el búfer supera las 2.000 filas, concatena y escribe un fragmento parquet en `refs/<ISO>/part-NNNNN.parquet`.
5. Mantiene un **registro de reanudación** (`fetch_state.csv`) con el estado de cada par (página, país), para que el proceso pueda reanudarse si se interrumpe.
6. Escribe registros de fallos por país en `failures/<ISO>.csv`.
7. Imprime un resumen de filas por país al final.


#### Decisiones de diseño

| Decisión | Justificación |
| :--- | :--- |
| **Una fila por referencia** | Preserva la estructura detallada necesaria para el análisis de plantillas y archivos. |
| **Tablas anchas y dispersas** | Las plantillas son heterogéneas; un esquema fijo forzaría la pérdida de información. |
| **Fragmentos parquet de ~2.000 filas** | Equilibra el uso de memoria y la sobrecarga de E/S en un portátil. |
| **Registro de reanudación** | El pipeline se ejecuta durante horas; una interrupción no debería requerir reiniciar. |
| **Sin elusión de límites de la API** | `SLEEP = 0.1` entre peticiones respeta los términos de servicio de Wikimedia. |

#### Limitaciones conocidas

- **Una llamada a la API por página.** La API de Wikimedia permite agrupar hasta 50 títulos por petición. Migrar a peticiones por lotes reduciría el tiempo de ejecución unas 30×, pero requiere refactorizar `fetch_page()` para manejar respuestas multipágina y dividir los resultados por página.
- **Archivos parquet anchos.** Debido a que cada parámetro de plantilla se convierte en una columna, los archivos parquet son más anchos de lo necesario. Una alternativa sería serializar los parámetros no base como una columna JSON, a costa de parsear al leer.
- **Solución alternativa para el almacenamiento de strings en Python.** El pipeline desactiva los strings respaldados por pyarrow (`pd.set_option("mode.string_storage", "python")`) para evitar un fallo de inferencia de esquema al escribir DataFrames heterogéneos en parquet. Es una solución específica del entorno, no una decisión de diseño.

### Enriquecimiento

Una vez que existen los parquets de referencias, el pipeline los enriquece con metadatos externos:

1. **Normalización de dominios** — Las URLs se normalizan a dominios registrados, y los envoltorios de archivo se resuelven a las fuentes originales.
2. **Clasificación de sufijos de dominio** — Los sufijos se extraen con [`pslr`](https://cran.r-project.org/package=pslr) (Public Suffix List) y se clasifican usando la metodología por capas descrita en la sección **Clasificación de sufijos de dominio** más arriba.
3. **Enriquecimiento con Wikidata** — Se recupera el QID de Wikidata de cada artículo, junto con sus propiedades `instance of` (P31) y `subclass of` (P279). Esto produce el `instance_of_parent_label` usado en las visualizaciones por tipo de entidad.
4. **Mapeo de país y región** — Los metadatos de país (código ISO, subcontinente de la ONU, región económica) se unen desde la tabla canónica de países de [Wikimedia Movement Insights](https://gitlab.wikimedia.org/repos/movement-insights/canonical-data).

#### Clasificación de sufijos de dominio

Los sufijos de dominio se extraen usando el paquete de R [`pslr`](https://cran.r-project.org/package=pslr), que se basa en la [Public Suffix List](https://publicsuffix.org/) para identificar el sufijo público efectivo de cada URL (p. ej., `com`, `com.mx`, `gov.br`). Los sufijos resultantes se clasifican luego usando una **metodología por capas** diseñada para separar los tipos semánticos de dominio de la información geográfica.

##### Capas de clasificación

| Capa | Descripción | Fuente |
| :--- | :--- | :--- |
| **Gobierno y educación** | Los espacios de nombres gubernamentales y educativos se identifican usando un catálogo curado manualmente de sufijos de gobierno y educación de países y regiones. | [`GovEduDomains`](https://github.com/thu-jzl/GovEduDomains) |
| **Espacios de nombres genéricos** | Los espacios de nombres genéricos como `com`, `org`, `net`, `mil` y `news` se clasifican usando una taxonomía semántica predefinida. | Taxonomía semántica predefinida |
| **Espacios de nombres compuestos con código de país** | Los espacios de nombres compuestos con código de país (p. ej., `com.mx`, `org.ar`, `net.br`, `ac.cr`) se clasifican composicionalmente combinando el significado semántico del espacio de nombres con el país identificado por su etiqueta final de código de país. | Regla composicional |
| **Metadatos de país** | Los metadatos de país—incluyendo código ISO, nombre del país, subcontinente de la ONU y región económica—se derivan del dataset canónico de países. | [Wikimedia Movement Insights](https://gitlab.wikimedia.org/repos/movement-insights/canonical-data/-/raw/main/country/countries.tsv) |
| **Excepciones regionales** | Las excepciones específicas de cada país y los espacios de nombres regionales, como los dominios de gobiernos estatales brasileños (`ac.gov.br`, `sp.gov.br`), se gestionan mediante reglas explícitas para evitar interpretar incorrectamente los códigos regionales como etiquetas semánticas. | Reglas explícitas |

#### Principios clave

- **Separación de preocupaciones:** Los tipos semánticos de dominio se distinguen de la información geográfica.
- **Auditabilidad y reproducibilidad:** La clasificación distingue entre categorías documentadas explícitamente en catálogos externos y categorías inferidas de la estructura del dominio, a la vez que **preserva la fuente de clasificación** para auditabilidad y reproducibilidad.

### Agregación y visualización

Las referencias enriquecidas se agregan a nivel de (país, dominio, tipo de entidad) para producir:

- **Dominios más citados** — Dominios más citados por país, ponderados por páginas distintas.
- **Dominios más citados por tipo de entidad** — Lo mismo, desglosado por la jerarquía `instance of` de Wikidata.
- **Páginas más citadas** — Artículos con el mayor número de referencias.

Estas agregaciones alimentan los treemaps publicados en la carpeta `dataviz/`.

### Dominios más citados

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

### Dominios más citados por tipo de entidad

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

### Páginas más citadas

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
- Los treemaps se construyen con [Plotly Express](https://plotly.com/python/treemaps/).
- Los países se ordenan alfabéticamente. Los códigos siguen ISO 3166-1 alpha-2.

## Relación con *Untangling Wikipedia's Sources*

Este trabajo está directamente relacionado con el proyecto de investigación de Wikimedia **[Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge](https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge)** (2024–2026), supervisado por el Prof. Dr. Manuel Burghardt en la Universidad de Leipzig.

Ese proyecto desarrolla metodologías para desbloquear la información latente en las URLs de Wikipedia, tratándolas no como puntos finales sino como puertas de entrada para comprender el linaje intelectual, el alcance geográfico y la diversidad epistémica de la enciclopedia. Aborda un punto ciego persistente en la investigación de citas: mientras que trabajos previos se centraron en gran medida en identificadores estructurados (DOIs, ISBNs, PMIDs), las URLs—el formato de cita más utilizado—permanecen analíticamente opacas.

Los treemaps de este repositorio contribuyen a esa misión proporcionando una **lente visual centrada en América Latina** sobre los patrones de fuentes de URLs que el proyecto busca revelar. En concreto, ayudan a explorar preguntas como:

- **¿Qué fuentes dominan los temas latinoamericanos?** Los treemaps muestran la concentración de referencias en páginas como *Paraguay*, *Estado de Hidalgo*, etc.
- **¿Las URLs de la Wikipedia en español apuntan a más fuentes estadounidenses que latinoamericanas?** Esta es una de las preguntas comparativas que plantea el proyecto de investigación.
- **¿Qué revela la mina de URLs "text"?** El proyecto encontró que una gran parte de las referencias "text" contienen al menos una URL no-Wikipedia, y que las URLs de la Wikipedia en español a menudo apuntan a datos geográficos (p. ej., `geonames.usgs.gov`), lo que sugiere traducción desde fuentes en inglés.

Al visualizar estos patrones específicamente para América Latina, este repositorio ofrece un estudio de caso regional que complementa los análisis interlingüísticos del proyecto.

## Hallazgos clave

*Por añadir.*

## Cómo reproducir

*Por completar.*

### Scripts

#### `classify_suffixes.R`

Clasifica los sufijos de dominio del corpus según su categoría funcional (gubernamental, académica, comercial, etc.), ver más en la sección [Clasificación de sufijos de dominio](#clasificación-de-sufijos-de-dominio) de este README. El código combina tres fuentes de datos:

- **Public Suffix List** (mediante el paquete de R `pslr`)
- **GovEduDomains** (catálogo comunitario de dominios gubernamentales y educativos)
- **Wikimedia Movement Insights** (metadatos canónicos de países y regiones)

**Entrada:** `data/long_domains.csv` (una fila por dominio único).
**Salida:** `data/dominios_latam_clasificado.csv`.

**Autoría:** La estructura y la documentación fueron revisadas con la asistencia de un modelo de lenguaje (DeepSeek y ChatGPT). El diseño metodológico y las reglas de clasificación son trabajo original de la autora.

## Referencias

- Gutiérrez, Silvia (2024–en curso). *Untangling Wikipedia's Sources: Mapping References To Reveal Global Knowledge*. Wikimedia Research. https://meta.wikimedia.org/wiki/Research:Untangling_Wikipedia%27s_Sources:_Mapping_References_To_Reveal_Global_Knowledge
- Miquel-Ribé, Marc; Laniado, David (2019). Wikipedia Cultural Diversity Dataset. figshare. Dataset. https://doi.org/10.6084/m9.figshare.7039514.v4

## Licencia

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)