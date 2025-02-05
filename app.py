import os
import logging
import streamlit as st
import time

# Importeer functies voor het laden van CSS en het tonen van de juiste pagina's
from utils.css_loader import load_css
from pages.home import VIPDataMakelaarApp

from pages.login import show_login


# Stel logging in op INFO-niveau zodat belangrijke informatie gelogd wordt (voor ontwikkelaars)
logging.basicConfig(level=logging.INFO)


# 1. Bepaal de huidige directory (waar deze app.py zich bevindt)
current_dir = os.path.dirname(__file__)

# 2. Laad de CSS styling voor de applicatie via de load_css functie
load_css(current_dir)

# Log dat de applicatie gestart is
server_time = time.strftime("%H:%M:%S", time.localtime())
print(f"Running app.py at {server_time}")

# 3. Controleer of de 'logged_in' status al in de sessie staat.
#    Als dat niet zo is, stel de standaardwaarde in op True (pas dit aan indien nodig).
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = True

# 4. Toon de juiste pagina op basis van de login status
if st.session_state.get("logged_in"):
    # Als de gebruiker ingelogd is, toon dan de hoofdpagina
    app = VIPDataMakelaarApp()
    app.run()
else:
    # Als de gebruiker niet ingelogd is, toon dan het inlogscherm
    show_login()
