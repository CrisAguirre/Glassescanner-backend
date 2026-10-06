"""S2: geometría real con MediaPipe Python (468/478 landmarks).
Funciones a implementar:
- detect_landmarks(bgr) -> np.ndarray[N,3]
- symmetry_index(lm) -> 0-100 (línea media nasion-filtrum-mentón, dif L/R ojos/pómulos/comisuras)
- ratios(lm) -> largo/ancho, frente/pómulo, mandíbula/frente
- classify_face(ratios, jaw_angle) -> 1 de 7 formas
- estimate_ipd_mm(lm, scale_ref) / nose_bridge(lm)
Por ahora stub documentado para no bloquear contratos.
"""
