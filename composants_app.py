import json
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

DATA_FILE = "donnees_composants.json"


def charger_donnees():
  if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  return {
      "sous_ensembles": [],
      "consommables": [],
      "planification_se": [],
      "techniciens": [],
      "absences": [],
  }


def sauvegarder_donnees(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


st.set_page_config(
    page_title="Planification - Atelier Sous-ensembles",
    layout="wide",
)

data = charger_donnees()

st.title("🧩 Planification & Pilotage - Sous-ensembles & Consommables")
st.markdown("---")

# Navigation principale recentrée
onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "📅 Planification de Production",
    "👥 Équipe",
    "🌴 Congés & Absences",
])

# --- ONGLET 1 : TABLEAU DE BORD ---
with onglets[0]:
  st.header("Indicateurs Clés de l'Atelier")

  col1, col2, col3 = st.columns(3)
  col1.metric("Sous-ensembles référencés", len(data.get("sous_ensembles", [])))
  col2.metric("Consommables / Pièces suivis", len(data.get("consommables", [])))
  col3.metric("Techniciens actifs", len(data.get("techniciens", [])))

  st.markdown("---")
  st.info(
      "💡 Cet outil est optimisé pour le pilotage de la charge et la"
      " planification des lancements en atelier (hors connexion ERP)."
  )

# --- ONGLET 2 : CRÉATION SOUS-ENSEMBLES ---
with onglets[1]:
  st.header("Nomenclature et Création des Sous-ensembles")
  st.markdown(
      "Définissez ici les sous-ensembles (pré-montages) et leur temps de"
      " fabrication unitaire."
  )

  with st.form("form_se"):
    c1, c2 = st.columns(2)
    with c1:
      nom_se = st.text_input("Désignation du sous-ensemble")
      equip_se = st.text_input("Équipement de destination (ex: Focal One)")
    with c2:
      temps_se = st.number_input(
          "Temps de fabrication unitaire (heures)",
          min_value=0.1,
          value=2.0,
          step=0.5,
      )
      statut_se = st.selectbox("Statut", ["Actif", "En révision", "Obsolète"])

    btn_se = st.form_submit_button("Enregistrer le sous-ensemble")
    if btn_se and nom_se:
      nouveau_se = {
          "id": f"SE-{len(data.get('sous_ensembles', [])) + 1:03d}",
          "nom": nom_se,
          "equipement_lie": equip_se,
          "temps_fabrication": temps_se,
          "statut": statut_se,
      }
      data.setdefault("sous_ensembles", []).append(nouveau_se)
      sauvegarder_donnees(data)
      st.success(f"Sous-ensemble '{nom_se}' enregistré avec succès.")
      st.rerun()

  st.subheader("Catalogue des sous-ensembles")
  if data.get("sous_ensembles"):
    st.dataframe(pd.DataFrame(data["sous_ensembles"]), use_container_width=True)
  else:
    st.info("Aucun sous-ensemble configuré pour l'instant.")

# --- ONGLET 3 : CONSOMMABLES ---
with onglets[2]:
  st.header("Catalogue des Consommables & Pièces d'usure")
  st.markdown(
      "Référencez les consommables nécessaires pour vos gammes de fabrication."
  )

  with st.form("form_cons"):
    c1, c2 = st.columns(2)
    with c1:
      nom_c = st.text_input("Désignation du consommable")
      ref_c = st.text_input("Référence interne / constructeur")
    with c2:
      fourn_c = st.text_input("Fournisseur habituel")
      delai_c = st.number_input(
           théorique_delai := "Délai d'approvisionnement indicatif (jours)",
          min_value=1,
          value=5,
      )

    btn_c = st.form_submit_button("Enregistrer la référence")
    if btn_c and nom_c:
      nouveau_c = {
          "id": f"CONS-{len(data.get('consommables', [])) + 1:03d}",
          "nom": nom_c,
          "reference": ref_c,
          "fournisseur": fourn_c,
          "delai_appro_jours": delai_c,
      }
      data.setdefault("consommables", []).append(nouveau_c)
      sauvegarder_donnees(data)
      st.success(f"Référence '{nom_c}' enregistrée.")
      st.rerun()

  st.subheader("Liste des références consommables")
  if data.get("consommables"):
    st.dataframe(pd.DataFrame(data["consommables"]), use_container_width=True)
  else:
    st.info("Aucune référence consommable enregistrée.")

# --- ONGLET 4 : PLANIFICATION DE PRODUCTION ---
with onglets[3]:
  st.header("📅 Planification des Lancements de Sous-ensembles")

  liste_se = data.get("sous_ensembles", [])
  liste_tech = [t["nom"] for t in data.get("techniciens", [])]

  if not liste_se:
    st.warning(
        "Veuillez d'abord créer au moins un sous-ensemble dans l'onglet"
        " 'Création Sous-ensembles'."
    )
  else:
    with st.form("form_planification"):
      st.subheader("Lancer un ordre de fabrication (OF)")

      options_se = {
          f"{se['nom']} (Équipement: {se['equipement_lie']} - {se['temps_fabrication']}h unit.)": se
          for se in liste_se
      }
      choix_se_cle = st.selectbox(
          "Sélectionner le sous-ensemble à fabriquer", list(options_se.keys())
      )

      c1, c2 = st.columns(2)
      with c1:
        quantite_a_fabriquer = st.number_input(
            "Quantité à produire", min_value=1, value=1
        )
        date_lancement = st.date_input(
            "Date de lancement souhaitée", value=datetime.today()
        )
      with c2:
        priorite = st.selectbox(
            "Niveau de priorité", ["Normale", "Haute", "Urgente"]
        )
        assigne_a = st.selectbox("Technicien assigné", ["Non assigné"] + liste_tech)

      btn_planifier = st.form_submit_button("Planifier la production")

      if btn_planifier:
        se_selectionne = options_se[choix_se_cle]
        temps_total = (
            se_selectionne["temps_fabrication"] * quantite_a_fabriquer
        )

        nouveau_planning = {
            "id_plan": f"PLAN-{len(data.get('planification_se', [])) + 1:03d}",
            "sous_ensemble": se_selectionne["nom"],
            "quantite": quantite_a_fabriquer,
            "temps_total_estime_h": temps_total,
            "date_lancement": str(date_lancement),
            "priorite": priorite,
            "assigne": assigne_a,
            "statut": "Planifié",
        }

        data.setdefault("planification_se", []).append(nouveau_planning)
        sauvegarder_donnees(data)
        st.success(
            f"Ordre de fabrication planifié pour {quantite_a_fabriquer}x"
            f" '{se_selectionne['nom']}' ({temps_total}h de charge estimée)."
        )
        st.rerun()

  st.subheader("🛠️ Ordres de fabrication planifiés")
  plannings = data.get("planification_se", [])
  if plannings:
    st.dataframe(pd.DataFrame(plannings), use_container_width=True)
  else:
    st.info("Aucune planification enregistrée.")

# --- ONGLET 5 : ÉQUIPE ---
with onglets[4]:
  st.header("👥 Gestion des Techniciens")

  with st.form("form_ajout_tech"):
    c1, c2 = st.columns(2)
    with c1:
      nom_tech = st.text_input("Nom et Prénom du technicien")
    with c2:
      role_tech = st.selectbox(
          "Rôle / Qualification",
          [
              "Technicien Production",
              "Monteur Assembleur",
              "Responsable d'Atelier",
              "Intérimaire",
          ],
      )

    btn_ajout_tech = st.form_submit_button("Ajouter le technicien")
    if btn_ajout_tech and nom_tech:
      nouveau_tech = {
          "id": f"TECH-{len(data.get('techniciens', [])) + 1:03d}",
          "nom": nom_tech,
          "role": role_tech,
      }
      data.setdefault("techniciens", []).append(nouveau_tech)
      sauvegarder_donnees(data)
      st.success(f"Technicien '{nom_tech}' ajouté.")
      st.rerun()

  st.subheader("Liste des techniciens de l'atelier")
  techniciens = data.get("techniciens", [])
  if techniciens:
    df_tech = pd.DataFrame(techniciens)
    st.dataframe(df_tech, use_container_width=True)

    suppr_tech = st.selectbox(
        "Sélectionner un technicien à supprimer", [t["nom"] for t in techniciens]
    )
    if st.button("Supprimer le technicien sélectionné"):
      data["techniciens"] = [
          t for t in techniciens if t["nom"] != suppr_tech
      ]
      sauvegarder_donnees(data)
      st.success(f"Technicien '{suppr_tech}' supprimé.")
      st.rerun()
  else:
    st.info("Aucun technicien enregistré.")

# --- ONGLET 6 : CONGÉS & ABSENCES ---
with onglets[5]:
  st.header("🌴 Gestion des Congés & Absences")

  techniciens = data.get("techniciens", [])
  if not techniciens:
    st.warning(
        "Veuillez d'abord enregistrer au moins un technicien dans l'onglet"
        " 'Équipe'."
    )
  else:
    with st.form("form_absence"):
      c1, c2 = st.columns(2)
      with c1:
        op_absence = st.selectbox(
            "Technicien", [t["nom"] for t in techniciens]
        )
        motif_absence = st.selectbox(
            "Motif", ["Congés Payés", "RTT", "Maladie", "Formation", "Autre"]
        )
      with c2:
        date_debut = st.date_input("Date de début", value=datetime.today())
        date_fin = st.date_input(
            "Date de fin", value=datetime.today() + timedelta(days=1)
        )

      btn_absence = st.form_submit_button("Enregistrer l'absence")
      if btn_absence:
        nouvelle_absence = {
            "id": f"ABS-{len(data.get('absences', [])) + 1:03d}",
            "technicien": op_absence,
            "motif": motif_absence,
            "date_debut": str(date_debut),
            "date_fin": str(date_fin),
        }
        data.setdefault("absences", []).append(nouvelle_absence)
        sauvegarder_donnees(data)
        st.success(f"Absence enregistrée pour {op_absence}.")
        st.rerun()

  st.subheader("Planning des absences enregistrées")
  absences = data.get("absences", [])
  if absences:
    df_abs = pd.DataFrame(absences)
    st.dataframe(df_abs, use_container_width=True)

    suppr_abs = st.selectbox(
        "Sélectionner une absence à supprimer (par ID)",
        [a["id"] for a in absences],
    )
    if st.button("Supprimer l'absence sélectionnée"):
      data["absences"] = [a for a in absences if a["id"] != suppr_abs]
      sauvegarder_donnees(data)
      st.success("Absence supprimée.")
      st.rerun()
  else:
    st.info("Aucune absence enregistrée.")
