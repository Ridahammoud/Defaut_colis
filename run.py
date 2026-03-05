import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Qualité - Défauts équipements", layout="wide")

st.title("📊 Visualisation des défauts par équipement")

uploaded = st.file_uploader("Upload ton fichier (CSV ou Excel)", type=["csv", "xlsx", "xls"])

@st.cache_data
def load_data(file):
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)  # nécessite openpyxl
    return df

def guess_photo_cols(df):
    return [c for c in df.columns if str(c).lower().startswith("photo")]

def to_datetime_safe(s):
    # Ta date ressemble à: 2/28/2026 10:37:00 PM (format US possible)
    # On laisse pandas inférer, mais on tolère les erreurs.
    return pd.to_datetime(s, errors="coerce", infer_datetime_format=True)

if not uploaded:
    st.info("⬆️ Upload un fichier pour commencer.")
    st.stop()

df = load_data(uploaded)

st.subheader("Aperçu des données")
st.dataframe(df.head(20), use_container_width=True)

# --- Paramétrage colonnes (tu peux laisser auto ou choisir)
st.sidebar.header("⚙️ Paramètres")

default_equipment_col = "Équipement" if "Équipement" in df.columns else df.columns[0]
default_date_col = "Début d'intervention" if "Début d'intervention" in df.columns else df.columns[0]

equipment_col = st.sidebar.selectbox("Colonne Équipement", df.columns, index=list(df.columns).index(default_equipment_col))
date_col = st.sidebar.selectbox("Colonne Date (début)", df.columns, index=list(df.columns).index(default_date_col))

photo_cols_auto = guess_photo_cols(df)
photo_cols = st.sidebar.multiselect(
    "Colonnes Photo (liens)",
    df.columns.tolist(),
    default=photo_cols_auto if photo_cols_auto else []
)

examples_per_equipment = st.sidebar.number_input("Nb d'exemples par équipement (top 10)", min_value=1, max_value=50, value=10)

# --- Nettoyage / features temps
work = df.copy()

work[date_col] = to_datetime_safe(work[date_col])
work = work.dropna(subset=[date_col, equipment_col])

# semaine / mois
work["week"] = work[date_col].dt.to_period("W").dt.start_time
work["month"] = work[date_col].dt.to_period("M").dt.start_time

# --- Sélecteurs de période
min_date, max_date = work[date_col].min(), work[date_col].max()
date_range = st.sidebar.date_input(
    "Filtrer sur une période",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)

start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
work = work[(work[date_col] >= start_date) & (work[date_col] <= end_date)]

# --- Fonctions top 10
def top10_by_period(df_, period_col):
    counts = (
        df_.groupby([period_col, equipment_col])
          .size()
          .reset_index(name="defauts")
    )
    # Top 10 global (sur toute la plage filtrée)
    top_global = (
        df_.groupby(equipment_col)
           .size()
           .sort_values(ascending=False)
           .head(10)
           .reset_index(name="defauts")
    )
    return counts, top_global

weekly_counts, weekly_top10_global = top10_by_period(work, "week")
monthly_counts, monthly_top10_global = top10_by_period(work, "month")

# --- Layout
tab1, tab2, tab3 = st.tabs(["📅 Top 10 / Semaine", "🗓️ Top 10 / Mois", "🖼️ Exemples + Photos (Top 10)"])

with tab1:
    st.subheader("Top 10 équipements les plus en défaut (global sur la période filtrée)")
    st.dataframe(weekly_top10_global, use_container_width=True)

    st.subheader("Évolution hebdomadaire (uniquement Top 10 global)")
    top_equipments = set(weekly_top10_global[equipment_col].tolist())
    w = weekly_counts[weekly_counts[equipment_col].isin(top_equipments)]

#    fig = px.bar(
#        w.sort_values("week"),
#        x="week",
#        y="defauts",
#        color=equipment_col,
#        barmode="group",
#        title="Défauts par semaine (Top 10 global)"
#    )
#    st.plotly_chart(fig, use_container_width=True)
    fig = px.bar(
        w.sort_values("week"),
        x="week",
        y="defauts",
        color=equipment_col,
        barmode="group",
        title="Défauts par semaine (Top 10 global)",
        text="defauts",
        custom_data=[equipment_col]
    )

    fig.update_traces(
        texttemplate="%{y}<br>%{customdata[0]}",
        textposition="outside"
    )

    fig.update_layout(
        uniformtext_minsize=8,
        uniformtext_mode="hide"
    )

    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Top 10 équipements les plus en défaut (global sur la période filtrée)")
    st.dataframe(monthly_top10_global, use_container_width=True)

    st.subheader("Évolution mensuelle (uniquement Top 10 global)")
    top_equipments_m = set(monthly_top10_global[equipment_col].tolist())
    m = monthly_counts[monthly_counts[equipment_col].isin(top_equipments_m)]

    fig2 = px.bar(
        m.sort_values("month"),
        x="month",
        y="defauts",
        color=equipment_col,
        barmode="group",
        title="Défauts par mois (Top 10 global)"
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("10 exemples par équipement (Top 10 global) + photos")

    if not photo_cols:
        st.warning("Aucune colonne photo sélectionnée. Sélectionne au moins une colonne 'Photo ...' dans la sidebar.")
        st.stop()

    # Ici je prends le Top 10 global (sur la période filtrée) — tu peux basculer entre weekly_top10_global ou monthly_top10_global si tu veux
    top10_list = weekly_top10_global[equipment_col].tolist()

    for eq in top10_list:
        st.markdown(f"### 🔧 {eq}")

        sample = work[work[equipment_col] == eq].sort_values(date_col, ascending=False).head(examples_per_equipment)

        # Affiche les lignes
        st.dataframe(
            sample[[c for c in [date_col, equipment_col] if c in sample.columns] + [c for c in sample.columns if c not in [date_col, equipment_col]][:6]],
            use_container_width=True
        )

        # Affiche les photos
        cols = st.columns(2)
        with cols[0]:
            st.caption("Photos")
            for _, row in sample.iterrows():
                urls = []
                for pc in photo_cols:
                    val = row.get(pc)
                    if pd.notna(val) and str(val).strip():
                        urls.append(str(val).strip())

                if urls:
                    # Streamlit accepte une liste d’URLs directement
                    st.image(urls, caption=[f"{eq} - {row[date_col]}" for _ in urls], use_container_width=True)
                else:
                    st.info("Aucune photo sur cette ligne.")

        with cols[1]:
            st.caption("Détails (ligne complète)")
            st.dataframe(sample, use_container_width=True)

        st.divider()
