import logging
import os
import streamlit as st
from dotenv import load_dotenv

# Stel logging in op DEBUG-niveau voor extra informatie (voor ontwikkelaars)
logging.basicConfig(level=logging.DEBUG)


def toon_loginscherm():
    """
    Toon het inlogscherm en verwerk de ingevoerde inloggegevens.

    In dit formulier kunnen gebruikers op Enter drukken om het formulier in te dienen.
    De ingevoerde gegevens worden vergeleken met de waarden die zijn opgeslagen in omgevingsvariabelen.
    """
    # Laad de omgevingsvariabelen uit een .env-bestand (indien aanwezig)
    load_dotenv()

    # Log de huidige werkdirectory en een voorbeeld van een geladen omgevingsvariabele
    logging.debug(f"Huidige werkdirectory: {os.getcwd()}")
    logging.debug(f"Omgevingsvariabele APP_USERNAME: {os.getenv('APP_USERNAME')}")

    # Toon de titel van de loginpagina
    st.title("Inloggen")

    # Maak een formulier voor de inlogvelden
    with st.form(key="login_form"):
        # Vraag de gebruikersnaam op via een tekstveld
        gebruikersnaam = st.text_input("Gebruikersnaam")
        # Vraag het wachtwoord op via een tekstveld (wachtwoord wordt verborgen)
        wachtwoord = st.text_input("Wachtwoord", type="password")
        # Voeg een submit-knop toe; het formulier wordt ook ingediend als je op Enter drukt
        submit_knop = st.form_submit_button(label="Login")

        # Wanneer het formulier wordt ingediend, controleer de ingevoerde gegevens
        if submit_knop:
            # Haal de verwachte inloggegevens op uit de omgevingsvariabelen
            verwachte_gebruikersnaam = os.getenv("APP_USERNAME")
            verwachte_wachtwoord = os.getenv("APP_PASSWORD")

            # Vergelijk de ingevoerde gebruikersnaam en wachtwoord met de verwachte waarden
            if gebruikersnaam == verwachte_gebruikersnaam and wachtwoord == verwachte_wachtwoord:
                # Als de inloggegevens kloppen, zet de sessie-status op 'logged_in' en toon een succesbericht
                st.session_state["logged_in"] = True
                st.success("Je bent succesvol ingelogd!")
                st.rerun()  # Herstart de app zodat de nieuwe loginstatus direct wordt toegepast
            else:
                # Als de inloggegevens niet kloppen, toon een foutmelding
                st.error("Ongeldige inloggegevens, probeer opnieuw.")
