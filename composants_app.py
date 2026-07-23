import json
import pandas as pd
import streamlit as st

# --- Supposition : tes variables globales, chargement de données ('data'), 
#      'auj' et la définition de tes onglets sont faits un peu plus haut.
# Ex: onglets = st.tabs(["Onglet 1", "Onglet 2", "Onglet 3", "Onglet 4", "Onglet 5", "Absences", "Sauvegarde"])


# ==========================================
# GESTION DES ABSENCES (À placer dans ton onglet dédié aux absences)
# ==========================================

# --- 1. ABSENCES DE PRODUCTION ---
c_ab1, c_ab2 = st.columns(2)

with c_ab1:
    st.subheader("Absences de Production")
    # ... (ton formulaire d'enregistrement d'absence prod se trouve ici)
    
    if absences_prod:
        st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)
        id_sup_abp = st.selectbox(
            "ID Absence Prod à supprimer",
            [a["id"] for a in absences_prod],
            key="del_abp",
        )
        if st.button("Supprimer Absence Prod"):
            data["absences_prod"] = [
                a for a in absences_prod if a["id"] != id_sup_abp
            ]
            sauvegarder_donnees(data)
            st.success("Absence Prod supprimée avec succès.")
            st.rerun()

# --- 2. ABSENCES CONSOMMABLES ---
with c_ab2:
    st.subheader("Absences Consommables")
    if techniciens_cons:
        with st.form("absc"):
            t_c = st.selectbox(
                "Tech Cons.", [t["nom"] for t in techniciens_cons]
            )
            m_c = st.selectbox(
                "Motif Cons.",
                ["Congés Payés", "RTT", "Maladie", "Formation"],
                key="motif_c",
            )
            db_c = st.date_input("Début Cons.", auj, key="ab_dbc")
            df_c = st.date_input("Fin Cons.", auj, key="ab_dfc")
            
            if st.form_submit_button("Enregistrer absence Cons."):
                absences_cons.append({
                    "id": f"ABS-C-{len(absences_cons)+1:03d}",
                    "technicien": t_c,
                    "motif": m_c,
                    "date_debut": str(db_c),
                    "date_fin": str(df_c),
                })
                data["absences_cons"] = absences_cons
                sauvegarder_donnees(data)
                st.success("Absence Consommables enregistrée.")
                st.rerun()
                
    if absences_cons:
        st.dataframe(pd.DataFrame(absences_cons), use_container_width=True)
        id_sup_abc = st.selectbox(
            "ID Absence Cons. à supprimer",
            [a["id"] for a in absences_cons],
            key="del_abc",
        )
        if st.button("Supprimer Absence Cons."):
            data["absences_cons"] = [
                a for a in absences_cons if a["id"] != id_sup_abc
            ]
            sauvegarder_donnees(data)
            st.success("Absence Consommables supprimée avec succès.")
            st.rerun()


# ==========================================
# ONGLET 7 : SAUVEGARDE & DONNÉES BRUTES (À placer tout à la fin)
# ==========================================

with onglets[6]:
    st.header("💾 Sauvegarde, Restauration & Données Brutes")

    st.subheader("📥 Export global de la base de données")
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Télécharger le fichier JSON complet",
        data=json_str,
        file_name="donnees_composants_sauvegarde.json",
        mime="application/json",
    )

    st.markdown("---")
    st.subheader("📤 Importer / Restaurer une sauvegarde JSON")
    fichier_upload = st.file_uploader(
        "Sélectionner un fichier JSON de sauvegarde", type=["json"]
    )
    if fichier_upload is not None:
        try:
            donnees_importees = json.load(fichier_upload)
            if st.button("Confirmer et remplacer les données actuelles"):
                sauvegarder_donnees(donnees_importees)
                st.success("Données restaurées avec succès ! Rechargement...")
                st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier JSON : {e}")

    st.markdown("---")
    st.subheader("🔍 Visualisation brute des données (JSON)")
    st.json(data)
