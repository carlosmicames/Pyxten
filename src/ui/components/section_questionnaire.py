"""
Interactive questionnaire for Section 2.1.9 compliance check
Flowchart-style conditional questions before document upload
"""

import streamlit as st
from typing import Dict, List, Optional

class Section219Questionnaire:
    """Interactive questionnaire for Reglamento Conjunto Section 2.1.9"""
    
    def __init__(self):
        # Initialize questionnaire state
        if 'questionnaire_answers' not in st.session_state:
            st.session_state.questionnaire_answers = {}
        
        if 'questionnaire_complete' not in st.session_state:
            st.session_state.questionnaire_complete = False
        
        if 'questionnaire_errors' not in st.session_state:
            st.session_state.questionnaire_errors = []
        
        # Define the questionnaire tree
        self.questions = self._build_question_tree()
    
    def _build_question_tree(self) -> Dict:
        """
        Builds the conditional question tree for Section 2.1.9
        Each question has: text, id, next_if_yes, next_if_no, article_ref, fix_instructions
        """
        return {
            "start": {
                "id": "start",
                "text": "¿Es una construcción nueva, ampliación o remodelación?",
                "article": "Reglamento Conjunto 2023, Sección 2.1.9",
                "options": ["Nueva construcción", "Ampliación", "Remodelación"],
                "next": "ownership_status"
            },
            
            "ownership_status": {
                "id": "ownership_status",
                "text": "¿Es usted el propietario registrado de la propiedad?",
                "article": "Sección 2.1.9(a) - Titularidad",
                "options": ["Sí", "No"],
                "next_if_yes": "property_registered",
                "next_if_no": "stop_ownership",
                "error_if_no": {
                    "title": "Titularidad Requerida",
                    "message": "Solo el propietario registrado puede solicitar permisos de construcción",
                    "fix": [
                        "1. Obtener autorización escrita del propietario registrado",
                        "2. Registrar escritura de compraventa si eres el nuevo dueño",
                        "3. Presentar poder notarial si actúas en representación"
                    ]
                }
            },
            
            "property_registered": {
                "id": "property_registered",
                "text": "¿La propiedad está registrada en el Registro de la Propiedad?",
                "article": "Sección 2.1.9(b) - Certificación Registral",
                "options": ["Sí", "No"],
                "next_if_yes": "zoning_compatible",
                "next_if_no": "stop_registration",
                "error_if_no": {
                    "title": "Propiedad No Registrada",
                    "message": "La propiedad debe estar inscrita en el Registro de la Propiedad",
                    "fix": [
                        "1. Inscribir la propiedad en el Registro de la Propiedad",
                        "2. Obtener Certificación de Título",
                        "3. Resolver cualquier segregación o agregación pendiente"
                    ]
                }
            },
            
            "zoning_compatible": {
                "id": "zoning_compatible",
                "text": "¿El uso propuesto es compatible con la zonificación del predio?",
                "article": "Sección 2.1.9(c) - Compatibilidad de Uso",
                "options": ["Sí", "No", "No estoy seguro"],
                "next_if_yes": "has_professional",
                "next_if_no": "stop_zoning",
                "error_if_no": {
                    "title": "Incompatibilidad de Zonificación",
                    "message": "El uso propuesto no es permitido en esta zonificación",
                    "fix": [
                        "1. Solicitar Consulta de Ubicación (CUB) a la Junta de Planificación",
                        "2. Solicitar cambio de zonificación (rezoning)",
                        "3. Modificar el uso propuesto para que sea compatible"
                    ]
                }
            },
            
            "has_professional": {
                "id": "has_professional",
                "text": "¿Cuenta con un Profesional Autorizado (PA) - Arquitecto o Ingeniero?",
                "article": "Sección 2.1.9(d) - Requisito de PA",
                "options": ["Sí", "No", "No requerido (permiso menor)"],
                "next_if_yes": "has_plans",
                "next_if_no": "stop_professional",
                "error_if_no": {
                    "title": "Profesional Autorizado Requerido",
                    "message": "Se requiere un PA colegiado para firmar y sellar los planos",
                    "fix": [
                        "1. Contratar Arquitecto o Ingeniero colegiado en Puerto Rico",
                        "2. Verificar que esté al día con su colegiación",
                        "3. El PA debe supervisar el diseño y construcción"
                    ]
                }
            },
            
            "has_plans": {
                "id": "has_plans",
                "text": "¿Tiene planos arquitectónicos firmados y sellados por el PA?",
                "article": "Sección 2.1.9(e) - Planos Requeridos",
                "options": ["Sí", "No"],
                "next_if_yes": "plans_complete",
                "next_if_no": "stop_plans",
                "error_if_no": {
                    "title": "Planos Requeridos",
                    "message": "Debe contar con planos completos firmados y sellados",
                    "fix": [
                        "1. Solicitar al PA que prepare planos de construcción",
                        "2. Los planos deben incluir: plantas, elevaciones, detalles",
                        "3. Cada plano debe tener firma y sello original del PA"
                    ]
                }
            },
            
            "plans_complete": {
                "id": "plans_complete",
                "text": "¿Los planos incluyen: Planta Arquitectónica, Elevaciones (4 fachadas) y Planta de Conjunto?",
                "article": "Sección 2.1.9(f) - Contenido de Planos",
                "options": ["Sí, tengo todos", "No, me faltan algunos"],
                "next_if_yes": "has_certifications",
                "next_if_no": "stop_plans_incomplete",
                "error_if_no": {
                    "title": "Planos Incompletos",
                    "message": "Faltan componentes requeridos en los planos",
                    "fix": [
                        "1. Solicitar al PA los planos faltantes",
                        "2. Mínimo requerido: Planta, Elevaciones (4), Conjunto",
                        "3. También se requieren: Estructurales, Eléctricos, Plomería (si aplica)"
                    ]
                }
            },
            
            "has_certifications": {
                "id": "has_certifications",
                "text": "¿Tiene Certificación Registral de Cabida (menos de 90 días)?",
                "article": "Sección 2.1.9(g) - Certificaciones",
                "options": ["Sí", "No"],
                "next_if_yes": "has_utilities",
                "next_if_no": "stop_certification",
                "error_if_no": {
                    "title": "Certificación Registral Requerida",
                    "message": "Se requiere Certificación Registral vigente (< 90 días)",
                    "fix": [
                        "1. Solicitar Certificación Registral en el Registro de la Propiedad",
                        "2. Debe ser emisión reciente (últimos 90 días)",
                        "3. Debe incluir descripción de cabida y gravámenes"
                    ]
                }
            },
            
            "has_utilities": {
                "id": "has_utilities",
                "text": "¿Tiene certificación de disponibilidad de servicios (AAA, AEE)?",
                "article": "Sección 2.1.9(h) - Servicios Públicos",
                "options": ["Sí", "No", "No aplica (ya existen)"],
                "next_if_yes": "environmental_clearance",
                "next_if_no": "stop_utilities",
                "error_if_no": {
                    "title": "Certificaciones de Servicios Requeridas",
                    "message": "Se requiere certificación de disponibilidad de servicios públicos",
                    "fix": [
                        "1. Solicitar carta de disponibilidad de agua (AAA)",
                        "2. Solicitar carta de disponibilidad eléctrica (LUMA/AEE)",
                        "3. Si servicios existen, incluir factura o evidencia"
                    ]
                }
            },
            
            "environmental_clearance": {
                "id": "environmental_clearance",
                "text": "¿El proyecto requiere evaluación ambiental (zonas costeras, humedales, etc.)?",
                "article": "Sección 2.1.9(i) - Requisitos Ambientales",
                "options": ["No requiere", "Sí, ya tengo permiso DRNA/ARPE", "Sí, pero no tengo"],
                "next_if_yes": "ready_to_submit",
                "next_if_no": "stop_environmental",
                "error_if_no": {
                    "title": "Permisos Ambientales Requeridos",
                    "message": "Su proyecto requiere evaluación y permisos ambientales",
                    "fix": [
                        "1. Determinar si está en Zona Costanera o cerca de cuerpos de agua",
                        "2. Solicitar evaluación a DRNA (Recursos Naturales)",
                        "3. Obtener permisos de ARPE si está en zona de protección",
                        "4. Consultar con biólogo o especialista ambiental"
                    ]
                }
            },
            
            "ready_to_submit": {
                "id": "ready_to_submit",
                "text": "Verificación Final: ¿Confirma que todos los documentos están completos y actualizados?",
                "article": "Sección 2.1.9 - Verificación Final",
                "options": ["Sí, estoy listo para proceder", "No, necesito revisar"],
                "next_if_yes": "complete",
                "next_if_no": "start"
            }
        }
    
    def render(self) -> bool:
        """
        Renders the interactive questionnaire
        
        Returns:
            True if questionnaire is complete and user can proceed
            False if still in progress or has blocking errors
        """
        st.markdown("### Verificación de Cumplimiento - Sección 2.1.9")
        st.info("""
        **Antes de subir documentos**, verifiquemos que cumples con los requisitos básicos 
        del Reglamento Conjunto 2023, Sección 2.1.9 (Permisos de Construcción).
        
        Responde las siguientes preguntas para identificar posibles problemas.
        """)
        
        # Get current question
        current_question_id = st.session_state.get('current_question', 'start')
        
        # Check if complete
        if current_question_id == 'complete':
            st.success("✅ **Verificación Completada** - Cumples con los requisitos básicos de la Sección 2.1.9")
            st.info("Puedes proceder a subir tus documentos para validación con IA")
            
            if st.button("🔄 Reiniciar Cuestionario", key="restart_questionnaire"):
                self._reset_questionnaire()
                st.rerun()
            
            return True
        
        # Check if at a stop point (blocking error)
        if current_question_id.startswith('stop_'):
            return False
        
        # Get question data
        question = self.questions.get(current_question_id)
        
        if not question:
            st.error(f"Error: Pregunta '{current_question_id}' no encontrada")
            return False
        
        # Show progress
        total_questions = len([q for q in self.questions.keys() if not q.startswith('stop_')])
        answered = len(st.session_state.questionnaire_answers)
        progress = min(answered / total_questions, 1.0)
        
        st.progress(progress, text=f"Progreso: {answered}/{total_questions} preguntas")
        st.markdown("---")
        
        # Render question
        st.markdown(f"#### {question['text']}")
        st.caption(f"📄 {question['article']}")
        
        # Radio buttons for options
        answer = st.radio(
            "Selecciona tu respuesta:",
            options=question['options'],
            key=f"q_{current_question_id}",
            label_visibility="collapsed"
        )
        
        # Navigation buttons
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if answered > 0:
                if st.button("⬅️ Anterior", key=f"back_{current_question_id}"):
                    self._go_back()
                    st.rerun()
        
        with col2:
            if st.button("Continuar ➡️", key=f"next_{current_question_id}", type="primary", use_container_width=True):
                # Save answer
                st.session_state.questionnaire_answers[current_question_id] = answer
                
                # Determine next question
                next_question = self._get_next_question(question, answer)
                
                # Check if this triggers an error
                if next_question.startswith('stop_'):
                    self._show_blocking_error(next_question)
                    st.session_state.current_question = next_question
                else:
                    st.session_state.current_question = next_question
                
                st.rerun()
        
        return False
    
    def _get_next_question(self, question: Dict, answer: str) -> str:
        """Determines next question based on answer"""
        
        # Check for conditional next
        if answer.lower() == "sí" and "next_if_yes" in question:
            return question["next_if_yes"]
        
        elif answer.lower() == "no" and "next_if_no" in question:
            return question["next_if_no"]
        
        elif "next" in question:
            return question["next"]
        
        # Default progression
        return "complete"
    
    def _show_blocking_error(self, stop_id: str):
        """Shows blocking error with instructions to fix"""
        
        # Find the question that led to this stop
        for q_id, q_data in self.questions.items():
            if q_data.get('next_if_no') == stop_id and 'error_if_no' in q_data:
                error_info = q_data['error_if_no']
                
                st.error(f"### ⚠️ {error_info['title']}")
                st.warning(error_info['message'])
                
                st.markdown("#### Cómo Resolver:")
                for step in error_info['fix']:
                    st.markdown(step)
                
                st.markdown("---")
                st.info("Una vez resuelvas este issue, puedes reiniciar el cuestionario")
                
                if st.button("🔄 Reiniciar Cuestionario", key="restart_after_error"):
                    self._reset_questionnaire()
                    st.rerun()
                
                return
    
    def _go_back(self):
        """Goes back to previous question"""
        if st.session_state.questionnaire_answers:
            # Remove last answer
            last_q = list(st.session_state.questionnaire_answers.keys())[-1]
            del st.session_state.questionnaire_answers[last_q]
            
            # Set current to previous
            if st.session_state.questionnaire_answers:
                st.session_state.current_question = list(st.session_state.questionnaire_answers.keys())[-1]
            else:
                st.session_state.current_question = 'start'
    
    def _reset_questionnaire(self):
        """Resets questionnaire to start"""
        st.session_state.questionnaire_answers = {}
        st.session_state.current_question = 'start'
        st.session_state.questionnaire_complete = False
        st.session_state.questionnaire_errors = []
    
    def get_answers(self) -> Dict:
        """Returns all questionnaire answers"""
        return st.session_state.questionnaire_answers