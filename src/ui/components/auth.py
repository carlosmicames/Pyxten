import streamlit as st
import os


def render_auth_page():
    """Render login/signup page"""

    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3rem; font-weight: 800;
                   background: linear-gradient(135deg, #10b981 0%, #14b8a6 100%);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Pyxten
        </h1>
        <p style="font-size: 1.2rem; color: #6b7280;">
            Validacion Inteligente de Permisos
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Iniciar Sesion", "Crear Cuenta"])

    with tab1:
        render_login_form()

    with tab2:
        render_signup_form()


def render_login_form():
    """Login form"""

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="tu@email.com")
        password = st.text_input("Contrasena", type="password")

        submitted = st.form_submit_button("Iniciar Sesion", type="primary", use_container_width=True)

        if submitted:
            if email and password:
                try:
                    from src.services.supabase_client import SupabaseService

                    supabase = SupabaseService()
                    response = supabase.client.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })

                    if response.user:
                        st.session_state.user = response.user
                        st.session_state.authenticated = True
                        st.success("Bienvenido!")
                        st.rerun()

                except Exception as e:
                    error_msg = str(e)
                    if "Invalid login credentials" in error_msg:
                        st.error("Email o contrasena incorrectos")
                    else:
                        st.error(f"Error: {error_msg}")
            else:
                st.error("Completa todos los campos")


def render_signup_form():
    """Signup form"""

    with st.form("signup_form"):
        email = st.text_input("Email", placeholder="tu@email.com", key="signup_email")
        password = st.text_input("Contrasena", type="password", help="Minimo 6 caracteres", key="signup_pass")
        password_confirm = st.text_input("Confirmar Contrasena", type="password", key="signup_pass_confirm")

        submitted = st.form_submit_button("Crear Cuenta", type="primary", use_container_width=True)

        if submitted:
            if not all([email, password, password_confirm]):
                st.error("Completa todos los campos")
            elif password != password_confirm:
                st.error("Las contrasenas no coinciden")
            elif len(password) < 6:
                st.error("La contrasena debe tener al menos 6 caracteres")
            else:
                try:
                    from src.services.supabase_client import SupabaseService

                    supabase = SupabaseService()
                    response = supabase.client.auth.sign_up({
                        "email": email,
                        "password": password
                    })

                    if response.user:
                        st.success("Cuenta creada! Revisa tu email para confirmar.")
                        st.info("Luego inicia sesion en la pestana 'Iniciar Sesion'")

                except Exception as e:
                    error_msg = str(e)
                    if "already registered" in error_msg.lower():
                        st.error("Este email ya esta registrado")
                    else:
                        st.error(f"Error: {error_msg}")


def check_authentication() -> bool:
    """Check if user is authenticated"""

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if 'user' not in st.session_state:
        st.session_state.user = None

    # Check for Supabase credentials - if not set, allow unauthenticated use
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        # No Supabase configured - allow unauthenticated access
        return True

    return st.session_state.authenticated


def get_current_user():
    """Get current authenticated user"""
    return st.session_state.get('user')


def get_user_id() -> str:
    """Get current user's ID"""
    user = get_current_user()
    if user:
        return user.id
    return "anonymous"


def logout():
    """Logout user"""

    try:
        from src.services.supabase_client import SupabaseService

        supabase = SupabaseService()
        supabase.client.auth.sign_out()
    except Exception:
        pass

    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()


def render_user_menu():
    """Render user menu in sidebar"""

    user = get_current_user()

    if user:
        st.caption(f"Usuario: {user.email}")
        if st.button("Cerrar Sesion", use_container_width=True, key="logout_btn"):
            logout()
    else:
        st.caption("No autenticado")
