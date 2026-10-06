from ..schemas import Frame

def _mk(i, nombre, forma, A, B, D, total, material="acetato", color="negro"):
    return Frame(id=f"F{i:02d}", nombre=nombre, forma=forma, A_mm=A, B_mm=B, D_mm=D,
                 ancho_total_mm=total, material=material, color=color)

# Seed v1: 12 marcos (2 por forma base). Medidas plausibles de catálogo.
FRAMES = [
    _mk(1, "Ejecutivo Rectangular", "rectangular", 52, 36, 18, 140),
    _mk(2, "Urbano Rectangular Carey", "rectangular", 54, 37, 19, 144, color="carey"),
    _mk(3, "Clásico Cuadrado", "cuadrado", 50, 38, 20, 142),
    _mk(4, "Minimal Cuadrado Metal", "cuadrado", 51, 37, 19, 141, material="metal", color="dorado"),
    _mk(5, "Vintage Redondo", "redondo", 48, 44, 20, 138),
    _mk(6, "Suave Redondo Metal", "redondo", 47, 43, 21, 137, material="metal"),
    _mk(7, "Esencial Oval", "oval", 51, 35, 18, 139),
    _mk(8, "Aire Oval Rimless", "oval", 53, 34, 18, 140, material="mixto", color="transparente"),
    _mk(9, "Aviador Clásico", "aviador", 55, 46, 18, 143, material="metal", color="dorado-verde"),
    _mk(10, "Aviador Nocturno", "aviador", 56, 47, 19, 145, material="metal", color="negro"),
    _mk(11, "Wayfarer Ícono", "wayfarer", 52, 40, 20, 144),
    _mk(12, "Wayfarer Mate", "wayfarer", 53, 41, 21, 146, color="mate"),
]
