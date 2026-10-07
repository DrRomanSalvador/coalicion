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
  last <- NULL
  for (attempt in 1:5) {
    message("Downloading official Interior workbook, attempt ", attempt, "/5")
    status <- system2("curl", c(
      "-fL", "--retry", "2", "--retry-delay", "2",
      "--connect-timeout", "30", "--max-time", "600",
      "--insecure", "-A", "REINA-SEEC/1.0",
      "-o", local_xlsx, official_url
    ))
    if (identical(status, 0L) && file.exists(local_xlsx) && file.info(local_xlsx)$size > 1000) {
      last <- NULL
      break
    }
    last <- paste0("curl_exit_", status)
    if (file.exists(local_xlsx) && file.info(local_xlsx)$size < 1000) unlink(local_xlsx)
    if (attempt < 5) Sys.sleep(min(2^attempt, 30))
  }
  if (!is.null(last)) stop("Official Interior workbook download failed: ", last)
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
  "2023J"="2023-07-23"
)

wb <- readxl::excel_sheets(local_xlsx)
if (length(wb) != 1L || wb[[1]] != "Congreso")
  stop("Unexpected official Interior workbook sheets: ", paste(wb, collapse=", "))

raw <- readxl::read_excel(
  local_xlsx, sheet="Congreso", skip=3, col_names=TRUE,
  .name_repair="minimal"
)
if (!nrow(raw)) stop("Official Interior workbook is empty after header row.")

headers <- names(raw)
datecol <- find_col(headers, c("Fecha"))
desccol <- find_col(headers, c("Descripción","Descripcion"))
typecol <- find_col(headers, c("Tipo Elección","Tipo Eleccion"))

if (is.na(datecol) || is.na(desccol) || is.na(typecol))
  stop("Official workbook schema missing Fecha/Tipo Elección/Descripción.")

province_cols <- seq.int(5L, length.out=52L)
province_names <- trimws(headers[province_cols])
if (length(province_names) != 52L || any(!nzchar(province_names)))
  stop("Official workbook does not expose the expected 52 constituency columns.")

pieces <- list()
for (i in seq_len(nrow(raw))) {
  d <- raw[[datecol]][i]
  date_text <- tryCatch(format(as.Date(d), "%Y-%m-%d"), error=function(e) as.character(d))
  election <- names(target_dates)[match(date_text, unname(target_dates))]
  if (is.na(election)) next
  if (!identical(trimws(as.character(raw[[typecol]][i])), "Congreso")) next

  desc <- trimws(as.character(raw[[desccol]][i]))
  m <- regexec("^(Votos|Escaños|Escanos|Diputados)\\s*\\((.*)\\)$", desc, ignore.case=TRUE)
  z <- regmatches(desc, m)[[1]]
  if (!length(z)) next

  metric <- tolower(iconv(z[2], to="ASCII//TRANSLIT"))
  if (metric == "votos") {
    metric_name <- "votos"
  } else if (metric %in% c("escanos","diputados")) {
    metric_name <- "escanos"
  } else {
    next
  }
  party <- trimws(z[3])
  if (!nzchar(party)) next

  vals <- suppressWarnings(as.numeric(unlist(raw[i, province_cols], use.names=FALSE)))
  y <- tibble::tibble(
    election=election,
    fecha_eleccion=unname(target_dates[election]),
    circunscripcion=province_names,
    partido=party,
    metric=metric_name,
    value=vals
  ) |>
    dplyr::filter(!is.na(value), value >= 0)
  if (nrow(y)) pieces[[length(pieces)+1]] <- y
}

long <- dplyr::bind_rows(pieces)
if (!nrow(long)) stop("No official Votos/Escaños rows were recognized.")

result <- long |>
  dplyr::group_by(election, fecha_eleccion, circunscripcion, partido) |>
  dplyr::summarise(
    votos=sum(value[metric=="votos"], na.rm=TRUE),
    escaños=sum(value[metric=="escanos"], na.rm=TRUE),
    .groups="drop"
  ) |>
  dplyr::mutate(
    circunscripcion_codigo=NA_character_,
    partido_codigo=NA_character_,
    fuente="Ministerio del Interior / portal oficial de datos abiertos",
    nivel_fuente="PRIMARY_OFFICIAL"
  ) |>
  dplyr::select(election, fecha_eleccion, circunscripcion_codigo, circunscripcion,
                partido_codigo, partido, votos, escaños, fuente, nivel_fuente)

expected <- names(target_dates)
got <- unique(result$election)
missing_elections <- setdiff(expected, got)
if (length(missing_elections))
  stop("Official Interior workbook missing elections: ", paste(missing_elections, collapse=", "))

integrity <- result |>
  dplyr::group_by(election) |>
  dplyr::summarise(
    total_escaños=sum(escaños,na.rm=TRUE),
    n_circunscripciones=dplyr::n_distinct(circunscripcion),
    .groups="drop"
  )
bad <- integrity |>
  dplyr::filter(total_escaños != 350L | n_circunscripciones != 52L)
if (nrow(bad))
  stop("Historical official data failed 350/52 integrity: ",
       paste(paste0(bad$election, "(seats=",bad$total_escaños,
                    ",circ=",bad$n_circunscripciones,")"), collapse=", "))

readr::write_csv(result, "data/resultados_oficiales_2004_2023.csv")
message("Wrote ", nrow(result), " official constituency-party rows from ", official_url)
