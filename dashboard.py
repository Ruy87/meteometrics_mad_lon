from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_PATH = DATA_DIR / "df_total.parquet"

CITY_COLORS = {
    "Madrid": "#D62728",
    "Londres": "#1F77B4",
}
MONTH_LABELS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

st.set_page_config(page_title="Clima: Madrid y Londres", layout="wide")
st.title("Comparativa climática: Madrid y Londres")

if not DATA_PATH.is_file():
    st.error(
        "No se encontró data/df_total.parquet. "
        "Ejecuta primero app.py para generar los datos."
    )
    st.stop()

df_total = pd.read_parquet(DATA_PATH, engine="pyarrow")
df_total["date"] = pd.to_datetime(
    {
        "year": df_total["year"],
        "month": df_total["month"],
        "day": 1,
    },
    errors="coerce",
)
df_total = df_total.dropna(subset=["date"]).sort_values(
    ["city", "date"], ignore_index=True
)

st.subheader("Resumen instantáneo")
ultimos_registros = (
    df_total.groupby("city", group_keys=False).tail(1).set_index("city")
)
resumen_historico = df_total.groupby("city").agg(
    temperatura_media=("metrics.temperature.avg", "mean"),
    precipitacion_total=("metrics.precipitation.avg", "sum"),
)

tarjetas = st.columns(len(CITY_COLORS))
for tarjeta, city in zip(tarjetas, CITY_COLORS):
    with tarjeta:
        st.markdown(f"### {city}")
        if city not in ultimos_registros.index:
            st.info("No hay datos disponibles para esta ciudad.")
            continue

        ultimo = ultimos_registros.loc[city]
        periodo = ultimo["date"].strftime("%b %Y")
        tarjeta.metric(
            f"Temperatura media · {periodo}",
            f"{ultimo['metrics.temperature.avg']:.1f} °C",
        )
        tarjeta.metric(
            f"Precipitación · {periodo}",
            f"{ultimo['metrics.precipitation.avg']:.1f} mm",
        )
        tarjeta.caption(
            "Media histórica: "
            f"{resumen_historico.loc[city, 'temperatura_media']:.1f} °C · "
            "precipitación acumulada: "
            f"{resumen_historico.loc[city, 'precipitacion_total']:.1f} mm"
        )

st.subheader("Evolución de temperaturas")
st.caption(
    "La banda representa el intervalo entre la temperatura mínima y máxima; "
    "la línea muestra la temperatura media mensual."
)

fig_evolucion = go.Figure()
for city, color in CITY_COLORS.items():
    datos_ciudad = df_total[df_total["city"] == city]
    fig_evolucion.add_trace(
        go.Scatter(
            x=datos_ciudad["date"],
            y=datos_ciudad["metrics.temperature.min"],
            mode="lines",
            line={"color": color, "width": 1},
            name=f"{city} mínima",
            showlegend=False,
            hovertemplate="%{x|%b %Y}<br>Mínima: %{y:.1f} °C<extra></extra>",
        )
    )
    fig_evolucion.add_trace(
        go.Scatter(
            x=datos_ciudad["date"],
            y=datos_ciudad["metrics.temperature.max"],
            mode="lines",
            line={"color": color, "width": 1},
            fill="tonexty",
            fillcolor=(
                "rgba(214, 39, 40, 0.14)"
                if city == "Madrid"
                else "rgba(31, 119, 180, 0.14)"
            ),
            name=f"{city} máxima",
            showlegend=False,
            hovertemplate="%{x|%b %Y}<br>Máxima: %{y:.1f} °C<extra></extra>",
        )
    )
    fig_evolucion.add_trace(
        go.Scatter(
            x=datos_ciudad["date"],
            y=datos_ciudad["metrics.temperature.avg"],
            mode="lines",
            line={"color": color, "width": 2.5},
            name=city,
            hovertemplate="%{x|%b %Y}<br>Media: %{y:.1f} °C<extra></extra>",
        )
    )

fig_evolucion.update_layout(
    template="plotly_white",
    xaxis_title="Mes",
    yaxis_title="Temperatura (°C)",
    hovermode="x unified",
    legend_title="Ciudad",
)
st.plotly_chart(fig_evolucion, width="stretch")

for city in CITY_COLORS:
    datos_ciudad = df_total[df_total["city"] == city]
    medias = datos_ciudad.set_index("date")["metrics.temperature.avg"].dropna()
    if not medias.empty:
        mes_calido = medias.idxmax()
        mes_frio = medias.idxmin()
        st.markdown(
            f"**{city}:** la temperatura media alcanza su máximo en "
            f"{MONTH_LABELS[mes_calido.month - 1]} ({medias.max():.1f} °C) "
            f"y su mínimo en {MONTH_LABELS[mes_frio.month - 1]} "
            f"({medias.min():.1f} °C). La banda permite comparar la amplitud "
            "mensual de las temperaturas máximas y mínimas."
        )

st.subheader("Perfil climático mensual")
st.caption(
    "Cada valor es el promedio histórico del mes correspondiente. "
    "La temperatura y la precipitación se muestran en radares separados "
    "para conservar sus unidades."
)

climatologia = (
    df_total.groupby(["city", "month"], as_index=False)
    .agg(
        temperatura_media=("metrics.temperature.avg", "mean"),
        precipitacion_media=("metrics.precipitation.avg", "mean"),
    )
)
fig_radar = make_subplots(
    rows=1,
    cols=2,
    specs=[[{"type": "polar"}, {"type": "polar"}]],
    subplot_titles=("Temperatura media (°C)", "Precipitación media (mm)"),
)

for city, color in CITY_COLORS.items():
    datos_mensuales = (
        climatologia[climatologia["city"] == city]
        .set_index("month")
        .reindex(range(1, 13))
    )
    fig_radar.add_trace(
        go.Scatterpolar(
            theta=MONTH_LABELS,
            r=datos_mensuales["temperatura_media"],
            mode="lines+markers",
            fill="toself",
            fillcolor=(
                "rgba(214, 39, 40, 0.12)"
                if city == "Madrid"
                else "rgba(31, 119, 180, 0.12)"
            ),
            line={"color": color, "width": 2},
            marker={"color": color},
            name=city,
            legendgroup=city,
        ),
        row=1,
        col=1,
    )
    fig_radar.add_trace(
        go.Scatterpolar(
            theta=MONTH_LABELS,
            r=datos_mensuales["precipitacion_media"],
            mode="lines+markers",
            fill="toself",
            fillcolor=(
                "rgba(214, 39, 40, 0.12)"
                if city == "Madrid"
                else "rgba(31, 119, 180, 0.12)"
            ),
            line={"color": color, "width": 2},
            marker={"color": color},
            name=city,
            legendgroup=city,
            showlegend=False,
        ),
        row=1,
        col=2,
    )

fig_radar.update_layout(
    template="plotly_white",
    height=560,
    legend_title="Ciudad",
    legend={"groupclick": "togglegroup"},
    polar={"radialaxis": {"visible": True, "ticksuffix": " °C"}},
    polar2={"radialaxis": {"visible": True, "ticksuffix": " mm"}},
)
st.plotly_chart(fig_radar, width="stretch")

for city in CITY_COLORS:
    datos_mensuales = climatologia[climatologia["city"] == city]
    meses_temperatura = datos_mensuales.dropna(subset=["temperatura_media"])
    meses_lluvia = datos_mensuales.dropna(subset=["precipitacion_media"])
    if not meses_temperatura.empty and not meses_lluvia.empty:
        mes_mas_calido = meses_temperatura.loc[
            meses_temperatura["temperatura_media"].idxmax()
        ]
        mes_mas_lluvioso = meses_lluvia.loc[
            meses_lluvia["precipitacion_media"].idxmax()
        ]
        st.markdown(
            f"**{city}:** el mes más cálido es "
            f"{MONTH_LABELS[int(mes_mas_calido['month']) - 1]} "
            f"({mes_mas_calido['temperatura_media']:.1f} °C de media); "
            "el más lluvioso es "
            f"{MONTH_LABELS[int(mes_mas_lluvioso['month']) - 1]} "
            f"({mes_mas_lluvioso['precipitacion_media']:.1f} mm de media). "
            "El radar superpuesto facilita comparar la estacionalidad de "
            "temperatura y lluvia entre ambas ciudades."
        )
