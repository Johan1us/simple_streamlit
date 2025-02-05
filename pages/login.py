import logging
import streamlit as st


# Stel logging in op DEBUG-niveau voor extra informatie (voor ontwikkelaars)
logging.basicConfig(level=logging.INFO)

def show_login():
    """
    Toon het inlogscherm en verwerk de ingevoerde inloggegevens.
    Dit gebeurt nu binnen een formulier, zodat je met Enter kunt inloggen.
    """
    st.title("Inloggen")

    # Maak een formulier voor de inlogvelden
    with st.form(key="login_form"):
        # Tekstveld voor het invoeren van de gebruikersnaam
        username = st.text_input("Gebruikersnaam")
        # Tekstveld voor het invoeren van het wachtwoord (tekens worden verborgen)
        password = st.text_input("Wachtwoord", type="password")
        # Submit-knop; als op Enter gedrukt wordt, wordt het formulier automatisch ingediend
        submit_button = st.form_submit_button(label="Login")

        # Als het formulier is ingediend, controleer dan de ingevoerde gegevens
        if submit_button:
            # Dummy inloggegevens: gebruikersnaam 'admin' en wachtwoord 'admin'
            if username == "admin" and password == "admin":
                st.session_state["logged_in"] = True
                st.success("Je bent succesvol ingelogd!")
                st.rerun()
            else:
                st.error("Ongeldige inloggegevens, probeer opnieuw.")

