
import sys
import os

# Adiciona o diretório raiz ao path para encontrar o pacote software
sys.path.append(os.getcwd())

from software.core.state import CalculatorState

def test_deletion_behavior():
    state = CalculatorState()
    
    # Teste 1: polar(
    state.press("polar(")
    print(f"Expressão após polar(: '{state.expression}'")
    
    state.press("DEL")
    print(f"Expressão após 1x DEL: '{state.expression}'")
    
    if state.expression == "polar":
        print("COMPORTAMENTO ATUAL: Remove apenas '('")
    elif state.expression == "":
        print("COMPORTAMENTO DESEJADO: Remove 'polar(' de uma vez")
    else:
        print(f"Comportamento inesperado: '{state.expression}'")

    # Teste 2: polar(ab,cd)
    state.expression = ""
    state.press("polar(")
    state.press("a")
    state.press("b")
    state.press(",")
    state.press("c")
    state.press("d")
    state.press(")")
    print(f"Expressão: '{state.expression}'")
    
    # Pressionando DEL até chegar no nome da função
    for _ in range(7):
        state.press("DEL")
    
    print(f"Expressão antes de deletar o nome da função: '{state.expression}'")
    # Teste 3: Outras funções
    for func in ["sen(", "logbase(", "inv(", "sqrt("]:
        state.expression = ""
        state.press(func)
        state.press("DEL")
        if state.expression == "":
            print(f"Sucesso: '{func}' removido como bloco.")
        else:
            print(f"FALHA: '{func}' não removido como bloco. Restou: '{state.expression}'")

if __name__ == "__main__":
    test_deletion_behavior()
