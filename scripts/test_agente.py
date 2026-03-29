"""Test manual del agente: simula estados de DF y verifica decisiones.

Uso: python3 -m scripts.test_agente
"""
from scripts.agente_jugador import detectar_contexto, detectar_necesidad, _elegir_opcion_menu

# --- Test detectar_contexto ---

def test_contexto():
    print("=== detectar_contexto ===")

    default = "UNIT: Gonzalo\nFOCUS: dungeonmode/Default\nREGION: Hills"
    assert detectar_contexto(default) == "exploración", f"Expected exploración, got {detectar_contexto(default)}"
    print("  Default → exploración ✓")

    conv = "UNIT: Gonzalo\nFOCUS: dungeonmode/ConversationAddress\nREGION: Hills"
    assert detectar_contexto(conv) == "conversación"
    print("  ConversationAddress → conversación ✓")

    eat = "UNIT: Gonzalo\nFOCUS: dungeonmode/Eat\nREGION: Hills"
    assert detectar_contexto(eat) == "menú"
    print("  Eat → menú ✓")

    sleep = "UNIT: Gonzalo\nFOCUS: dungeonmode/SleepConfirm\nREGION: Hills"
    assert detectar_contexto(sleep) == "menú"
    print("  SleepConfirm → menú ✓")


# --- Test detectar_necesidad ---

def test_necesidad():
    print("\n=== detectar_necesidad ===")

    normal = "Gonzalo Usuknol\nThe Hills of Thundering"
    assert detectar_necesidad(normal) == ""
    print("  Sin estado → '' (sin necesidad) ✓")

    drowsy = "Gonzalo Usuknol     Drowsy                Speed 0.869\nThe Hills    HungThir"
    assert detectar_necesidad(drowsy) == "dormir"
    print("  Drowsy+HungThir → dormir (prioridad) ✓")

    hungthir = "Gonzalo Usuknol                Speed 0.9\nThe Hills    HungThir"
    assert detectar_necesidad(hungthir) == "comer_beber"
    print("  HungThir → comer_beber ✓")

    hungdhyd = "Gonzalo Usuknol                Speed 0.9\nThe Hills    HungDhyd"
    assert detectar_necesidad(hungdhyd) == "comer_beber"
    print("  HungDhyd → comer_beber ✓")

    stunned = "You eat the echidna tripe.\nYou feel really full.\nGonzalo Usuknol     Stunned\nThe Hills    HungThir"
    assert detectar_necesidad(stunned) == "", f"Expected '', got '{detectar_necesidad(stunned)}'"
    print("  Stunned+HungThir → '' (bloqueado) ✓")

    nauseous = "Gonzalo Usuknol     Stunned\nThe Hills    Nauseous    On Ground"
    assert detectar_necesidad(nauseous) == "", f"Expected '', got '{detectar_necesidad(nauseous)}'"
    print("  Nauseous → '' (bloqueado) ✓")

    full = "You eat the echidna tripe [2].\nYou feel really full.\nGonzalo Usuknol\nThe Hills    HungThir"
    assert detectar_necesidad(full) == "", f"Expected '', got '{detectar_necesidad(full)}'"
    print("  'really full'+HungThir → '' (bloqueado) ✓")

    toomuch = "It's too much!  You might not be able to keep it down.\nGonzalo Usuknol\nThe Hills    HungThir"
    assert detectar_necesidad(toomuch) == "", f"Expected '', got '{detectar_necesidad(toomuch)}'"
    print("  'too much'+HungThir → '' (bloqueado) ✓")


# --- Test elegir_opcion_menu ---

def test_eat_menu():
    print("\n=== _elegir_opcion_menu ===")

    screen_eat = """With what would you like to eat or Date:250-01-16

a - copper whip                                     Right hand
b - . apricot wood carving knife
c - . echidna tripe [5]
d - . porcupine leather waterskin
e - . ice [3]
f - . Shethbahdur gold coins [17]
g - . Shethbahdur silver coins [2]
"""
    r = _elegir_opcion_menu(screen_eat, "dungeonmode/Eat")
    assert r == "c", f"Expected 'c', got '{r}'"
    print(f"  Eat menu → '{r}' (echidna tripe) ✓")

    screen_full = """With what would you like to eat or Date:250-01-16

a - copper whip                                     Right hand
c - . echidna tripe [5]

You feel really full.
Gonzalo Usuknol     Stunned                Speed 0.2
The Hills    HungThir"""
    # Este test es para el check de full en el agente, no en _elegir_opcion_menu
    print("  (full/stunned detection is in agent loop, not in menu selector)")


def test_full_screen_detection():
    """Simula lo que el agente ve cuando está en el menú de Eat."""
    print("\n=== Detección de full/nausea en menú Eat ===")

    # Pantalla completa como la captura tmux (80 líneas)
    screen = """ENE
 E
 NE
* N
 W
 N
 E
 NNE
 NW

                        @

Tracks Visible: 0




You eat the echidna tripe [2].
You feel really full.
Gonzalo Usuknol     Stunned                           Speed 0.238
The Hills of TSnowering          HungThir             On Ground"""

    s = screen.lower()
    blocked = any(w in s for w in (
        "really full", "nausea", "nauseous", "stunned",
        "vomit", "too much", "keep it down",
    ))
    assert blocked, "Should detect 'really full' + 'stunned' in screen!"
    print("  Screen con 'really full'+'Stunned' → bloqueado ✓")

    # Pantalla normal sin problemas
    screen_ok = """ENE
* N

Gonzalo Usuknol                                      Speed 0.9
The Hills of Thundering          HungThir"""
    s2 = screen_ok.lower()
    blocked2 = any(w in s2 for w in (
        "really full", "nausea", "nauseous", "stunned",
        "vomit", "too much", "keep it down",
    ))
    assert not blocked2, "Should NOT block normal HungThir screen!"
    print("  Screen normal con HungThir → no bloqueado ✓")


if __name__ == "__main__":
    test_contexto()
    test_necesidad()
    test_eat_menu()
    test_full_screen_detection()
    print("\n✓ Todos los tests pasaron.")
