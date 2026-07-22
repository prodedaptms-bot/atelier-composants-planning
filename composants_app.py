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
  # Dictionnaire des absences par technicien : {nom_tech: [set de dates d'absence au format YYYY-MM-DD]}
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

  # Regrouper les OFs par technicien assigné
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

  # Fonction utilitaire pour ajouter des jours ouvrés (excluant week-ends et absences du tech)
  def ajouter_jours_ouvres(date_depart, nb_heures_necessaires, tech_nom):
    curr_date = date_depart
    heures_restantes = nb_heures_necessaires
    technicien_absences = abs_par_tech.get(tech_nom, set())

    # Sécurité anti-boucle infinie
    securite = 0
    while heures_restantes > 0 and securite < 365:
      # S'assurer qu'on est un jour ouvré (Lundi=0 ... Vendredi=4)
      while curr_date.weekday() >= 5 or curr_date.strftime(
          "%Y-%m-%d"
      ) in technicien_absences:
        curr_date += timedelta(days=1)

      # Capacité disponible ce jour-là pour ce tech
      capacite_jour = HEURES_JOUR_DEFAUT

      if heures_restantes <= capacite_jour:
        # L'OF se termine ce jour-là
        fin_date = curr_date
        break
      else:
        heures_restantes -= capacite_jour
        curr_date += timedelta(days=1)
        securite += 1

    return curr_date

  # Ordonnancement par technicien
  planning_ordonnance = []
  priorite_poids = {"Urgente": 0, "Haute": 1, "Normale": 2}

  for tech, ofs in ofs_par_tech.items():
    # Trier les OFs par priorité puis par date de lancement souhaitée
    ofs_tries = sorted(
        ofs,
        key=lambda x: (
            priorite_poids.get(x.get("priorite", "Normale"), 2),
            x.get("date_lancement", str(date_reference_debut)),
        ),
    )

    date_dispo_courante = date_reference_debut

    for p in ofs_tries:
      # Date de début au plus tôt entre la demande initiale et la dispo du technicien
      d_souhaitee = datetime.strptime(
          p.get("date_lancement", str(date_reference_debut)), "%Y-%m-%d"
      ).date()
      d_debut_reel = max(d_souhaitee, date_dispo_courante)

      # S'assurer que le jour de début n'est pas un week-end ou une absence
      technicien_absences = abs_par_tech.get(tech, set())
      while d_debut_reel.weekday() >= 5 or d_debut_reel.strftime(
          "%Y-%m-%d"
      ) in technicien_absences:
        d_debut_reel += timedelta(days=1)

      temps_tot = p.get("temps_total_estime_h", 0.0)

      # Calcul de la date de fin estimée en cascade
      d_fin_reel = ajouter_jours_ouvres(d_debut_reel, temps_tot, tech)

      # Mettre à jour l'OF avec ses nouvelles dates calculées
      p_maj = p.copy()
      p_maj["date_debut_cascade"] = str(d_debut_reel)
      p_maj["date_fin_cascade"] = str(d_fin_reel)
      planning_ordonnance.append(p_maj)

      # La prochaine tâche pour ce technicien commence le jour suivant la fin de celle-ci
      date_dispo_courante = d_fin_reel + timedelta(days=1)

  # Ajouter les non assignés sans cascade
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

st.title("🧩 Planification Cascade & Pilotage - Atelier")
st.markdown("---")

onglets = st.tabs([
    "📊 Tableau de Bord",
    "⚙️ Création Sous-ensembles",
    "📦 Références Consommables",
    "📅 Planification & Cascade",
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

# Calcul automatique de la cascade pour la vue globale
ofs_se_cascade = calculer_dates_cascade(
    plannings_se, techniciens_prod, absences_prod, debut_semaine
)
ofs_cons_cascade = calculer_dates_cascade(
    plannings_cons, techniciens_cons, absences_cons, debut_semaine
)

# 1. Analyse OF Sous-ensembles (basée sur la cascade)
ofs_se_semaine = [
    p
    for p in ofs_se_cascade
    if p.get("statut") not in ["Terminé", "Supprimé"]
    and debut_semaine
    <= datetime.strptime(
        p.get("date_debut_cascade", str(debut_semaine)), "%Y-%m-%d"
    ).date()
    <= fin_semaine
]
nb_se_a_realiser = len(plannings_se)
nb_se_termines = sum(
    1 for p in plannings_se if p.get("statut") == "Terminé"
)
charge_restante_se_h = sum(
    p.get("temps_total_estime_h", 0)
    for p in plannings_se
    if p.get("statut") not in ["Terminé", "Supprimé"]
)

# 2. Analyse Consommables
ofs_cons_semaine = [
    p
    for p in ofs_cons_cascade
    if p.get("statut") not in ["Terminé", "Supprimé"]
    and debut_semaine
    <= datetime.strptime(
        p.get("date_debut_cascade", str(debut_semaine)), "%Y-%m-%d"
    ).date()
    <= fin_semaine
]
nb_cons_a_realiser = len(plannings_cons)
nb_cons_termines = sum(
    1 for p in plannings_cons if p.get("statut") == "Terminé"
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
  st.header("📊 Tableau de Bord & Charge Globale")
  st.markdown(
      f"**Semaine en cours :** du {debut_semaine.strftime('%d/%m/%Y')} au"
      f" {fin_semaine.strftime('%d/%m/%Y')}"
  )

  c1, c2 = st.columns(2)
  with c1:
    st.subheader("🛠️ Production Sous-ensembles")
    st.metric("Charge totale restante", f"{charge_restante_se_h:.1f} h")
    st.metric(
        "Capacité théorique hebdo", f"{capacite_dispo_prod_h:.1f} h brut"
    )
    if charge_restante_se_h > capacite_dispo_prod_h:
      st.error("🚨 Surcharge détectée en Production SE")
    else:
      st.success("✅ Capacité Prod SE OK")

  with c2:
    st.subheader("📦 Fabrication Consommables")
    st.metric("Charge totale restante", f"{charge_restante_cons_h:.1f} h")
    st.metric(
        "Capacité théorique hebdo", f"{capacite_dispo_cons_h:.1f} h brut"
    )
    if charge_restante_cons_h > capacite_dispo_cons_h:
      st.error("🚨 Surcharge détectée en Consommables")
    else:
      st.success("✅ Capacité Consommables OK")


# --- ONGLET 4 : PLANIFICATION & CASCADE ---
with onglets[3]:
  st.header("📅 Ordonnancement en Cascade & Simulation")
  st.markdown(
      "L'ordonnancement place automatiquement les OFs les uns à la suite des"
      " autres par technicien, en sautant les week-ends et les jours d'absence"
      " saisis."
  )

  sub_tab1, sub_tab2, sub_tab_cascade = st.tabs([
      "🛠️ OFs Sous-ensembles",
      "📦 OFs Consommables",
      "⚡ Vue Cascade & Simulation",
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
          st.success(
              "OF planifié ! Le calendrier en cascade a été recalculé."
          )
          st.rerun()

    if plannings_se:
      st.subheader("Gestion des OFs SE existants")
      df_se_brut = pd.DataFrame(plannings_se)
      st.dataframe(df_se_brut, use_container_width=True)

      id_sup_se = st.selectbox(
          "ID OF à supprimer/terminer",
          [p["id_plan"] for p in plannings_se],
          key="del_se",
      )
      c_a, c_b = st.columns(2)
      with c_a:
        if st.button("Marquer comme Terminé SE"):
          for p in plannings_se:
            if p["id_plan"] == id_sup_se:
              p["statut"] = "Terminé"
          sauvegarder_donnees(data)
          st.rerun()
      with c_b:
        if st.button("Supprimer OF SE"):
          data["planification_se"] = [
              p for p in plannings_se if p["id_plan"] != id_sup_se
          ]
          sauvegarder_donnees(data)
          st.rerun()

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

    if plannings_cons:
      st.subheader("Gestion des OFs Consommables existants")
      df_co_brut = pd.DataFrame(plannings_cons)
      st.dataframe(df_co_brut, use_container_width=True)

      id_sup_co = st.selectbox(
          "ID OF Cons. à supprimer/terminer",
          [p["id_plan"] for p in plannings_cons],
          key="del_co",
      )
      cc_a, cc_b = st.columns(2)
      with cc_a:
        if st.button("Marquer comme Terminé Cons."):
          for p in plannings_cons:
            if p["id_plan"] == id_sup_co:
              p["statut"] = "Terminé"
          sauvegarder_donnees(data)
          st.rerun()
      with cc_b:
        if st.button("Supprimer OF Cons."):
          data["planification_cons"] = [
              p for p in plannings_cons if p["id_plan"] != id_sup_co
          ]
          sauvegarder_donnees(data)
          st.rerun()

  with sub_tab_cascade:
    st.subheader(
        "⚡ Planning Ordonnancé en Cascade (Affectations & Enchaînements réels)"
    )
    if st.button(
        "🔄 Recalculer la cascade (Actualisation congés / modifications)"
    ):
      st.rerun()

    st.markdown("### 🛠️ Production - Sous-ensembles (Cascade)")
    if ofs_se_cascade:
      df_cas_se = pd.DataFrame(ofs_se_cascade)
      st.dataframe(df_cas_se, use_container_width=True)
      st.download_button(
          label="📥 Exporter la cascade SE (CSV)",
          data=convertir_df_en_csv(df_cas_se),
          file_name="cascade_sous_ensembles.csv",
          mime="text/csv",
      )
    else:
      st.info("Aucun sous-ensemble à ordonnancer.")

    st.markdown("### 📦 Consommables (Cascade)")
    if ofs_cons_cascade:
      df_cas_co = pd.DataFrame(ofs_cons_cascade)
      st.dataframe(df_cas_co, use_container_width=True)
      st.download_button(
          label="📥 Exporter la cascade Consommables (CSV)",
          data=convertir_df_en_csv(df_cas_co),
          file_name="cascade_consommables.csv",
          mime="text/csv",
      )
    else:
      st.info("Aucun consommable à ordonnancer.")


# --- ONGLETS 2, 3, 5, 6 (Reste inchangé pour Catalogue, Équipe et Absences) ---
with onglets[1]:
  st.header("Catalogue des Sous-ensembles")
  if data.get("sous_ensembles"):
    st.dataframe(pd.DataFrame(data["sous_ensembles"]), use_container_width=True)

with onglets[2]:
  st.header("Catalogue des Consommables")
  if data.get("consommables"):
    st.dataframe(pd.DataFrame(data["consommables"]), use_container_width=True)

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
      st.dataframe(pd.DataFrame(techniciens_prod))
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
      st.dataframe(pd.DataFrame(techniciens_cons))

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
              "date_lancement": str(db_p),
              "date_debut": str(db_p),
              "date_fin": str(df_p),
          })
          data["absences_prod"] = absences_prod
          sauvegarder_donnees(data)
          st.success(
              "Absence enregistrée, la cascade s'ajustera automatiquement."
          )
          st.rerun()
      if absences_prod:
        st.dataframe(pd.DataFrame(absences_prod))
