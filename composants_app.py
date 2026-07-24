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
    """Moteur d'ordonnancement en cascade (Forward Scheduling) respectant strictement la date de lancement souhaitée."""
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

st.set_page_config(
    page_title="Planification - Atelier Sous-ensembles & Consommables",
    layout="wide",
)

data = charger_donnees()

# --- BANDEAU IMAGE TOUT EN HAUT ---
if os.path.exists("fond_bandeau.jpg"):
    st.image("fond_bandeau.jpg", use_container_width=True)
else:
    st.warning(
        "Image 'fond_bandeau.jpg' introuvable dans le dossier du script."
    )

st.title("🧩 Planification Cascade & Pilotage - Atelier")
st.markdown("---")

onglets = st.tabs([
    "📊 Tableau de Bord",
    "📈 KPIs & Indicateurs",
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

# --- MAPPE DE COULEURS PAR TECHNICIEN ---
tous_techniciens_noms = [t["nom"] for t in techniciens_prod + techniciens_cons]
palette_icones_tech = ["🔵", "🟢", "🟠", "🟣", "🔴", "🟤", "🟡", "🔷", "🟩", "🟧"]
tech_couleur_map = {
    tech: palette_icones_tech[i % len(palette_icones_tech)]
    for i, tech in enumerate(tous_techniciens_noms)
}


# --- ONGLET 1 : TABLEAU DE BORD ---
with onglets[0]:
    st.header("📊 Tableau de Bord & Suivi des OFs")
    st.markdown(
        f"**Semaine en cours :** du {debut_semaine.strftime('%d/%m/%Y')} au"
        f" {fin_semaine.strftime('%d/%m/%Y')}"
    )

    st.markdown("### ⚙️ Options d'affichage & Conversion")
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
            
            abs_par_tech_synth = {}
            for abs_rec in absences_prod + absences_cons:
                tech = abs_rec.get("technicien")
                try:
                    d_deb = datetime.strptime(abs_rec["date_debut"], "%Y-%m-%d").date()
                    d_fin = datetime.strptime(abs_rec["date_fin"], "%Y-%m-%d").date()
                    curr = d_deb
                    if tech not in abs_par_tech_synth:
                        abs_par_tech_synth[tech] = set()
                    while curr <= d_fin:
                        abs_par_tech_synth[tech].add(curr.strftime("%Y-%m-%d"))
                        curr += timedelta(days=1)
                except:
                    pass

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
                technicien_absences = abs_par_tech_synth.get(tech, set())
                
                curr = d_curr
                securite = 0
                while curr <= d_fin and securite < 365:
                    if curr.weekday() < 5 and curr.strftime("%Y-%m-%d") not in technicien_absences:
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
                else:
                    lignes_ventilees.append({
                        "Technicien": tech,
                        "Semaine": row.get("semaine_concernee", "Non planifié"),
                        "Charge Totale (h)": temps_total
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
    
    st.markdown("---")

    # --- SOUS-ENSEMBLES : Tableau + Mini-Gantt Sexy & Coloré ---
    st.subheader("🛠️ Suivi détaillé des OFs Sous-ensembles (avec Cascade)")
    if ofs_se_cascade:
        df_dashboard_se = pd.DataFrame(ofs_se_cascade)
        df_dashboard_se = appliquer_conversion(df_dashboard_se)
        st.dataframe(df_dashboard_se, use_container_width=True)
        st.download_button(
            label="📥 Exporter le suivi OFs SE (CSV)",
            data=convertir_df_en_csv(df_dashboard_se),
            file_name="suivi_ofs_se.csv",
            mime="text/csv",
            key="exp_dash_se",
        )

        # Mini-Gantt Sous-ensembles (Ciblé & Coloré par Technicien)
        st.markdown("##### 📅 Planning Visuel (Gantt Dynamique SE)")
        actifs_se = [x for x in ofs_se_cascade if x.get("statut") not in ["Terminé", "Supprimé"]]
        if actifs_se:
            toutes_dates = []
            for x in actifs_se:
                d_str = x.get("date_debut_cascade")
                if d_str:
                    try:
                        toutes_dates.append(datetime.strptime(str(d_str)[:10], "%Y-%m-%d").date())
                    except:
                        pass
            
            date_debut_gantt = min(toutes_dates) if toutes_dates else auj
            while date_debut_gantt.weekday() >= 5:
                date_debut_gantt += timedelta(days=1)

            jours_gantt = []
            curr_g = date_debut_gantt
            while len(jours_gantt) < 10:
                if curr_g.weekday() < 5:
                    jours_gantt.append(curr_g)
                curr_g += timedelta(days=1)

            lignes_gantt_se = []
            for x in actifs_se:
                nom_op = x.get('sous_ensemble', 'OF')
                tech = x.get('assigne', 'Non assigné')
                prio = x.get('priorite', 'Normale')
                
                couleur_tech = tech_couleur_map.get(tech, "⚪")
                symb_prio = "🔥" if prio == "Urgente" else ("⚡" if prio == "Haute" else "🔹")
                
                ligne = {"OF / Tech": f"{couleur_tech} {symb_prio} {nom_op} ({tech})"}
                d_deb = x.get("date_debut_cascade", "")
                d_fin = x.get("date_fin_cascade", "")
                
                for j in jours_gantt:
                    j_str = str(j)
                    col_nom = j.strftime("%a %d/%m")
                    if d_deb and d_fin and d_deb <= j_str <= d_fin:
                        ligne[col_nom] = f"{couleur_tech}████"
                    else:
                        ligne[col_nom] = "·"
                lignes_gantt_se.append(ligne)
            st.dataframe(pd.DataFrame(lignes_gantt_se), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun OF SE actif à afficher sur le Gantt.")
    else:
        st.info("Aucun OF Sous-ensemble enregistré.")

    st.markdown("---")

    # --- CONSOMMABLES : Tableau + Mini-Gantt Sexy & Coloré ---
    st.subheader("📦 Suivi détaillé des OFs Consommables (avec Cascade)")
    if ofs_cons_cascade:
        df_dashboard_cons = pd.DataFrame(ofs_cons_cascade)
        df_dashboard_cons = appliquer_conversion(df_dashboard_cons)
        st.dataframe(df_dashboard_cons, use_container_width=True)
        st.download_button(
            label="📥 Exporter le suivi OFs Consommables (CSV)",
            data=convertir_df_en_csv(df_dashboard_cons),
            file_name="suivi_ofs_consommables.csv",
            mime="text/csv",
            key="exp_dash_cons",
        )

        # Mini-Gantt Consommables (Ciblé & Coloré par Technicien)
        st.markdown("##### 📅 Planning Visuel (Gantt Dynamique Consommables)")
        actifs_cons = [x for x in ofs_cons_cascade if x.get("statut") not in ["Terminé", "Supprimé"]]
        if actifs_cons:
            toutes_dates_c = []
            for x in actifs_cons:
                d_str = x.get("date_debut_cascade")
                if d_str:
                    try:
                        toutes_dates_c.append(datetime.strptime(str(d_str)[:10], "%Y-%m-%d").date())
                    except:
                        pass
            
            date_debut_gantt_c = min(toutes_dates_c) if toutes_dates_c else auj
            while date_debut_gantt_c.weekday() >= 5:
                date_debut_gantt_c += timedelta(days=1)

            jours_gantt_c = []
            curr_gc = date_debut_gantt_c
            while len(jours_gantt_c) < 10:
                if curr_gc.weekday() < 5:
                    jours_gantt_c.append(curr_gc)
                curr_gc += timedelta(days=1)

            lignes_gantt_cons = []
            for x in actifs_cons:
                nom_op = x.get('consommable', 'OF')
                tech = x.get('assigne', 'Non assigné')
                prio = x.get('priorite', 'Normale')
                
                couleur_tech = tech_couleur_map.get(tech, "⚪")
                symb_prio = "🔥" if prio == "Urgente" else ("⚡" if prio == "Haute" else "🔹")
                
                ligne = {"OF / Tech": f"{couleur_tech} {symb_prio} {nom_op} ({tech})"}
                d_deb = x.get("date_debut_cascade", "")
                d_fin = x.get("date_fin_cascade", "")
                
                for j in jours_gantt_c:
                    j_str = str(j)
                    col_nom = j.strftime("%a %d/%m")
                    if d_deb and d_fin and d_deb <= j_str <= d_fin:
                        ligne[col_nom] = f"{couleur_tech}████"
                    else:
                        ligne[col_nom] = "·"
                lignes_gantt_cons.append(ligne)
            st.dataframe(pd.DataFrame(lignes_gantt_cons), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun OF Consommable actif à afficher sur le Gantt.")
    else:
        st.info("Aucun OF Consommable enregistré.")


# --- ONGLET 1.5 : KPIS & INDICATEURS ---
with onglets[1]:
    st.header("📈 KPIs & Indicateurs de Production (Mise en stock)")
    st.markdown("Suivi des volumes produits et mis en stock (basé sur les OFs au statut **Terminé**).")

    # On fusionne / traite les OFs terminés des deux catégories
    termines_se = [p for p in plannings_se if p.get("statut") == "Terminé"]
    termines_cons = [p for p in plannings_cons if p.get("statut") == "Terminé"]

    st.subheader("📦 Consommables mis en stock")
    if termines_cons:
        df_tc = pd.DataFrame(termines_cons)
        if "date_fin_cascade" not in df_tc.columns:
            df_tc["date_fin_cascade"] = df_tc.get("date_lancement", str(auj))
        
        df_tc["date_ref"] = pd.to_datetime(df_tc["date_fin_cascade"].astype(str).str[:10], errors="coerce").dt.date
        df_tc = df_tc.dropna(subset=["date_ref"])

        annee_courante = auj.year
        semaine_actuelle_num = auj.isocalendar()[1]
        
        qte_semaine_cons = 0
        qte_mois_cons = 0
        qte_ytd_cons = 0

        for _, r in df_tc.iterrows():
            d = r["date_ref"]
            q = r.get("quantite", 0)
            if d.year == annee_courante:
                qte_ytd_cons += q
                if d.month == auj.month:
                    qte_mois_cons += q
                if d.isocalendar()[1] == semaine_actuelle_num:
                    qte_semaine_cons += q

        kpi_c1, kpi_c2, kpi_c3 = st.columns(3)
        with kpi_c1:
            st.metric("Semaine en cours", f"{qte_semaine_cons} unités")
        with kpi_c2:
            st.metric("Mois en cours", f"{qte_mois_cons} unités")
        with kpi_c3:
            st.metric(f"Année {annee_courante} (YTD)", f"{qte_ytd_cons} unités")

        st.markdown("##### Historique détaillé des Consommables terminés")
        st.dataframe(df_tc[["id_plan", "consommable", "quantite", "assigne", "date_fin_cascade", "priorite"]], use_container_width=True, hide_index=True)
    else:
        st.info("Aucun OF Consommable au statut 'Terminé' pour le calcul des KPIs.")

    st.markdown("---")

    st.subheader("🛠️ Sous-ensembles mis en stock")
    if termines_se:
        df_ts = pd.DataFrame(termines_se)
        if "date_fin_cascade" not in df_ts.columns:
            df_ts["date_fin_cascade"] = df_ts.get("date_lancement", str(auj))
        
        df_ts["date_ref"] = pd.to_datetime(df_ts["date_fin_cascade"].astype(str).str[:10], errors="coerce").dt.date
        df_ts = df_ts.dropna(subset=["date_ref"])

        qte_semaine_se = 0
        qte_mois_se = 0
        qte_ytd_se = 0

        for _, r in df_ts.iterrows():
            d = r["date_ref"]
            q = r.get("quantite", 0)
            if d.year == annee_courante:
                qte_ytd_se += q
                if d.month == auj.month:
                    qte_mois_se += q
                if d.isocalendar()[1] == semaine_actuelle_num:
                    qte_semaine_se += q

        kpi_s1, kpi_s2, kpi_s3 = st.columns(3)
        with kpi_s1:
            st.metric("Semaine en cours", f"{qte_semaine_se} unités")
        with kpi_s2:
            st.metric("Mois en cours", f"{qte_mois_se} unités")
        with kpi_s3:
            st.metric(f"Année {annee_courante} (YTD)", f"{qte_ytd_se} unités")

        st.markdown("##### Historique détaillé des Sous-ensembles terminés")
        st.dataframe(df_ts[["id_plan", "sous_ensemble", "quantite", "assigne", "date_fin_cascade", "priorite"]], use_container_width=True, hide_index=True)
    else:
        st.info("Aucun OF Sous-ensemble au statut 'Terminé' pour le calcul des KPIs.")


# --- ONGLET 2 : CRÉATION SOUS-ENSEMBLES ---
with onglets[2]:
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
with onglets[3]:
    st.header("📦 Gestion & Références des Consommables")

    with st.form("form_creer_cons"):
        st.subheader("Ajouter un nouveau Consommable")
        nom_cons = st.text_input("Nom du Consommable")
        ref_cons = st.text_input("Référence / Code Consommable")

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
                f"💡 Temps unitaire recalculé automatiquement :"
                f" **{calcul_temps_unitaire:.4f} h / pièce** (soit {temps_lot_ref}h"
                f" pour {qte_lot_ref} pièces)."
            )

        desc_cons = st.text_area(
            "Description / Instructions Consommable", key="desc_c"
        )

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


# --- ONGLET 4 : PLANIFICATION & CASCADE ---
with onglets[4]:
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
                "Veuillez d'abord créer des sous-ensembles dans l'onglet '⚙️ Création Sous-ensembles'."
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
                "Veuillez d'abord créer des consommables dans l'onglet '📦 Références Consommables'."
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
with onglets[5]:
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
with onglets[6]:
    st.header("🌴 Congés & Absences")
    c_ab1, c_ab2 = st.columns(2)
    
    # --- 1. ABSENCES PROD ---
    with c_ab1:
        st.subheader("Absences Prod")
        if techniciens_prod:
            with st.form("absp"):
                t_p = st.selectbox("Tech Prod", [t["nom"] for t in techniciens_prod])
                m_p = st.selectbox(
                    "Motif Prod", ["Congés Payés", "RTT", "Maladie", "Formation"]
                )
                db_p = st.date_input("Début Prod", auj, key="ab_db")
                df_p = st.date_input("Fin Prod", auj, key="ab_df")
                if st.form_submit_button("Enregistrer absence Prod"):
                    absences_prod.append({
                        "id": f"ABS-P-{len(absences_prod)+1:03d}",
                        "technicien": t_p,
                        "motif": m_p,
                        "date_debut": str(db_p),
                        "date_fin": str(df_p),
                    })
                    data["absences_prod"] = absences_prod
                    sauvegarder_donnees(data)
                    st.success("Absence Prod enregistrée.")
                    st.rerun()
        else:
            st.warning("Ajoute d'abord des techniciens de production.")

        if absences_prod:
            st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)
            id_sup_abp = st.selectbox(
                "ID Absence Prod à supprimer",
                [a["id"] for a in absences_prod],
                key="del_abp",
            )
            if st.button("Supprimer Absence Prod"):
                data["absences_prod"] = [
                    a for a in absences_prod if a["id"] != id_sup_abp
                ]
                sauvegarder_donnees(data)
                st.success("Absence Prod supprimée.")
                st.rerun()

    # --- 2. ABSENCES CONSOMMABLES ---
    with c_ab2:
        st.subheader("Absences Consommables")
        if techniciens_cons:
            with st.form("absc"):
                t_c = st.selectbox("Tech Cons.", [t["nom"] for t in techniciens_cons])
                m_c = st.selectbox(
                    "Motif Cons.",
                    ["Congés Payés", "RTT", "Maladie", "Formation"],
                    key="motif_c",
                )
                db_c = st.date_input("Début Cons.", auj, key="ab_dbc")
                df_c = st.date_input("Fin Cons.", auj, key="ab_dfc")
                
                if st.form_submit_button("Enregistrer absence Cons."):
                    absences_cons.append({
                        "id": f"ABS-C-{len(absences_cons)+1:03d}",
                        "technicien": t_c,
                        "motif": m_c,
                        "date_debut": str(db_c),
                        "date_fin": str(df_c),
                    })
                    data["absences_cons"] = absences_cons
                    sauvegarder_donnees(data)
                    st.success("Absence Consommables enregistrée.")
                    st.rerun()
        else:
            st.warning("Ajoute d'abord des techniciens consommables.")
                
        if absences_cons:
            st.dataframe(pd.DataFrame(absences_cons), use_container_width=True)
            id_sup_abc = st.selectbox(
                "ID Absence Cons. à supprimer",
                [a["id"] for a in absences_cons],
                key="del_abc",
            )
            if st.button("Supprimer Absence Cons."):
                data["absences_cons"] = [
                    a for a in absences_cons if a["id"] != id_sup_abc
                ]
                sauvegarder_donnees(data)
                st.success("Absence Consommables supprimée.")
                st.rerun()


# --- ONGLET 7 : SAUVEGARDE & DONNÉES ---
with onglets[7]:
    st.header("💾 Sauvegarde, Restauration & Données Brutes")

    st.subheader("📥 Export global de la base de données")
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    st.download_button(
        label="📥 Télécharger le fichier JSON complet",
        data=json_str,
        file_name="donnees_composants_sauvegarde.json",
        mime="application/json",
    )

    st.markdown("---")
    st.subheader("📤 Importer / Restaurer une sauvegarde JSON")
    fichier_upload = st.file_uploader(
        "Sélectionner un fichier JSON de sauvegarde", type=["json"]
    )
    if fichier_upload is not None:
        try:
            donnees_importees = json.load(fichier_upload)
            if st.button("Confirmer et remplacer les données actuelles"):
                sauvegarder_donnees(donnees_importees)
                st.success("Données restaurées avec succès ! Rechargement...")
                st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier JSON : {e}")

    st.markdown("---")
    st.subheader("🔍 Visualisation brute des données (JSON)")
    st.json(data)
