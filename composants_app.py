import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Planification Atelier", layout="wide"
)

# --- INITIALISATION DES DONNÉES ---
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
st.title("🛠️ Tableau de Bord - Planification Atelier & Ligne de Production")

# Navigation complète par onglets
tab_planning, tab_saisie, tab_gestion, tab_export = st.tabs([
    "📅 Planning & Gantt", 
    "➕ Saisie des OFs", 
    "⚙️ Gestion & Statuts", 
    "📥 Export & Analyse"
])

# --- 1. VUE PLANNING & GANTT ---
with tab_planning:
    st.subheader("Planning de la Semaine par Technicien")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        semaine_offset = st.slider(
            "Décalage de semaine", min_value=-2, max_value=4, value=0, key="slider_semaine"
        )
    with col_opt2:
        afficher_fermes = st.checkbox("Afficher les OFs Terminés/Supprimés dans le Gantt", value=False)

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
            
            # Application du filtre selon la case cochée
            if afficher_fermes:
                matches = [
                    f"[{x['statut'].upper()}] {x.get('sous_ensemble') or x.get('consommable')} (x{x['quantite']})"
                    for x in tous_ofs_cascade
                    if x.get("assigne") == tech
                    and x.get("date_debut_cascade") <= j_str <= x.get("date_fin_cascade")
                ]
            else:
                matches = [
                    f"{x.get('sous_ensemble') or x.get('consommable')} (x{x['quantite']})"
                    for x in tous_ofs_cascade
                    if x.get("assigne") == tech
                    and x.get("statut") not in ["Terminé", "Supprimé"]
                    and x.get("date_debut_cascade") <= j_str <= x.get("date_fin_cascade")
                ]

            ligne_tech[j.strftime("%A %d/%m")] = " | ".join(matches) if matches else ""
        grille_gantt_couleur.append(ligne_tech)

    if grille_gantt_couleur:
        df_gantt = pd.DataFrame(grille_gantt_couleur)
        st.dataframe(df_gantt, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun planning à afficher pour cette semaine.")

# --- 2. SAISIE DES OFs ---
with tab_saisie:
    st.subheader("Création d'un Nouvel Ordre de Fabrication")
    with st.form("form_nouveau_of"):
        c1, c2 = st.columns(2)
        with c1:
            type_element = st.radio("Type d'élément", ["Sous-ensemble", "Consommable"])
            if type_element == "Sous-ensemble":
                val_sous_ensemble = st.text_input("Nom du sous-ensemble")
                val_consommable = ""
            else:
                val_sous_ensemble = ""
                val_consommable = st.text_input("Nom du consommable")
            
            quantite = st.number_input("Quantité", min_value=1, value=1)

        with c2:
            assigne = st.selectbox("Assigner à un technicien", st.session_state.techs)
            date_debut = st.date_input("Date de début (Cascade)", datetime.date.today())
            date_fin = st.date_input("Date de fin (Cascade)", datetime.date.today() + datetime.timedelta(days=2))

        submitted = st.form_submit_button("Ajouter l'OF")
        if submitted:
            nouveau_id = max([o["id"] for o in st.session_state.ofs], default=0) + 1
            st.session_state.ofs.append({
                "id": nouveau_id,
                "sous_ensemble": val_sous_ensemble,
                "consommable": val_consommable,
                "quantite": quantite,
                "assigne": assigne,
                "statut": "Planifié",
                "date_debut_cascade": str(date_debut),
                "date_fin_cascade": str(date_fin),
            })
            st.success(f"OF #{nouveau_id} ajouté avec succès !")
            st.rerun()

# --- 3. GESTION & STATUTS ---
with tab_gestion:
    st.subheader("Gestion, Modification et Suivi des Statuts")
    st.markdown("Passez rapidement un OF en **Terminé** ou **Supprimé** pour l'écarter automatiquement du calcul de charge de l'atelier.")

    for i, of in enumerate(st.session_state.ofs):
        titre_element = of.get('sous_ensemble') or of.get('consommable') or "Élément sans nom"
        with st.expander(f"OF #{of['id']} - {titre_element} (Assigné : {of['assigne']} | Statut actuel : {of['statut']})"):
            col_g, col_d = st.columns([2, 1])
            with col_g:
                st.write(f"**Quantité :** {of['quantite']}")
                st.write(f"**Période :** Du {of['date_debut_cascade']} au {of['date_fin_cascade']}")
            with col_d:
                nouveau_statut = st.selectbox(
                    "Modifier le statut",
                    ["Planifié", "En cours", "Terminé", "Supprimé"],
                    index=["Planifié", "En cours", "Terminé", "Supprimé"].index(of['statut']),
                    key=f"select_statut_{i}"
                )
                if nouveau_statut != of['statut']:
                    st.session_state.ofs[i]['statut'] = nouveau_statut
                    st.rerun()

# --- 4. EXPORT & ANALYSE ---
with tab_export:
    st.subheader("Exports et Données Brutes")
    if st.session_state.ofs:
        df_export = pd.DataFrame(st.session_state.ofs)
        st.dataframe(df_export, use_container_width=True)
        
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Télécharger les données en CSV",
            data=csv,
            file_name='planning_atelier.csv',
            mime='text/csv',
        )
    else:
        st.info("Aucune donnée à exporter.")
