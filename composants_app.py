import pandas as pd
import streamlit as st

st.title("Outil de Logistique et Planification - Atelier")

# Exemple de données de stock / production
data = {
    "Référence": ["REF-001", "REF-002", "REF-003"],
    "Composant": ["Boîtier", "Carte Mère", "Câblage"],
    "Quantité de base": [100, 250, 500],
    "Unité": ["Pièces", "Pièces", "Mètres"],
}
df = pd.DataFrame(data)

st.subheader("Données Actuelles")
st.dataframe(df, use_container_width=True)

---

## ⚙️ Option de Conversion de Quantité
# Sélection du facteur de conversion (ex: conversion en lots, palettes ou sous-unités)
type_conversion = st.selectbox(
    "Choisir un mode de conversion des quantités :",
    ["Aucune", "Conversion en Lots (1 lot = 10 unités)", "Conversion en Millivis"],
)

# Application de la logique de conversion
df_converti = df.copy()
if type_conversion == "Conversion en Lots (1 lot = 10 unités)":
  df_converti["Quantité Convertie"] = df_converti["Quantité de base"] / 10
  df_converti["Unité Convertie"] = "Lots"
elif type_conversion == "Conversion en Millivis":
  df_converti["Quantité Convertie"] = df_converti["Quantité de base"] * 1000
  df_converti["Unité Convertie"] = "Unités de base"
else:
  df_converti["Quantité Convertie"] = df_converti["Quantité de base"]
  df_converti["Unité Convertie"] = df_converti["Unité"]

st.subheader("Résultat avec Quantités Converties")
st.dataframe(df_converti, use_container_width=True)

---

## 📥 Export des Données
# Bouton de téléchargement CSV
csv_data = df_converti.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Télécharger les données converties (CSV)",
    data=csv_data,
    file_name="suivi_atelier_converti.csv",
    mime="text/csv",
)
