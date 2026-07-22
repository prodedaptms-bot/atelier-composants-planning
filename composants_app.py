from datetime import datetime, timedelta
import json
import os
import pandas as pd
import streamlit as st

DATA_FILE = "donnees_composants.json"
CAPACITE_HEBDO = 35.0
HEURES_JOUR_DEFAUT = 7.0  # Capacité journalière effective par technicien


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


def calculer_dates_cascade(
    plannings, techniciens, absences, date_reference_debut
):
  """Moteur d'ordonnancement en cascade (Forward Scheduling) tenant compte des absences."""
  abs_par_tech = {}
  for abs_rec in absences:
    tech = abs_rec.get("technicien")
    try:
      d_deb = datetime.strptime(abs_rec["date_debut"], "%Y-%m-%d").date()
      d_fin = datetime.strptime(abs_rec["date_fin"], "%Y-%m-%d").date()
      curr = d_deb
      if tech not in abs_par_tech:
        abs_par_tech[tech] = set()
      while curr <= d_fin:
        abs_par_tech[tech].add(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    except:
      pass

  ofs_par_tech = {}
  ofs_non_assignes = []

  for p in plannings:
    if p.get("statut") in ["Terminé", "Supprimé"]:
      continue
    tech = p.get("assigne")
    if tech and tech != "Non assigné":
      ofs_par_tech.setdefault(tech, []).append(p)
    else:
      ofs_non_assignes.append(p)

  def ajouter_jours_ouvres(date_depart, nb_heures_necessaires, tech_nom):
    curr_date = date_depart
    heures_restantes = nb_heures_necessaires
    technicien_absences = abs_par_tech.get(tech_nom, set())

    securite = 0
    while heures_restantes > 0 and securite < 365:
      while curr_date.weekday() >= 5 or curr_date.strftime(
          "%Y-%m-%d"
      ) in technicien_absences:
        curr_date += timedelta(days=1)

      capacite_jour = HEURES_JOUR_DEFAUT

      if heures_restantes <= capacite_jour:
        break
      else:
        heures_restantes -= capacite_jour
        curr_date += timedelta(days=1)
        securite += 1

    return curr_date

  planning_ordonnance = []
  priorite_poids = {"Urgente": 0, "Haute": 1, "Normale": 2}

  for tech, ofs in ofs_par_tech.items():
    ofs_tries = sorted(
        ofs,
        key=lambda x: (
            priorite_poids.get(x.get("priorite", "Normale"), 2),
            x.get("date_lancement", str(date_reference_debut)),
        ),
    )

    date_dispo_courante = date_reference_debut

    for p in ofs_tries:
      d_souhaitee = datetime.strptime(
          p.get("date_lancement", str(date_reference_debut)), "%Y-%m-%d"
      ).date()
      d_debut_reel = max(d_souhaitee, date_dispo_courante)

      technicien_absences = abs_par_tech.get(tech, set())
      while d_debut_reel.weekday() >= 5 or d_debut_reel.strftime(
          "%Y-%m-%d"
      ) in technicien_absences:
        d_debut_reel += timedelta(days=1)

      temps_tot = p.get("temps_total_estime_h", 0.0)
      d_fin_reel = ajouter_jours_ouvres(d_debut_reel, temps_tot, tech)

      p_maj = p.copy()
      p_maj["date_debut_cascade"] = str(d_debut_reel)
      p_maj["date_fin_cascade"] = str(d_fin_reel)
      planning_ordonnance.append(p_maj)

      date_dispo_courante = d_fin_reel + timedelta(days=1)

  for p in ofs_non_assignes:
    p_maj = p.copy()
    p_maj["date_debut_cascade"] = p.get("date_lancement")
    p_maj["date_fin_cascade"] = p.get("date_lancement")
    planning_ordonnance.append(p_maj)

  return planning_ordonnance


st.set_page_config(
    page_title="Planification - Atelier Sous-ensembles & Consommables",
    layout="wide",
)

data = charger_donnees()

# --- BANDEAU TOUT EN HAUT ---
st.markdown(
    """
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #ff4b4b;">
        <h3 style="margin: 0; color: #31333F;">🧩 Atelier de Production - Pilotage & Planification en Cascade</h3>
        <p style="margin: 5px 0 0 0; color: #555;">Gestion centralisée des sous-ensembles, des consommables, des charges et des plannings de l'équipe.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.title("🧩 Planification Cascade & Pilotage - Atelier")
st.markdown("---")

onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "📅 Planification & Cascade",
    "👥 Équipe",
    "🌴 Congés & Absences",
    "💾 Sauvegarde & Données",
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

# Calcul automatique de la cascade
ofs_se_cascade = calculer_dates_cascade(
    plannings_se, techniciens_prod, absences_prod, debut_semaine
)
ofs_cons_cascade = calculer_dates_cascade(
    plannings_cons, techniciens_cons, absences_cons, debut_semaine
)

charge_restante_se_h = sum(
    p.get("temps_total_estime_h", 0)
    for p in plannings_se
    if p.get("statut") not in ["Terminé", "Supprimé"]
)
charge_restante_cons_h = sum(
    p.get("temps_total_estime_h", 0)
    for p in plannings_cons
    if p.get("statut") not in ["Terminé", "Supprimé"]
)

capacite_dispo_prod_h = len(techniciens_prod) * CAPACITE_HEBDO
capacite_dispo_cons_h = len(techniciens_cons) * CAPACITE_HEBDO


# --- ONGLET 1 : TABLEAU DE BORD ---
with onglets[0]:
  st.header("📊 Tableau de Bord & Suivi des OFs")
  st.markdown(
      f"**Semaine en cours :** du {debut_semaine.strftime('%d/%m/%Y')} au"
      f" {fin_semaine.strftime('%d/%m/%Y')}"
  )

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🛠️ Production Sous-ensembles")
    st.metric("Charge totale restante", f"{charge_restante_se_h:.1f} h")
    if charge_restante_se_h > capacite_dispo_prod_h:
      st.error("🚨 Surcharge détectée en Production SE")
    else:
      st.success("✅ Capacité Prod SE OK")

  with c2:
    st.subheader("📦 Fabrication Consommables")
    st.metric("Charge totale restante", f"{charge_restante_cons_h:.1f} h")
    if charge_restante_cons_h > capacite_dispo_cons_h:
      st.error("🚨 Surcharge détectée en Consommables")
    else:
      st.success("✅ Capacité Consommables OK")

  st.markdown("---")

  st.subheader("🛠️ Suivi détaillé des OFs Sous-ensembles (avec Cascade)")
  if ofs_se_cascade:
    df_dashboard_se = pd.DataFrame(ofs_se_cascade)
    st.dataframe(df_dashboard_se, use_container_width=True)
    st.download_button(
        label="📥 Exporter le suivi OFs SE (CSV)",
        data=convertir_df_en_csv(df_dashboard_se),
        file_name="suivi_ofs_se.csv",
        mime="text/csv",
        key="exp_dash_se",
    )
  else:
    st.info("Aucun OF Sous-ensemble enregistré.")

  st.markdown("---")

  st.subheader("📦 Suivi détaillé des OFs Consommables (avec Cascade)")
  if ofs_cons_cascade:
    df_dashboard_cons = pd.DataFrame(ofs_cons_cascade)
    st.dataframe(df_dashboard_cons, use_container_width=True)
    st.download_button(
        label="📥 Exporter le suivi OFs Consommables (CSV)",
        data=convertir_df_en_csv(df_dashboard_cons),
        file_name="suivi_ofs_consommables.csv",
        mime="text/csv",
        key="exp_dash_cons",
    )
  else:
    st.info("Aucun OF Consommable enregistré.")


# --- ONGLET 2 : CRÉATION SOUS-ENSEMBLES ---
with onglets[1]:
  st.header("⚙️ Gestion & Création des Sous-ensembles")

  with st.form("form_creer_se"):
    st.subheader("Ajouter un nouveau modèle de Sous-ensemble")
    nom_se = st.text_input("Nom du Sous-ensemble")
    ref_se = st.text_input("Référence / Code")
    temps_fab_se = st.number_input(
        "Temps de fabrication unitaire (heures)",
        min_value=0.1,
        value=1.0,
        step=0.1,
    )
    desc_se = st.text_area("Description / Instructions")

    if st.form_submit_button("Enregistrer le Sous-ensemble"):
      if nom_se:
        nouveau_modele_se = {
            "id": f"SE-{len(data.get('sous_ensembles', [])) + 1:03d}",
            "nom": nom_se,
            "reference": ref_se,
            "temps_fabrication": temps_fab_se,
            "description": desc_se,
        }
        data.setdefault("sous_ensembles", []).append(nouveau_modele_se)
        sauvegarder_donnees(data)
        st.success(f"Sous-ensemble '{nom_se}' créé avec succès !")
        st.rerun()
      else:
        st.error("Le nom du sous-ensemble est obligatoire.")

  st.markdown("---")
  st.subheader("Catalogue actuel des Sous-ensembles")
  liste_se_actuelle = data.get("sous_ensembles", [])
  if liste_se_actuelle:
    df_se = pd.DataFrame(liste_se_actuelle)
    st.dataframe(df_se, use_container_width=True)

    id_a_supprimer = st.selectbox(
        "Sélectionner un Sous-ensemble à supprimer du catalogue",
        [item["id"] for item in liste_se_actuelle],
        key="suppr_cat_se",
    )
    if st.button("Supprimer ce Sous-ensemble"):
      data["sous_ensembles"] = [
          item for item in liste_se_actuelle if item["id"] != id_a_supprimer
      ]
      sauvegarder_donnees(data)
      st.success("Sous-ensemble supprimé.")
      st.rerun()
  else:
    st.info("Aucun sous-ensemble configuré pour l'instant.")


# --- ONGLET 3 : RÉFÉRENCES CONSOMMABLES ---
with onglets[2]:
  st.header("📦 Gestion & Références des Consommables")

  with st.form("form_creer_cons"):
    st.subheader("Ajouter un nouveau Consommable")
    nom_cons = st.text_input("Nom du Consommable")
    ref_cons = st.text_input("Référence / Code Consommable")
    temps_fab_cons = st.number_input(
        "Temps de fabrication unitaire (heures)",
        min_value=0.1,
        value=0.5,
        step=0.1,
        key="t_fab_c",
    )
    desc_cons = st.text_area("Description / Instructions Consommable", key="desc_c")

    if st.form_submit_button("Enregistrer le Consommable"):
      if nom_cons:
        nouveau_modele_cons = {
            "id": f"CONS-{len(data.get('consommables', [])) + 1:03d}",
            "nom": nom_cons,
            "reference": ref_cons,
            "temps_fabrication": temps_fab_cons,
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


# --- ONGLET 4 : PLANIFICATION & CASCADE ---
with onglets[3]:
  st.header("📅 Ordonnancement en Cascade & Vues Gantt Semaine")

  sub_tab1, sub_tab2, sub_tab_cascade, sub_tab_gantt_couleurs = st.tabs([
      "🛠️ Lancer un OF SE",
      "📦 Lancer un OF Cons.",
      "⚡ Gestion & Cascade Globale",
      "🎨 Planning Gantt par Technicien (Couleurs)",
  ])

  with sub_tab1:
    liste_se = data.get("sous_ensembles", [])
    liste_tech_prod = [t["nom"] for t in techniciens_prod]
    if liste_se:
      with st.form("form_plan_se"):
        options_se = {
            f"{se['nom']} ({se.get('temps_fabrication', 1.0)}h unit.)": se
            for se in liste_se
        }
        choix_se_cle = st.selectbox(
            "Sous-ensemble à fabriquer", list(options_se.keys())
        )
        qte_se = st.number_input("Quantité", min_value=1, value=1)
        date_l_se = st.date_input("Date de lancement souhaitée", value=auj)
        prio_se = st.selectbox("Priorité", ["Normale", "Haute", "Urgente"])
        tech_se = st.selectbox(
            "Assigné à (Technicien Production)",
            ["Non assigné"] + liste_tech_prod,
        )

        if st.form_submit_button("Planifier et enchaîner"):
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
          }
          plannings_se.append(nouveau_p)
          data["planification_se"] = plannings_se
          sauvegarder_donnees(data)
          st.success("OF planifié avec succès.")
          st.rerun()
    else:
      st.warning(
          "Veuillez d'abord créer des sous-ensembles dans l'onglet '⚙️ Création"
          " Sous-ensembles'."
      )

  with sub_tab2:
    liste_cons = data.get("consommables", [])
    liste_tech_cons = [t["nom"] for t in techniciens_cons]
    if liste_cons:
      with st.form("form_plan_cons"):
        options_c = {
            f"{c['nom']} ({c.get('temps_fabrication', 1.0)}h unit.)": c
            for c in liste_cons
        }
        choix_c_cle = st.selectbox(
            "Consommable à fabriquer", list(options_c.keys())
        )
        qte_c = st.number_input("Quantité", min_value=1, value=1, key="qc")
        date_l_c = st.date_input(
            "Date de lancement souhaitée", value=auj, key="dlc"
        )
        prio_c = st.selectbox(
            "Priorité", ["Normale", "Haute", "Urgente"], key="pric"
        )
        tech_c = st.selectbox(
            "Assigné à (Technicien Consommables)",
            ["Non assigné"] + liste_tech_cons,
            key="techc",
        )

        if st.form_submit_button("Planifier fabrication consommable"):
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
          }
          plannings_cons.append(nouveau_pc)
          data["planification_cons"] = plannings_cons
          sauvegarder_donnees(data)
          st.success("Planification consommable enregistrée.")
          st.rerun()
    else:
      st.warning(
          "Veuillez d'abord créer des consommables dans l'onglet '📦 Références"
          " Consommables'."
      )

  with sub_tab_cascade:
    st.subheader("⚡ Gestion & Actions sur les OFs")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
      if plannings_se:
        id_sup_se = st.selectbox(
            "ID OF SE à modifier/terminer",
            [p["id_plan"] for p in plannings_se],
            key="del_se",
        )
        if st.button("Marquer comme Terminé SE"):
          for p in plannings_se:
            if p["id_plan"] == id_sup_se:
              p["statut"] = "Terminé"
          sauvegarder_donnees(data)
          st.rerun()
        if st.button("Supprimer OF SE"):
          data["planification_se"] = [
              p for p in plannings_se if p["id_plan"] != id_sup_se
          ]
          sauvegarder_donnees(data)
          st.rerun()

    with col_act2:
      if plannings_cons:
        id_sup_co = st.selectbox(
            "ID OF Cons. à modifier/terminer",
            [p["id_plan"] for p in plannings_cons],
            key="del_co",
        )
        if st.button("Marquer comme Terminé Cons."):
          for p in plannings_cons:
            if p["id_plan"] == id_sup_co:
              p["statut"] = "Terminé"
          sauvegarder_donnees(data)
          st.rerun()
        if st.button("Supprimer OF Cons."):
          data["planification_cons"] = [
              p for p in plannings_cons if p["id_plan"] != id_sup_co
          ]
          sauvegarder_donnees(data)
          st.rerun()

  with sub_tab_gantt_couleurs:
    st.subheader("🎨 Planning Semaine par Technicien & Code Couleur")
    st.markdown(
        "Visualisez l'affectation de chaque technicien pour la semaine en"
        " cours. Une couleur unique est attribuée par technicien."
    )

    tous_techs = [t["nom"] for t in techniciens_prod + techniciens_cons]
    palette_couleurs = [
        "🔵",
        "🟢",
        "🟠",
        "🟣",
        "🔴",
        "🟤",
        "🟡",
        "🔷",
        "🟩",
        "🟧",
    ]
    tech_couleur_map = {
        tech: palette_couleurs[i % len(palette_couleurs)]
        for i, tech in enumerate(tous_techs)
    }

    st.markdown("**Légende des techniciens :**")
    légende_markdown = " | ".join([
        f"{couleur} **{tech}**" for tech, couleur in tech_couleur_map.items()
    ])
    st.markdown(légende_markdown if légende_markdown else "Aucun technicien.")

    jours_semaine = [debut_semaine + timedelta(days=i) for i in range(5)]
    tous_ofs_cascade = ofs_se_cascade + ofs_cons_cascade

    grille_gantt_couleur = []
    ligne_na = {"Technicien": "Non assigné ⚪"}
    for j in jours_semaine:
      j_str = str(j)
      matches = [
          f"[Non assigné] {x.get('sous_ensemble') or x.get('consommable')} (x{x['quantite']})"
          for x in tous_ofs_cascade
          if x.get("assigne") in [None, "Non assigné"]
          and x.get("statut") not in ["Terminé", "Supprimé"]
          and x.get("date_debut_cascade")
          <= j_str
          <= x.get("date_fin_cascade")
      ]
      ligne_na[j.strftime("%A %d/%m")] = " | ".join(matches) if matches else ""
    grille_gantt_couleur.append(ligne_na)

    for tech in tous_techs:
      couleur = tech_couleur_map.get(tech, "🔵")
      ligne_tech = {"Technicien": f"{tech} {couleur}"}
      for j in jours_semaine:
        j_str = str(j)
        matches = [
            f"{x.get('sous_ensemble') or x.get('consommable')} (x{x['quantite']}) [{x.get('statut')}]"
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

    df_gantt_couleur = pd.DataFrame(grille_gantt_couleur)
    st.dataframe(df_gantt_couleur, use_container_width=True)

    st.download_button(
        label="📥 Exporter le Planning Gantt Couleurs (CSV)",
        data=convertir_df_en_csv(df_gantt_couleur),
        file_name=f"planning_gantt_couleurs_{debut_semaine}.csv",
        mime="text/csv",
    )


# --- ONGLET 5 : ÉQUIPE ---
with onglets[4]:
  st.header("👥 Gestion des Équipes")
  col_eq1, col_eq2 = st.columns(2)
  with col_eq1:
    st.subheader("Techniciens Prod")
    with st.form("form_tp"):
      ntp = st.text_input("Nom Tech Prod")
      if st.form_submit_button("Ajouter") and ntp:
        techniciens_prod.append(
            {"id": f"TECH-P-{len(techniciens_prod)+1:03d}", "nom": ntp}
        )
        data["techniciens_prod"] = techniciens_prod
        sauvegarder_donnees(data)
        st.rerun()
    if techniciens_prod:
      st.dataframe(pd.DataFrame(techniciens_prod), use_container_width=True)
  with col_eq2:
    st.subheader("Techniciens Consommables")
    with st.form("form_tc"):
      ntc = st.text_input("Nom Tech Cons.")
      if st.form_submit_button("Ajouter") and ntc:
        techniciens_cons.append(
            {"id": f"TECH-C-{len(techniciens_cons)+1:03d}", "nom": ntc}
        )
        data["techniciens_cons"] = techniciens_cons
        sauvegarder_donnees(data)
        st.rerun()
    if techniciens_cons:
      st.dataframe(pd.DataFrame(techniciens_cons), use_container_width=True)


# --- ONGLET 6 : CONGÉS & ABSENCES ---
with onglets[5]:
  st.header("🌴 Congés & Absences")
  c_ab1, c_ab2 = st.columns(2)
  with c_ab1:
    st.subheader("Absences Prod")
    if techniciens_prod:
      with st.form("absp"):
        t_p = st.selectbox("Tech", [t["nom"] for t in techniciens_prod])
        m_p = st.selectbox(
            "Motif", ["Congés Payés", "RTT", "Maladie", "Formation"]
        )
        db_p = st.date_input("Début", auj, key="ab_db")
        df_p = st.date_input("Fin", auj, key="ab_df")
        if st.form_submit_button("Enregistrer absence"):
          absences_prod.append({
              "id": f"ABS-P-{len(absences_prod)+1:03d}",
              "technicien": t_p,
              "motif": m_p,
              "date_debut": str(db_p),
              "date_fin": str(df_p),
          })
          data["absences_prod"] = absences_prod
          sauvegarder_donnees(data)
          st.success("Absence enregistrée.")
          st.rerun()
      if absences_prod:
        st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)


# --- ONGLET 7 : SAUVEGARDE & DONNÉES (EXPORT / IMPORT) ---
with onglets[6]:
  st.header("💾 Gestion de la Base de Données (Sauvegarde & Import)")
  st.markdown(
      "Vous pouvez ici sauvegarder l'intégralité de vos données (catalogues,"
      " plannings, équipes) sous forme de fichier JSON, ou restaurer une"
      " sauvegarde précédente."
  )

  col_sav1, col_sav2 = st.columns(2)

  with col_sav1:
    st.subheader("📤 Sauvegarder / Exporter")
    st.markdown("Télécharger la base de données active sur votre poste.")
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Télécharger le fichier de sauvegarde (.json)",
        data=json_str,
        file_name=f"sauvegarde_atelier_{auj.strftime('%Y-%m-%d')}.json",
        mime="application/json",
    )

  with col_sav2:
    st.subheader("📥 Importer / Restaurer")
    st.markdown(
        "Remplacer les données actuelles par un fichier de sauvegarde JSON."
    )
    fichier_importe = st.file_uploader(
        "Choisir un fichier de sauvegarde JSON", type=["json"]
    )
    if fichier_importe is not None:
      if st.button("⚠️ Valider et restaurer cette base de données"):
        try:
          donnees_chargees = json.load(fichier_importe)
          # Vérification basique des clés principales
          if isinstance(donnees_chargees, dict):
            sauvegarder_donnees(donnees_chargees)
            st.success(
                "Base de données importée et restaurée avec succès ! Rechargement"
                " en cours..."
            )
            st.rerun()
          else:
            st.error("Format de fichier invalide.")
        except Exception as e:
          st.error(f"Erreur lors de l'importation du fichier : {e}")
