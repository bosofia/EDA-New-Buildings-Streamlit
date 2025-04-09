import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
import json
import numpy as np
import matplotlib.pyplot as plt

from General_Presentation import load_data

# Load data
dpe_data = load_data()
dpe_data.drop_duplicates(subset='Adresse_(BAN)', inplace=True)


# 3. Add UI for Filters
st.sidebar.header("📇 ​Filters")

# 3a. Year Slider
#    Get the min and max years from your DPE date
valid_years = dpe_data["Date_établissement_DPE"].dropna().dt.year
min_year, max_year = int(valid_years.min()), int(valid_years.max())
year_range = st.sidebar.slider(
    "Select a Year Range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year),
    step=1
)

# 3b. Building Type Filter (multi-select)
all_building_types = dpe_data["Type_bâtiment"].dropna().unique().tolist()
selected_building_types = st.sidebar.multiselect(
    "Building Type",
    options=all_building_types,
    default=all_building_types  # By default, select all
)

# 3c. DPE Category Filter (multi-select)
all_categories = dpe_data["Etiquette_DPE"].dropna().unique().tolist()
selected_categories = st.sidebar.multiselect(
    "DPE Category (A, B, C, ...)",
    options=all_categories,
    default=all_categories
)

# 4. Filter the data based on UI selections
filtered_data = dpe_data.copy()

# 4a. Filter by year range
filtered_data = filtered_data[
    (filtered_data["Date_établissement_DPE"].dt.year >= year_range[0]) &
    (filtered_data["Date_établissement_DPE"].dt.year <= year_range[1])
]

# 4b. Filter by building types
filtered_data = filtered_data[
    filtered_data["Type_bâtiment"].isin(selected_building_types)
]

# 4c. Filter by DPE categories
filtered_data_map = filtered_data[
    filtered_data["Etiquette_DPE"].isin(selected_categories).copy()
]

# 5. Group by department to compute metrics for the map
#    Adjust column names as needed. This example calculates:
#    - total_new: count of N°DPE
#    - efg_count: how many are E/F/G
#    - efg_percent: efg_count / total_new
#    - ghg_m2_avg: mean of Emission_GES_5_usages_par_m²
#    - conso_m2_avg: mean of Conso_5_usages_é_finale_par_m² (if available)
if (
    "N°_département_(BAN)" in filtered_data_map.columns and
    "Emission_GES_5_usages_par_m²" in filtered_data_map.columns and
    "N°DPE" in filtered_data_map.columns
):
    dept_summary = (
        filtered_data_map
        .groupby("N°_département_(BAN)")
        .agg(
            total_new=("N°DPE", "count"),
            efg_count=("Etiquette_DPE", lambda x: x.isin(["E", "F", "G"]).sum()),
            ghg_m2_avg=("Emission_GES_5_usages_par_m²", "mean")
            # If you have a column for total consumption per m², uncomment the line below:
            # conso_m2_avg=("Conso_5_usages_é_finale_par_m²", "mean")
        )
        .reset_index()
        .rename(columns={"N°_département_(BAN)": "departement"})
    )

    # efg percentage
    dept_summary["efg_percent"] = dept_summary["efg_count"] / dept_summary["total_new"]

    # Convert department codes to string, zero-pad if needed
    dept_summary["departement"] = dept_summary["departement"].astype(str).str.zfill(2)
else:
    st.write("Error: Required columns not found for department grouping.")
    dept_summary = pd.DataFrame(columns=["departement", "ghg_m2_avg"])

# 6. Load GeoJSON
try:
    with open("data/departements.geojson", "r", encoding="utf-8") as f:
        france_geojson = json.load(f)
except FileNotFoundError:
    st.error("GeoJSON file for French departments not found.")
    france_geojson = None

# 7. Create the Map
st.subheader("🌍 Geographic Overview: Departmental Metrics")
st.markdown(f"""
*Current filters for this map*:
- **Year Range**: {year_range[0]} to {year_range[1]}  
- **Building Types**: {', '.join(selected_building_types)}  
- **DPE Category**: {', '.join(selected_categories)}  
""")
if not dept_summary.empty and france_geojson is not None:
    # Round GHG to 2 decimals in hover
    dept_summary["ghg_m2_avg"] = dept_summary["ghg_m2_avg"].round(2)
    # If you have conso_m2_avg, also round it: dept_summary["conso_m2_avg"] = dept_summary["conso_m2_avg"].round(2)

    fig = px.choropleth(
        dept_summary,
        geojson=france_geojson,
        locations="departement",
        color="ghg_m2_avg",  # color by average GHG
        color_continuous_scale='Reds',
        featureidkey="properties.code",
        hover_data={
            "departement": True,
            "total_new": True,
            "efg_count": True,
            "efg_percent": ":.2%",   # show as percentage
            "ghg_m2_avg": ":.2f"    # 2 decimals
            # If you added conso_m2_avg, include here:
            # "conso_m2_avg": ":.2f"
        },
        labels={
            "departement": "Département",
            "total_new": "Total New Constructions",
            "efg_count": "E/F/G Performers",
            "efg_percent": "E/F/G (%)",
            "ghg_m2_avg": "GHG by m² (kg CO₂e/m²/yr)"
            # If you added conso_m2_avg, also add label:
            # "conso_m2_avg": "Energy by m² (kWh/m²/yr)"
        }
    )

    fig.update_geos(
        fitbounds="locations",
        visible=True,
        showland=True,
        landcolor="white",
        showcoastlines=False,
        projection=dict(type="mercator", scale=5)
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="white",
        geo_bgcolor="white",
        title="Average GHG by m² per Department",
        title_x=0.05,
        title_y=0.99,
        plot_bgcolor="black",
        coloraxis_colorbar=dict(
            title="GHG by m² (kg CO₂e/m²/yr)",
            tickformat=".2f",
            
        )
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.write("No map data to display. Check filters or missing columns.")


# -----------------------------------------------------------------------------
# --------------------  INEFFICIENT BUILDINGS (E/F/G) ------------------------
# -----------------------------------------------------------------------------

# FOCUS ON INEFFICIENT BUILDINGS (E, F, G) - BY DEPARTMENT

st.subheader("🔬​ Focus on Inefficient Buildings (E, F, G) - Detailed Department View")
st.markdown(f"""
*Current filters for this map*:
- **Year Range**: {year_range[0]} to {year_range[1]}  
- **Building Types**: {', '.join(selected_building_types)}  
- *DPE Category is ignored here so we always see a complete departmental overview.*
""")
# Re-use filtered_data_map (year + building type only)
inefficient_data = filtered_data[filtered_data["Etiquette_DPE"].isin(["E", "F", "G"])]

if not inefficient_data.empty:
    # Group by department & DPE category to compute:
    # - building_count: how many E/F/G buildings in each dept
    # - avg_GHG: average GHG per m² for these buildings
    # - avg_conso: average consumption per m² (if you have such a column)
    #   Adjust column names as needed:
    ineff_dept = (
        inefficient_data
        .groupby(["N°_département_(BAN)", "Etiquette_DPE"])
        .agg(
            building_count=("N°DPE", "count"),
            avg_GHG=("Emission_GES_5_usages_par_m²", "mean"),
            # If you have a per-m² consumption column, uncomment:
            # avg_conso=("Conso_5_usages_é_finale_par_m²", "mean")
        )
        .reset_index()
    )

    # Convert department to string, zero-pad if needed
    ineff_dept["N°_département_(BAN)"] = (
        ineff_dept["N°_département_(BAN)"]
        .astype(str)
        .str.zfill(2)
    )
    # Create a stacked bar chart in Altair
    brush_dep = alt.selection(type='interval', encodings=['x'])
    chart = (
        alt.Chart(ineff_dept)
        .mark_bar()
        .encode(
            x=alt.X("N°_département_(BAN):N", title="Département", sort=alt.SortField("building_count", order="descending")),
            y=alt.Y("building_count:Q", title="Number of Inefficient Buildings"),
            color=alt.Color("Etiquette_DPE:N", legend=alt.Legend(title="E/F/G Category"), scale=alt.Scale(scheme="teals")),
            tooltip=[
                alt.Tooltip("N°_département_(BAN):N", title="Département"),
                alt.Tooltip("Etiquette_DPE:N", title="DPE Category"),
                alt.Tooltip("building_count:Q", title="# of Buildings"),
                alt.Tooltip("avg_GHG:Q", title="Avg GHG (kg CO₂e/m²/yr)", format=".2f"),
                # If you have avg_conso:
                # alt.Tooltip("avg_conso:Q", title="Avg Consumption (kWh/m²/yr)", format=".2f")
            ]
        )
        .properties(width=700, height=400)
        .configure_axis(labelAngle=-45)
        .add_selection(brush_dep)
    )

    st.altair_chart(chart, use_container_width=True)

    st.markdown("""
    *This stacked bar chart shows how many inefficient buildings (E, F, G) exist in each 
    département under the **year** and **building type** filters. Hover over a bar to see 
    the average GHG per m² and other metrics. DPE category filtering is intentionally 
    ignored here so we can always see E/F/G data.*
    """)
else:
    st.write("No inefficient buildings (E/F/G) found with the current filters.")

