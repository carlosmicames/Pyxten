"""
PCOCValidator - Validador completo de Permisos de Construcción
Valida contra Sección 2.1.9 del Reglamento Conjunto
"""

from typing import Dict, List
from datetime import datetime
import json

class PCOCValidator:
    """Valida solicitudes completas de Permiso de Construcción"""
    
    def __init__(self, model_router, rules_db):
        """
        Args:
            model_router: Instancia de ModelRouter
            rules_db: Instancia de RulesDatabase (de Fase 1)
        """
        self.router = model_router
        self.rules_db = rules_db
        
        # Cargar requisitos de Sección 2.1.9
        self.requirements = self._load_requirements()
    
    def validate_full_pcoc(self, project_data: Dict, uploaded_docs: Dict) -> Dict:
        """
        Valida solicitud completa de PCOC
        
        Args:
            project_data: Info del proyecto (nombre, dirección, etc.)
            uploaded_docs: Dict de {doc_type: file_bytes}
        
        Returns:
            {
                "overall_score": 0.0-1.0,
                "compliant": bool,
                "permit_type": "ministerial" | "discrecional",
                "document_scores": {...},
                "critical_blockers": [...],
                "recommendations": [...],
                "validated_at": str
            }
        """
        
        results = {
            "overall_score": 0.0,
            "compliant": False,
            "permit_type": "desconocido",
            "document_scores": {},
            "critical_blockers": [],
            "recommendations": [],
            "validated_at": datetime.now().isoformat()
        }
        
        # 1. Verificar documentos requeridos presentes
        missing_docs = self._check_required_documents(uploaded_docs)
        if missing_docs:
            results['critical_blockers'].extend([
                f"Documento faltante: {doc}" for doc in missing_docs
            ])
        
        # 2. Analizar cada documento con IA
        for doc_type, file_bytes in uploaded_docs.items():
            if doc_type in self.requirements:
                requirements_list = self.requirements[doc_type]['requirements']
                
                doc_result = self.router.analyze_document(
                    doc_type=doc_type,
                    file_bytes=file_bytes,
                    requirements=requirements_list
                )
                
                results['document_scores'][doc_type] = doc_result
                
                # Recopilar issues críticos
                if doc_result.get('critical_issues'):
                    results['critical_blockers'].extend([
                        f"{doc_type}: {issue}" 
                        for issue in doc_result['critical_issues']
                    ])
        
        # 3. Validar coherencia entre documentos
        coherence_issues = self._validate_coherence(results['document_scores'])
        results['critical_blockers'].extend(coherence_issues)
        
        # 4. Calcular score general
        results['overall_score'] = self._calculate_overall_score(results['document_scores'])
        
        # 5. Determinar si cumple
        results['compliant'] = (
            results['overall_score'] >= 0.90 and 
            len(results['critical_blockers']) == 0
        )
        
        # 6. Determinar tipo de permiso
        results['permit_type'] = self._determine_permit_type(
            project_data, 
            results['compliant']
        )
        
        # 7. Generar recomendaciones
        results['recommendations'] = self._generate_recommendations(results)
        
        return results
    
    def _load_requirements(self) -> Dict:
        """Carga requisitos de cada tipo de documento"""
        
        return {
            "planta_arquitectonica": {
                "name": "Planta Arquitectónica",
                "required": True,
                "requirements": [
                    "Firma y sello de profesional autorizado (arquitecto/ingeniero)",
                    "Escala gráfica y numérica claramente indicadas",
                    "Dimensiones de todos los espacios interiores",
                    "Retiros frontal, lateral y trasero marcados y dimensionados",
                    "Norte geográfico indicado",
                    "Área total de construcción calculada",
                    "Leyenda de materiales y símbolos",
                    "Accesos claramente identificados"
                ]
            },
            "elevaciones": {
                "name": "Elevaciones (4 fachadas)",
                "required": True,
                "requirements": [
                    "Las 4 elevaciones presentes (Norte, Sur, Este, Oeste)",
                    "Altura total del edificio indicada",
                    "Niveles de piso terminado marcados",
                    "Materiales de fachada especificados",
                    "Pendientes de techo indicadas",
                    "Firma y sello profesional"
                ]
            },
            "planta_conjunto": {
                "name": "Planta de Conjunto",
                "required": True,
                "requirements": [
                    "Ubicación de edificio dentro del predio",
                    "Retiros dimensionados y marcados",
                    "Accesos vehiculares y peatonales",
                    "Estacionamientos numerados",
                    "Áreas verdes y pavimentadas identificadas",
                    "Norte y colindancias",
                    "Firma y sello profesional"
                ]
            },
            "certificacion_registral": {
                "name": "Certificación Registral",
                "required": True,
                "requirements": [
                    "Emisión dentro de los últimos 90 días",
                    "Nombre del propietario coincide con solicitante",
                    "Descripción de cabida del predio",
                    "Gravámenes e hipotecas (si aplican)",
                    "Sello del Registro de la Propiedad"
                ]
            }
        }
    
    def _check_required_documents(self, uploaded_docs: Dict) -> List[str]:
        """Verifica que documentos requeridos estén presentes"""
        
        required = [
            doc_type for doc_type, info in self.requirements.items()
            if info.get('required', False)
        ]
        
        missing = [
            self.requirements[doc_type]['name']
            for doc_type in required
            if doc_type not in uploaded_docs
        ]
        
        return missing
    
    def _validate_coherence(self, document_scores: Dict) -> List[str]:
        """Valida coherencia entre documentos"""
        issues = []
        # TODO Sprint 2: Implementar validaciones cruzadas
        return issues
    
    def _calculate_overall_score(self, document_scores: Dict) -> float:
        """Calcula score general ponderado"""
        
        if not document_scores:
            return 0.0
        
        weights = {
            "planta_arquitectonica": 0.30,
            "elevaciones": 0.25,
            "planta_conjunto": 0.20,
            "certificacion_registral": 0.15,
            "formulario_ogpe": 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for doc_type, result in document_scores.items():
            weight = weights.get(doc_type, 0.10)
            score = result.get('score', 0.0)
            
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        
        return 0.0
    
    def _determine_permit_type(self, project_data: Dict, compliant: bool) -> str:
        """Determina si permiso es ministerial o discrecional"""
        
        if not compliant:
            return "no_aplica"
        
        use_code = project_data.get('proposed_use_code', '')
        
        if use_code in ['RES-SF', 'RES-MF']:
            return "ministerial"
        
        return "discrecional"
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Genera recomendaciones accionables"""
        
        recommendations = []
        
        if results['critical_blockers']:
            recommendations.append(
                "PRIORIDAD ALTA: Corregir todos los issues críticos antes de someter"
            )
            
            for blocker in results['critical_blockers'][:3]:
                recommendations.append(f"• {blocker}")
        
        elif 0.70 <= results['overall_score'] < 0.90:
            recommendations.append(
                "Tu solicitud está cerca de cumplir. Revisa los siguientes items:"
            )
            
            for doc_type, doc_result in results['document_scores'].items():
                if doc_result.get('score', 1.0) < 0.85:
                    doc_name = self.requirements.get(doc_type, {}).get('name', doc_type)
                    recommendations.append(
                        f"• Revisar {doc_name} (score: {doc_result['score']*100:.0f}%)"
                    )
        
        else:
            recommendations.append(
                "✅ Tu solicitud cumple con los requisitos. Próximos pasos:"
            )
            recommendations.extend([
                "1. Descargar reporte completo",
                "2. Revisar checklist de cumplimiento",
                "3. Preparar documentos físicos para someter",
                "4. Someter a OGPe o municipio según corresponda"
            ])
        
        return recommendations