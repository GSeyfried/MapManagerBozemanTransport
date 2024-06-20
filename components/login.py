import yaml
import streamlit as st
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.exceptions import (CredentialsError,
                                                          ForgotError,
                                                          LoginError,
                                                          RegisterError,
                                                          ResetError,
                                                          UpdateError)

def load_users():
    with open('credentials.yaml', 'r', encoding='utf-8') as file:
        credentials = yaml.load(file, Loader=SafeLoader)
    # Creating the authenticator object
    authenticator = stauth.Authenticate(
        credentials['credentials'],
        credentials['cookie']['name'],
        credentials['cookie']['key'],
        credentials['cookie']['expiry_days'],
        credentials['pre-authorized']
    )
    return authenticator, credentials

output = load_users()
authenticator = output[0]
credentials = output[1]

def log_in():
    # Creating a login widget
    try:
        authenticator.login()
    except LoginError as e:
        st.error(e)

    if st.session_state["authentication_status"]:
        col1, col2, col3 = st.columns(3)

        with col2:
            st.write(f'Welcome *{st.session_state["name"]}*')
            authenticator.logout()
        st.write('Use the Upload Data Side bar to load the google maps data, then view and adjust it in the Adjust Map page.')    

    #incorrect or abscent password
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

def initialize_user_session():
    if "username" not in st.session_state:
        st.session_state["username"] = st.session_state.get("name", None)


def reset_passowrd ():
    # Creating a password reset widget
    if st.session_state["authentication_status"]:
        try:
            if authenticator.reset_password(st.session_state["username"]):
                st.success('Password modified successfully')
        except ResetError as e:
            st.error(e)
        except CredentialsError as e:
            st.error(e)
    
    # Saving credentials file
    with open('credentials.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(credentials, file, default_flow_style=False)

def register_user ():
    # # Creating a new user registration widget
    try:
        (email_of_registered_user,
            username_of_registered_user,
            name_of_registered_user) = authenticator.register_user(pre_authorization=False)
        if email_of_registered_user:
            st.success('User registered successfully')
    except RegisterError as e:
        st.error(e)

    with open('credentials.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(credentials, file, default_flow_style=False)

def forgot_password ():
    # # Creating a forgot password widget
    try:
        (username_of_forgotten_password,
            email_of_forgotten_password,
            new_random_password) = authenticator.forgot_password()
        if username_of_forgotten_password:
            st.success('New password sent securely')
            # Random password to be transferred to the user securely
        elif not username_of_forgotten_password:
            st.error('Username not found')
    except ForgotError as e:
        st.error(e)
    with open('credentials.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(credentials, file, default_flow_style=False)

def forgot_username ():
    # # Creating a forgot username widget
    try:
        (username_of_forgotten_username,
            email_of_forgotten_username) = authenticator.forgot_username()
        if username_of_forgotten_username:
            st.success('Username sent securely')
            # Username to be transferred to the user securely
        elif not username_of_forgotten_username:
            st.error('Email not found')
    except ForgotError as e:
        st.error(e)
    with open('credentials.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(credentials, file, default_flow_style=False)

def update_user_details ():
    # # Creating an update user details widget
    if st.session_state["authentication_status"]:
        try:
            if authenticator.update_user_details(st.session_state["username"]):
                st.success('Entries updated successfully')
        except UpdateError as e:
            st.error(e)
    with open('credentials.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(credentials, file, default_flow_style=False)
