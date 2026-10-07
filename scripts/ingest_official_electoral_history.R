#!/usr/bin/env Rscript

options(stringsAsFactors=FALSE)

required <- c("readxl","dplyr","readr","tibble")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))

dir.create("data/raw", showWarnings=FALSE, recursive=TRUE)
dir.create("data", showWarnings=FALSE, recursive=TRUE)

official_url <- "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
local_xlsx <- "data/raw/Elecciones-Congreso.xlsx"

if (!file.exists(local_xlsx) || file.info(local_xlsx)$size < 1000) {
  options(timeout=600)
  last <- NULL
  for (attempt in 1:5) {
    message("Downloading official Interior workbook, attempt ", attempt, "/5")
    tryCatch({
      utils::download.file(official_url, local_xlsx, mode="wb", method="libcurl", quiet=FALSE)
      if (file.exists(local_xlsx) && file.info(local_xlsx)$size > 1000) {
        last <- NULL
        break
      }
      stop("downloaded workbook is empty")
    }, error=function(e) {
      last <<- e
      if (file.exists(local_xlsx) && file.info(local_xlsx)$size < 1000) unlink(local_xlsx)
      if (attempt < 5) Sys.sleep(min(2^attempt, 30))
    })
  }
  if (!is.null(last)) stop("Official Interior workbook download failed: ", conditionMessage(last))
}

norm <- function(x) gsub("[^a-z0-9]", "", tolower(iconv(as.character(x), to="ASCII//TRANSLIT")))

find_col <- function(headers, patterns) {
  h <- norm(headers)
  for (p in patterns) {
    idx <- which(h == norm(p))
    if (length(idx)) return(idx[1])
  }
  for (p in patterns) {
    idx <- which(grepl(norm(p), h, fixed=TRUE))
    if (length(idx)) return(idx[1])
  }
  NA_integer_
}

target_dates <- c(
  "2004"="2004-03-14",
  "2008"="2008-03-09",
  "2011"="2011-11-20",
  "2015"="2015-12-20",
  "2016"="2016-06-26",
  "2019A"="2019-04-28",
  "2019N"="2019-11-10",
  "2023J"="2023-07-23",
  "2023N"="2023-11-23"
)

election_from_text <- function(x) {
  z <- tolower(iconv(as.character(x), to="ASCII//TRANSLIT"))
  if (grepl("14[ -]?03[ -]?2004|marzo.*2004|2004", z)) return("2004")
  if (grepl("09[ -]?03[ -]?2008|marzo.*2008|2008", z)) return("2008")
  if (grepl("20[ -]?11[ -]?2011|noviembre.*2011|2011", z)) return("2011")
  if (grepl("20[ -]?12[ -]?2015|diciembre.*2015|2015", z)) return("2015")
  if (grepl("26[ -]?06[ -]?2016|junio.*2016|2016", z)) return("2016")
  if (grepl("28[ -]?04[ -]?2019|abril.*2019", z)) return("2019A")
  if (grepl("10[ -]?11[ -]?2019|noviembre.*2019", z)) return("2019N")
  if (grepl("23[ -]?07[ -]?2023|julio.*2023", z)) return("2023J")
  if (grepl("23[ -]?11[ -]?2023|noviembre.*2023", z)) return("2023N")
  NA_character_
}

wb <- readxl::excel_sheets(local_xlsx)
pieces <- list()

for (sheet in wb) {
  message("Inspecting official Interior sheet: ", sheet)
  raw <- tryCatch(readxl::read_excel(local_xlsx, sheet=sheet, col_names=TRUE, .name_repair="minimal"),
                  error=function(e) NULL)
  if (is.null(raw) || !nrow(raw)) next

  headers <- names(raw)
  pcol <- find_col(headers, c("Provincia","Circunscripcion","Circunscripción"))
  partycol <- find_col(headers, c("Candidatura","Candidaturas","Partido","Siglas"))
  votescol <- find_col(headers, c("Votos","Votos candidatura"))
  seatscol <- find_col(headers, c("Escanos","Escaños","Diputados","Representantes"))
  datecol <- find_col(headers, c("Fecha","Fecha eleccion","Fecha elección","Convocatoria","Eleccion","Elección"))

  if (is.na(pcol) || is.na(partycol) || is.na(votescol)) next

  election <- election_from_text(sheet)
  if (is.na(election) && !is.na(datecol)) {
    vals <- raw[[datecol]]
    for (v in vals) {
      e <- election_from_text(v)
      if (!is.na(e)) { election <- e; break }
    }
  }
  if (is.na(election)) next

  y <- tibble::tibble(
    election=election,
    fecha_eleccion=unname(target_dates[election]),
    circunscripcion=trimws(as.character(raw[[pcol]])),
    partido=trimws(as.character(raw[[partycol]])),
    votos=suppressWarnings(as.numeric(raw[[votescol]])),
    escaños=if (!is.na(seatscol)) suppressWarnings(as.numeric(raw[[seatscol]])) else NA_real_
  ) |>
    dplyr::filter(!is.na(fecha_eleccion), nzchar(circunscripcion), nzchar(partido),
                  !is.na(votos), votos >= 0)

  if (nrow(y)) pieces[[length(pieces)+1]] <- y
}

result <- dplyr::bind_rows(pieces) |>
  dplyr::distinct(election, fecha_eleccion, circunscripcion, partido, .keep_all=TRUE)

expected <- names(target_dates)
got <- unique(result$election)
missing_elections <- setdiff(expected, got)
if (length(missing_elections))
  stop("Official Interior workbook did not expose all required elections: ",
       paste(missing_elections, collapse=", "))

if (any(is.na(result$escaños))) {
  result <- result |>
    dplyr::mutate(escaños=ifelse(is.na(escaños), 0, escaños))
}

integrity <- result |>
  dplyr::group_by(election) |>
  dplyr::summarise(total_escaños=sum(escaños,na.rm=TRUE),
                   n_circunscripciones=dplyr::n_distinct(circunscripcion),
                   .groups="drop")

bad <- integrity |>
  dplyr::filter(total_escaños != 350L | n_circunscripciones != 52L)
if (nrow(bad))
  stop("Historical official data failed 350/52 integrity: ",
       paste(paste0(bad$election, "(seats=",bad$total_escaños,
                    ",circ=",bad$n_circunscripciones,")"), collapse=", "))

result <- result |>
  dplyr::mutate(
    circunscripcion_codigo=NA_character_,
    partido_codigo=NA_character_,
    fuente="Ministerio del Interior / portal oficial de datos abiertos",
    nivel_fuente="PRIMARY_OFFICIAL"
  ) |>
  dplyr::select(election, fecha_eleccion, circunscripcion_codigo, circunscripcion,
                partido_codigo, partido, votos, escaños, fuente, nivel_fuente)

readr::write_csv(result, "data/resultados_oficiales_2004_2023.csv")
message("Wrote ", nrow(result), " official constituency-party rows from ", official_url)
