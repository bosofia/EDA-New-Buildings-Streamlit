import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

from General_Presentation import load_data

# Load data
dpe_data = load_data()
dpe_data.drop_duplicates(subset='Adresse_(BAN)', inplace=True)

#---------------------------------------------------------------------------------------
# --------------------   AVERAGE DPE AND GES BY DEPARTEMENT --------------------------
# ---------------------------------------------------------------------------------------

st.subheader("📮​ Breakdown by Departement of Average DPE and GES", help="Compared to the average of number of DPE and GES Etiquettes per Departement")

departement = st.selectbox("Choose a Departement", options=dpe_data["N°_département_(BAN)"].unique().tolist())

dpeb = {
    "Etiquette":["A", "B", "C", "D", "E", "F", "G"],
    "Etiquette_DPE":[0, 0, 0, 0, 0, 0, 0],
    "Etiquette_GES":[0, 0, 0, 0, 0, 0, 0],
}
dpe_m = pd.DataFrame(dpeb)
for i, et in enumerate(dpe_m["Etiquette"]):
    dpe_m.at[i,"Etiquette_DPE"] = len(dpe_data[dpe_data["Etiquette_DPE"]==et])/len(dpe_data["N°_département_(BAN)"].unique())
    dpe_m.at[i,"Etiquette_GES"] = len(dpe_data[dpe_data["Etiquette_GES"]==et])/len(dpe_data["N°_département_(BAN)"].unique())

dpe_m_melted = dpe_m.melt(
    id_vars='Etiquette',
    value_vars=['Etiquette_DPE', 'Etiquette_GES'],
    var_name='count_type',
    value_name='Count'
)

basem = alt.Chart(dpe_m_melted).mark_bar(color="lightgrey").encode(
    x=alt.X('Count:Q', 
            axis=alt.Axis(labelExpr="abs(datum.value)"),
            scale=alt.Scale(domain=[-1600, 1600]),
            title='Etiquette DPE                                Count                                  Etiquette GES'
        ),
    y=alt.Y('Etiquette:N', 
            sort=alt.SortField("Etiquette", order="ascending"),
            axis=alt.Axis(labels=False),
            title=''
        )
).transform_calculate(
    Count="datum.count_type == 'Etiquette_DPE' ? -datum.Count : datum.Count"  
).properties(
    width=700,
    height=400,
    title="Average DPE and GES by Departement"
)

dpeb_p = pd.DataFrame(dpeb)
for i, et in enumerate(dpeb_p["Etiquette"]):
    dpeb_p.at[i,"Etiquette_DPE"] = len(dpe_data[(dpe_data["N°_département_(BAN)"]==departement) & (dpe_data["Etiquette_DPE"]==et)])
    dpeb_p.at[i,"Etiquette_GES"] = len(dpe_data[(dpe_data["N°_département_(BAN)"]==departement) & (dpe_data["Etiquette_GES"]==et)])

dpeb_p_melted = dpeb_p.melt(
    id_vars='Etiquette',
    value_vars=['Etiquette_DPE', 'Etiquette_GES'],
    var_name='count_type',
    value_name='Count'
)
chart3 = alt.Chart(dpeb_p_melted).mark_bar(clip=True, opacity=0.6).encode(
    x=alt.X('Count:Q', 
        ),
    y=alt.Y('Etiquette:N', 
            sort=alt.SortField("Etiquette", order="ascending")
        ),
    # color=alt.Color('count_type:N', 
    #                legend=alt.Legend(title="Etiquette Type"))
    color=alt.Color('Etiquette:N',
                    legend=alt.Legend(title="Etiquette Type", orient="bottom-right", columns=2),
                    scale=alt.Scale(scheme="redyellowgreen", reverse=True))
    
).transform_calculate(
    Count="datum.count_type == 'Etiquette_DPE' ? -datum.Count : datum.Count"  
)

combined = basem + chart3

st.altair_chart(combined, use_container_width=True)

#---------------------------------------------------------------------------------------
# --------------------   BREAKDOWN PER ADRESS ----------------------------------------
# ---------------------------------------------------------------------------------------

st.subheader("​📫​ Breakdown per Adress")

adress = st.selectbox("Choose an Adress", options=dpe_data['Adresse_(BAN)'].unique().tolist())

col1, col2 = st.columns([2, 2])

# Adress cart
col1.subheader('Adress Cart')

row = dpe_data[dpe_data['Adresse_(BAN)']==adress]

markdown_text = f"""
**Adresse** : {adress}

**Type of Batiment**: {row['Type_bâtiment'].iloc[0]}

**Habitable Area** : {row['Surface_habitable_logement'].iloc[0]} m²

**GES Category** : {row['Etiquette_GES'].iloc[0]}

**N°DPE** :{row['N°DPE'].iloc[0]}

**DPE Category** : {row['Etiquette_DPE'].iloc[0]}

**DPE Model** : {row['Modèle_DPE'].iloc[0]} in {row['Date_établissement_DPE'].iloc[0]}
"""

col1.markdown(markdown_text)

# Show statistics and compare 
col2.subheader("Energy Consumption & Cost", help=f"Compared with batiments with:\n\n Type of Batiment: {row['Type_bâtiment'].iloc[0]}\n\n GES Category: {row['Etiquette_GES'].iloc[0]}\n\n DPE Category: {row['Etiquette_DPE'].iloc[0]}")

query_txt = f"Type_bâtiment =='{row['Type_bâtiment'].iloc[0]}' and Etiquette_GES=='{row['Etiquette_GES'].iloc[0]}' and Etiquette_DPE=='{row['Etiquette_DPE'].iloc[0]}'"
query = dpe_data.query(query_txt)
dfb = {
    "type":["Heating", "Lighting", "ECS", "Cooling"],
    "cost":[np.mean(query["Coût_chauffage"]), np.mean(query["Coût_éclairage"]), np.mean(query["Coût_ECS"]), np.mean(query["Coût_refroidissement"])],
    "conso":[np.mean(query["Conso_chauffage_é_finale"]), np.mean(query["Conso_éclairage_é_finale"]), np.mean(query["Conso_ECS_é_finale"]), np.mean(query["Conso_refroidissement_é_finale"])]
}
dfb = pd.DataFrame(dfb)

base = alt.Chart(dfb).mark_bar(color="lightgrey").encode(
    x=alt.X("type", title='Energy type'),
    y=alt.Y("conso", title="Consumption (kWh)"),
    tooltip=["type", "conso", "cost"]
)

df = {
    "type":["Heating", "Lighting", "ECS", "Cooling"],
    "cost":[row["Coût_chauffage"].iloc[0], row["Coût_éclairage"].iloc[0], row["Coût_ECS"].iloc[0], row["Coût_refroidissement"].iloc[0]],
    "conso":[row["Conso_chauffage_é_finale"].iloc[0], row["Conso_éclairage_é_finale"].iloc[0], row["Conso_ECS_é_finale"].iloc[0], row["Conso_refroidissement_é_finale"].iloc[0]]
}
df = pd.DataFrame(df)

norm = (df['cost'] - df['cost'].min()) / (df['cost'].max() - df['cost'].min()) 
df['color'] = norm  

selection = alt.selection_single(fields=["type"], bind='legend')
bars = alt.Chart(df).mark_bar().encode(
    x=alt.X("type", title='Energy type'),
    y=alt.Y("conso", title="Consumption (kWh)"),
    color=alt.condition(selection,
                        alt.Color('cost:Q', scale=alt.Scale(scheme='oranges'),
                                legend=alt.Legend(title="Cost (€)")),
                        alt.value('lightgrey')),
    tooltip=["type", "conso", "cost"],
).add_selection(selection)

col2.altair_chart(base+bars, theme=None, use_container_width=True)

