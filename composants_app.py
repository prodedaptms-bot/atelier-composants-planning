import streamlit as st

# --- CONFIGURATION DE LA PAGE (DOIT ÊTRE STRICTEMENT EN PREMIER) ---
st.set_page_config(
    page_title="Pilotage Atelier - Planification & Charges",
    page_layout="wide"
)

from datetime import datetime, timedelta
import pandas as pd

HEURES_JOUR_DEFAUT = 7.0

def charger_donnees():
    if "donnees_atelier" not in st.session_state:
        st.session_state["donnees_atelier"] = {
            "plannings_se": [],
            "plannings_cons": [],
            "technicien_prod": [{"nom": "Alexandre"}, {"nom": "Thomas"}],
            "technicien_cons": [{"nom": "Nicolas"}, {"nom": "Julien"}],
            "absences_prod": [],
            "absences_cons": []
        }
    return st.session_state["donnees_atelier"]

def sauvegarder_donnees(data):
    st.session_state["donnees_atelier"] = data

data = charger_donnees()
plannings_se = data.get("plannings_se", [])
plannings_cons = data.get("plannings_cons", [])
techniciens_prod = data.get("technicien_prod", [])
techniciens_cons = data.get("technicien_cons", [])
absences_prod = data.get("absences_prod", [])
absences_cons = data.get("absences_cons", [])

absences_globales = absences_prod.copy()
for ac in absences_cons:
    if ac not in absences_globales:
        absences_globales.append(ac)

def calculer_dates_cascade(plannings, techniciens, absences, date_reference_debut):
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
            while curr_date.weekday() >= 5 or curr_date.strftime("%Y-%m-%d") in technicien_absences:
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
            d_souhaitee_str = p.get("date_lancement", str(date_reference_debut))
            try:
                d_souhaitee = datetime.strptime(d_souhaitee_str, "%Y-%m-%d").date()
            except:
                d_souhaitee = date_reference_debut

            d_debut_reel = max(d_souhaitee, date_dispo_courante)

            technicien_absences = abs_par_tech.get(tech, set())
            while d_debut_reel.weekday() >= 5 or d_debut_reel.strftime("%Y-%m-%d") in technicien_absences:
                d_debut_reel += timedelta(days=1)

            temps_tot = p.get("temps_total_estime_h", 0.0)
            d_fin_reel = ajouter_jours_ouvres(d_debut_reel, temps_tot, tech)

            semaine_debut = d_debut_reel - timedelta(days=d_debut_reel.weekday())
            semaine_fin = semaine_debut + timedelta(days=4)

            p_maj = p.copy()
            p_maj["date_debut_cascade"] = str(d_debut_reel)
            p_maj["date_fin_cascade"] = str(d_fin_reel)
            p_maj["semaine_concernee"] = f"S{semaine_debut.isocalendar()[1]} ({semaine_debut.strftime('%d/%m')} au {semaine_fin.strftime('%d/%m')})"
            planning_ordonnance.append(p_maj)

            date_dispo_courante = max(date_dispo_courante, d_fin_reel + timedelta(days=1))

    for p in ofs_non_assignes:
        p_maj = p.copy()
        p_maj["date_debut_cascade"] = p.get("date_lancement")
        p_maj["date_fin_cascade"] = p.get("date_lancement")
        p_maj["semaine_concernee"] = "Non assigné / Non planifié"
        planning_ordonnance.append(p_maj)

    return planning_ordonnance

auj = datetime.today().date()
debut_semaine = auj - timedelta(days=auj.weekday())
fin_semaine = debut_semaine + timedelta(days=4)

ofs_se_cascade = calculer_dates_cascade(plannings_se, techniciens_prod, absences_globales, debut_semaine)
ofs_cons_cascade = calculer_dates_cascade(plannings_cons, techniciens_cons, absences_globales, debut_semaine)

charge_restante_se_h = sum([p.get("temps_total_estime_h", 0.0) for p in ofs_se_cascade if p.get("statut") not in ["Terminé", "Supprimé"]])
charge_restante_cons_h = sum([p.get("temps_total_estime_h", 0.0) for p in ofs_cons_cascade if p.get("statut") not in ["Terminé", "Supprimé"]])

capacite_dispo_prod_h = len(techniciens_prod) * 5 * HEURES_JOUR_DEFAUT
capacite_dispo_cons_h = len(techniciens_cons) * 5 * HEURES_JOUR_DEFAUT

def convertir_df_en_csv(df):
    return df.to_csv(index=False).encode('utf-8')

st.title("⚙️ Pilotage & Planification Atelier")

onglets = st.tabs(["Tableau de Bord", "OFs Sous-ensembles", "OFs Consommables", "Techniciens", "Planification", "Congés & Absences"])

with onglets[0]:
    st.header("📊 Tableau de Bord & Suivi des OFs")
    st.markdown(f"**Semaine en cours :** du {debut_semaine.strftime('%d/%m/%Y')} au {fin_semaine.strftime('%d/%m/%Y')}")

    type_conversion = st.selectbox(
        "Mode de conversion des quantités (Tableau de bord) :",
        ["Aucune (Unités de base)", "Conversion en Lots (1 lot = 10 unités)", "Conversion en Millivis (x1000)"],
        key="conv_dashboard"
    )

    def appliquer_conversion(df):
        if df.empty:
            return df
        df_c = df.copy()
        if "quantite" in df_c.columns:
            if type_conversion == "Conversion en Lots (1 lot = 10 unités)":
                df_c["quantite_convertie"] = df_c["quantite"] / 10
                df_c["unite_convertie"] = "Lots"
            elif type_conversion == "Conversion en Millivis (x1000)":
                df_c["quantite_convertie"] = df_c["quantite"] * 1000
                df_c["unite_convertie"] = "Millivis"
            else:
                df_c["quantite_convertie"] = df_c["quantite"]
                df_c["unite_convertie"] = "Unités"
        return df_c

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

    st.subheader("👥 Suivi détaillé de la charge par Technicien et par Semaine (Ventilé)")
    tous_ofs_synthese = ofs_se_cascade + ofs_cons_cascade
    
    if tous_ofs_synthese:
        df_synth = pd.DataFrame(tous_ofs_synthese)
        df_synth_actifs = df_synth[~df_synth["statut"].isin(["Terminé", "Supprimé"])]
        
        if not df_synth_actifs.empty and "date_debut_cascade" in df_synth_actifs.columns:
            lignes_ventilees = []
            
            for _, row in df_synth_actifs.iterrows():
                tech = row.get("assigne", "Non assigné")
                if not tech or tech == "Nan":
                    tech = "Non assigné"
                
                temps_total = row.get("temps_total_estime_h", 0.0)
                d_deb_str = row.get("date_debut_cascade")
                d_fin_str = row.get("date_fin_cascade")
                
                if not d_deb_str or not d_fin_str or temps_total <= 0:
                    continue
                
                try:
                    d_curr = datetime.strptime(str(d_deb_str)[:10], "%Y-%m-%d").date()
                    d_fin = datetime.strptime(str(d_fin_str)[:10], "%Y-%m-%d").date()
                except:
                    continue
                
                jours_tache = []
                curr = d_curr
                securite = 0
                while curr <= d_fin and securite < 365:
                    if curr.weekday() < 5 and curr.strftime("%Y-%m-%d") not in [a["date_debut"] for a in absences_globales if a.get("technicien") == tech]:
                        jours_tache.append(curr)
                    curr += timedelta(days=1)
                    securite += 1
                
                nb_jours_total = len(jours_tache)
                if nb_jours_total > 0:
                    heures_par_jour = temps_total / nb_jours_total
                    semaines_repartition = {}
                    for j in jours_tache:
                        sem_debut = j - timedelta(days=j.weekday())
                        sem_fin = sem_debut + timedelta(days=4)
                        lib_semaine = f"S{sem_debut.isocalendar()[1]} ({sem_debut.strftime('%d/%m')} au {sem_fin.strftime('%d/%m')})"
                        semaines_repartition[lib_semaine] = semaines_repartition.get(lib_semaine, 0.0) + heures_par_jour
                    
                    for sem, h_valeur in semaines_repartition.items():
                        lignes_ventilees.append({
                            "Technicien": tech,
                            "Semaine": sem,
                            "Charge Totale (h)": h_valeur
                        })
            
            if lignes_ventilees:
                df_ventilee = pd.DataFrame(lignes_ventilees)
                df_charge_tech_sem = df_ventilee.groupby(["Technicien", "Semaine"])["Charge Totale (h)"].sum().reset_index()
                
                st.dataframe(
                    df_charge_tech_sem,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Technicien": st.column_config.TextColumn("Technicien", width="medium"),
                        "Semaine": st.column_config.TextColumn("Semaine", width="medium"),
                        "Charge Totale (h)": st.column_config.NumberColumn("Charge Totale (h)", format="%.1f h")
                    }
                )
                
                st.download_button(
                    label="📥 Exporter la charge ventilée par technicien et semaine (CSV)",
                    data=convertir_df_en_csv(df_charge_tech_sem),
                    file_name="charge_ventilee_technicien_semaine.csv",
                    mime="text/csv",
                    key="exp_charge_tech_sem_vent"
                )
            else:
                st.info("Aucune charge à ventiler.")
        else:
            st.info("Aucune donnée de date de cascade disponible.")

with onglets[1]:
    st.subheader("🛠️ Gestion des OFs Sous-ensembles")
    if ofs_se_cascade:
        st.dataframe(pd.DataFrame(ofs_se_cascade), use_container_width=True)

with onglets[2]:
    st.subheader("📦 Gestion des OFs Consommables")
    if ofs_cons_cascade:
        st.dataframe(pd.DataFrame(ofs_cons_cascade), use_container_width=True)

with onglets[3]:
    st.subheader("👥 Gestion des Techniciens")
    st.write(f"Techniciens Prod : {[t['nom'] for t in techniciens_prod]}")
    st.write(f"Techniciens Consommables : {[t['nom'] for t in techniciens_cons]}")

with onglets[4]:
    st.subheader("📅 Vue Planning / Gantt")
    st.info("Module de planification globale.")

with onglets[5]:
    st.header("🌴 Congés & Absences")
    c_ab1, c_ab2 = st.columns(2)
    with c_ab1:
        st.subheader("Enregistrer une absence / un congé")
        tous_les_techs = [t["nom"] for t in techniciens_prod] + [t["nom"] for t in techniciens_cons]
        tous_les_techs = list(dict.fromkeys(tous_les_techs))

        if tous_les_techs:
            with st.form("form_abs_global"):
                t_p = st.selectbox("Technicien", tous_les_techs)
                m_p = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation"])
                db_p = st.date_input("Date de début", auj, key="ab_db")
                df_p = st.date_input("Date de fin", auj, key="ab_df")
                
                if st.form_submit_button("Enregistrer l'absence"):
                    if db_p <= df_p:
                        nouvelle_absence = {
                            "id": f"ABS-{len(absences_prod)+len(absences_cons)+1:03d}",
                            "technicien": t_p,
                            "motif": m_p,
                            "date_debut": str(db_p),
                            "date_fin": str(df_p),
                        }
                        absences_prod.append(nouvelle_absence)
                        data["absences_prod"] = absences_prod
                        sauvegarder_donnees(data)
                        st.success(f"Absence de {t_p} enregistrée avec succès.")
                        st.rerun()
                    else:
                        st.error("La date de fin doit être postérieure ou égale à la date de début.")
        else:
            st.warning("Aucun technicien enregistré.")

    with c_ab2:
        st.subheader("Liste des absences enregistrées")
        if absences_globales:
            df_abs = pd.DataFrame(absences_globales)
            st.dataframe(df_abs, use_container_width=True, hide_index=True)
            
            id_sup_abs = st.selectbox("ID de l'absence à supprimer", [a["id"] for a in absences_globales], key="del_abs")
            if st.button("Supprimer cette absence"):
                data["absences_prod"] = [a for a in absences_prod if a["id"] != id_sup_abs]
                data["absences_cons"] = [a for a in absences_cons if a["id"] != id_sup_abs]
                sauvegarder_donnees(data)
                st.success("Absence supprimée.")
                st.rerun()
        else:
            st.info("Aucune absence enregistrée pour le moment.")
