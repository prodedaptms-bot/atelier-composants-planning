import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Atelier - Pilotage & Planification",
    page_icon="⚙️",
    layout="wide"
)

FICHIER_DONNEES = "donnees_atelier.json"

def charger_donnees():
    if os.path.exists(FICHIER_DONNEES):
        with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {
        "equipe": [],
        "sous_ensembles": [],
        "consommables": [],
        "absences": [],
        "ofs": []
    }

def sauvegarder_donnees(data):
    with open(FICHIER_DONNEES, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = charger_donnees()

st.title("⚙️ Atelier - Pilotage, Ordonnancement & Planification")

# --- NAVIGATION / ONGLETS ---
onglets = st.tabs([
    "📊 Tableau de Bord",
    "👥 Équipe",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "🌴 Congés & Absences",
    "📅 Planification & Cascade",
    "💾 Sauvegarde & Données"
])

# --- ONGLET 0 : TABLEAU DE BORD ---
with onglets[0]:
    st.header("📊 Tableau de Bord & Indicateurs de Charge")
    st.info("Vue globale des capacités et de la charge de l'atelier.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Techniciens actifs", len(data.get("equipe", [])))
    with col2:
        st.metric("Modèles Sous-ensembles", len(data.get("sous_ensembles", [])))
    with col3:
        st.metric("Références Consommables", len(data.get("consommables", [])))

# --- ONGLET 1 : ÉQUIPE ---
with onglets[1]:
    st.header("👥 Gestion de l'Équipe")
    
    with st.form("form_tech"):
        st.subheader("Ajouter un technicien")
        nom_tech = st.text_input("Nom du technicien")
        atelier_tech = st.selectbox("Atelier de rattachement", ["Production Sous-Ensembles", "Consommables", "Polyvalent"])
        capacité_h = st.number_input("Capacité hebdomadaire (heures)", value=35.0)
        
        if st.form_submit_button("Enregistrer le technicien"):
            if nom_tech:
                data.setdefault("equipe", []).append({
                    "id": f"TECH-{len(data.get('equipe', []))+1:03d}",
                    "nom": nom_tech,
                    "atelier": atelier_tech,
                    "capacite": capacité_h
                })
                sauvegarder_donnees(data)
                st.success(f"Technicien {nom_tech} ajouté avec succès !")
                st.rerun()
            else:
                st.error("Le nom est obligatoire.")

    st.subheader("Effectif actuel")
    if data.get("equipe"):
        st.dataframe(pd.DataFrame(data["equipe"]), use_container_width=True)
    else:
        st.info("Aucun technicien enregistré.")

# --- ONGLET 2 : SOUS-ENSEMBLES ---
with onglets[2]:
    st.header("⚙️ Création & Catalogue des Sous-ensembles")
    
    with st.form("form_se"):
        st.subheader("Nouveau modèle de Sous-ensemble")
        nom_se = st.text_input("Nom du sous-ensemble")
        ref_se = st.text_input("Référence")
        temps_se = st.number_input("Temps de fabrication unitaire (heures)", min_value=0.01, value=2.0)
        desc_se = st.text_area("Description")
        
        if st.form_submit_button("Enregistrer le Sous-ensemble"):
            if nom_se:
                data.setdefault("sous_ensembles", []).append({
                    "id": f"SE-{len(data.get('sous_ensembles', []))+1:03d}",
                    "nom": nom_se,
                    "reference": ref_se,
                    "temps_fabrication": temps_se,
                    "description": desc_se
                })
                sauvegarder_donnees(data)
                st.success("Sous-ensemble enregistré !")
                st.rerun()
            else:
                st.error("Le nom est obligatoire.")

    st.subheader("Catalogue actuel")
    if data.get("sous_ensembles"):
        st.dataframe(pd.DataFrame(data["sous_ensembles"]), use_container_width=True)
    else:
        st.info("Aucun sous-ensemble configuré.")

# --- ONGLET 3 : CONSOMMABLES ---
with onglets[3]:
    st.header("📦 Gestion & Références des Consommables")

    with st.form("form_creer_cons"):
        st.subheader("Ajouter un nouveau Consommable")
        nom_cons = st.text_input("Nom du Consommable")
        ref_cons = st.text_input("Référence / Code Consommable")

        # Choix du mode de saisie du temps (Intégration de la demande lot vs unitaire)
        mode_saisie = st.radio(
            "Mode de calcul du temps de fabrication",
            [
                "Temps unitaire direct (ex: X heures par pièce)",
                "Lot de production (ex: X pièces pour Y heures)",
            ],
        )

        if mode_saisie == "Temps unitaire direct (ex: X heures par pièce)":
            temps_fab_cons = st.number_input(
                "Temps de fabrication unitaire (heures)",
                min_value=0.01,
                value=0.5,
                step=0.01,
            )
            calcul_temps_unitaire = temps_fab_cons
        else:
            col_lot1, col_lot2 = st.columns(2)
            with col_lot1:
                qte_lot_ref = st.number_input(
                    "Quantité de pièces du lot", min_value=1, value=60
                )
            with col_lot2:
                temps_lot_ref = st.number_input(
                    "Temps total pour ce lot (heures)", min_value=0.1, value=8.0
                )

            calcul_temps_unitaire = temps_lot_ref / qte_lot_ref
            st.info(
                f"💡 Temps unitaire recalculé automatiquement : "
                f"**{calcul_temps_unitaire:.4f} h / pièce** (soit {temps_lot_ref}h pour {qte_lot_ref} pièces)."
            )

        desc_cons = st.text_area("Description / Instructions Consommable", key="desc_c")

        if st.form_submit_button("Enregistrer le Consommable"):
            if nom_cons:
                nouveau_modele_cons = {
                    "id": f"CONS-{len(data.get('consommables', [])) + 1:03d}",
                    "nom": nom_cons,
                    "reference": ref_cons,
                    "temps_fabrication": calcul_temps_unitaire,
                    "description": desc_cons,
                }
                data.setdefault("consommables", []).append(nouveau_modele_cons)
                sauvegarder_donnees(data)
                st.success(f"Consommable '{nom_cons}' créé avec succès !")
                st.rerun()
            else:
                st.error("Le nom du consommable est obligatoire.")

    st.markdown("---")
    st.subheader("Catalogue actuel des Consommables")
    liste_cons_actuelle = data.get("consommables", [])
    if liste_cons_actuelle:
        df_cons = pd.DataFrame(liste_cons_actuelle)
        st.dataframe(df_cons, use_container_width=True)

        id_suppr_cons = st.selectbox(
            "Sélectionner un Consommable à supprimer du catalogue",
            [item["id"] for item in liste_cons_actuelle],
            key="suppr_cat_cons",
        )
        if st.button("Supprimer ce Consommable"):
            data["consommables"] = [
                item for item in liste_cons_actuelle if item["id"] != id_suppr_cons
            ]
            sauvegarder_donnees(data)
            st.success("Consommable supprimé.")
            st.rerun()
    else:
        st.info("Aucun consommable configuré pour l'instant.")

# --- ONGLET 4 : CONGÉS & ABSENCES ---
with onglets[4]:
    st.header("🌴 Suivi des Congés & Absences")
    st.info("Saisissez ici les absences pour impacter le calcul de charge et le planning en cascade.")
    
    if data.get("equipe"):
        with st.form("form_absence"):
            tech_abs = st.selectbox("Technicien", [t["nom"] for t in data["equipe"]])
            date_abs = st.date_input("Date d'absence", datetime.today())
            motif_abs = st.text_input("Motif (ex: RTT, Congés, Maladie)")
            
            if st.form_submit_button("Enregistrer l'absence"):
                data.setdefault("absences", []).append({
                    "technicien": tech_abs,
                    "date": str(date_abs),
                    "motif": motif_abs
                })
                sauvegarder_donnees(data)
                st.success("Absence enregistrée.")
                st.rerun()
                
        if data.get("absences"):
            st.subheader("Historique des absences")
            st.dataframe(pd.DataFrame(data["absences"]), use_container_width=True)
    else:
        st.warning("Veuillez d'abord enregistrer des techniciens dans l'onglet 'Équipe'.")

# --- ONGLET 5 : PLANIFICATION & CASCADE ---
with onglets[5]:
    st.header("📅 Planification & Ordonnancement en Cascade")
    st.info("Lancez vos Ordres de Fabrication (OF). Le calcul unitaire s'applique automatiquement.")
    
    if data.get("equipe") and (data.get("sous_ensembles") or data.get("consommables")):
        with st.form("form_of"):
            type_article = st.radio("Type d'élément à fabriquer", ["Sous-ensemble", "Consommable"])
            
            if type_article == "Sous-ensemble":
                catalogue_dispo = data.get("sous_ensembles", [])
            else:
                catalogue_dispo = data.get("consommables", [])
                
            if catalogue_dispo:
                article_choisi = st.selectbox("Sélectionner l'article", [item["nom"] for item in catalogue_dispo])
                qte_of = st.number_input("Quantité à produire", min_value=1, value=10)
                tech_assigne = st.selectbox("Technicien assigné", [t["nom"] for t in data["equipe"]])
                priorite = st.selectbox("Priorité", ["Normale", "Haute", "Urgente"])
                
                if st.form_submit_button("Lancer l'Ordre de Fabrication"):
                    item_ref = next((item for item in catalogue_dispo if item["nom"] == article_choisi), None)
                    temps_u = item_ref["temps_fabrication"] if item_ref else 1.0
                    charge_totale = qte_of * temps_u
                    
                    data.setdefault("ofs", []).append({
                        "id": f"OF-{len(data.get('ofs', []))+1:03d}",
                        "type": type_article,
                        "article": article_choisi,
                        "quantite": qte_of,
                        "technicien": tech_assigne,
                        "priorite": priorite,
                        "charge_heures": round(charge_totale, 2),
                        "date_lancement": str(datetime.today().date())
                    })
                    sauvegarder_donnees(data)
                    st.success(f"OF lancé avec succès ! Charge estimée : {charge_totale:.2f} heures.")
                    st.rerun()
            else:
                st.warning("Le catalogue sélectionné est vide.")
                
        if data.get("ofs"):
            st.subheader("Ordres de Fabrication en cours")
            st.dataframe(pd.DataFrame(data["ofs"]), use_container_width=True)
    else:
        st.warning("Veuillez configurer au moins un technicien et un article dans les catalogues.")

# --- ONGLET 6 : SAUVEGARDE & DONNÉES ---
with onglets[6]:
    st.header("💾 Sauvegarde & Sécurité des Données")
    
    if os.path.exists(FICHIER_DONNEES):
        with open(FICHIER_DONNEES, "r", encoding="utf-8") as f:
            json_str = f.read()
        st.download_button(
            label="Télécharger la base de données (JSON)",
            data=json_str,
            file_name="donnees_atelier_sauvegarde.json",
            mime="application/json"
        )
    else:
        st.info("Aucune donnée enregistrée pour le moment.")
