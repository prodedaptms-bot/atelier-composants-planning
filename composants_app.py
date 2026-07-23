import os
import json
import pandas as pd
import streamlit as st

DATA_FILE = "donnees_composants_sauvegarde.json"

def charger_donnees():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "techniciens_prod": [],
        "techniciens_cons": [],
        "absences_prod": [],
        "absences_cons": []
    }

def sauvegarder_donnees(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = charger_donnees()
techniciens_prod = data.get("techniciens_prod", [])
techniciens_cons = data.get("techniciens_cons", [])
absences_prod = data.get("absences_prod", [])
absences_cons = data.get("absences_cons", [])

auj = pd.Timestamp.today().date()

st.title("Gestion de Planning et des Ressources")

onglets = st.tabs([
    "Équipe Prod", 
    "Équipe Consommables", 
    "Absences Prod", 
    "Absences Consommables", 
    "Absences Globales", 
    "Planning", 
    "Sauvegarde & Données"
])

# --- ONGLET 1 : ÉQUIPE PROD ---
with onglets[0]:
    st.header("👥 Gestion de l'équipe Production")
    
    with st.form("ajout_tech_prod"):
        nom_tp = st.text_input("Nom du technicien (Production)")
        if st.form_submit_button("Ajouter le technicien"):
            if nom_tp:
                techniciens_prod.append({"id": f"TP-{len(techniciens_prod)+1:03d}", "nom": nom_tp})
                data["techniciens_prod"] = techniciens_prod
                sauvegarder_donnees(data)
                st.success(f"Technicien {nom_tp} ajouté avec succès !")
                st.rerun()
            else:
                st.error("Veuillez entrer un nom.")

    if techniciens_prod:
        st.markdown("#### Liste des techniciens (Production)")
        st.dataframe(pd.DataFrame(techniciens_prod), use_container_width=True)
        
        id_sup_tp = st.selectbox("ID à supprimer", [t["id"] for t in techniciens_prod], key="suppr_tp")
        if st.button("Supprimer ce technicien Prod"):
            data["techniciens_prod"] = [t for t in techniciens_prod if t["id"] != id_sup_tp]
            sauvegarder_donnees(data)
            st.success("Technicien supprimé.")
            st.rerun()

# --- ONGLET 2 : ÉQUIPE CONSOMMABLES ---
with onglets[1]:
    st.header("👥 Gestion de l'équipe Consommables")
    
    with st.form("ajout_tech_cons"):
        nom_tc = st.text_input("Nom du technicien (Consommables)")
        if st.form_submit_button("Ajouter le technicien"):
            if nom_tc:
                techniciens_cons.append({"id": f"TC-{len(techniciens_cons)+1:03d}", "nom": nom_tc})
                data["techniciens_cons"] = techniciens_cons
                sauvegarder_donnees(data)
                st.success(f"Technicien {nom_tc} ajouté avec succès !")
                st.rerun()
            else:
                st.error("Veuillez entrer un nom.")

    if techniciens_cons:
        st.markdown("#### Liste des techniciens (Consommables)")
        st.dataframe(pd.DataFrame(techniciens_cons), use_container_width=True)
        
        id_sup_tc = st.selectbox("ID à supprimer", [t["id"] for t in techniciens_cons], key="suppr_tc")
        if st.button("Supprimer ce technicien Consommables"):
            data["techniciens_cons"] = [t for t in techniciens_cons if t["id"] != id_sup_tc]
            sauvegarder_donnees(data)
            st.success("Technicien supprimé.")
            st.rerun()

# --- ONGLET 3 : ABSENCES PROD ---
with onglets[2]:
    st.subheader("Absences Production")
    if techniciens_prod:
        with st.form("absp"):
            t_p = st.selectbox("Tech", [t["nom"] for t in techniciens_prod], key="ab_tp")
            m_p = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation"], key="ab_mp")
            db_p = st.date_input("Début", auj, key="ab_dbp")
            df_p = st.date_input("Fin", auj, key="ab_dfp")
            if st.form_submit_button("Enregistrer absence Prod."):
                absences_prod.append({
                    "id": f"ABS-P-{len(absences_prod)+1:03d}",
                    "technicien": t_p,
                    "motif": m_p,
                    "date_debut": str(db_p),
                    "date_fin": str(df_p),
                })
                data["absences_prod"] = absences_prod
                sauvegarder_donnees(data)
                st.success("Absence enregistrée avec succès !")
                st.rerun()
    else:
        st.info("Aucun technicien de production enregistré.")

    if absences_prod:
        st.markdown("#### Historique des absences (Prod)")
        st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)
        
        id_sup_absp = st.selectbox("ID Absence à supprimer", [item["id"] for item in absences_prod], key="suppr_absp")
        if st.button("Supprimer cette absence Prod"):
            data["absences_prod"] = [item for item in absences_prod if item["id"] != id_sup_absp]
            sauvegarder_donnees(data)
            st.success("Absence supprimée.")
            st.rerun()

# --- ONGLET 4 : ABSENCES CONSOMMABLES ---
with onglets[3]:
    st.subheader("Absences Consommables")
    if techniciens_cons:
        with st.form("absc"):
            t_c = st.selectbox("Tech", [t["nom"] for t in techniciens_cons], key="ab_tc")
            m_c = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation"], key="ab_mc")
            db_c = st.date_input("Début", auj, key="ab_dbc")
            df_c = st.date_input("Fin", auj, key="ab_dfc")
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
                st.success("Absence enregistrée avec succès !")
                st.rerun()
    else:
        st.info("Aucun technicien consommables enregistré.")

    if absences_cons:
        st.markdown("#### Historique des absences (Consommables)")
        st.dataframe(pd.DataFrame(absences_cons), use_container_width=True)
        
        id_sup_absc = st.selectbox("ID Absence à supprimer", [item["id"] for item in absences_cons], key="suppr_absc")
        if st.button("Supprimer cette absence Cons."):
            data["absences_cons"] = [item for item in absences_cons if item["id"] != id_sup_absc]
            sauvegarder_donnees(data)
            st.success("Absence supprimée.")
            st.rerun()

# --- ONGLET 5 : ABSENCES GLOBALES (2 colonnes) ---
with onglets[4]:
    st.header("📅 Vue globale des Absences")
    c_ab1, c_ab2 = st.columns(2)
    
    with c_ab1:
        st.subheader("Absences Production")
        if techniciens_prod:
            with st.form("absp_g"):
                t_p = st.selectbox("Tech", [t["nom"] for t in techniciens_prod], key="ab_tp_g")
                m_p = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation"], key="ab_mp_g")
                db_p = st.date_input("Début", auj, key="ab_dbp_g")
                df_p = st.date_input("Fin", auj, key="ab_dfp_g")
                if st.form_submit_button("Enregistrer absence Prod."):
                    absences_prod.append({
                        "id": f"ABS-P-{len(absences_prod)+1:03d}",
                        "technicien": t_p,
                        "motif": m_p,
                        "date_debut": str(db_p),
                        "date_fin": str(df_p),
                    })
                    data["absences_prod"] = absences_prod
                    sauvegarder_donnees(data)
                    st.success("Absence enregistrée avec succès !")
                    st.rerun()
        else:
            st.info("Aucun technicien de production enregistré.")

        if absences_prod:
            st.markdown("#### Historique (Prod)")
            st.dataframe(pd.DataFrame(absences_prod), use_container_width=True)
            id_sup_absp_g = st.selectbox("ID Absence à supprimer", [item["id"] for item in absences_prod], key="suppr_absp_g")
            if st.button("Suppr. absence Prod", key="btn_sup_ap_g"):
                data["absences_prod"] = [item for item in absences_prod if item["id"] != id_sup_absp_g]
                sauvegarder_donnees(data)
                st.success("Supprimé.")
                st.rerun()

    with c_ab2:
        st.subheader("Absences Consommables")
        if techniciens_cons:
            with st.form("absc_g"):
                t_c = st.selectbox("Tech", [t["nom"] for t in techniciens_cons], key="ab_tc_g")
                m_c = st.selectbox("Motif", ["Congés Payés", "RTT", "Maladie", "Formation"], key="ab_mc_g")
                db_c = st.date_input("Début", auj, key="ab_dbc_g")
                df_c = st.date_input("Fin", auj, key="ab_dfc_g")
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
                    st.success("Absence enregistrée avec succès !")
                    st.rerun()
        else:
            st.info("Aucun technicien consommables enregistré.")

        if absences_cons:
            st.markdown("#### Historique (Consommables)")
            st.dataframe(pd.DataFrame(absences_cons), use_container_width=True)
            id_sup_absc_g = st.selectbox("ID Absence à supprimer", [item["id"] for item in absences_cons], key="suppr_absc_g")
            if st.button("Suppr. absence Cons.", key="btn_sup_ac_g"):
                data["absences_cons"] = [item for item in absences_cons if item["id"] != id_sup_absc_g]
                sauvegarder_donnees(data)
                st.success("Supprimé.")
                st.rerun()

# --- ONGLET 6 : PLANNING ---
with onglets[5]:
    st.header("🗓️ Planning et Disponibilités des Ressources")
    
    st.markdown("Vérifiez l'impact des congés et absences en sélectionnant une date cible :")
    
    # Sélecteur de date pour l'analyse
    date_selectionnee = st.date_input("Date à analyser", auj, key="date_planning_cible")
    date_str = str(date_selectionnee)
    
    st.markdown("---")
    
    c_p_plan, c_c_plan = st.columns(2)
    
    # --- ANALYSE ÉQUIPE PRODUCTION ---
    with c_p_plan:
        st.subheader("Production")
        if techniciens_prod:
            # Identifier les techs de prod absents à cette date
            absents_prod_du_jour = []
            for ab in absences_prod:
                if ab["date_debut"] <= date_str <= ab["date_fin"]:
                    absents_prod_du_jour.append((ab["technicien"], ab["motif"]))
            
            noms_absents_p = [item[0] for item in absents_prod_du_jour]
            
            st.markdown(f"**Techniciens absents le {date_selectionnee.strftime('%d/%m/%Y')} :**")
            if absents_prod_du_jour:
                for tech, motif in absents_prod_du_jour:
                    st.warning(f"🔴 **{tech}** ({motif})")
            else:
                st.success("🟢 Aucun absent ce jour-là.")
                
            st.markdown("**Techniciens disponibles :**")
            dispos_p = [t for t in techniciens_prod if t["nom"] not in noms_absents_p]
            if dispos_p:
                for t in dispos_p:
                    st.info(f"✔️ {t['nom']} ({t['id']})")
            else:
                st.error("⚠️ Aucun technicien disponible dans cette équipe à cette date.")
        else:
            st.info("Aucun technicien de production enregistré.")

    # --- ANALYSE ÉQUIPE CONSOMMABLES ---
    with c_c_plan:
        st.subheader("Consommables")
        if techniciens_cons:
            # Identifier les techs consommables absents à cette date
            absents_cons_du_jour = []
            for ab in absences_cons:
                if ab["date_debut"] <= date_str <= ab["date_fin"]:
                    absents_cons_du_jour.append((ab["technicien"], ab["motif"]))
            
            noms_absents_c = [item[0] for item in absents_cons_du_jour]
            
            st.markdown(f"**Techniciens absents le {date_selectionnee.strftime('%d/%m/%Y')} :**")
            if absents_cons_du_jour:
                for tech, motif in absents_cons_du_jour:
                    st.warning(f"🔴 **{tech}** ({motif})")
            else:
                st.success("🟢 Aucun absent ce jour-là.")
                
            st.markdown("**Techniciens disponibles :**")
            dispos_c = [t for t in techniciens_cons if t["nom"] not in noms_absents_c]
            if dispos_c:
                for t in dispos_c:
                    st.info(f"✔️ {t['nom']} ({t['id']})")
            else:
                st.error("⚠️ Aucun technicien disponible dans cette équipe à cette date.")
        else:
            st.info("Aucun technicien consommables enregistré.")

# --- ONGLET 7 : SAUVEGARDE & DONNÉES ---
with onglets[6]:
    st.header("💾 Sauvegarde, Restauration & Données Brutes")
    st.markdown("Téléchargez l'intégralité de la base de données au format JSON ou réinitialisez les données.")

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            json_str = f.read()
        st.download_button(
            label="📥 Télécharger la base de données complète (JSON)",
            data=json_str,
            file_name="donnees_composants_sauvegarde.json",
            mime="application/json",
            key="download_full_json"
        )
    else:
        st.info("Aucun fichier de données actif pour le moment.")

    st.markdown("---")
    st.subheader("🗑️ Zone de danger")
    if st.button("Réinitialiser toutes les données (Effacer le fichier)"):
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            st.success("Base de données réinitialisée avec succès !")
            st.rerun()
        else:
            st.info("Le fichier de données n'existe pas encore.")
