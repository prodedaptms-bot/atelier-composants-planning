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
      "techniciens_prod": [],
      "techniciens_cons": [],
      "absences_prod": [],
      "absences_cons": [],
  }


def sauvegarder_donnees(data):
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


def convertir_df_en_csv(df):
  return df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")


st.set_page_config(
    page_title="Planification - Atelier Sous-ensembles & Consommables",
    layout="wide",
)

data = charger_donnees()

st.title("🧩 Planification & Pilotage - Atelier")
st.markdown("---")

onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "📅 Planification Production",
    "👥 Équipe",
    "🌴 Congés & Absences",
])

auj = datetime.today().date()
debut_semaine = auj - timedelta(days=auj.weekday())
fin_semaine = debut_semaine + timedelta(days=6)

plannings_se = data.get("planification_se", [])
plannings_cons = data.get("planification_cons", [])
techniciens_prod = data.get("techniciens_prod", [])
techniciens_cons = data.get("techniciens_cons", [])
absences_prod = data.get("absences_prod", [])
absences_cons = data.get("absences_cons", [])

# 1. Analyse OF Sous-ensembles
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

# 2. Analyse Consommables
ofs_cons_semaine = []
for p in plannings_cons:
  try:
    d_lanc = datetime.strptime(p["date_lancement"], "%Y-%m-%d").date()
    if debut_semaine <= d_lanc <= fin_semaine:
      ofs_cons_semaine.append(p)
  except:
    pass

nb_cons_a_realiser = len(ofs_cons_semaine)
nb_cons_termines = sum(
    1 for p in ofs_cons_semaine if p.get("statut") == "Terminé"
)
pct_cons_realise = (
    int((nb_cons_termines / nb_cons_a_realiser) * 100)
    if nb_cons_a_realiser > 0
    else 100
)

charge_restante_cons_h = sum(
    p.get("temps_total_estime_h", 0)
    for p in ofs_cons_semaine
    if p.get("statut") not in ["Terminé", "Supprimé"]
)

# 3. Calcul Capacités & Disponibilités
capacite_hebdo = 35.0

# Tech Prod
cap_brute_prod = len(techniciens_prod) * capacite_hebdo
h_abs_prod = 0
for abs_rec in absences_prod:
  try:
    d_deb = datetime.strptime(abs_rec["date_debut"], "%Y-%m-%d").date()
    d_fin = datetime.strptime(abs_rec["date_fin"], "%Y-%m-%d").date()
    deb_inter = max(debut_semaine, d_deb)
    fin_inter = min(fin_semaine, d_fin)
    if deb_inter <= fin_inter:
      h_abs_prod += ((fin_inter - deb_inter).days + 1) * 7.0
  except:
    pass
capacite_dispo_prod_h = max(0.0, cap_brute_prod - h_abs_prod)

# Tech Consommables
cap_brute_cons = len(techniciens_cons) * capacite_hebdo
h_abs_cons = 0
for abs_rec in absences_cons:
  try:
    d_deb = datetime.strptime(abs_rec["date_debut"], "%Y-%m-%d").date()
    d_fin = datetime.strptime(abs_rec["date_fin"], "%Y-%m-%d").date()
    deb_inter = max(debut_semaine, d_deb)
    fin_inter = min(fin_semaine, d_fin)
    if deb_inter <= fin_inter:
      h_abs_cons += ((fin_inter - deb_inter).days + 1) * 7.0
  except:
    pass
capacite_dispo_cons_h = max(0.0, cap_brute_cons - h_abs_cons)


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
      "Effectif Prod dispo.",
      f"{len(techniciens_prod)} tech. (-{int(h_abs_prod)}h abs.)",
  )

  cc1, cc2 = st.columns(2)
  cc1.metric("Charge SE restante", f"{charge_restante_se_h:.1f} heures")
  cc2.metric("Capacité nette Prod", f"{capacite_dispo_prod_h:.1f} heures")

  if charge_restante_se_h > capacite_dispo_prod_h:
    ecart = charge_restante_se_h - capacite_dispo_prod_h
    st.error(
        f"🚨 **ALERTE CHARGE SE :** La charge ({charge_restante_se_h:.1f}h)"
        f" dépasse la capacité ({capacite_dispo_prod_h:.1f}h) de"
        f" **{ecart:.1f} heures**."
    )
  else:
    st.success("✅ **Capacité SE OK**")

  st.markdown("---")

  # Indicateurs Consommables
  st.subheader("📦 Activité Fabrication de Consommables")
  d1, d2, d3, d4 = st.columns(4)
  d1.metric("À fabriquer", nb_cons_a_realiser)
  d2.metric("Terminés", nb_cons_termines)
  d3.metric("Progression Cons.", f"{pct_cons_realise}%")
  d4.metric(
      "Effectif Cons. dispo.",
      f"{len(techniciens_cons)} tech. (-{int(h_abs_cons)}h abs.)",
  )

  dc1, dc2 = st.columns(2)
  dc1.metric(
      "Charge Consommables restante", f"{charge_restante_cons_h:.1f} heures"
  )
  dc2.metric("Capacité nette Cons.", f"{capacite_dispo_cons_h:.1f} heures")

  if charge_restante_cons_h > capacite_dispo_cons_h:
    ecart_c = charge_restante_cons_h - capacite_dispo_cons_h
    st.error(
        f"🚨 **ALERTE CHARGE CONSOMMABLES :** La charge"
        f" ({charge_restante_cons_h:.1f}h) dépasse la capacité"
        f" ({capacite_dispo_cons_h:.1f}h) de **{ecart_c:.1f} heures**."
    )
  else:
    st.success("✅ **Capacité Consommables OK**")

  st.markdown("---")
  st.subheader("📋 Détails des plannings de la semaine")

  tab_det1, tab_det2 = st.tabs(
      ["Ordres de Fabrication SE", "Fabrication Consommables"]
  )
  with tab_det1:
    if ofs_se_semaine:
      df_sh_se = pd.DataFrame(ofs_se_semaine)
      st.dataframe(df_sh_se, use_container_width=True)
      st.download_button(
          label="📥 Exporter les OFs SE (CSV)",
          data=convertir_df_en_csv(df_sh_se),
          file_name=f"ofs_se_semaine_{debut_semaine}.csv",
          mime="text/csv",
      )
    else:
      st.info("Aucun sous-ensemble planifié cette semaine.")

  with tab_det2:
    if ofs_cons_semaine:
      df_sh_co = pd.DataFrame(ofs_cons_semaine)
      st.dataframe(df_sh_co, use_container_width=True)
      st.download_button(
          label="📥 Exporter la fabrication consommables (CSV)",
          data=convertir_df_en_csv(df_sh_co),
          file_name=f"ofs_cons_semaine_{debut_semaine}.csv",
          mime="text/csv",
      )
    else:
      st.info("Aucun consommable planifié cette semaine.")


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
        label="📥 Exporter le catalogue (CSV)",
        data=convertir_df_en_csv(df_catalogue_se),
        file_name="catalogue_sous_ensembles.csv",
        mime="text/csv",
    )
  else:
    st.info("Aucun sous-ensemble configuré.")


# --- ONGLET 3 : CONSOMMABLES ---
with onglets[2]:
  st.header("Nomenclature et Fabrication des Consommables")

  with st.form("form_cons"):
    c1, c2 = st.columns(2)
    with c1:
      nom_c = st.text_input("Désignation du consommable")
      ref_c = st.text_input("Référence interne")
    with c2:
      temps_c = st.number_input(
          "Temps de fabrication unitaire (heures)",
          min_value=0.1,
          value=1.0,
          step=0.5,
      )
      statut_c = st.selectbox(
          "Statut", ["Actif", "En révision", "Obsolète"], key="statut_c"
      )

    btn_c = st.form_submit_button("Enregistrer la référence consommable")
    if btn_c and nom_c:
      nouveau_c = {
          "id": f"CONS-{len(data.get('consommables', [])) + 1:03d}",
          "nom": nom_c,
          "reference": ref_c,
          "temps_fabrication": temps_c,
          "statut": statut_c,
      }
      data.setdefault("consommables", []).append(nouveau_c)
      sauvegarder_donnees(data)
      st.success(f"Référence consommable '{nom_c}' enregistrée.")
      st.rerun()

  st.subheader("Catalogue des consommables")
  if data.get("consommables"):
    df_catalogue_cons = pd.DataFrame(data["consommables"])
    st.dataframe(df_catalogue_cons, use_container_width=True)
    st.download_button(
        label="📥 Exporter le catalogue consommables (CSV)",
        data=convertir_df_en_csv(df_catalogue_cons),
        file_name="catalogue_consommables.csv",
        mime="text/csv",
    )
  else:
    st.info("Aucune référence consommable enregistrée.")


# --- ONGLET 4 : PLANIFICATION PRODUCTION ---
with onglets[3]:
  st.header("📅 Planification Atelier (Sous-ensembles & Consommables)")

  liste_se = data.get("sous_ensembles", [])
  liste_cons = data.get("consommables", [])
  liste_tech_prod = [t["nom"] for t in techniciens_prod]
  liste_tech_cons = [t["nom"] for t in techniciens_cons]

  sub_tab1, sub_tab2, sub_tab_gantt = st.tabs([
      "🛠️ Lancer un OF Sous-ensemble",
      "📦 Lancer un OF Consommable",
      "📈 Vue Gantt Semaine",
  ])

  with sub_tab1:
    if not liste_se:
      st.warning("Veuillez créer au moins un sous-ensemble.")
    else:
      with st.form("form_plan_se"):
        options_se = {
            f"{se['nom']} ({se.get('temps_fabrication', 1.0)}h unit.)": se
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
              "Assigné à (Technicien Production)",
              ["Non assigné"] + liste_tech_prod,
              key="tech_se",
          )

        if st.form_submit_button("Planifier le sous-ensemble"):
          se_sel = options_se[choix_se_cle]
          t_tot = se_sel.get("temps_fabrication", 1.0) * qte_se
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
          st.success("OF Sous-ensemble planifié avec succès.")
          st.rerun()

    st.subheader("Suivi & Gestion des OF Sous-ensembles")
    if plannings_se:
      df_all_se = pd.DataFrame(plannings_se)
      st.dataframe(df_all_se, use_container_width=True)
      st.download_button(
          label="📥 Exporter tous les OFs SE (CSV)",
          data=convertir_df_en_csv(df_all_se),
          file_name="tous_les_ofs_se.csv",
          mime="text/csv",
      )

      id_mod_se = st.selectbox(
          "Sélectionner un OF SE (par ID)", [p["id_plan"] for p in plannings_se]
      )
      of_courant = next(
          (p for p in plannings_se if p["id_plan"] == id_mod_se), None
      )

      col_a, col_b, col_c, col_d = st.columns(4)
      with col_a:
        if st.button("✅ Terminer SE"):
          if of_courant:
            of_courant["statut"] = "Terminé"
            of_courant["cause_blocage"] = ""
            sauvegarder_donnees(data)
            st.success(f"OF {id_mod_se} terminé.")
            st.rerun()
      with col_b:
        cause_bloc = st.text_input("Motif du blocage SE", key="input_bloc_se")
        if st.button("🔒 Bloquer SE"):
          if of_courant:
            of_courant["statut"] = "Bloqué"
            of_courant["cause_blocage"] = cause_bloc
            sauvegarder_donnees(data)
            st.warning(f"OF {id_mod_se} bloqué.")
            st.rerun()
      with col_c:
        cause_dec = st.text_input("Motif du décalage SE", key="input_dec_se")
        if st.button("⏳ Décaler SE"):
          if of_courant:
            of_courant["statut"] = "Décalé"
            of_courant["cause_decalage"] = cause_dec
            sauvegarder_donnees(data)
            st.info(f"OF {id_mod_se} décalé.")
            st.rerun()
      with col_d:
        st.write("")
        if st.button("🗑️ Supprimer OF SE"):
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
        options_c = {
            f"{c['nom']} ({c.get('temps_fabrication', 1.0)}h unit.)": c
            for c in liste_cons
        }
        choix_c_cle = st.selectbox(
            "Consommable à fabriquer", list(options_c.keys())
        )

        c1, c2 = st.columns(2)
        with c1:
          qte_c = st.number_input("Quantité", min_value=1, value=1, key="q_c")
          date_l_c = st.date_input(
              "Date de lancement", value=datetime.today(), key="d_l_c"
          )
        with c2:
          prio_c = st.selectbox(
              "Priorité", ["Normale", "Haute", "Urgente"], key="prio_c"
          )
          tech_c = st.selectbox(
              "Assigné à (Technicien Consommables)",
              ["Non assigné"] + liste_tech_cons,
              key="tech_c",
          )

        if st.form_submit_button("Planifier la fabrication"):
          c_sel = options_c[choix_c_cle]
          t_tot_c = c_sel.get("temps_fabrication", 1.0) * qte_c
          nouveau_pc = {
              "id_plan": f"PLAN-CONS-{len(plannings_cons) + 1:03d}",
              "consommable": c_sel["nom"],
              "quantite": qte_c,
              "temps_total_estime_h": t_tot_c,
              "date_lancement": str(date_l_c),
              "priorite": prio_c,
              "assigne": tech_c,
              "statut": "Planifié",
              "cause_blocage": "",
              "cause_decalage": "",
          }
          plannings_cons.append(nouveau_pc)
          data["planification_cons"] = plannings_cons
          sauvegarder_donnees(data)
          st.success("Fabrication de consommable planifiée avec succès.")
          st.rerun()

    st.subheader("Suivi & Gestion des OF Consommables")
    if plannings_cons:
      df_all_co = pd.DataFrame(plannings_cons)
      st.dataframe(df_all_co, use_container_width=True)
      st.download_button(
          label="📥 Exporter tous les OFs Consommables (CSV)",
          data=convertir_df_en_csv(df_all_co),
          file_name="tous_les_ofs_consommables.csv",
          mime="text/csv",
      )

      id_mod_c = st.selectbox(
          "Sélectionner un OF Consommable (par ID)",
          [p["id_plan"] for p in plannings_cons],
      )
      cons_courant = next(
          (p for p in plannings_cons if p["id_plan"] == id_mod_c), None
      )

      col_ca, col_cb, col_cc, col_cd = st.columns(4)
      with col_ca:
        if st.button("✅ Terminer Cons."):
          if cons_courant:
            cons_courant["statut"] = "Terminé"
            cons_courant["cause_blocage"] = ""
            sauvegarder_donnees(data)
            st.success(f"OF {id_mod_c} terminé.")
            st.rerun()
      with col_cb:
        cause_bloc_c = st.text_input(
            "Motif du blocage Cons.", key="input_bloc_c"
        )
        if st.button("🔒 Bloquer Cons."):
          if cons_courant:
            cons_courant["statut"] = "Bloqué"
            cons_courant["cause_blocage"] = cause_bloc_c
            sauvegarder_donnees(data)
            st.warning(f"OF {id_mod_c} bloqué.")
            st.rerun()
      with col_cc:
        cause_dec_c = st.text_input(
            "Motif du décalage Cons.", key="input_dec_c"
        )
        if st.button("⏳ Décaler Cons."):
          if cons_courant:
            cons_courant["statut"] = "Décalé"
            cons_courant["cause_decalage"] = cause_dec_c
            sauvegarder_donnees(data)
            st.info(f"OF {id_mod_c} décalé.")
            st.rerun()
      with col_cd:
        st.write("")
        if st.button("🗑️ Supprimer OF Cons."):
          data["planification_cons"] = [
              p for p in plannings_cons if p["id_plan"] != id_mod_c
          ]
          sauvegarder_donnees(data)
          st.error(f"OF {id_mod_c} supprimé.")
          st.rerun()

  with sub_tab_gantt:
    st.subheader(
        "📈 Vue de type Planning Hebdomadaire (Gantt - Semaine en Cours)"
    )
    st.markdown(
        f"**Semaine du {debut_semaine.strftime('%d/%m/%Y')} au"
        f" {fin_semaine.strftime('%d/%m/%Y')}**"
    )

    jours_semaine = [debut_semaine + timedelta(days=i) for i in range(5)]
    noms_jours = [j.strftime("%A %d/%m") for j in jours_semaine]

    tous_ofs = plannings_se + plannings_cons
    if tous_ofs:
      lignes_gantt = []
      for p in tous_ofs:
        try:
          d_l = datetime.strptime(p["date_lancement"], "%Y-%m-%d").date()
          if debut_semaine <= d_l <= fin_semaine:
            jour_str = d_l.strftime("%A %d/%m")
            nom_objet = p.get("sous_ensemble") or p.get("consommable")
            lignes_gantt.append({
                "ID": p["id_plan"],
                "Élément": nom_objet,
                "Qté": p["quantite"],
                "Technicien": p["assigne"],
                "Statut": p["statut"],
                "Jour": jour_str,
            })
        except:
          pass

      if lignes_gantt:
        st.write(
            "**Répartition globale des lancements (Sous-ensembles &"
            " Consommables) :**"
        )
        tous_techs = ["Tous / Non assigné"] + [
            t["nom"] for t in techniciens_prod + techniciens_cons
        ]

        grille_affichage = []
        for tech in tous_techs:
          ligne_data = {"Technicien / Ressource": tech}
          for j_nom in noms_jours:
            if tech == "Tous / Non assigné":
              matches = [
                  f"{x['Élément']} (x{x['Qté']}) [{x['Statut']}]"
                  for x in lignes_gantt
                  if x["Jour"] == j_nom
              ]
            else:
              matches = [
                  f"{x['Élément']} (x{x['Qté']}) [{x['Statut']}]"
                  for x in lignes_gantt
                  if x["Jour"] == j_nom and x["Technicien"] == tech
              ]
            ligne_data[j_nom] = " | ".join(matches) if matches else ""
          grille_affichage.append(ligne_data)

        df_grille = pd.DataFrame(grille_affichage)
        st.dataframe(df_grille, use_container_width=True)
        st.download_button(
            label="📥 Exporter la vue Gantt / Semaine (CSV)",
            data=convertir_df_en_csv(df_grille),
            file_name=f"gantt_semaine_{debut_semaine}.csv",
            mime="text/csv",
        )
      else:
        st.info("Aucun ordre planifié pour cette semaine.")
    else:
      st.info("Aucun OF disponible.")


# --- ONGLET 5 : ÉQUIPE ---
with onglets[4]:
  st.header("👥 Gestion des Équipes")

  col_eq1, col_eq2 = st.columns(2)

  with col_eq1:
    st.subheader("🛠️ Techniciens Production (Sous-ensembles)")
    with st.form("form_ajout_tech_prod"):
      nom_tp = st.text_input("Nom et Prénom (Prod)")
      if st.form_submit_button("Ajouter technicien Prod") and nom_tp:
        nouveau_tp = {
            "id": f"TECH-P-{len(techniciens_prod) + 1:03d}",
            "nom": nom_tp,
        }
        techniciens_prod.append(nouveau_tp)
        data["techniciens_prod"] = techniciens_prod
        sauvegarder_donnees(data)
        st.success(f"Technicien Prod '{nom_tp}' ajouté.")
        st.rerun()

    if techniciens_prod:
      df_tp = pd.DataFrame(techniciens_prod)
      st.dataframe(df_tp, use_container_width=True)
      suppr_tp = st.selectbox(
          "Supprimer tech. Prod", [t["nom"] for t in techniciens_prod], key="s_tp"
      )
      if st.button("Supprimer Prod"):
        data["techniciens_prod"] = [
            t for t in techniciens_prod if t["nom"] != suppr_tp
        ]
        sauvegarder_donnees(data)
        st.success("Supprimé.")
        st.rerun()
    else:
      st.info("Aucun technicien production.")

  with col_eq2:
    st.subheader("📦 Techniciens Consommables")
    with st.form("form_ajout_tech_cons"):
      nom_tc = st.text_input("Nom et Prénom (Consommables)")
      if st.form_submit_button("Ajouter tech. Consommables") and nom_tc:
        nouveau_tc = {
            "id": f"TECH-C-{len(techniciens_cons) + 1:03d}",
            "nom": nom_tc,
        }
        techniciens_cons.append(nouveau_tc)
        data["techniciens_cons"] = techniciens_cons
        sauvegarder_donnees(data)
        st.success(f"Technicien Cons. '{nom_tc}' ajouté.")
        st.rerun()

    if techniciens_cons:
      df_tc = pd.DataFrame(techniciens_cons)
      st.dataframe(df_tc, use_container_width=True)
      suppr_tc = st.selectbox(
          "Supprimer tech. Cons.", [t["nom"] for t in techniciens_cons], key="s_tc"
      )
      if st.button("Supprimer Cons."):
        data["techniciens_cons"] = [
            t for t in techniciens_cons if t["nom"] != suppr_tc
        ]
        sauvegarder_donnees(data)
        st.success("Supprimé.")
        st.rerun()
    else:
      st.info("Aucun technicien consommables.")


# --- ONGLET 6 : CONGÉS & ABSENCES ---
with onglets[5]:
  st.header("🌴 Gestion des Congés & Absences")

  col_abs1, col_abs2 = st.columns(2)

  with col_abs1:
    st.subheader("Absences - Équipe Production")
    if not techniciens_prod:
      st.warning("Ajoutez d'abord des techniciens Prod.")
    else:
      with st.form("form_abs_prod"):
        op_abs_p = st.selectbox(
            "Technicien Prod", [t["nom"] for t in techniciens_prod]
        )
        motif_p = st.selectbox(
            "Motif",
            ["Congés Payés", "RTT", "Maladie", "Formation", "Autre"],
            key="m_p",
        )
        d_deb_p = st.date_input("Date début", value=datetime.today(), key="dd_p")
        d_fin_p = st.date_input(
            "Date fin", value=datetime.today() + timedelta(days=1), key="df_p"
        )
        if st.form_submit_button("Enregistrer absence Prod"):
          nouvelle_abs = {
              "id": f"ABS-P-{len(absences_prod) + 1:03d}",
              "technicien": op_abs_p,
              "motif": motif_p,
              "date_debut": str(d_deb_p),
              "date_fin": str(d_fin_p),
          }
          absences_prod.append(nouvelle_abs)
          data["absences_prod"] = absences_prod
          sauvegarder_donnees(data)
          st.success("Absence enregistrée.")
          st.rerun()

      if absences_prod:
        st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)
        suppr_ap = st.selectbox(
            "Supprimer absence ID", [a["id"] for a in absences_prod], key="sap"
        )
        if st.button("Supprimer", key="btn_sap"):
          data["absences_prod"] = [
              a for a in absences_prod if a["id"] != suppr_ap
          ]
          sauvegarder_donnees(data)
          st.rerun()

  with col_abs2:
    st.subheader("Absences - Équipe Consommables")
    if not techniciens_cons:
      st.warning("Ajoutez d'abord des techniciens Consommables.")
    else:
      with st.form("form_abs_cons"):
        op_abs_c = st.selectbox(
            "Technicien Consommables", [t["nom"] for t in techniciens_cons]
        )
        motif_c = st.selectbox(
            "Motif",
            ["Congés Payés", "RTT", "Maladie", "Formation", "Autre"],
            key="m_c",
        )
        d_deb_c = st.date_input("Date début", value=datetime.today(), key="dd_c")
        d_fin_c = st.date_input(
            "Date fin", value=datetime.today() + timedelta(days=1), key="df_c"
        )
        if st.form_submit_button("Enregistrer absence Cons."):
          nouvelle_abs_c = {
              "id": f"ABS-C-{len(absences_cons) + 1:03d}",
              "technicien": op_abs_c,
              "motif": motif_c,
              "date_debut": str(d_deb_c),
              "date_fin": str(d_fin_c),
          }
          absences_cons.append(nouvelle_abs_c)
          data["absences_cons"] = absences_cons
          sauvegarder_donnees(data)
          st.success("Absence enregistrée.")
          st.rerun()

      if absences_cons:
        st.dataframe(pd.DataFrame(absences_cons), use_container_width=True)
        suppr_ac = st.selectbox(
            "Supprimer absence ID", [a["id"] for a in absences_cons], key="sac"
        )
        if st.button("Supprimer", key="btn_sac"):
          data["absences_cons"] = [
              a for a in absences_cons if a["id"] != suppr_ac
          ]
          sauvegarder_donnees(data)
          st.rerun()
