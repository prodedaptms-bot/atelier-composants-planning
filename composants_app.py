import io
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
      "planification_cons": [],
      "techniciens": [],
      "absences": [],
  }


def sauvegarder_donnees(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# Fonction pour exporter un DataFrame en Excel en mémoire
def convertir_df_en_excel(df):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Export_Atelier")
  processed_data = output.getvalue()
  return processed_data


st.set_page_config(
    page_title="Planification - Atelier Sous-ensembles & Consommables",
    layout="wide",
)

data = charger_donnees()

st.title("🧩 Planification & Pilotage - Atelier")
st.markdown("---")

# Navigation principale
onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "📅 Planification Production",
    "👥 Équipe",
    "🌴 Congés & Absences",
])

# --- CALCULS POUR LA SEMAINE EN COURS ---
auj = datetime.today().date()
debut_semaine = auj - timedelta(days=auj.weekday())
fin_semaine = debut_semaine + timedelta(days=6)

plannings_se = data.get("planification_se", [])
plannings_cons = data.get("planification_cons", [])
techniciens = data.get("techniciens", [])
absences = data.get("absences", [])

# 1. Analyse OF Sous-ensembles de la semaine
ofs_se_semaine = []
for p in plannings_se:
  try:
    d_lanc = datetime.strptime(p["date_lancement"], "%Y-%m-%d").date()
    if debut_semaine <= d_lanc <= fin_semaine:
      ofs_se_semaine.append(p)
  except:
    pass

nb_se_a_realiser = len(ofs_se_semaine)
nb_se_termines = sum(1 for p in ofs_se_semaine if p.get("statut") == "Terminé")
pct_se_realise = (
    int((nb_se_termines / nb_se_a_realiser) * 100)
    if nb_se_a_realiser > 0
    else 100
)

charge_restante_se_h = sum(
    p.get("temps_total_estime_h", 0)
    for p in ofs_se_semaine
    if p.get("statut") not in ["Terminé", "Supprimé"]
)

# 2. Analyse Consommables de la semaine
ofs_cons_semaine = []
for p in plannings_cons:
  try:
    d_lanc = datetime.strptime(p["date_besoin"], "%Y-%m-%d").date()
    if debut_semaine <= d_lanc <= fin_semaine:
      ofs_cons_semaine.append(p)
  except:
    pass

nb_cons_a_preparer = len(ofs_cons_semaine)
nb_cons_prepares = sum(
    1 for p in ofs_cons_semaine if p.get("statut") == "Préparé"
)
pct_cons_prepare = (
    int((nb_cons_prepares / nb_cons_a_preparer) * 100)
    if nb_cons_a_preparer > 0
    else 100
)

# 3. Calcul Capacité & Disponibilité Techniciens
capacite_hebdo_par_tech = 35.0
capacite_totale_brute = len(techniciens) * capacite_hebdo_par_tech

heures_absence_semaine = 0
for abs_rec in absences:
  try:
    d_deb = datetime.strptime(abs_rec["date_debut"], "%Y-%m-%d").date()
    d_fin = datetime.strptime(abs_rec["date_fin"], "%Y-%m-%d").date()
    deb_inter = max(debut_semaine, d_deb)
    fin_inter = min(fin_semaine, d_fin)
    if deb_inter <= fin_inter:
      nb_jours = (fin_inter - deb_inter).days + 1
      heures_absence_semaine += nb_jours * 7.0
  except:
    pass

capacite_disponible_h = max(0.0, capacite_totale_brute - heures_absence_semaine)


# --- ONGLET 1 : TABLEAU DE BORD ---
with onglets[0]:
  st.header("📊 Tableau de Bord - Semaine en Cours")
  st.markdown(
      f"**Période :** du {debut_semaine.strftime('%d/%m/%Y')} au"
      f" {fin_semaine.strftime('%d/%m/%Y')}"
  )

  # Indicateurs Sous-ensembles
  st.subheader("🛠️ Activité Sous-ensembles (Production)")
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("À réaliser", nb_se_a_realiser)
  c2.metric("Terminés", nb_se_termines)
  c3.metric("Progression SE", f"{pct_se_realise}%")
  c4.metric(
      "Effectif dispo.",
      f"{len(techniciens)} tech. (-{int(heures_absence_semaine)}h abs.)",
  )

  # Analyse Charge vs Capacité SE
  cc1, cc2 = st.columns(2)
  cc1.metric("Charge SE restante", f"{charge_restante_se_h:.1f} heures")
  cc2.metric("Capacité nette atelier", f"{capacite_disponible_h:.1f} heures")

  if charge_restante_se_h > capacite_disponible_h:
    ecart = charge_restante_se_h - capacite_disponible_h
    st.error(
        f"🚨 **ALERTE CHARGE SE :** La charge restante ({charge_restante_se_h:.1f}h)"
        f" dépasse la capacité nette ({capacite_disponible_h:.1f}h) de"
        f" **{ecart:.1f} heures**. Risque de décalage planning."
    )
  else:
    st.success(
        "✅ **Capacité SE OK :** La charge de la semaine est couverte par"
        " l'équipe."
    )

  st.markdown("---")

  # Indicateurs Consommables
  st.subheader("📦 Activité Consommables & Approvisionnements/Préparations")
  d1, d2, d3 = st.columns(3)
  d1.metric("Consommables à préparer", nb_cons_a_preparer)
  d2.metric("Préparés / Validés", nb_cons_prepares)
  d3.metric("Progression Consommables", f"{pct_cons_prepare}%")

  st.markdown("---")
  st.subheader("📋 Détails des plannings de la semaine")

  tab_det1, tab_det2 = st.tabs(
      ["Ordres de Fabrication SE", "Consommables de la semaine"]
  )
  with tab_det1:
    if ofs_se_semaine:
      df_sh_se = pd.DataFrame(ofs_se_semaine)
      st.dataframe(df_sh_se, use_container_width=True)
      
      # Bouton d'export Excel
      excel_data = convertir_df_en_excel(df_sh_se)
      st.download_button(
          label="📥 Exporter les OFs de la semaine (Excel)",
          data=excel_data,
          file_name=f"ofs_semaine_{debut_semaine}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )
    else:
      st.info("Aucun sous-ensemble planifié cette semaine.")

  with tab_det2:
    if ofs_cons_semaine:
      df_sh_co = pd.DataFrame(ofs_cons_semaine)
      st.dataframe(df_sh_co, use_container_width=True)
      
      excel_data_co = convertir_df_en_excel(df_sh_co)
      st.download_button(
          label="📥 Exporter les Consommables de la semaine (Excel)",
          data=excel_data_co,
          file_name=f"consommables_semaine_{debut_semaine}.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )
    else:
      st.info("Aucun consommable planifié/requis cette semaine.")


# --- ONGLET 2 : CRÉATION SOUS-ENSEMBLES ---
with onglets[1]:
  st.header("Nomenclature et Création des Sous-ensembles")

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
      st.success(f"Sous-ensemble '{nom_se}' enregistré.")
      st.rerun()

  st.subheader("Catalogue des sous-ensembles")
  if data.get("sous_ensembles"):
    df_catalogue_se = pd.DataFrame(data["sous_ensembles"])
    st.dataframe(df_catalogue_se, use_container_width=True)
    
    st.download_button(
        label="📥 Exporter le catalogue (Excel)",
        data=convertir_df_en_excel(df_catalogue_se),
        file_name="catalogue_sous_ensembles.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
  else:
    st.info("Aucun sous-ensemble configuré.")


# --- ONGLET 3 : CONSOMMABLES ---
with onglets[2]:
  st.header("Catalogue des Consommables & Pièces d'usure")

  with st.form("form_cons"):
    c1, c2 = st.columns(2)
    with c1:
      nom_c = st.text_input("Désignation du consommable")
      ref_c = st.text_input("Référence interne / constructeur")
    with c2:
      fourn_c = st.text_input("Fournisseur habituel")
      delai_c = st.number_input(
          "Délai d'approvisionnement indicatif (jours)", min_value=1, value=5
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
    df_catalogue_cons = pd.DataFrame(data["consommables"])
    st.dataframe(df_catalogue_cons, use_container_width=True)
    
    st.download_button(
        label="📥 Exporter les consommables (Excel)",
        data=convertir_df_en_excel(df_catalogue_cons),
        file_name="catalogue_consommables.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
  else:
    st.info("Aucune référence consommable enregistrée.")


# --- ONGLET 4 : PLANIFICATION PRODUCTION ---
with onglets[3]:
  st.header("📅 Planification Atelier (Sous-ensembles & Consommables)")

  liste_se = data.get("sous_ensembles", [])
  liste_cons = data.get("consommables", [])
  liste_tech = [t["nom"] for t in data.get("techniciens", [])]

  sub_tab1, sub_tab2, sub_tab_gantt = st.tabs([
      "🛠️ Lancer un OF Sous-ensemble",
      "📦 Planifier un Consommable",
      "📈 Vue Gantt Semaine",
  ])

  with sub_tab1:
    if not liste_se:
      st.warning("Veuillez créer au moins un sous-ensemble.")
    else:
      with st.form("form_plan_se"):
        options_se = {
            f"{se['nom']} ({se['temps_fabrication']}h unit.)": se
            for se in liste_se
        }
        choix_se_cle = st.selectbox(
            "Sous-ensemble à fabriquer", list(options_se.keys())
        )

        c1, c2 = st.columns(2)
        with c1:
          qte_se = st.number_input("Quantité", min_value=1, value=1)
          date_l_se = st.date_input("Date de lancement", value=datetime.today())
        with c2:
          prio_se = st.selectbox(
              "Priorité", ["Normale", "Haute", "Urgente"], key="prio_se"
          )
          tech_se = st.selectbox(
              "Assigné à", ["Non assigné"] + liste_tech, key="tech_se"
          )

        if st.form_submit_button("Planifier le sous-ensemble"):
          se_sel = options_se[choix_se_cle]
          t_tot = se_sel["temps_fabrication"] * qte_se
          nouveau_p = {
              "id_plan": f"PLAN-SE-{len(plannings_se) + 1:03d}",
              "sous_ensemble": se_sel["nom"],
              "quantite": qte_se,
              "temps_total_estime_h": t_tot,
              "date_lancement": str(date_l_se),
              "priorite": prio_se,
              "assigne": tech_se,
              "statut": "Planifié",
              "cause_blocage": "",
              "cause_decalage": "",
          }
          plannings_se.append(nouveau_p)
          data["planification_se"] = plannings_se
          sauvegarder_donnees(data)
          st.success("OF planifié avec succès.")
          st.rerun()

    st.subheader("Suivi & Gestion des OF Sous-ensembles")
    if plannings_se:
      df_all_se = pd.DataFrame(plannings_se)
      st.dataframe(df_all_se, use_container_width=True)

      st.download_button(
          label="📥 Exporter tous les OFs (Excel)",
          data=convertir_df_en_excel(df_all_se),
          file_name="tous_les_ofs_production.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

      id_mod_se = st.selectbox(
          "Sélectionner un OF (par ID)", [p["id_plan"] for p in plannings_se]
      )
      of_courant = next(
          (p for p in plannings_se if p["id_plan"] == id_mod_se), None
      )

      col_a, col_b, col_c, col_d = st.columns(4)

      with col_a:
        if st.button("✅ Terminer"):
          if of_courant:
            of_courant["statut"] = "Terminé"
            of_courant["cause_blocage"] = ""
            sauvegarder_donnees(data)
            st.success(f"OF {id_mod_se} marqué comme Terminé.")
            st.rerun()

      with col_b:
        cause_bloc = st.text_input("Motif du blocage", key="input_bloc_se")
        if st.button("🔒 Bloquer"):
          if of_courant:
            of_courant["statut"] = "Bloqué"
            of_courant["cause_blocage"] = cause_bloc
            sauvegarder_donnees(data)
            st.warning(f"OF {id_mod_se} bloqué.")
            st.rerun()

      with col_c:
        cause_dec = st.text_input("Motif du décalage", key="input_dec_se")
        if st.button("⏳ Décaler"):
          if of_courant:
            of_courant["statut"] = "Décalé"
            of_courant["cause_decalage"] = cause_dec
            sauvegarder_donnees(data)
            st.info(f"OF {id_mod_se} décalé.")
            st.rerun()

      with col_d:
        st.write("")
        if st.button("🗑️ Supprimer OF"):
          data["planification_se"] = [
              p for p in plannings_se if p["id_plan"] != id_mod_se
          ]
          sauvegarder_donnees(data)
          st.error(f"OF {id_mod_se} supprimé.")
          st.rerun()

  with sub_tab2:
    if not liste_cons:
      st.warning("Veuillez enregistrer au moins un consommable.")
    else:
      with st.form("form_plan_cons"):
        options_c = {f"{c['nom']} (Réf: {c['reference']})": c for c in liste_cons}
        choix_c_cle = st.selectbox("Consommable concerné", list(options_c.keys()))

        c1, c2 = st.columns(2)
        with c1:
          qte_c = st.number_input("Quantité nécessaire", min_value=1, value=1)
          date_b_c = st.date_input(
              "Date de besoin / préparation", value=datetime.today()
          )
        with c2:
          prio_c = st.selectbox(
              "Priorité", ["Normale", "Haute", "Urgente"], key="prio_c"
          )
          dest_c = st.text_input(
              "Affectation / Machine (ex: Poste Ligne 2)", value=""
          )

        if st.form_submit_button("Planifier / Demander le consommable"):
          c_sel = options_c[choix_c_cle]
          nouveau_pc = {
              "id_plan_cons": f"PLAN-CONS-{len(plannings_cons) + 1:03d}",
              "consommable": c_sel["nom"],
              "reference": c_sel["reference"],
              "quantite": qte_c,
              "date_besoin": str(date_b_c),
              "priorite": prio_c,
              "affectation": dest_c,
              "statut": "À préparer",
              "cause_blocage": "",
          }
          plannings_cons.append(nouveau_pc)
          data["planification_cons"] = plannings_cons
          sauvegarder_donnees(data)
          st.success("Consommable planifié.")
          st.rerun()

    st.subheader("Suivi & Gestion des Consommables planifiés")
    if plannings_cons:
      df_all_co = pd.DataFrame(plannings_cons)
      st.dataframe(df_all_co, use_container_width=True)

      st.download_button(
          label="📥 Exporter tous les consommables planifiés (Excel)",
          data=convertir_df_en_excel(df_all_co),
          file_name="tous_les_consommables_planifies.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      )

      id_mod_c = st.selectbox(
          "Sélectionner un consommable (par ID)",
          [p["id_plan_cons"] for p in plannings_cons],
      )
      cons_courant = next(
          (p for p in plannings_cons if p["id_plan_cons"] == id_mod_c), None
      )

      col_ca, col_cb, col_cc = st.columns(3)

      with col_ca:
        if st.button("✅ Préparé / Validé"):
          if cons_courant:
            cons_courant["statut"] = "Préparé"
            cons_courant["cause_blocage"] = ""
            sauvegarder_donnees(data)
            st.success(f"Ligne {id_mod_c} marquée comme préparée.")
            st.rerun()

      with col_cb:
        cause_bloc_c = st.text_input("Motif du blocage / rupture", key="input_bloc_c")
        if st.button("🔒 Bloquer Consommable"):
          if cons_courant:
            cons_courant["statut"] = "Bloqué"
            cons_courant["cause_blocage"] = cause_bloc_c
            sauvegarder_donnees(data)
            st.warning(f"Ligne {id_mod_c} bloquée.")
            st.rerun()

      with col_cc:
        st.write("")
        if st.button("🗑️ Supprimer Ligne"):
          data["planification_cons"] = [
              p for p in plannings_cons if p["id_plan_cons"] != id_mod_c
          ]
          sauvegarder_donnees(data)
          st.error(f"Ligne {id_mod_c} supprimée.")
          st.rerun()

  with sub_tab_gantt:
    st.subheader("📈 Vue de type Planning Hebdomadaire (Gantt - Semaine en Cours)")
    st.markdown(f"**Semaine du {debut_semaine.strftime('%d/%m/%Y')} au {fin_semaine.strftime('%d/%m/%Y')}**")

    # Génération des jours de la semaine (Lundi -> Vendredi ou Dimanche)
    jours_semaine = [debut_semaine + timedelta(days=i) for i in range(5)] # Lundi à Vendredi
    noms_jours = [j.strftime("%A %d/%m") for j in jours_semaine]

    # Construction d'une matrice simplifiée pour la vue visuelle (Gantt textuel/matrice)
    if plannings_se:
      lignes_gantt = []
      for p in plannings_se:
        try:
          d_l = datetime.strptime(p["date_lancement"], "%Y-%m-%d").date()
          # On vérifie si l'OF tombe dans la semaine
          if debut_semaine <= d_l <= fin_semaine:
            jour_str = d_l.strftime("%A %d/%m")
            lignes_gantt.append({
                "ID": p["id_plan"],
                "Sous-ensemble": p["sous_ensemble"],
                "Qté": p["quantite"],
                "Technicien": p["assigne"],
                "Statut": p["statut"],
                "Jour": jour_str
            })
        except:
          pass

      if lignes_gantt:
        df_gantt_brut = pd.DataFrame(lignes_gantt)
        
        # Création d'un tableau croisé simulant un Gantt de charge par jour
        # Colonnes = Jours de la semaine, Lignes = Techniciens ou Sous-ensembles
        st.write("**Répartition des lancements sur la semaine :**")
        
        # Tableau pivot visuel
        grille_affichage = []
        for tech in ["Tous / Non assigné"] + [t["nom"] for t in techniciens]:
          ligne_data = {"Technicien / Ressource": tech}
          for j_nom in noms_jours:
            # Chercher les OFs ce jour-là pour ce tech
            if tech == "Tous / Non assigné":
              matches = [f"{x['Sous-ensemble']} (x{x['Qté']}) [{x['Statut']}]" for x in lignes_gantt if x['Jour'] == j_nom]
            else:
              matches = [f"{x['Sous-ensemble']} (x{x['Qté']}) [{x['Statut']}]" for x in lignes_gantt if x['Jour'] == j_nom and x['Technicien'] == tech]
            
            ligne_data[j_nom] = " | ".join(matches) if matches else ""
          grille_affichage.append(ligne_data)

        st.dataframe(pd.DataFrame(grille_affichage), use_container_width=True)
      else:
        st.info("Aucun ordre de fabrication positionné pour cette semaine dans la vue Gantt.")
    else:
      st.info("Aucun OF disponible.")


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

    if st.form_submit_button("Ajouter le technicien") and nom_tech:
      nouveau_tech = {
          "id": f"TECH-{len(techniciens) + 1:03d}",
          "nom": nom_tech,
          "role": role_tech,
      }
      techniciens.append(nouveau_tech)
      data["techniciens"] = techniciens
      sauvegarder_donnees(data)
      st.success(f"Technicien '{nom_tech}' ajouté.")
      st.rerun()

  st.subheader("Liste des techniciens")
  if techniciens:
    df_tech = pd.DataFrame(techniciens)
    st.dataframe(df_tech, use_container_width=True)
    
    st.download_button(
        label="📥 Exporter la liste de l'équipe (Excel)",
        data=convertir_df_en_excel(df_tech),
        file_name="equipe_techniciens.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    suppr_tech = st.selectbox(
        "Supprimer un technicien", [t["nom"] for t in techniciens]
    )
    if st.button("Supprimer le technicien"):
      data["techniciens"] = [
          t for t in techniciens if t["nom"] != suppr_tech
      ]
      sauvegarder_donnees(data)
      st.success("Technicien supprimé.")
      st.rerun()
  else:
    st.info("Aucun technicien enregistré.")


# --- ONGLET 6 : CONGÉS & ABSENCES ---
with onglets[5]:
  st.header("🌴 Gestion des Congés & Absences")

  if not techniciens:
    st.warning("Veuillez d'abord enregistrer au moins un technicien.")
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

      if st.form_submit_button("Enregistrer l'absence"):
        nouvelle_absence = {
            "id": f"ABS-{len(absences) + 1:03d}",
            "technicien": op_absence,
            "motif": motif_absence,
            "date_debut": str(date_debut),
            "date_fin": str(date_fin),
        }
        absences.append(nouvelle_absence)
        data["absences"] = absences
        sauvegarder_donnees(data)
        st.success("Absence enregistrée.")
        st.rerun()

  st.subheader("Planning des absences")
  if absences:
    df_abs = pd.DataFrame(absences)
    st.dataframe(df_abs, use_container_width=True)
    
    st.download_button(
        label="📥 Exporter le planning des absences (Excel)",
        data=convertir_df_en_excel(df_abs),
        file_name="planning_absences.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    suppr_abs = st.selectbox(
        "Supprimer une absence (par ID)", [a["id"] for a in absences]
    )
    if st.button("Supprimer l'absence"):
      data["absences"] = [a for a in absences if a["id"] != suppr_abs]
      sauvegarder_donnees(data)
      st.success("Absence supprimée.")
      st.rerun()
  else:
    st.info("Aucune absence enregistrée.")
