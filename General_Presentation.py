import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import altair as alt
import json
import numpy as np

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    # Load the dataset
    dpe_data = pd.read_csv("data\dpe-v2-logements-neufs.csv")
    # Convert date columns to datetime format
    dpe_data["Date_établissement_DPE"] = pd.to_datetime(dpe_data["Date_établissement_DPE"], errors="coerce")
    return dpe_data

dpe_data = load_data()
dpe_data.drop_duplicates(subset='Adresse_(BAN)', inplace=True)
dpe_data.dropna(subset=['Date_établissement_DPE'], inplace=True)

cart_adress = ['Adresse_(BAN)', 'Type_bâtiment',
                'Surface_habitable_logement', 'Etiquette_GES',
                'N°DPE', 'Etiquette_DPE', 'Modèle_DPE',
                'Date_établissement_DPE']
chart_conso = ["Conso_chauffage_é_finale", "Conso_éclairage_é_finale",
                "Conso_ECS_é_finale",
                "Conso_refroidissement_é_finale",
                "Conso_auxiliaires_é_finale"]
chart_cout = ["Coût_chauffage", "Coût_éclairage", "Coût_ECS",
                "Coût_refroidissement"]

dpe_data.drop_duplicates(subset='Adresse_(BAN)', inplace=True)
dpe_data.dropna(subset=cart_adress + chart_conso + chart_cout, inplace=True)

st.markdown("""
# 🏠 Buildings for Tomorrow: Visualizing the Energy Performance of New Homes in France Since July 2021

**Authors**: Sofia Bouaila, Alexandre Boistard  
**Affiliation**: Mathematics and Data Science, Data and Information Science, CentraleSupélec  
**Date**: March 20, 2025  

Our team has chosen to focus on the energy performance of newly constructed 
residential buildings. This topic is highly relevant because reducing energy 
consumption and carbon emissions in the housing sector is a significant 
step toward meeting environmental and sustainability goals. By examining 
how new homes perform in terms of energy efficiency, we can gain insights 
into current building practices, compliance with regulations, and areas for 
future improvements. This research is especially pertinent in the context 
of ongoing efforts to combat climate change and optimize resource usage in 
urban development.
""")

st.subheader("Global Trends: are new buildings getting more efficient?")

# Copy the data
trend_data = dpe_data.copy()

# Create a monthly period
trend_data["month"] = trend_data["Date_établissement_DPE"].dt.to_period("M").dt.to_timestamp()

# Define a helper function to compute weighted average, weighted variance, and standard error
def weighted_stats(group):
    # Weighted average of CO₂ emissions
    w = group["Surface_habitable_logement"]
    x = group["Emission_GES_5_usages_par_m²"]
    weighted_mean = (x * w).sum() / w.sum()
    # Weighted variance (using weights as given)
    weighted_var = ((w * (x - weighted_mean)**2).sum()) / w.sum()
    # Standard error: sqrt(variance)/sqrt(n)
    n = len(group)
    error = np.sqrt(weighted_var) / np.sqrt(n) if n > 0 else 0
    return pd.Series({
        "avg_co2": weighted_mean,
        "building_count": n,
        "error": error,
        "lower": weighted_mean - error,
        "upper": weighted_mean + error
    })

# Group by (month, building type) and compute weighted stats
grouped_types = (
    trend_data
    .groupby(["month", "Type_bâtiment"], dropna=True)
    .apply(weighted_stats)
    .reset_index()
)

# Also compute overall monthly weighted stats
grouped_overall = (
    trend_data
    .groupby("month", dropna=True)
    .apply(weighted_stats)
    .reset_index()
)
grouped_overall["Type_bâtiment"] = "Overall"

# Combine the DataFrames
combined_df = pd.concat([grouped_types, grouped_overall], ignore_index=True)

# ---------------------------------------------------------------------------
# MANUALLY REMOVE AN OUTLIER FOR A SPECIFIC MONTH & BUILDING TYPE
# Example: Suppose the outlier is for "appartement" in November 2024,
# and we'll set it to the December 2024 value for "appartement".
# ---------------------------------------------------------------------------
outlier_month = pd.Timestamp("2024-11-01")
fix_month = pd.Timestamp("2024-12-01")

mask_outlier = (
    (combined_df["Type_bâtiment"] == "appartement") &
    (combined_df["month"] == outlier_month)
)
mask_fix = (
    (combined_df["Type_bâtiment"] == "appartement") &
    (combined_df["month"] == fix_month)
)

if not combined_df[mask_fix].empty:
    fix_value = combined_df.loc[mask_fix, "avg_co2"].values[0]
    combined_df.loc[mask_outlier, "avg_co2"] = fix_value

# ---------------------------------------------------------------------------
# Filter out "immeuble" from the per-building-type data (but leave overall intact)
# ---------------------------------------------------------------------------
filtered_df = combined_df[
    (combined_df["Type_bâtiment"] != "Overall") &
    (combined_df["Type_bâtiment"] != "immeuble")
]
overall_df_before = combined_df[combined_df["Type_bâtiment"] == "Overall"]
overall_df = overall_df_before[
    overall_df_before["Type_bâtiment"].str.lower() != "immeuble"]

# ---------------------------------------------------------------------------
# CREATE THE ALTAR CHART
# ---------------------------------------------------------------------------
# Lines for each building type (filtered)
lines_by_type = (
    alt.Chart(filtered_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y("avg_co2:Q", title="Avg CO₂ (kg CO₂e/m²/yr)"),
        color=alt.Color("Type_bâtiment:N", legend=alt.Legend(title="Building Type")),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("Type_bâtiment:N", title="Building Type"),
            alt.Tooltip("avg_co2:Q", title="Avg CO₂ (kg/m²/yr)", format=".2f"),
            alt.Tooltip("building_count:Q", title="New Buildings Count")
        ]
    )
)

# Overall line
overall_line = (
    alt.Chart(overall_df)
    .mark_line(point=True, color="black", strokeDash=[4, 2])
    .encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y("avg_co2:Q", title="Avg CO₂ (kg CO₂e/m²/yr)"),
        tooltip=[
            alt.Tooltip("month:T", title="Month"),
            alt.Tooltip("avg_co2:Q", title="Overall Avg CO₂ (kg/m²/yr)", format=".2f"),
            alt.Tooltip("building_count:Q", title="New Buildings Count")
        ]
    )
)




# Layer all charts together
final_chart = alt.layer(
    lines_by_type,
    overall_line).resolve_scale(y='shared').encode(
        x=alt.X("month:T", title="Month"),
        y=alt.Y(title="Avg CO₂ (kg/m²/yr)", scale=alt.Scale(domain=[0,
                                                                    15])),
    )

st.altair_chart(final_chart, use_container_width=True)

st.markdown("""
This chart shows the average CO₂ emissions (kg CO₂-eq/m²/yr) for two 
building types over time:

- **Appartement** (blue line)
- **Maison** (dotted black line)

On the x-axis, you can see monthly data points spanning from mid-2022 
through 2024, while the y-axis indicates the average CO₂ emissions 
per square meter per year. 

This chart can be useful for politicians, urban planners, 
and decision-makers to assess the effectiveness of current policies and 
propose new ones. 

Observations:
- The **Appartement** line generally trends higher, with a few noticeable 
spikes.
- The **Maison** line remains lower overall but still shows some variation.
- We see overall downward trend in houses, but apartments do not seem to 
show improvement before 2024, which seems a bit better.

These data help us explore whether policy changes, technological 
advancements, or other factors might be influencing the carbon footprint of 
new buildings over time.

Note that we removed the "immeuble" type from the analysis, as their
data is noisy. We also manually fixed an outlier for the "appartement" 
type in November 2024 by replacing it with the December 2024 value.""")


