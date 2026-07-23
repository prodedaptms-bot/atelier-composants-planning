import json
import pandas as pd
import streamlit as st

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Atelier Composants - Planning",
    page_icon="🛠️",
    layout="wide",
)

# --- CHARGEMENT DES DONNÉES (Exemple de structure standard) ---
# (Adapte cette fonction selon la façon dont tu charges ton fichier JSON chez toi)
def charger_donnees():
    try:
        with open("donnees_composants.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Structure de secours si le fichier n'existe pas encore
        return {
            "absences_prod": [],
            "absences_cons": [],
            "techniciens_cons": []
        }

def sauvegarder_donnees(data):
    with open("donnees_composants.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = charger_donnees()
absences_prod = data.get("absences_prod", [])
absences_cons = data.get("absences_cons", [])
techniciens_cons = data.get("techniciens_cons", [])
auj = pd.Timestamp.today().date()

# --- CRÉATION DES ONGLET DE L'APPLICATION (7 onglets au total) ---
# Note : Ajuste les noms des 5 premiers selon ce que tu avais déjà dans ton application
onglets = st.tabs([
    "📊 Tableau de Bord", 
    "👥 Équipe", 
    "⚙️ Composants", 
    "📋 Planning Prod", 
    "🔧 Maintenance", 
    "📅 Absences", 
    "💾 Sauvegarde"
])

# --- ONGLET 0 à 4 : TES AUTRES FONCTIONNALITÉS EXISTANTES ---
with onglets[0]:
    st.header("Tableau de Bord")
    st.write("Bienvenue sur ton application de gestion d'atelier.")

with onglets[1]:
    st.header("Gestion de l'Équipe")

with onglets[2]:
    st.header("Gestion des Composants")

with onglets[3]:
    st.header("Planning de Production")

with onglets[4]:
    st.header("Maintenance")


# ==========================================
# ONGLET 5 : GESTION DES ABSENCES (Complet)
# ==========================================
with onglets[5]:
    st.header("📅 Gestion des Absences")

    # Création des deux colonnes pour séparer Production et Consommables
    c_ab1, c_ab2 = st.columns(2)

    # --- 1. ABSENCES DE PRODUCTION ---
    with c_ab1:
        st.subheader("Absences de Production")
        
        # Formulaire ou enregistrement d'absence prod (à adapter si tu as un form dédié)
        # S'il y a un formulaire prod, il se place ici.
        
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
                st.success("Absence Prod supprimée.")
                st.rerun()
        else:
            st.info("Aucune absence de production enregistrée.")

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
        else:
            st.warning("Ajoute d'abord des techniciens consommables pour enregistrer des absences.")
                
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
                st.success("Absence Consommables supprimée.")
                st.rerun()


# ==========================================
# ONGLET 6 : SAUVEGARDE & DONNÉES BRUTES
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
