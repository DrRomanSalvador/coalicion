#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE)

required <- c("infoelectoral", "dplyr", "readr", "tibble")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))

dir.create("data", showWarnings=FALSE, recursive=TRUE)

elections <- tibble::tribble(
  ~election, ~date, ~year, ~month,
  "2004","2004-03-14",2004,"03",
  "2008","2008-03-09",2008,"03",
  "2011","2011-11-20",2011,"11",
  "2015","2015-12-20",2015,"12",
  "2016","2016-06-26",2016,"06",
  "2019A","2019-04-28",2019,"04",
  "2019N","2019-11-10",2019,"11",
  "2023","2023-07-23",2023,"07"
)

out <- list()

for (i in seq_len(nrow(elections))) {
  e <- elections[i,]
  message("Downloading official Interior data: ", e$election)
  x <- tryCatch(
    infoelectoral::provincias("congreso", as.character(e$year), e$month),
    error=function(err) stop("Official Interior download failed for ", e$election, ": ", conditionMessage(err))
  )
  needed <- c("codigo_provincia","codigo_distrito_electoral","codigo_partido",
              "denominacion","siglas","votos","diputados")
  if (!all(needed %in% names(x)))
    stop("Unexpected Infoelectoral schema for ", e$election, ": ", paste(names(x), collapse=", "))

  y <- x |>
    dplyr::transmute(
      election=e$election,
      fecha_eleccion=e$date,
      circunscripcion_codigo=as.character(codigo_provincia),
      circunscripcion=as.character(codigo_distrito_electoral),
      partido_codigo=as.character(codigo_partido),
      partido=dplyr::if_else(trimws(as.character(siglas))!="",
                             trimws(as.character(siglas)),
                             trimws(as.character(denominacion))),
      votos=as.integer(votos),
      escaños=as.integer(diputados),
      fuente="Ministerio del Interior / Infoelectoral",
      nivel_fuente="PRIMARY_OFFICIAL"
    )
  if (!nrow(y)) stop("Empty official result for ", e$election)
  out[[e$election]] <- y
}

result <- dplyr::bind_rows(out)

if (length(unique(result$election)) != nrow(elections))
  stop("Not all historical elections were materialized.")
if (anyNA(result$votos) || anyNA(result$escaños))
  stop("Official result contains NA votes/seats.")

integrity <- result |>
  dplyr::group_by(election) |>
  dplyr::summarise(total_escaños=sum(escaños,na.rm=TRUE),
                   n_circunscripciones=dplyr::n_distinct(circunscripcion_codigo),
                   .groups="drop")

bad <- integrity |>
  dplyr::filter(total_escaños != 350L | n_circunscripciones != 52L)
if (nrow(bad))
  stop("Historical official data failed 350/52 integrity: ", paste(bad$election, collapse=", "))

readr::write_csv(result, "data/resultados_oficiales_2004_2023.csv")
message("Wrote ", nrow(result), " official constituency-party rows.")

# CI trigger: official historical ingestion is fail-closed and source-pinned.

# Execute integration after system-library fix.
