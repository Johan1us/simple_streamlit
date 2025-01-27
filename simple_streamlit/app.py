import streamlit as st

st.title("Hello World!")

st.write("Welcome to my first Streamlit app!")

# Add a fun interactive element
name = st.text_input("What's your name?")
if name:
    st.write(f"Hello, {name}! 👋") 