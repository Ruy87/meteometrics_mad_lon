import requests
import pandas as pd
from pandas import json_normalize

url_mad = "https://meteometrics.rlopez.org/historical-data/MAD"
url_lon = "https://meteometrics.rlopez.org/historical-data/LON"

try:
    # Realiza la petición para Madrid
    response = requests.get(url_mad)
    response.raise_for_status()
    raw_data_madrid = response.json()

    # Realiza la petición para Londres
    response = requests.get(url_lon)
    response.raise_for_status()
    raw_data_londres = response.json()

    df_madrid = json_normalize(raw_data_madrid)
    df_madrid["city"] = "Madrid"

    df_londres = json_normalize(raw_data_londres)
    df_londres["city"] = "Londres"

    df = pd.concat([df_madrid, df_londres], ignore_index=True)

    registros_iniciales = len(df)

    # 1. Unifica el separador decimal en las columnas de métricas.
    columnas_metricas = df.columns[
        df.columns.str.startswith("metrics.")
        & ~df.columns.str.endswith(".unit")
    ]
    df[columnas_metricas] = df[columnas_metricas].replace(",", ".", regex=True)

    # 2. Excluye la ciudad y las unidades de las columnas numéricas.
    columnas_no_numericas = [
        "city",
        "metrics.temperature.unit",
        "metrics.precipitation.unit",
    ]
    columnas_numericas = df.columns.difference(columnas_no_numericas)

    # 3. Convierte texto numérico; los valores inválidos pasan a nulos.
    df[columnas_numericas] = df[columnas_numericas].apply(
        pd.to_numeric, errors="coerce"
    )

    # 4. Trata el valor sentinela como dato ausente.
    df[columnas_numericas] = df[columnas_numericas].replace(-999.0, float("nan"))

    # 5. Conserva un registro por ciudad, año y mes.
    df = df.drop_duplicates(subset=["city", "year", "month"])
    registros_borrados = registros_iniciales - len(df)

    # 6. Ordena cronológicamente dentro de cada ciudad.
    df = df.sort_values(
        ["city", "year", "month"], ignore_index=True
    )

    # 7. Convierte temperaturas Fahrenheit a Celsius solo donde corresponde.
    columnas_temperatura = [
        "metrics.temperature.max",
        "metrics.temperature.avg",
        "metrics.temperature.min",
    ]
    es_fahrenheit = df["metrics.temperature.unit"].eq("F")
    df.loc[es_fahrenheit, columnas_temperatura] = (
        df.loc[es_fahrenheit, columnas_temperatura] - 32
    ) * 5 / 9
    df.loc[es_fahrenheit, "metrics.temperature.unit"] = "C"

    # Convierte la lluvia de pulgadas a milímetros solo donde corresponde.
    es_pulgadas = df["metrics.precipitation.unit"].eq("inches")
    df.loc[es_pulgadas, "metrics.precipitation.avg"] = (
        df.loc[es_pulgadas, "metrics.precipitation.avg"] * 25.4
    )
    df.loc[es_pulgadas, "metrics.precipitation.unit"] = "mm"

    print(df)

    # Resume los registros antes y después de eliminar duplicados.
    with open("informe_limpieza.txt", "w", encoding="utf-8") as informe:
        informe.write(
            "Informe de limpieza de datos\n"
            f"Registros iniciales: {registros_iniciales}\n"
            f"Registros borrados: {registros_borrados}\n"
            f"Registros finales: {len(df)}\n"
        )
except requests.exceptions.RequestException as e:
    print(f'Error en la petición: {e}')
    print(df)

  