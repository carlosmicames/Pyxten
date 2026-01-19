import streamlit as st
import os


def render_chatbot_page():
    """Chatbot page for regulation queries"""

    st.markdown("## Asistente de Regulaciones")
    st.caption("Preguntame sobre el Reglamento Conjunto o exclusiones categoricas")

    # Check if OpenAI API is configured
    if not os.getenv("OPENAI_API_KEY"):
        st.warning("""
        **Chatbot no disponible**

        Para habilitar el asistente de regulaciones, agrega OPENAI_API_KEY a tu archivo .env
        """)
        return

    # Initialize chatbot
    if 'chatbot' not in st.session_state:
        try:
            from src.services.chatbot_service import RegulationChatbot
            st.session_state.chatbot = RegulationChatbot()
        except Exception as e:
            st.error(f"Error inicializando chatbot: {e}")
            return

    # Initialize conversation history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Escribe tu pregunta..."):
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                response = st.session_state.chatbot.ask(
                    question=prompt,
                    conversation_history=st.session_state.chat_history[:-1]
                )

                st.markdown(response)

        # Add assistant response to history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response
        })

    # Sidebar with examples and clear button
    with st.sidebar:
        st.markdown("### Opciones de Chat")

        if st.button("Limpiar Conversacion", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

        st.markdown("---")

        st.markdown("### Preguntas de ejemplo")
        example_questions = st.session_state.chatbot.get_example_questions()

        for question in example_questions[:5]:
            if st.button(question, key=f"ex_{hash(question)}", use_container_width=True):
                # Add as user message and get response
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": question
                })
                st.rerun()

    # Help section at bottom
    with st.expander("Sobre el Asistente"):
        st.markdown("""
        Este asistente esta entrenado con informacion sobre:

        - **Reglamento Conjunto 2023** - Especialmente Tomo 6 (Zonificacion)
        - **Reglamento 2025-10** - Exclusiones Categoricas
        - **Proceso OGPe** - Permisos de construccion
        - **Distritos de Zonificacion** - R, C, I, A, etc.

        **Nota:** Las respuestas son orientativas. Siempre consulta con un
        Profesional Autorizado para decisiones finales.
        """)
