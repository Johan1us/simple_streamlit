import os
import logging
import streamlit as st
from utils.css_loader import load_css
from pages.home import show_home
from pages.login import show_login

# Stel logging in op DEBUG-niveau voor extra informatie (voor ontwikkelaars)
logging.basicConfig(level=logging.INFO)

# CURRENT_DIR = os.path.dirname(__file__)
current_dir = os.path.dirname(__file__)

# def load_css():
#     """
#     Laad het CSS-bestand voor de styling van de webapp.
#     Als het bestand niet gevonden wordt of er een fout optreedt bij het lezen,
#     wordt er fallback CSS toegepast en wordt extra informatie getoond om te helpen bij het debuggen.
#     """
#     # Bepaal de huidige directory en het pad naar het CSS-bestand
#     current_dir = os.path.dirname(__file__)
#     css_path = os.path.join(current_dir, "assets", "css", "style.css")
#
#     # Controleer of het CSS-bestand bestaat
#     if os.path.exists(css_path):
#         try:
#             # Lees het CSS-bestand in
#             with open(css_path, 'r', encoding='utf-8') as file:
#                 css_content = file.read()
#             # Pas de CSS styling toe in de Streamlit app
#             st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
#             logging.debug("CSS is succesvol geladen en toegepast.")
#         except Exception as error:
#             # Toon een foutmelding als er een probleem is bij het lezen van het bestand
#             st.error(f"Fout bij het lezen van het CSS-bestand: {error}")
#             logging.error(f"CSS leesfout: {error}", exc_info=True)
#     else:
#         # Als het CSS-bestand niet gevonden is, toon een foutmelding en de directorystructuur
#         st.error(f"CSS-bestand niet gevonden op: {css_path}")
#         st.write("We tonen de directorystructuur om te helpen bij het vinden van het probleem:")
#
#         # Pas fallback CSS styling toe zodat de app er toch redelijk uitziet
#         st.warning("Fallback CSS styling wordt toegepast...")
#         st.markdown("""
#             <style>
#                 .stButton > button {
#                     background-color: #0066cc;
#                     color: white;
#                     border-radius: 4px;
#                     padding: 0.5rem 1rem;
#                     border: none;
#                 }
#                 .stButton > button:hover {
#                     background-color: #0052a3;
#                 }
#             </style>
#         """, unsafe_allow_html=True)



# --- Hoofdprogramma ---

# 1. Laad de CSS styling voor de app
load_css(current_dir)

print("Running app.py")

# 2. Zorg dat er een standaardwaarde is voor de 'logged_in' status in de sessie
if "logged_in" not in st.session_state:
    # Hier kun je de standaardinstelling aanpassen (standaard staat het nu op True)
    st.session_state["logged_in"] = True

# 3. Controleer of de gebruiker is ingelogd en toon de juiste pagina
if st.session_state.get("logged_in"):
    # Als de gebruiker is ingelogd, toon dan de hoofdpagina
    show_home()
else:
    # Als de gebruiker niet is ingelogd, toon dan het inlogscherm
    show_login()
