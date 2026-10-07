#!/usr/bin/env Rscript
# Integrates official Spanish election results and CIS barometer voting-intention data.
# No synthetic observations are created. Missing/ambiguous source structures fail closed.

options(stringsAsFactors = FALSE)

dir.create("data/raw_cis", recursive=TRUE, showWarnings=FALSE)
dir.create("ci_evidence", recursive=TRUE, showWarnings=FALSE)

required <- c("dplyr","tidyr","stringr","purrr","readr","haven","infoelectoral","opencis")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if(length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))

elections <- tibble::tribble(
  ~election, ~date, ~year, ~month,
  "2004", "2004-03-14", 2004, "03",
  "2008", "2008-03-09", 2008, "03",
  "2011", "2011-11-20", 2011, "11",
  "2015", "2015-12-20", 2015, "12",
  "2016", "2016-06-26", 2016, "06",
  "2019A", "2019-04-28", 2019, "04",
  "2019N", "2019-11-10", 2019, "11",
  "2023", "2023-07-23", 2023, "07"
)

# 1) Official Ministry data via rOpenSpain/infoelectoral.
# The package documents that its data are provided by the Ministry of the Interior.
extract_results <- function(e) {
  x <- infoelectoral::municipios(tipoeleccion="generales", yr=as.character(e$year), mes=e$month)
  if(is.list(x) && !is.data.frame(x)) x <- dplyr::bind_rows(x)
  if(!is.data.frame(x) || nrow(x)==0) stop("No official data returned for ", e$election)
  n <- names(x)
  prov_col <- n[which(stringr::str_detect(stringr::str_to_lower(n), "prov|circuns"))][1]
  party_col <- n[which(stringr::str_detect(stringr::str_to_lower(n), "candid|partid|sigla|abrev"))][1]
  vote_col <- n[which(stringr::str_detect(stringr::str_to_lower(n), "votos|vot"))][1]
  if(anyNA(c(prov_col, party_col, vote_col))) {
    readr::write_lines(capture.output(str(x)), file.path("ci_evidence", paste0("infoelectoral_schema_",e$election,".txt")))
    stop("Could not identify province/party/votes columns for ",e$election)
  }
  out <- x |>
    transmute(circunscripcion=as.character(.data[[prov_col]]),
              partido=as.character(.data[[party_col]]),
              votos=as.numeric(.data[[vote_col]])) |>
    filter(!is.na(circunscripcion), !is.na(partido), !is.na(votos)) |>
    group_by(circunscripcion, partido) |>
    summarise(votos=sum(votos), .groups="drop") |>
    mutate(fecha_eleccion=e$date, election=e$election,
           fuente="Ministerio del Interior; retrieved via rOpenSpain/infoelectoral",
           source_tier="PRIMARY_INTERIOR_RETRIEVED")
  out
}

results <- purrr::map_dfr(seq_len(nrow(elections)), ~extract_results(elections[.x,]))
if(nrow(results)==0 || dplyr::n_distinct(results$election)<8) stop("Official result integration incomplete")
readr::write_csv(results, "data/resultados_oficiales_2004_2023.csv", na="")

# 2) CIS barometers: use public microdata and extract the voting-intention variable.
# This is declared voting intention, not a reconstructed CIS seat forecast.
studies <- opencis::search_all_cis(
  q="*title_es_ES:(+barometro)",
  from="2004-01-01", to="2023-12-31",
  sort="publishDate+"
)
studies <- studies |>
  filter(as.Date(date) >= as.Date("2004-01-01"), as.Date(date) <= as.Date("2023-12-31")) |>
  distinct(study, date, title)

if(nrow(studies)<20) stop("Too few CIS barometer studies discovered: ",nrow(studies))

extract_cis <- function(study, date, title) {
  df <- tryCatch(opencis::read_cis(study), error=function(e) NULL)
  if(is.null(df)) return(NULL)
  dict <- tryCatch(opencis::get_data_dictionary(df), error=function(e) NULL)
  if(is.null(dict)) return(NULL)
  hits <- dict |>
    filter(stringr::str_detect(stringr::str_to_lower(label),
      "intención de voto|intencion de voto|votaría|votaria|votaría usted|votaria usted"))
  if(nrow(hits)==0) return(NULL)
  # Prefer variables whose value labels contain party names.
  score <- purrr::map_int(hits$variable, function(v) {
    z <- tryCatch(dict$value_labels[[match(v,dict$variable)]], error=function(e) NULL)
    txt <- stringr::str_to_lower(paste(names(z), unname(z), collapse=" "))
    sum(stringr::str_detect(txt,c("psoe","partido popular|pp","vox","podemos","sumar","iu|izquierda unida")))
  })
  hits <- hits[order(score, decreasing=TRUE),]
  v <- hits$variable[1]
  vals <- df[[v]]
  labs <- tryCatch(haven::as_factor(vals, levels="labels"), error=function(e) as.character(vals))
  tab <- as.data.frame(table(labs, useNA="no"), stringsAsFactors=FALSE)
  names(tab) <- c("respuesta","n")
  tab <- tab |>
    mutate(respuesta=as.character(respuesta), n=as.numeric(n)) |>
    filter(!is.na(respuesta), n>0)
  if(nrow(tab)==0) return(NULL)
  total <- sum(tab$n)
  tab |>
    transmute(
      fecha_encuesta=as.character(as.Date(date)),
      estudio=as.character(study),
      titulo_estudio=as.character(title),
      partido=respuesta,
      estimacion_voto=n/total*100,
      tipo_encuesta="CIS barómetro; intención declarada",
      fuente="Centro de Investigaciones Sociológicas (CIS)",
      source_tier="PRIMARY_CIS_MICRODATA",
      n_respuestas=total,
      variable=v
    )
}

cis <- purrr::pmap_dfr(studies, extract_cis)
if(nrow(cis)<1000) stop("CIS dataset too small after extraction: ",nrow(cis))
readr::write_csv(cis, "data/encuestas_historicas_2004_2023.csv", na="")

manifest <- list(
  generated_at=as.character(Sys.time()),
  official_results=list(
    file="data/resultados_oficiales_2004_2023.csv",
    elections=as.list(elections$election),
    dates=as.list(elections$date),
    source="Ministerio del Interior via rOpenSpain/infoelectoral",
    note="No 2023-11 general election is invented; 2023 refers to 23 July."
  ),
  cis=list(
    file="data/encuestas_historicas_2004_2023.csv",
    studies=nrow(studies),
    rows=nrow(cis),
    source="CIS public microdata via opencis",
    interpretation="Declared voting intention; not the CIS modelled vote estimate."
  )
)
jsonlite::write_json(manifest, "ci_evidence/historical_data_manifest.json", pretty=TRUE, auto_unbox=TRUE)
cat("INTEGRATION PASS\n")
cat("Official rows:",nrow(results)," elections:",dplyr::n_distinct(results$election),"\n")
cat("CIS rows:",nrow(cis)," studies:",nrow(studies),"\n")

# CI trigger: source integration is deterministic and fail-closed.

# test-run trigger
