#!/usr/bin/env Rscript
# Canonical historical integration trigger: keep acquisition logic in this script.

options(stringsAsFactors=FALSE)

required <- c("readxl","dplyr","readr","tibble","jsonlite")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))

dir.create("data/raw", showWarnings=FALSE, recursive=TRUE)
dir.create("data", showWarnings=FALSE, recursive=TRUE)

official_urls <- c(
  "https://descargas.interior.gob.es/datasets/resultados_electorales/Elecciones-Congreso.xlsx"
)
official_download_page <- "https://infoelectoral.interior.gob.es/es/elecciones-celebradas/area-de-descargas/index.html"
local_xlsx <- "data/raw/Elecciones-Congreso.xlsx"

curl_bin <- Sys.which("curl")
if (!nzchar(curl_bin)) curl_bin <- "/usr/bin/curl"
if (!file.exists(curl_bin)) stop("FAIL-CLOSED: curl executable is required for official Interior ingestion.")

download_candidate <- function(url, destination) {
  tmp <- paste0(destination, ".part")
  if (file.exists(tmp)) unlink(tmp)
  status <- system2(curl_bin, c(
    "-fL", "--retry", "4", "--retry-all-errors", "--retry-delay", "3",
    "--connect-timeout", "30", "--max-time", "900",
    "--compressed", "--location-trusted",
    "-A", "Mozilla/5.0-coalicion-historical-ingest/2.0",
    "-o", tmp, url
  ))
  ok <- identical(status, 0L) && file.exists(tmp) && file.info(tmp)$size > 10000
  if (ok) {
    con <- file(tmp, "rb"); on.exit(close(con), add=TRUE)
    magic <- readBin(con, "raw", n=4)
    ok <- identical(as.integer(magic), c(80L,75L,3L,4L))
  }
  if (ok) {
    file.rename(tmp, destination)
    return(TRUE)
  }
  if (file.exists(tmp)) unlink(tmp)
  FALSE
}

discover_xlsx_urls <- function(page_url) {
  tmp <- tempfile(fileext=".html")
  on.exit(unlink(tmp), add=TRUE)
  status <- system2(curl_bin, c(
    "-fL", "--retry", "2", "--retry-delay", "2",
    "--connect-timeout", "30", "--max-time", "120",
    "-A", "Mozilla/5.0-coalicion-historical-ingest/1.0",
    "-o", tmp, page_url
  ))
  if (!identical(status, 0L) || !file.exists(tmp)) return(character())
  html <- paste(readLines(tmp, warn=FALSE, encoding="UTF-8"), collapse="\\n")
  hrefs <- regmatches(html, gregexpr("(?i)(?:href=[\\\"'])([^\\\"']+\\.(?:xlsx|xls)(?:\\?[^\\\"']*)?)", html, perl=TRUE))[[1]]
  if (!length(hrefs)) return(character())
  urls <- sub("(?i)^href=[\\\"']([^\\\"']+)[\\\"']$", "\\1", hrefs, perl=TRUE)
  urls <- gsub("&amp;", "&", urls, fixed=TRUE)
  urls <- vapply(urls, function(u) {
    if (grepl("^https?://", u, ignore.case=TRUE)) return(u)
    if (startsWith(u, "/")) return(paste0("https://infoelectoral.interior.gob.es", u))
    paste0(sub("/[^/]*$", "/", page_url), u)
  }, character(1))
  unique(urls)
}

source_url <- NA_character_
# Never trust a pre-existing workspace/repository cache for canonical provenance.
# Every canonical run acquires the workbook from an explicit official URL.
if (file.exists(local_xlsx)) unlink(local_xlsx)
if (file.exists(paste0(local_xlsx, ".part"))) unlink(paste0(local_xlsx, ".part"))
{

  # Canonical provenance is strict: acquire only from the explicit official
  # Interior XLSX endpoint. The download page is retained as human-readable
  # provenance, but alternate discovered links are not allowed to change source_url.
  candidates <- official_urls
  last <- NULL
  for (url in candidates) {
    message("Trying official Interior workbook: ", url)
    ok <- FALSE
    for (attempt in 1:3) {
      if (download_candidate(url, local_xlsx)) {
        valid <- tryCatch({
          sheets <- readxl::excel_sheets(local_xlsx)
          length(sheets) >= 1L && any(sheets == "Congreso")
        }, error=function(e) FALSE)
        if (valid) {
          source_url <- url
          ok <- TRUE
          break
        }
      }
      last <- paste0(url, " attempt ", attempt)
      if (file.exists(local_xlsx)) unlink(local_xlsx)
      if (attempt < 3) Sys.sleep(min(2^attempt, 15))
    }
    if (ok) break
  }
  if (!length(candidates)) stop("FAIL-CLOSED: no official Interior XLSX candidates were discovered. Last attempt: ", ifelse(is.null(last), "none", last))
}

norm <- function(x) gsub("[^a-z0-9]", "", tolower(iconv(as.character(x), to="ASCII//TRANSLIT")))
canonical_id <- function(x) {
  y <- toupper(iconv(trimws(as.character(x)), to="ASCII//TRANSLIT"))
  y <- gsub("[^A-Z0-9]+", "_", y)
  y <- gsub("^_+|_+$", "", y)
  ifelse(nzchar(y), y, NA_character_)
}
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
  "2004"="2004-03-14","2008"="2008-03-09","2011"="2011-11-20",
  "2015"="2015-12-20","2016"="2016-06-26","2019A"="2019-04-28",
  "2019N"="2019-11-10","2023J"="2023-07-23"
)

wb <- readxl::excel_sheets(local_xlsx)
if (!"Congreso" %in% wb)
  stop("Official Interior workbook does not contain the Congreso sheet: ", paste(wb, collapse=", "))

raw <- readxl::read_excel(local_xlsx, sheet="Congreso", skip=3, col_names=TRUE, .name_repair="minimal")
if (!nrow(raw)) stop("Official Interior workbook is empty after header row.")

headers <- names(raw)
datecol <- find_col(headers, c("Fecha"))
desccol <- find_col(headers, c("Descripción","Descripcion"))
typecol <- find_col(headers, c("Tipo Elección","Tipo Eleccion"))
if (is.na(datecol) || is.na(desccol) || is.na(typecol))
  stop("Official workbook schema missing Fecha/Tipo Elección/Descripción.")

province_cols <- seq.int(5L, length.out=52L)
province_names <- trimws(headers[province_cols])
# Interior's workbook is authoritative for the constituency columns. Guard against
# accidental schema drift before parsing any values.
if (anyDuplicated(province_names))
  stop("Official workbook has duplicate constituency column names.")
if (any(grepl("^NA$|^N/?A$|^$", province_names, ignore.case=TRUE)))
  stop("Official workbook has blank/invalid constituency names in the 52-column block.")
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
  metric_name <- if (metric == "votos") "votos" else if (metric %in% c("escanos","diputados")) "escanos" else NA_character_
  if (is.na(metric_name)) next
  party <- trimws(z[3])
  if (!nzchar(party)) next

  vals <- suppressWarnings(as.numeric(unlist(raw[i, province_cols], use.names=FALSE)))
  y <- tibble::tibble(election=election, fecha_eleccion=unname(target_dates[election]),
    circunscripcion=province_names, partido=party, metric=metric_name, value=vals) |>
    dplyr::filter(!is.na(value), value >= 0)
  if (nrow(y)) pieces[[length(pieces)+1]] <- y
}

long <- dplyr::bind_rows(pieces)
if (!nrow(long)) stop("No official Votos/Escaños rows were recognized.")

result <- long |>
  dplyr::group_by(election, fecha_eleccion, circunscripcion, partido) |>
  dplyr::summarise(votos=sum(value[metric=="votos"], na.rm=TRUE),
                   escaños=sum(value[metric=="escanos"], na.rm=TRUE), .groups="drop") |>
  dplyr::mutate(circunscripcion_codigo=canonical_id(circunscripcion),
    partido_codigo=canonical_id(partido),
    fuente="Ministerio del Interior / portal oficial de datos abiertos",
    nivel_fuente="PRIMARY_OFFICIAL") |>
  dplyr::select(election, fecha_eleccion, circunscripcion_codigo, circunscripcion,
                partido_codigo, partido, votos, escaños, fuente, nivel_fuente)

expected <- names(target_dates)
got <- unique(result$election)
missing_elections <- setdiff(expected, got)
if (length(missing_elections))
  stop("Official Interior workbook missing elections: ", paste(missing_elections, collapse=", "))

integrity <- result |>
  dplyr::group_by(election) |>
  dplyr::summarise(total_escaños=sum(escaños,na.rm=TRUE),
                   n_circunscripciones=dplyr::n_distinct(circunscripcion), .groups="drop")
bad <- integrity |> dplyr::filter(total_escaños != 350L | n_circunscripciones != 52L)
if (nrow(bad))
  stop("Historical official data failed 350/52 integrity: ",
       paste(paste0(bad$election, "(seats=",bad$total_escaños,",circ=",bad$n_circunscripciones,")"), collapse=", "))

readr::write_csv(result, "data/resultados_oficiales_2004_2023.csv")
# Provenance sidecar: the materialization must always record the exact acquisition
# route used for the primary workbook.
prov <- list(
  schema = "INTERIOR_OFFICIAL_ACQUISITION_V2",
  source_url = source_url,
  download_page = official_download_page,
  sha256 = sub("  .*", "", system2(ifelse(nzchar(Sys.which("sha256sum")), Sys.which("sha256sum"), "/usr/bin/sha256sum"), local_xlsx, stdout=TRUE)),
  file_bytes = file.info(local_xlsx)$size,
  elections = target_dates,
  n_rows = nrow(result),
  n_constituencies_per_election = integrity$n_circunscripciones,
  identifier_policy = "circunscripcion_codigo and partido_codigo are deterministic identifiers derived from official labels; they are not claimed as Ministry-issued codes."
)
jsonlite::write_json(prov, "data/manifests/INTERIOR_ACQUISITION.json", auto_unbox=TRUE, pretty=TRUE)
message("Wrote ", nrow(result), " official constituency-party rows from ", source_url)
