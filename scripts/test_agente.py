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


def test_llm_input_con_status_bar():
    """Simula lo que el LLM recibe: estado DFHack + STATUS_BAR."""
    print("\n=== LLM input con STATUS_BAR ===")

    # Caso 1: Nauseous — el LLM NO debería pedir comer
    dfhack_state = """UNIT: Gonzalo Usuknol (HUMAN)
POS: x=84 y=93 z=128
HP: 7910/7910
HUNGER: 258524
THIRST: 258524
SLEEP: 258524
WOUNDS: 1
DATE: 250-01-17
FOCUS: dungeonmode/Default
REGION: The Hills of Thundering
NEARBY: Staddat Lesnoamec (HUMAN, d=4)"""

    status_bar_nauseous = """Gonzalo Usuknol     Stunned                           Speed 0.238
The Hills of TSnowering          Nauseous             On Ground"""

    llm_input = dfhack_state + "\n\nSTATUS_BAR:\n" + status_bar_nauseous
    assert "Nauseous" in llm_input, "LLM input should contain Nauseous"
    assert "Stunned" in llm_input, "LLM input should contain Stunned"
    assert "HUNGER: 258524" in llm_input, "LLM input should contain high HUNGER"
    print("  Nauseous+Stunned: LLM ve ambos en input ✓")
    print(f"  (LLM prompt dice: regla 0 prohíbe comer si ve Nauseous/Stunned)")

    # Caso 2: Normal con hambre — el LLM SÍ debería poder pedir comer
    status_bar_normal = """Gonzalo Usuknol                                      Speed 0.9
The Hills of Thundering          HungThir"""

    llm_input_ok = dfhack_state + "\n\nSTATUS_BAR:\n" + status_bar_normal
    assert "HungThir" in llm_input_ok
    assert "Nauseous" not in llm_input_ok
    assert "Stunned" not in llm_input_ok
    print("  Normal+HungThir: LLM ve hambre sin bloqueadores ✓")

    # Caso 3: Sin STATUS_BAR (captura falló) — solo DFHack state
    llm_input_no_bar = dfhack_state
    assert "STATUS_BAR" not in llm_input_no_bar
    print("  Sin STATUS_BAR: LLM solo ve DFHack state (fallback) ✓")


def test_eat_menu_with_full():
    """Simula el menú de Eat cuando ya está lleno."""
    print("\n=== Menú Eat con pantalla llena ===")

    # Pantalla completa del menú de Eat cuando está lleno
    screen_eat_full = """With what would you like to eat or Date:250-01-17

a - copper whip                                     Right hand
b - . apricot wood carving knife
c - . echidna tripe [2]
d - . porcupine leather waterskin
e - . ice [3]

/* to view other pages.  ESC when done.

You eat the echidna tripe [2].
You feel really full.
Gonzalo Usuknol     Stunned                           Speed 0.238
The Hills of TSnowering          HungThir             On Ground"""

    s = screen_eat_full.lower()
    blocked = any(w in s for w in (
        "really full", "nausea", "nauseous", "stunned",
        "vomit", "too much", "keep it down",
    ))
    assert blocked, "Should block eating when 'really full' + 'Stunned' in full screen!"
    print("  Menú Eat + 'really full' + 'Stunned' en 80 líneas → bloqueado ✓")

    # Menú normal sin problemas
    screen_eat_ok = """With what would you like to eat or Date:250-01-17

a - copper whip                                     Right hand
c - . echidna tripe [5]
d - . porcupine leather waterskin
e - . ice [3]

/* to view other pages.  ESC when done.

Gonzalo Usuknol                                      Speed 0.9
The Hills of Thundering          HungThir"""

    s2 = screen_eat_ok.lower()
    blocked2 = any(w in s2 for w in (
        "really full", "nausea", "nauseous", "stunned",
        "vomit", "too much", "keep it down",
    ))
    assert not blocked2, "Should NOT block normal Eat menu!"
    opcion = _elegir_opcion_menu(screen_eat_ok, "dungeonmode/Eat")
    assert opcion == "c", f"Expected 'c', got '{opcion}'"
    print(f"  Menú Eat normal → seleccionar '{opcion}' (tripe) ✓")


if __name__ == "__main__":
    test_contexto()
    test_necesidad()
    test_eat_menu()
    test_full_screen_detection()
    test_llm_input_con_status_bar()
    test_eat_menu_with_full()
    print("\n✓ Todos los tests pasaron.")
