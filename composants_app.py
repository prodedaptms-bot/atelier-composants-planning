import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Planification Atelier", layout="wide"
)

# --- INITIALISATION DES DONNÉES SIMULÉES ---
if "ofs" not in st.session_state:
    st.session_state.ofs = [
        {
            "id": 1,
            "sous_ensemble": "Focal Pak A",
            "consommable": "",
            "quantite": 5,
            "assigne": "Thomas",
            "statut": "En cours",
            "date_debut_cascade": "2026-07-20",
            "date_fin_cascade": "2026-07-24",
        },
        {
            "id": 2,
            "sous_ensemble": "",
            "consommable": "Câblage B",
            "quantite": 12,
            "assigne": "Sarah",
            "statut": "Planifié",
            "date_debut_cascade": "2026-07-21",
            "date_fin_cascade": "2026-07-23",
        },
    ]

if "techs" not in st.session_state:
    st.session_state.techs = ["Thomas", "Sarah", "Marc", "Julie"]

# --- INTERFACE PRINCIPALE ---
st.title("🛠️ Tableau de Bord - Planification Atelier")

tab_planning, tab_gestion = st.tabs(["📅 Vue Planning & Gantt", "⚙️ Gestion des OFs & Statuts"])

with tab_planning:
    st.subheader("Planning de la Semaine par Technicien")

    semaine_offset = st.slider(
        "Décalage de semaine", min_value=-2, max_value=4, value=0, key="slider_semaine"
    )
    aujourdhui = datetime.date.today()
    debut_semaine = aujourdhui - datetime.timedelta(
        days=aujourdhui.weekday()
    ) + datetime.timedelta(weeks=semaine_offset)
    jours_semaine = [
        debut_semaine + datetime.timedelta(days=i) for i in range(5)
    ]

    tous_techs = st.session_state.techs
    tous_ofs_cascade = st.session_state.ofs

    tech_couleur_map = {
        "Thomas": "🟢",
        "Sarah": "🔵",
        "Marc": "🟠",
        "Julie": "🟣",
    }

    grille_gantt_couleur = []

    for tech in tous_techs:
        couleur = tech_couleur_map.get(tech, "🔵")
        ligne_tech = {"Technicien": f"{tech} {couleur}"}
        for j in jours_semaine:
            j_str = str(j)
            # Exclusion automatique des OFs Terminés ou Supprimés du planning
            matches = [
                f"{x.get('sous_ensemble') or x.get('consommable')} (x{x['quantite']})"
                for x in tous_ofs_cascade
                if x.get("assigne") == tech
                and x.get("statut") not in ["Terminé", "Supprimé"]
                and x.get("date_debut_cascade")
                <= j_str
                <= x.get("date_fin_cascade")
            ]
            ligne_tech[j.strftime("%A %d/%m")] = (
                " | ".join(matches) if matches else ""
            )
        grille_gantt_couleur.append(ligne_tech)

    if grille_gantt_couleur:
        df_gantt = pd.DataFrame(grille_gantt_couleur)
        st.dataframe(df_gantt, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun planning à afficher pour cette semaine.")

with tab_gestion:
    st.subheader("Gestion et Suivi des Ordres de Fabrication")
    st.markdown("Modifiez les statuts ci-dessous pour mettre à jour instantanément la charge de l'atelier.")

    # Interface de mise à jour rapide par OF
    for i, of in enumerate(st.session_state.ofs):
        with st.expander(f"OF #{of['id']} - {of.get('sous_ensemble') or of.get('consommable')} (Assigné à : {of['assigne']})"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.text(f"Quantité : {of['quantite']}")
                st.text(f"Dates : du {of['date_debut_cascade']} au {of['date_fin_cascade']}")
            
            with col2:
                nouveau_statut = st.selectbox(
                    "Statut",
                    ["Planifié", "En cours", "Terminé", "Supprimé"],
                    index=["Planifié", "En cours", "Terminé", "Supprimé"].index(of['statut']),
                    key=f"statut_{i}"
                )
                if nouveau_statut != of['statut']:
                    st.session_state.ofs[i]['statut'] = nouveau_statut
                    st.rerun()

            with col3:
                if of['statut'] == "Terminé":
                    st.success("Statut : Terminé")
                elif of['statut'] == "Supprimé":
                    st.error("Statut : Supprimé")
                else:
                    st.info(f"Statut : {of['statut']}")
