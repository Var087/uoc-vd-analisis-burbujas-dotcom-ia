# Script de descarga y preparación de datos bursátiles para el proyecto dotcom vs IA
# Autor: Álvaro García
# Descripción: descarga datos diarios del Nasdaq (^IXIC) y del S&P 500 (^GSPC) desde Yahoo Finance
# y construye un conjunto de datos procesado con las variables definidas en la Parte I de la práctica.

# -------------------------------------------------------------------
# 0. Carga de paquetes
# -------------------------------------------------------------------

# Ejecutar una sola vez si no están instalados:
# install.packages(c("quantmod", "dplyr", "tidyr", "readr", "lubridate", "zoo"))

library(quantmod)
library(dplyr)
library(tidyr)
library(readr)
library(lubridate)
library(zoo)

# -------------------------------------------------------------------
# 1. Directorios de trabajo
# -------------------------------------------------------------------

data_raw_dir <- "data_raw"
data_processed_dir <- "data_processed"

if (!dir.exists(data_raw_dir)) dir.create(data_raw_dir)
if (!dir.exists(data_processed_dir)) dir.create(data_processed_dir)

# -------------------------------------------------------------------
# 2. Parámetros: índices y rango temporal
# -------------------------------------------------------------------

tickers <- c("^IXIC", "^GSPC")
names(tickers) <- c("NASDAQ", "SP500")

start_date <- as.Date("1997-01-01")
end_date   <- as.Date("2025-12-31")

# -------------------------------------------------------------------
# 3. Función auxiliar para descargar datos de Yahoo Finance
# -------------------------------------------------------------------

download_index_yahoo <- function(ticker, index_name, from, to, raw_dir) {
  message("Descargando datos para ", index_name, " (", ticker, ")...")
  
  xts_obj <- getSymbols(
    ticker,
    src         = "yahoo",
    from        = from,
    to          = to,
    auto.assign = FALSE
  )
  
  df <- data.frame(
    date = index(xts_obj),
    coredata(xts_obj),
    row.names = NULL
  )
  
  # Renombrar columnas a un formato estándar: date, open, high, low, close, volume, adj_close
  colnames(df) <- c("date", "open", "high", "low", "close", "volume", "adj_close")
  
  df <- df %>%
    mutate(
      date  = as.Date(date),
      index = index_name
    )
  
  # Guardar datos crudos en CSV
  raw_path <- file.path(raw_dir, paste0(tolower(index_name), "_raw_1997_2025.csv"))
  write_csv(df, raw_path)
  
  return(df)
}

# -------------------------------------------------------------------
# 4. Descarga de datos crudos para Nasdaq y S&P 500
# -------------------------------------------------------------------

nasdaq_df <- download_index_yahoo(tickers["NASDAQ"], "NASDAQ", start_date, end_date, data_raw_dir)
sp500_df  <- download_index_yahoo(tickers["SP500"],  "SP500",  start_date, end_date, data_raw_dir)

# -------------------------------------------------------------------
# 5. Combinación de índices y selección de periodos de interés
# -------------------------------------------------------------------

all_df <- bind_rows(nasdaq_df, sp500_df) %>%
  arrange(index, date) %>%
  mutate(
    period = case_when(
      date >= as.Date("1997-01-01") & date <= as.Date("2002-12-31") ~ "dotcom",
      date >= as.Date("2020-01-01") & date <= as.Date("2025-12-31") ~ "ia",
      TRUE ~ NA_character_
    )
  ) %>%
  filter(!is.na(period))

# -------------------------------------------------------------------
# 6. Cálculo de variables derivadas básicas
# -------------------------------------------------------------------

all_df <- all_df %>%
  group_by(index, period) %>%
  arrange(date, .by_group = TRUE) %>%
  mutate(
    trading_day_id = row_number(),
    daily_return   = close / lag(close) - 1,
    log_return     = log(close) - log(lag(close)),
    max_to_date    = cummax(close),
    drawdown       = close / max_to_date - 1
  ) %>%
  ungroup()

# -------------------------------------------------------------------
# 7. Cálculo de volatilidad rolling a 30 días
# -------------------------------------------------------------------

all_df <- all_df %>%
  group_by(index, period) %>%
  arrange(date, .by_group = TRUE) %>%
  mutate(
    rolling_vol_30d = rollapply(
      data   = daily_return,
      width  = 30,
      FUN    = sd,
      align  = "right",
      fill   = NA_real_,
      na.rm  = TRUE
    )
  ) %>%
  ungroup()

# -------------------------------------------------------------------
# 8. Cálculo del ratio NASDAQ / S&P 500
# -------------------------------------------------------------------

ratio_df <- all_df %>%
  select(date, index, close) %>%
  pivot_wider(
    names_from  = index,
    values_from = close
  ) %>%
  mutate(
    nasdaq_sp500_ratio = NASDAQ / SP500
  ) %>%
  select(date, nasdaq_sp500_ratio)

all_df <- all_df %>%
  left_join(ratio_df, by = "date")

# -------------------------------------------------------------------
# 9. Incorporación de eventos (tabla externa opcional)
# -------------------------------------------------------------------
# Se espera un fichero data_raw/events.csv con, al menos:
#   date (fecha en formato AAAA-MM-DD)
#   event_name (descripción breve del evento)
#   Opcionalmente, columnas adicionales como 'period' o 'index'
#
# Si no existe el archivo, se crea un indicador de evento vacío.

events_path <- file.path(data_raw_dir, "events.csv")

if (file.exists(events_path)) {
  events_df <- read_csv(events_path, show_col_types = FALSE) %>%
    mutate(date = as.Date(date))
  
  all_df <- all_df %>%
    left_join(events_df, by = "date") %>%
    mutate(
      event_flag = !is.na(event_name)
    )
} else {
  all_df <- all_df %>%
    mutate(
      event_name = NA_character_,
      event_flag = FALSE
    )
}

# -------------------------------------------------------------------
# 10. Selección y orden de variables finales
# -------------------------------------------------------------------

final_df <- all_df %>%
  select(
    date,
    index,
    period,
    trading_day_id,
    open,
    high,
    low,
    close,
    adj_close,
    volume,
    daily_return,
    log_return,
    rolling_vol_30d,
    max_to_date,
    drawdown,
    nasdaq_sp500_ratio,
    event_flag,
    event_name
  ) %>%
  arrange(index, period, date)

# -------------------------------------------------------------------
# 11. Guardar el conjunto de datos procesado
# -------------------------------------------------------------------

processed_path <- file.path(data_processed_dir, "indices_dotcom_ia_dataset.csv")
write_csv(final_df, processed_path)

message("Conjunto de datos procesado guardado en: ", processed_path)
