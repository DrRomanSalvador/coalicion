#!/usr/bin/env Rscript

# CIS historical survey integration from official CIS microdata.
# Derived percentages are INTENCION_DE_VOTO_MICRODATOS, not the
# CIS scenario-based published "estimación de voto".

options(stringsAsFactors=FALSE)
required <- c("opencis","dplyr","readr","tibble","haven","purrr")
missing <- required[!vapply(required, requireNamespace, logical(1), quietly=TRUE)]
if (length(missing)) stop("Missing R packages: ", paste(missing, collapse=", "))
dir.create("data", showWarnings=FALSE, recursive=TRUE)

queries <- c("barometro","preelectoral","postelectoral","elecciones generales")
search_complete <- function(q) {
  x <- opencis::search_all_cis(q=q, from="2004-01-01", to="2023-12-31",
                               sort="publishDate+", catalogo="estudio")
  complete <- attr(x, "complete")
  if (!isTRUE(complete)) stop("FAIL-CLOSED: incomplete CIS catalog response for query: ", q)
  x
}
studies <- dplyr::bind_rows(lapply(queries, search_complete)) |>
  dplyr::distinct(study, .keep_all=TRUE) |>
  dplyr::filter(date >= as.Date("2004-01-01"), date <= as.Date("2023-12-31")) |>
  dplyr::arrange(date, study)
if (!nrow(studies)) stop("CIS catalog returned no historical studies.")

nonparty <- "(no sabe|no contesta|ningun|ninguna|ninguno|blanco|no votaria|no votaría|no piensa votar|abstencion|abstención|indeciso|indecisa|ns/nc)"

extract_study <- function(study_id, study_date, title) {
  df <- tryCatch(opencis::read_cis(study_id), error=function(e) {
    message("SKIP CIS ", study_id, ": ", conditionMessage(e)); NULL
  })
  if (is.null(df) || !nrow(df)) return(NULL)
  dict <- tryCatch(opencis::get_data_dictionary(df), error=function(e) NULL)
  if (is.null(dict) || !nrow(dict)) return(NULL)

  labels <- tolower(ifelse(is.na(dict$label), "", as.character(dict$label)))
  candidates <- which(
    grepl("intenc.*voto|voto.*(hoy|ahora|partido)|partido.*(votaria|votaría)", labels) &
    !grepl("recuerdo|ultima.*eleccion|última.*elección|eleccion.*anterior|elección.*anterior", labels)
  )
  if (!length(candidates)) return(NULL)

  score <- vapply(candidates, function(i) {
    vl <- dict$value_labels[[i]]
    if (is.null(vl)) return(0)
    sum(grepl("psoe|partido popular|^pp$|vox|podemos|sumar|iu|izquierda unida|ciudadanos|^cs$|erc|esquerra|junts|ci[uú]|pnv|eaj|bildu|bng|coalici[oó]n canaria|upn|mas pais|más país|comprom[ií]s|pacma|otros",
              tolower(names(vl))))
  }, numeric(1))
  idx <- candidates[which.max(score)]
  var <- dict$variable[[idx]]
  if (!var %in% names(df)) return(NULL)
  vl <- dict$value_labels[[idx]]
  if (is.null(vl) || !length(vl)) return(NULL)

  weight_name <- intersect(c("PESO","PESOCCAA"), names(df))[1]
  w <- if (!is.na(weight_name)) suppressWarnings(as.numeric(df[[weight_name]])) else rep(1, nrow(df))
  v <- suppressWarnings(as.numeric(df[[var]]))
  ok <- !is.na(v) & !is.na(w) & w > 0
  if (!any(ok)) return(NULL)
  total <- sum(w[ok])

  tibble::tibble(codigo_estudio=as.character(study_id), fecha_encuesta=as.character(study_date),
    partido=unname(names(vl)), value_code=as.numeric(vl)) |>
    dplyr::filter(!grepl(nonparty, tolower(partido), perl=TRUE)) |>
    dplyr::rowwise() |>
    dplyr::mutate(estimacion_voto=100 * sum(w[ok & v == value_code]) / total) |>
    dplyr::ungroup() |>
    dplyr::filter(is.finite(estimacion_voto), estimacion_voto >= 0, estimacion_voto <= 100) |>
    dplyr::mutate(
      encuesta=title,
      tipo_encuesta=dplyr::case_when(
        grepl("postelectoral", tolower(title)) ~ "postelectoral",
        grepl("preelectoral", tolower(title)) ~ "preelectoral",
        TRUE ~ "barometro"
      ),
      fuente="Centro de Investigaciones Sociológicas (CIS)",
      nivel_fuente="PRIMARY_OFFICIAL_MICRODATA",
      metodo="weighted_microdata_vote_intention", variable=var, sample_size=sum(ok)
    ) |>
    dplyr::select(fecha_encuesta, partido, estimacion_voto, tipo_encuesta, encuesta,
                  fuente, nivel_fuente, metodo, codigo_estudio, variable, sample_size)
}

pieces <- vector("list", nrow(studies))
for (i in seq_len(nrow(studies))) {
  s <- studies[i,]
  message("CIS ", i, "/", nrow(studies), ": ", s$study, " ", s$title)
  pieces[[i]] <- extract_study(s$study, s$date, s$title)
}
result <- dplyr::bind_rows(pieces)
if (!nrow(result)) stop("No CIS vote-intention observations could be extracted.")
if (nrow(result) < 1000) stop("Fail-closed: only ", nrow(result), " CIS observations extracted; expected >=1000.")
result <- result |> dplyr::arrange(fecha_encuesta, codigo_estudio, partido)
readr::write_csv(result, "data/encuestas_historicas_2004_2023.csv")
message("Wrote ", nrow(result), " CIS vote-intention observations from ",
        dplyr::n_distinct(result$codigo_estudio), " studies.")
