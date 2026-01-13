"""
visualizacion_burbujas.py

Proyecto: Comparación entre la burbuja puntocom y la narrativa de burbuja de la IA
Autor: Álvaro García

Requisitos:
    pip install pandas plotly openpyxl
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# ---------------------------------------------------------------------
# 1. Carga de datos
# ---------------------------------------------------------------------

# Dataset procesado generado desde R
df = pd.read_csv(
    "data_processed/indices_dotcom_ia_dataset.csv",
    parse_dates=["date"]
)

# Tabla de eventos (Excel) con columnas: date, event_name, description
events = pd.read_excel(
    "eventos_dotcom_ia.xlsx",
    engine="openpyxl"
)
events["date"] = pd.to_datetime(events["date"])

# ---------------------------------------------------------------------
# 2. Preparación de datos para las visualizaciones
# ---------------------------------------------------------------------

# Ordenamos por índice, periodo y fecha
df = df.sort_values(["index", "period", "date"])

# Etiquetas legibles para los periodos
period_labels = {
    "dotcom": "Burbuja puntocom (1997–2002)",
    "ia": "Narrativa IA (2020–2025)"
}
df["period_label"] = df["period"].map(period_labels)

# 2.1. Precio normalizado (base 100 al inicio de cada índice y periodo)
df["close_indexed_100"] = (
    df
    .groupby(["index", "period"])["close"]
    .transform(lambda s: s / s.iloc[0] * 100)
)

# 2.2. Drawdown en porcentaje
df["drawdown_pct"] = df["drawdown"] * 100

# 2.3. Filtramos filas válidas para volatilidad rolling
df_vol = df[df["rolling_vol_30d"].notna()].copy()

# 2.4. Preparamos datos de eventos alineados con el Nasdaq
# Usamos solo el Nasdaq como índice principal para anotar eventos
nasdaq = df[df["index"] == "NASDAQ"].sort_values("date")

# Inferimos el periodo del evento por su fecha
def infer_period(date):
    if pd.Timestamp("1997-01-01") <= date <= pd.Timestamp("2002-12-31"):
        return "dotcom"
    elif pd.Timestamp("2020-01-01") <= date <= pd.Timestamp("2025-12-31"):
        return "ia"
    else:
        return None

events["period"] = events["date"].apply(infer_period)
events = events[events["period"].notna()].copy()
events["period_label"] = events["period"].map(period_labels)

# Alineamos cada evento con el último día de cotización disponible del Nasdaq
events_aligned = pd.merge_asof(
    events.sort_values("date"),
    nasdaq[["date", "close", "period", "period_label"]].sort_values("date"),
    on="date",
    direction="backward",
    suffixes=("_event", "_idx")
)

# Unificamos las columnas de periodo y etiqueta de periodo
events_aligned["period_final"] = events_aligned["period_event"].where(
    events_aligned["period_event"].notna(),
    events_aligned["period_idx"]
)
events_aligned["period_label_final"] = events_aligned["period_label_event"].where(
    events_aligned["period_label_event"].notna(),
    events_aligned["period_label_idx"]
)

events_aligned = events_aligned.rename(
    columns={
        "period_final": "period",
        "period_label_final": "period_label"
    }
)

# Nos quedamos solo con las columnas que vamos a usar
events_aligned = events_aligned[["date", "event_name", "description", "close", "period", "period_label"]]


# ---------------------------------------------------------------------
# 3. Gráfico 1: Evolución normalizada de Nasdaq y S&P 500
# ---------------------------------------------------------------------

from plotly.subplots import make_subplots
import plotly.graph_objects as go

df_dotcom = df[df["period"] == "dotcom"].copy()
df_ia = df[df["period"] == "ia"].copy()

fig1 = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    subplot_titles=[
        "Burbuja puntocom (1997–2002)",
        "Narrativa IA (2020–2025)"
    ]
)

colors = {
    "NASDAQ": "#1f77b4",
    "SP500": "#ff7f0e"
}

# Panel izquierdo: puntocom
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_dotcom[df_dotcom["index"] == idx_name]
    fig1.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["close_indexed_100"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=True
        ),
        row=1,
        col=1
    )

# Panel derecho: IA
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_ia[df_ia["index"] == idx_name]
    fig1.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["close_indexed_100"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=False  # para no duplicar leyenda
        ),
        row=1,
        col=2
    )

fig1.update_xaxes(
    title_text="Fecha",
    row=1,
    col=1,
    dtick="M12",          # tick cada 12 meses
    tickformat="%Y"       # mostrar solo el año
)

fig1.update_xaxes(
    title_text="Fecha",
    row=1,
    col=2,
    dtick="M12",
    tickformat="%Y"
)

fig1.update_layout(
    template="plotly_white",
    title="Evolución normalizada de Nasdaq y S&P 500 en las dos épocas",
    legend_title_text="Índice",
    height=500,
    margin=dict(l=60, r=20, t=80, b=40)
)


# ---------------------------------------------------------------------
# 4. Gráfico 2: Drawdown por índice y periodo
# ---------------------------------------------------------------------

fig2 = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    subplot_titles=[
        "Burbuja puntocom (1997–2002)",
        "Narrativa IA (2020–2025)"
    ]
)

min_dd = df["drawdown_pct"].min()

# Panel izquierdo: puntocom
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_dotcom[df_dotcom["index"] == idx_name]
    fig2.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["drawdown_pct"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=True
        ),
        row=1,
        col=1
    )

# Panel derecho: IA
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_ia[df_ia["index"] == idx_name]
    fig2.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["drawdown_pct"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=False
        ),
        row=1,
        col=2
    )

fig2.update_xaxes(
    title_text="Fecha",
    row=1,
    col=1,
    dtick="M12",
    tickformat="%Y"
)

fig2.update_xaxes(
    title_text="Fecha",
    row=1,
    col=2,
    dtick="M12",
    tickformat="%Y"
)

fig2.update_yaxes(
    title_text="Drawdown (%)",
    row=1,
    col=1,
    ticksuffix=" %",
    range=[-100, 10]   # rango más amplio para tener espacio arriba
)

fig2.update_yaxes(
    title_text="Drawdown (%)",
    row=1,
    col=2,
    ticksuffix=" %",
    range=[-100, 10]   # misma ampliación
)


fig2.update_layout(
    template="plotly_white",
    title="Profundidad de las caídas (drawdown) en cada burbuja",
    legend_title_text="Índice",
    height=500,
    margin=dict(l=60, r=20, t=80, b=40)
)

# ---------------------------------------------------------------------
# 5. Gráfico 3: Volatilidad rolling a 30 días
# ---------------------------------------------------------------------

df_vol_dotcom = df_vol[df_vol["period"] == "dotcom"].copy()
df_vol_ia = df_vol[df_vol["period"] == "ia"].copy()

fig3 = make_subplots(
    rows=1,
    cols=2,
    shared_yaxes=True,
    subplot_titles=[
        "Burbuja puntocom (1997–2002)",
        "Narrativa IA (2020–2025)"
    ]
)

# Panel izquierdo: puntocom
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_vol_dotcom[df_vol_dotcom["index"] == idx_name]
    fig3.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["rolling_vol_30d"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=True
        ),
        row=1,
        col=1
    )

# Panel derecho: IA
for idx_name in ["NASDAQ", "SP500"]:
    sub = df_vol_ia[df_vol_ia["index"] == idx_name]
    fig3.add_trace(
        go.Scatter(
            x=sub["date"],
            y=sub["rolling_vol_30d"],
            mode="lines",
            name=idx_name,
            line=dict(color=colors[idx_name]),
            showlegend=False
        ),
        row=1,
        col=2
    )

fig3.update_xaxes(
    title_text="Fecha",
    row=1,
    col=1,
    dtick="M12",
    tickformat="%Y"
)

fig3.update_xaxes(
    title_text="Fecha",
    row=1,
    col=2,
    dtick="M12",
    tickformat="%Y"
)

fig3.update_yaxes(title_text="Volatilidad rolling 30 días", row=1, col=1)

fig3.update_layout(
    template="plotly_white",
    title="Volatilidad rolling a 30 días en las dos épocas",
    legend_title_text="Índice",
    height=500,
    margin=dict(l=60, r=20, t=80, b=40)
)


# ---------------------------------------------------------------------
# 6. Gráfico 4: Línea del Nasdaq con eventos anotados
# ---------------------------------------------------------------------

# Creamos dos subgráficos: uno para cada periodo
fig4 = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=False,
    subplot_titles=[
        "Nasdaq en la burbuja puntocom (1997–2002)",
        "Nasdaq en la narrativa de IA (2020–2025)"
    ]
)

# Dotcom
nasdaq_dotcom = nasdaq[nasdaq["period"] == "dotcom"]
events_dotcom = events_aligned[events_aligned["period"] == "dotcom"]

fig4.add_trace(
    go.Scatter(
        x=nasdaq_dotcom["date"],
        y=nasdaq_dotcom["close"],
        mode="lines",
        name="Nasdaq (dotcom)",
        line=dict(color="#1f77b4")
    ),
    row=1,
    col=1
)

if not events_dotcom.empty:
    fig4.add_trace(
        go.Scatter(
            x=events_dotcom["date"],
            y=events_dotcom["close"],
            mode="markers",
            name="Eventos dotcom",
            marker=dict(size=9, color="#d62728", symbol="circle"),
            text=events_dotcom["event_name"],
            hovertemplate="<b>%{text}</b><br>Fecha: %{x|%Y-%m-%d}<br>Cierre Nasdaq: %{y:.2f}<extra></extra>"
        ),
        row=1,
        col=1
    )

# IA
nasdaq_ia = nasdaq[nasdaq["period"] == "ia"]
events_ia = events_aligned[events_aligned["period"] == "ia"]

fig4.add_trace(
    go.Scatter(
        x=nasdaq_ia["date"],
        y=nasdaq_ia["close"],
        mode="lines",
        name="Nasdaq (IA)",
        line=dict(color="#2ca02c")
    ),
    row=2,
    col=1
)

if not events_ia.empty:
    fig4.add_trace(
        go.Scatter(
            x=events_ia["date"],
            y=events_ia["close"],
            mode="markers",
            name="Eventos IA",
            marker=dict(size=9, color="#ff7f0e", symbol="diamond"),
            text=events_ia["event_name"],
            hovertemplate="<b>%{text}</b><br>Fecha: %{x|%Y-%m-%d}<br>Cierre Nasdaq: %{y:.2f}<extra></extra>"
        ),
        row=2,
        col=1
    )

fig4.update_xaxes(title_text="Fecha", row=1, col=1)
fig4.update_xaxes(title_text="Fecha", row=2, col=1)
fig4.update_yaxes(title_text="Cierre Nasdaq", row=1, col=1)
fig4.update_yaxes(title_text="Cierre Nasdaq", row=2, col=1)

fig4.update_layout(
    template="plotly_white",
    height=700,
    margin=dict(l=60, r=20, t=80, b=40),
    legend_title_text="Serie"
)

# ---------------------------------------------------------------------
# 7. Exportar a HTML con narrativa en capítulos
# ---------------------------------------------------------------------

fig1_html = pio.to_html(fig1, include_plotlyjs=False, full_html=False)
fig2_html = pio.to_html(fig2, include_plotlyjs=False, full_html=False)
fig3_html = pio.to_html(fig3, include_plotlyjs=False, full_html=False)
fig4_html = pio.to_html(fig4, include_plotlyjs=False, full_html=False)

html_template = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <title>Dos burbujas, una narrativa: Nasdaq y S&amp;P 500 entre la puntocom y la IA</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{
            margin: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f5f7;
            color: #222;
        }}
        header {{
            background: #111827;
            color: #f9fafb;
            padding: 1.5rem 0;
        }}
        header .wrapper {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }}
        header h1 {{
            margin: 0;
            font-size: 1.6rem;
        }}
        header p {{
            margin: 0.25rem 0 0;
            font-size: 0.95rem;
            opacity: 0.85;
        }}
        main {{
            max-width: 1100px;
            margin: 1.5rem auto 2rem;
            padding: 0 1.5rem;
        }}
        section {{
            background: #ffffff;
            border-radius: 0.75rem;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
        }}
        h2 {{
            margin-top: 0;
            font-size: 1.3rem;
        }}
        p.lead {{
            font-size: 0.98rem;
            line-height: 1.5;
            margin-bottom: 0.75rem;
        }}
        .plot-container {{
            margin-top: 0.75rem;
        }}
        footer {{
            text-align: center;
            font-size: 0.8rem;
            padding: 1rem 0 1.5rem;
            color: #6b7280;
        }}
        @media (max-width: 768px) {{
            section {{
                padding: 1rem 1rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="wrapper">
            <h1>Dos burbujas, una narrativa</h1>
            <p>Comparación entre la burbuja puntocom y la actual narrativa de burbuja de la IA a través del Nasdaq y el S&amp;P 500.</p>
        </div>
    </header>
    <main>
        <section id="capitulo1">
            <h2>1. Dos épocas, dos narrativas de mercado</h2>
            <p class="lead">
                Este primer gráfico muestra la evolución normalizada del Nasdaq y del S&amp;P 500 en cada una de las dos épocas.
                El panel de la izquierda recoge la burbuja puntocom (1997–2002) y el de la derecha la narrativa reciente de la IA (2020–2025).
                Al fijar una base 100 en el inicio de cada periodo y compartir la escala vertical, podemos comparar de forma directa
                la intensidad relativa de las subidas y de las correcciones entre ambas burbujas.
            </p>
            <div class="plot-container">
                {fig1_html}
            </div>
        </section>

        <section id="capitulo2">
            <h2>2. La profundidad de las caídas: drawdown</h2>
            <p class="lead">
                El segundo gráfico se centra en el drawdown, es decir, en la caída porcentual desde el máximo histórico hasta cada día.
                De nuevo, el panel izquierdo muestra la fase puntocom y el derecho la época de la IA, compartiendo la misma escala vertical.
                Esto permite visualizar de un vistazo la severidad de las correcciones en cada burbuja y comparar el comportamiento
                de ambos índices en las fases de ajuste.
            </p>
            <div class="plot-container">
                {fig2_html}
            </div>
        </section>

        <section id="capitulo3">
            <h2>3. Volatilidad como síntoma de tensión</h2>
            <p class="lead">
                El tercer gráfico representa la volatilidad calculada como la desviación estándar de los retornos diarios en una ventana
                móvil de 30 días. El panel izquierdo corresponde a la burbuja puntocom y el derecho a la narrativa de la IA. De este modo
                se puede observar cómo la volatilidad se incrementa en los momentos de mayor tensión del mercado y hasta qué punto
                los patrones difieren entre las dos épocas.
            </p>
            <div class="plot-container">
                {fig3_html}
            </div>
        </section>

        <section id="capitulo4">
            <h2>4. Eventos clave en el Nasdaq</h2>
            <p class="lead">
                Por último, este gráfico sitúa algunos eventos significativos sobre la trayectoria del Nasdaq en cada época,
                desde fusiones emblemáticas y quiebras corporativas en la burbuja puntocom hasta hitos recientes como el lanzamiento de ChatGPT,
                las inversiones en modelos fundacionales o la revalorización de Nvidia.
                Las anotaciones permiten conectar la narrativa cualitativa con el comportamiento cuantitativo del índice.
            </p>
            <div class="plot-container">
                {fig4_html}
            </div>
        </section>
    </main>
    <footer>
        Proyecto de visualización – Máster de Ciencia de Datos (UOC)
    </footer>
</body>
</html>
"""

# Guardamos el HTML final
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("Visualización generada en 'index.html'")

