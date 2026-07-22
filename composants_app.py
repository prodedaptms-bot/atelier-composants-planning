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
    page_title="Gestion & Planification - Atelier",
    layout="wide",
)

data = charger_donnees()

st.title("🧩 Pilotage & Planification - Sous-ensembles & Consommables")
st.markdown("---")

# Navigation principale
onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Suivi des Consommables",
    "📅 Planification de Production",
    "👥 Équipe",
    "🌴 Congés & Absences",
])

# --- ONGLET 1 : TABLEAU DE BORD ---
with onglets[0]:
  st.header("Indicateurs Clés")

  col1, col2, col3, col4 = st.columns(4)
  nb_se = len(data.get("sous_ensembles", []))
  nb_cons = len(data.get("consommables", []))
  nb_tech = len(data.get("techniciens", []))

  alertes_se = sum(
      1
      for s in data.get("sous_ensembles", [])
      if s["stock_actuel"] <= s["stock_minimum"]
  )
  alertes_cons = sum(
      1
      for c in data.get("consommables", [])
      if c["stock_actuel"] <= c["seuil_alerte"]
  )

  col1.metric("Sous-ensembles", nb_se, delta=f"-{alertes_se} en alerte" if alertes_se > 0 else "OK", delta_color="inverse" if alertes_se > 0 else "normal")
  col2.metric("Consommables", nb_cons, delta=f"-{alertes_cons} critiques" if alertes_cons > 0 else "OK", delta_color="inverse" if alertes_cons > 0 else "normal")
  col3.metric("Techniciens actifs", nb_tech)
  col4.metric("Total alertes", alertes_se + alertes_cons)

  st.subheader("⚠️ Articles nécessitant une attention immédiate")

  items_critiques = []
  for s in data.get("sous_ensembles", []):
    if s["stock_actuel"] <= s["stock_minimum"]:
      items_critiques.append({
          "Type": "Sous-ensemble",
          "Nom": s["nom"],
          "Stock": s["stock_actuel"],
          "Seuil / Min": s["stock_minimum"],
      })
  for c in data.get("consommables", []):
    if c["stock_actuel"] <= c["seuil_alerte"]:
      items_critiques.append({
          "Type": "Consommable",
          "Nom": c["nom"],
          "Stock": c["stock_actuel"],
          "Seuil / Min": c["seuil_alerte"],
      })

  if items_critiques:
    st.dataframe(pd.DataFrame(items_critiques), use_container_width=True)
  else:
    st.success("Aucune rupture ou seuil critique détecté pour le moment.")

# --- ONGLET 2 : CRÉATION SOUS-ENSEMBLES ---
with onglets[1]:
  st.header("Nomenclature et Création des Sous-ensembles")

  with st.form("form_se"):
    c1, c2 = st.columns(2)
    with c1:
      nom_se = st.text_input("Désignation du sous-ensemble")
      equip_se = st.text_input("Équipement de destination (ex: Focal One)")
      temps_se = st.number_input(
          "Temps de fabrication (heures)", min_value=0.1, value=2.0, step=0.5
      )
    with c2:
      stock_se = st.number_input("Stock physique actuel", min_value=0, value=2)
      min_se = st.number_input("Stock minimum d'alerte", min_value=0, value=3)
      statut_se = st.selectbox(
          "État de référence", ["Actif", "En cours de modification", "Obsolète"]
      )

    btn_se = st.form_submit_button("Enregistrer le nouveau sous-ensemble")
    if btn_se and nom_se:
      nouveau_se = {
          "id": f"SE-{len(data.get('sous_ensembles', [])) + 1:03d}",
          "nom": nom_se,
          "equipement_lie": equip_se,
          "temps_fabrication": temps_se,
          "stock_actuel": stock_se,
          "stock_minimum": min_se,
          "statut": statut_se,
      }
      data.setdefault("sous_ensembles", []).append(nouveau_se)
      sauvegarder_donnees(data)
      st.success(f"Sous-ensemble '{nom_se}' créé avec succès.")
      st.rerun()

  st.subheader("Catalogue des sous-ensembles configurés")
  if data.get("sous_ensembles"):
    st.dataframe(pd.DataFrame(data["sous_ensembles"]), use_container_width=True)
  else:
    st.info("Aucun sous-ensemble configuré pour l'instant.")

# --- ONGLET 3 : CONSOMMABLES ---
with onglets[2]:
  st.header("Suivi des Consommables & Pièces d'usure")

  with st.expander("➕ Enregistrer un nouveau consommable", expanded=False):
    with st.form("form_cons"):
      c1, c2, c3 = st.columns(3)
      with c1:
        nom_c = st.text_input("Désignation")
        ref_c = st.text_input("Référence interne / fournisseur")
      with c2:
        stock_c = st.number_input("Quantité en stock", min_value=0, value=10)
        seuil_c = st.number_input("Seuil d'alerte", min_value=0, value=5)
      with c3:
        fourn_c = st.text_input("Fournisseur")
        delai_c = st.number_input(
            "Délai de livraison (jours)", min_value=1, value=5
        )

      btn_c = st.form_submit_button("Ajouter le consommable")
      if btn_c and nom_c:
        nouveau_c = {
            "id": f"CONS-{len(data.get('consommables', [])) + 1:03d}",
            "nom": nom_c,
            "reference": ref_c,
            "stock_actuel": stock_c,
            "seuil_alerte": seuil_c,
            "fournisseur": fourn_c,
            "delai_appro_jours": delai_c,
        }
        data.setdefault("consommables", []).append(nouveau_c)
        sauvegarder_donnees(data)
        st.success(f"Consommable '{nom_c}' enregistré.")
        st.rerun()

  st.subheader("Inventaire des consommables")
  if data.get("consommables"):
    st.dataframe(pd.DataFrame(data["consommables"]), use_container_width=True)
  else:
    st.info("Aucun consommable enregistré.")

# --- ONGLET 4 : PLANIFICATION DE PRODUCTION ---
with onglets[3]:
  st.header("📅 Planification des Lancements de Sous-ensembles")
  
  liste_se = data.get("sous_ensembles", [])
  liste_tech = [t["nom"] for t in data.get("techniciens", [])]
  
  if not liste_se:
    st.warning("Veuillez d'abord créer au moins un sous-ensemble dans l'onglet 'Création Sous-ensembles'.")
  else:
    with st.form("form_planification"):
      st.subheader("Lancer un ordre de fabrication")
      
      options_se = {f"{se['nom']} (Équipement: {se['equipement_lie']} - {se['temps_fabrication']}h unit.)": se for se in liste_se}
      choix_se_cle = st.selectbox("Sélectionner le sous-ensemble à fabriquer", list(options_se.keys()))
      
      c1, c2 = st.columns(2)
      with c1:
        quantite_a_fabriquer = st.number_input("Quantité à produire", min_value=1, value=1)
        date_lancement = st.date_input("Date de lancement souhaitée", value=datetime.today())
      with c2:
        priorite = st.selectbox("Niveau de priorité", ["Normale", "Haute", "Urgente"])
        assigne_a = st.selectbox("Technicien assigné", ["Non assigné"] + liste_tech)

      btn_planifier = st.form_submit_button("Planifier la production")
      
      if btn_planifier:
        se_selectionne = options_se[choix_se_cle]
        temps_total = se_selectionne["temps_fabrication"] * quantite_a_fabriquer
        
        nouveau_planning = {
            "id_plan": f"PLAN-{len(data.get('planification_se', [])) + 1:03d}",
            "sous_ensemble": se_selectionne["nom"],
            "quantite": quantite_a_fabriquer,
            "temps_total_estime_h": temps_total,
            "date_lancement": str(date_lancement),
            "priorite": priorite,
            "assigne": assigne_a,
            "statut": "Planifié"
        }
        
        data.setdefault("planification_se", []).append(nouveau_planning)
        sauvegarder_donnees(data)
        st.success(f"Ordre de fabrication planifié pour {quantite_a_fabriquer}x '{se_selectionne['nom']}' ({temps_total}h de charge).")
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
      role_tech = st.selectbox("Rôle / Qualification", ["Technicien Production", "Monteur Assembleur", "Responsable d'Atelier", "Intérimaire"])

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

    suppr_tech = st.selectbox("Sélectionner un technicien à supprimer", [t["nom"] for t in techniciens])
    if st.button("Supprimer le technicien sélectionné"):
      data["techniciens"] = [t for t in techniciens if t["nom"] != suppr_tech]
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
    st.warning("Veuillez d'abord enregistrer au moins un technicien dans l'onglet 'Équipe'.")
  else:
    with st.form("form_absence"):
      c1, c2 = st.columns(2)
      with c1:
        op_absence = st.selectbox("Technicien", [t["nom"] for t in techniciens])
        motif_absence = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation", "Autre"])
      with c2:
        date_debut = st.date_input("Date de début", value=datetime.today())
        date_fin = st.date_input("Date de fin", value=datetime.today() + timedelta(days=1))

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

    suppr_abs = st.selectbox("Sélectionner une absence à supprimer (par ID)", [a["id"] for a in absences])
    if st.button("Supprimer l'absence sélectionnée"):
      data["absences"] = [a for a in absences if a["id"] != suppr_abs]
      sauvegarder_donnees(data)
      st.success("Absence supprimée.")
      st.rerun()
  else:
    st.info("Aucune absence enregistrée.")
