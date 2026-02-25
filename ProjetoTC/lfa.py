from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Set, Tuple, List, Optional, FrozenSet

State = str
Symbol = str

# -------------------------
# Helpers: parsing/inputs
# -------------------------
def parse_csv_set(user_input: str) -> Set[str]:
    items = [x.strip() for x in user_input.split(",")]
    return {x for x in items if x != ""}

def prompt_non_empty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("⚠️  Entrada vazia. Tente novamente.")

def prompt_csv_set(prompt: str) -> Set[str]:
    while True:
        raw = prompt_non_empty(prompt)
        s = parse_csv_set(raw)
        if s:
            return s
        print("⚠️  Precisa informar pelo menos 1 item.")

def prompt_choice(prompt: str, allowed: Set[str]) -> str:
    allowed_sorted = ", ".join(sorted(allowed))
    while True:
        s = prompt_non_empty(f"{prompt} (opções: {allowed_sorted}): ")
        if s in allowed:
            return s
        print("⚠️  Valor inválido. Escolha uma das opções.")

def prompt_yes_no(prompt: str) -> bool:
    while True:
        s = prompt_non_empty(prompt + " [s/n]: ").lower()
        if s in ("s", "sim"):
            return True
        if s in ("n", "nao", "não"):
            return False
        print("⚠️  Responda com 's' ou 'n'.")


# ============================================================
# 1) DFA + MEF trace
# ============================================================
TransitionKey = Tuple[State, Symbol]
TransitionFunction = Dict[TransitionKey, State]

@dataclass(frozen=True)
class DFA:
    alphabet: Set[Symbol]
    states: Set[State]
    delta: TransitionFunction
    start: State
    finals: Set[State]

    def validate_structure(self) -> List[str]:
        errors: List[str] = []
        if not self.alphabet:
            errors.append("Alfabeto Σ está vazio.")
        if not self.states:
            errors.append("Conjunto de estados Q está vazio.")
        if self.start not in self.states:
            errors.append(f"Estado inicial '{self.start}' não pertence a Q.")
        if not self.finals.issubset(self.states):
            errors.append("Conjunto de finais F contém estados que não pertencem a Q.")

        for (q, a), q2 in self.delta.items():
            if q not in self.states:
                errors.append(f"Transição usa estado origem inválido: '{q}'.")
            if a not in self.alphabet:
                errors.append(f"Transição usa símbolo fora do alfabeto: '{a}'.")
            if q2 not in self.states:
                errors.append(f"Transição aponta para estado inválido: '{q2}'.")
        return errors

    def is_total(self) -> bool:
        for q in self.states:
            for a in self.alphabet:
                if (q, a) not in self.delta:
                    return False
        return True

    def missing_transitions(self) -> List[Tuple[State, Symbol]]:
        miss = []
        for q in self.states:
            for a in self.alphabet:
                if (q, a) not in self.delta:
                    miss.append((q, a))
        return miss


@dataclass
class MEFRun:
    dfa: DFA

    def run_word(self, w: str, verbose: bool = True) -> bool:
        tape = list(w)
        control_state = self.dfa.start

        if verbose:
            print("\n=== MEF: INÍCIO DA EXECUÇÃO ===")
            print(f"Entrada (w): {w!r}")
            print(f"Fita: {tape}")
            print(f"Estado inicial (q0): {control_state}")
            print(f"Finais (F): {sorted(self.dfa.finals)}")
            print("================================\n")

        for i, symbol in enumerate(tape):
            if symbol not in self.dfa.alphabet:
                if verbose:
                    print(f"[PASSO {i}] Símbolo '{symbol}' NÃO pertence a Σ. Rejeita ❌")
                return False

            key = (control_state, symbol)
            if key not in self.dfa.delta:
                if verbose:
                    print(f"[PASSO {i}] Não existe δ({control_state}, '{symbol}'). Rejeita ❌")
                return False

            next_state = self.dfa.delta[key]
            if verbose:
                print(f"[PASSO {i}] Estado atual (UC): {control_state}")
                print(f"          Lê símbolo: '{symbol}'")
                print(f"          δ({control_state}, '{symbol}') = {next_state}")
                print(f"          Próximo estado -> {next_state}\n")

            control_state = next_state

        accepted = control_state in self.dfa.finals
        if verbose:
            print("=== MEF: FIM DA EXECUÇÃO ===")
            print(f"Estado final alcançado: {control_state}")
            print(f"Resultado: {'ACEITA ✅' if accepted else 'REJEITA ❌'}")
            print("============================\n")
        return accepted


def print_dfa_summary(dfa: DFA) -> None:
    print("\n=== RESUMO DO AFD ===")
    print(f"Σ: {sorted(dfa.alphabet)}")
    print(f"Q: {sorted(dfa.states)}")
    print(f"q0: {dfa.start}")
    print(f"F: {sorted(dfa.finals)}")
    print("δ:")
    for q in sorted(dfa.states):
        for a in sorted(dfa.alphabet):
            nxt = dfa.delta.get((q, a))
            print(f"  δ({q}, '{a}') = {nxt}")
    print("=====================\n")


# ============================================================
# 2) Persistência em JSON (AFD)
# ============================================================
def dfa_to_json_dict(dfa: DFA) -> dict:
    transitions = []
    for (q, a), q2 in dfa.delta.items():
        transitions.append({"from": q, "symbol": a, "to": q2})
    transitions.sort(key=lambda t: (t["from"], t["symbol"], t["to"]))
    return {
        "type": "DFA",
        "alphabet": sorted(dfa.alphabet),
        "states": sorted(dfa.states),
        "start": dfa.start,
        "finals": sorted(dfa.finals),
        "delta": transitions,
    }

def dfa_from_json_dict(data: dict) -> DFA:
    if data.get("type") != "DFA":
        raise ValueError("JSON não parece ser um DFA (campo type != 'DFA').")

    alphabet = set(data["alphabet"])
    states = set(data["states"])
    start = data["start"]
    finals = set(data["finals"])
    delta: TransitionFunction = {}
    for t in data["delta"]:
        delta[(t["from"], t["symbol"])] = t["to"]

    dfa = DFA(alphabet=alphabet, states=states, delta=delta, start=start, finals=finals)
    errs = dfa.validate_structure()
    if errs:
        raise ValueError("DFA inválido carregado do JSON:\n - " + "\n - ".join(errs))
    return dfa

def save_dfa_json(dfa: DFA, path: str) -> None:
    data = dfa_to_json_dict(dfa)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ AFD salvo em: {path}")

def load_dfa_json(path: str) -> DFA:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    dfa = dfa_from_json_dict(data)
    print(f"✅ AFD carregado de: {path}")
    return dfa


# ============================================================
# 3) Construção AFD pelo usuário (console)
# ============================================================
def build_dfa_from_user() -> DFA:
    print("\n==============================")
    print("  DEFINIÇÃO DE UM AFD (M = Σ,Q,δ,q0,F)")
    print("==============================")

    alphabet = prompt_csv_set("Digite o alfabeto Σ (vírgulas). Ex: 0,1: ")
    states = prompt_csv_set("Digite os estados Q (vírgulas). Ex: q0,q1: ")
    start = prompt_choice("Digite o estado inicial q0", states)

    finals_raw = prompt_csv_set("Digite os estados finais F (vírgulas). Ex: q1: ")
    finals = {f for f in finals_raw if f in states}
    if finals_raw and not finals:
        print("⚠️  Você informou finais, mas nenhum estava em Q. (F ficou vazio)")

    print("\nDefinindo δ(q,a) para TODO q∈Q e a∈Σ (AFD total).")
    delta: TransitionFunction = {}
    for q in sorted(states):
        for a in sorted(alphabet):
            nxt = prompt_choice(f"δ({q}, '{a}') =", states)
            delta[(q, a)] = nxt

    dfa = DFA(alphabet=alphabet, states=states, delta=delta, start=start, finals=finals)
    errs = dfa.validate_structure()
    if errs:
        print("\n❌ Erros na definição do AFD:")
        for e in errs:
            print(" -", e)
        print("➡️  Você pode redefinir pelo menu.")
    else:
        print("\n✅ AFD definido com sucesso!")
    return dfa


# ============================================================
# 4) NFA (AFND) + conversão para DFA (subset construction)
# ============================================================
# Representação: delta_nfa[(q, a)] = {q1,q2,...}
# onde a pode ser símbolo em Σ, e opcionalmente "eps" (ε)
NfaDelta = Dict[Tuple[State, Symbol], Set[State]]
EPS = "eps"

@dataclass(frozen=True)
class NFA:
    alphabet: Set[Symbol]        # Σ (não inclui eps)
    states: Set[State]           # Q
    delta: NfaDelta              # δ: Q × (Σ ∪ {eps}) → P(Q)
    start: State                 # q0
    finals: Set[State]           # F
    uses_epsilon: bool = False

    def validate_structure(self) -> List[str]:
        errors: List[str] = []
        if self.start not in self.states:
            errors.append(f"Estado inicial '{self.start}' não pertence a Q.")
        if not self.finals.issubset(self.states):
            errors.append("Conjunto de finais F contém estados que não pertencem a Q.")
        for (q, a), dests in self.delta.items():
            if q not in self.states:
                errors.append(f"Transição usa estado origem inválido: '{q}'.")
            if a != EPS and a not in self.alphabet:
                errors.append(f"Transição usa símbolo fora do alfabeto: '{a}'.")
            for d in dests:
                if d not in self.states:
                    errors.append(f"Transição aponta para estado inválido: '{d}'.")
        return errors


def build_nfa_from_user() -> NFA:
    print("\n==============================")
    print("  DEFINIÇÃO DE UM AFND (NFA)")
    print("==============================")

    alphabet = prompt_csv_set("Digite o alfabeto Σ (vírgulas). Ex: 0,1: ")
    states = prompt_csv_set("Digite os estados Q (vírgulas). Ex: q0,q1,q2: ")
    start = prompt_choice("Digite o estado inicial q0", states)

    finals_raw = prompt_csv_set("Digite os estados finais F (vírgulas). Ex: q2: ")
    finals = {f for f in finals_raw if f in states}
    if finals_raw and not finals:
        print("⚠️  Você informou finais, mas nenhum estava em Q. (F ficou vazio)")

    uses_eps = prompt_yes_no("Seu AFND usa transições ε (epsilon)? (use 'eps')")

    print("\nAgora vamos definir δ do AFND.")
    print("Para cada (q, símbolo), você pode informar VÁRIOS destinos separados por vírgula.")
    if uses_eps:
        print("Para ε, você também definirá destinos para o símbolo especial: eps")
    print("Se não houver transição, basta digitar: - (hífen)\n")

    delta: NfaDelta = {}

    symbols = sorted(alphabet) + ([EPS] if uses_eps else [])
    for q in sorted(states):
        for a in symbols:
            raw = prompt_non_empty(f"δ({q}, '{a}') = (destinos separados por vírgula ou '-' ) ")
            if raw.strip() == "-":
                continue
            dests = parse_csv_set(raw)
            # filtra destinos inválidos
            dests = {d for d in dests if d in states}
            if dests:
                delta[(q, a)] = dests
            else:
                print("⚠️  Nenhum destino válido em Q; essa transição será ignorada.")

    nfa = NFA(alphabet=alphabet, states=states, delta=delta, start=start, finals=finals, uses_epsilon=uses_eps)
    errs = nfa.validate_structure()
    if errs:
        print("\n❌ Erros na definição do AFND:")
        for e in errs:
            print(" -", e)
        print("➡️  Você pode redefinir pelo menu.")
    else:
        print("\n✅ AFND definido com sucesso!")
    return nfa


def epsilon_closure(nfa: NFA, start_states: Set[State]) -> Set[State]:
    """
    ε-fecho: todos estados alcançáveis por zero ou mais transições eps.
    """
    if not nfa.uses_epsilon:
        return set(start_states)

    stack = list(start_states)
    closed = set(start_states)
    while stack:
        q = stack.pop()
        dests = nfa.delta.get((q, EPS), set())
        for d in dests:
            if d not in closed:
                closed.add(d)
                stack.append(d)
    return closed


def move(nfa: NFA, states: Set[State], symbol: Symbol) -> Set[State]:
    """
    Move(S, a) = união das transições a a partir dos estados em S.
    """
    out: Set[State] = set()
    for q in states:
        out |= nfa.delta.get((q, symbol), set())
    return out


def subset_name(state_set: FrozenSet[State]) -> str:
    """
    Nome determinístico para um conjunto de estados.
    Ex: {q0,q2} -> "{q0,q2}"
    """
    if not state_set:
        return "{}"
    return "{" + ",".join(sorted(state_set)) + "}"


def nfa_to_dfa(nfa: NFA, verbose: bool = True) -> DFA:
    """
    Construção por subconjuntos (com ε-fecho opcional).
    """
    if verbose:
        print("\n=== AFND → AFD: CONSTRUÇÃO POR SUBCONJUNTOS ===")

    start_set = epsilon_closure(nfa, {nfa.start})
    start_fs: FrozenSet[State] = frozenset(start_set)

    dfa_states_fs: Set[FrozenSet[State]] = set()
    dfa_states_fs.add(start_fs)

    unmarked: List[FrozenSet[State]] = [start_fs]

    dfa_delta: TransitionFunction = {}
    dfa_finals: Set[State] = set()

    while unmarked:
        T = unmarked.pop(0)  # conjunto de estados do NFA
        T_name = subset_name(T)

        if verbose:
            print(f"\nProcessando estado DFA T = {T_name}")

        # se T contém algum final do NFA, então T é final no DFA
        if any(q in nfa.finals for q in T):
            dfa_finals.add(T_name)

        for a in sorted(nfa.alphabet):
            U = move(nfa, set(T), a)
            U = epsilon_closure(nfa, U)
            U_fs = frozenset(U)
            U_name = subset_name(U_fs)

            if verbose:
                print(f"  Para símbolo '{a}': move(T,'{a}') -> {sorted(U)} => U = {U_name}")

            # registra transição do DFA
            dfa_delta[(T_name, a)] = U_name

            # adiciona novo estado se ainda não visto
            if U_fs not in dfa_states_fs:
                dfa_states_fs.add(U_fs)
                unmarked.append(U_fs)
                if verbose:
                    print(f"    Novo estado DFA descoberto: {U_name}")

    # Constrói conjunto final de nomes (strings)
    dfa_states = {subset_name(s) for s in dfa_states_fs}
    dfa = DFA(
        alphabet=set(nfa.alphabet),
        states=dfa_states,
        delta=dfa_delta,
        start=subset_name(start_fs),
        finals=dfa_finals,
    )

    if verbose:
        print("\n=== FIM DA CONVERSÃO AFND→AFD ===")
        print_dfa_summary(dfa)

    return dfa


# ============================================================
# 5) Minimização de DFA
#    (remover inalcançáveis + completar δ com estado artificial + partições)
# ============================================================
def reachable_states(dfa: DFA) -> Set[State]:
    """
    Estados alcançáveis a partir de q0.
    """
    visited = {dfa.start}
    stack = [dfa.start]
    while stack:
        q = stack.pop()
        for a in dfa.alphabet:
            q2 = dfa.delta.get((q, a))
            if q2 is not None and q2 not in visited:
                visited.add(q2)
                stack.append(q2)
    return visited


def make_total_with_sink(dfa: DFA, sink_name: str = "A") -> DFA:
    """
    Garante δ total criando um estado artificial (sink) para transições ausentes.
    """
    states = set(dfa.states)
    delta = dict(dfa.delta)
    finals = set(dfa.finals)
    alphabet = set(dfa.alphabet)

    need_sink = False
    for q in list(states):
        for a in alphabet:
            if (q, a) not in delta:
                need_sink = True

    if not need_sink:
        return dfa

    # garantir nome único
    base = sink_name
    i = 0
    while sink_name in states:
        i += 1
        sink_name = f"{base}{i}"

    states.add(sink_name)

    # self-loop no sink
    for a in alphabet:
        delta[(sink_name, a)] = sink_name

    # completa faltantes indo para sink
    for q in list(states):
        for a in alphabet:
            if (q, a) not in delta:
                delta[(q, a)] = sink_name

    return DFA(alphabet=alphabet, states=states, delta=delta, start=dfa.start, finals=finals)


def strip_unreachable(dfa: DFA) -> DFA:
    reach = reachable_states(dfa)
    delta2: TransitionFunction = {}
    for (q, a), q2 in dfa.delta.items():
        if q in reach and q2 in reach:
            delta2[(q, a)] = q2
    finals2 = set(dfa.finals) & reach
    return DFA(alphabet=set(dfa.alphabet), states=reach, delta=delta2, start=dfa.start, finals=finals2)


def minimize_dfa(dfa: DFA, verbose: bool = True) -> DFA:
    """
    Minimização via refinamento de partições (estilo Hopcroft simples / Moore).
    Passos:
      1) remover inalcançáveis
      2) completar δ (sink)
      3) partições iniciais: F e Q\\F
      4) refinar até estabilizar
      5) montar AFD mínimo
    """
    if verbose:
        print("\n=== MINIMIZAÇÃO DE AFD ===")
        print("Passo 1) Remover estados inalcançáveis...")
    dfa1 = strip_unreachable(dfa)

    if verbose:
        print(f"  Estados alcançáveis: {sorted(dfa1.states)}")

    if verbose:
        print("Passo 2) Garantir δ total (estado artificial/sink se necessário)...")
    dfa2 = make_total_with_sink(dfa1, sink_name="A")

    if verbose:
        print(f"  δ total? {'SIM' if dfa2.is_total() else 'NÃO'}")
        if not dfa2.is_total():
            print("  Faltantes:", dfa2.missing_transitions())

    Q = set(dfa2.states)
    F = set(dfa2.finals)
    nonF = Q - F

    # partições iniciais
    P: List[Set[State]] = []
    if F:
        P.append(set(F))
    if nonF:
        P.append(set(nonF))

    if verbose:
        print("Passo 3) Partições iniciais:")
        for i, block in enumerate(P, start=1):
            print(f"  B{i} = {sorted(block)}")

    def block_index_of(state: State, partitions: List[Set[State]]) -> int:
        for i, b in enumerate(partitions):
            if state in b:
                return i
        raise RuntimeError(f"Estado {state} não encontrado em partições.")

    changed = True
    iteration = 0

    if verbose:
        print("\nPasso 4) Refinamento de partições...")

    while changed:
        changed = False
        iteration += 1
        newP: List[Set[State]] = []

        if verbose:
            print(f"\n  Iteração {iteration}:")

        for block in P:
            # agrupa estados do bloco por "assinatura" (para cada símbolo, qual bloco vai)
            groups: Dict[Tuple[int, ...], Set[State]] = {}
            for q in block:
                signature = tuple(
                    block_index_of(dfa2.delta[(q, a)], P) for a in sorted(dfa2.alphabet)
                )
                groups.setdefault(signature, set()).add(q)

            if len(groups) == 1:
                newP.append(block)
                if verbose:
                    print(f"    Bloco mantém: {sorted(block)}")
            else:
                changed = True
                if verbose:
                    print(f"    Bloco DIVIDE: {sorted(block)} em {len(groups)} grupos")
                for sig, g in groups.items():
                    newP.append(g)
                    if verbose:
                        print(f"      grupo sig={sig} -> {sorted(g)}")

        P = newP

    if verbose:
        print("\nPasso 5) Montar AFD mínimo a partir das partições finais...")
        for i, block in enumerate(P, start=1):
            print(f"  C{i} = {sorted(block)}")

    # cada partição vira um estado novo
    # nome: [q0,q1] etc
    def block_name(block: Set[State]) -> State:
        return "[" + ",".join(sorted(block)) + "]"

    block_of: Dict[State, Set[State]] = {}
    for block in P:
        for q in block:
            block_of[q] = block

    new_states = {block_name(b) for b in P}
    new_start = block_name(block_of[dfa2.start])
    new_finals = {block_name(block_of[q]) for q in dfa2.finals}

    new_delta: TransitionFunction = {}
    for block in P:
        rep = next(iter(block))  # representante
        from_name = block_name(block)
        for a in dfa2.alphabet:
            to_state = dfa2.delta[(rep, a)]
            to_block = block_of[to_state]
            new_delta[(from_name, a)] = block_name(to_block)

    minimized = DFA(
        alphabet=set(dfa2.alphabet),
        states=new_states,
        delta=new_delta,
        start=new_start,
        finals=new_finals,
    )

    if verbose:
        print("\n✅ AFD minimizado:")
        print_dfa_summary(minimized)

    return minimized


# ============================================================
# Menu principal
# ============================================================
def main():
    dfa: Optional[DFA] = None
    nfa: Optional[NFA] = None
    dfa_from_nfa: Optional[DFA] = None
    dfa_min: Optional[DFA] = None

    while True:
        print("============== MENU ==============")
        print("AFD")
        print("  1) Definir novo AFD (via console)")
        print("  2) Mostrar resumo do AFD atual")
        print("  3) Testar palavra no AFD (MEF rastreio)")
        print("  4) Salvar AFD em JSON")
        print("  5) Carregar AFD de JSON")
        print("")
        print("AFND → AFD")
        print("  6) Definir novo AFND (via console)")
        print("  7) Converter AFND → AFD (subset construction)")
        print("  8) Testar palavra no AFD convertido (MEF rastreio)")
        print("")
        print("Minimização")
        print("  9) Minimizar AFD atual")
        print(" 10) Testar palavra no AFD minimizado (MEF rastreio)")
        print("")
        print(" 11) Sair")
        print("==================================")

        choice = prompt_non_empty("Escolha uma opção: ")

        # -------- AFD --------
        if choice == "1":
            dfa = build_dfa_from_user()
            dfa_min = None

        elif choice == "2":
            if dfa is None:
                print("⚠️  Nenhum AFD definido/carregado.")
            else:
                print_dfa_summary(dfa)

        elif choice == "3":
            if dfa is None:
                print("⚠️  Nenhum AFD definido/carregado.")
                continue
            mef = MEFRun(dfa)
            print("\nDigite palavras para testar. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.run_word(w, verbose=True)

        elif choice == "4":
            if dfa is None:
                print("⚠️  Nenhum AFD definido/carregado.")
                continue
            path = prompt_non_empty("Caminho do arquivo JSON (ex: afd.json): ")
            try:
                save_dfa_json(dfa, path)
            except Exception as e:
                print("❌ Falha ao salvar:", e)

        elif choice == "5":
            path = prompt_non_empty("Caminho do arquivo JSON (ex: afd.json): ")
            try:
                dfa = load_dfa_json(path)
                dfa_min = None
            except Exception as e:
                print("❌ Falha ao carregar:", e)

        # -------- AFND → AFD --------
        elif choice == "6":
            nfa = build_nfa_from_user()
            dfa_from_nfa = None

        elif choice == "7":
            if nfa is None:
                print("⚠️  Nenhum AFND definido.")
                continue
            dfa_from_nfa = nfa_to_dfa(nfa, verbose=True)

        elif choice == "8":
            if dfa_from_nfa is None:
                print("⚠️  Você ainda não converteu AFND→AFD (use opção 7).")
                continue
            mef = MEFRun(dfa_from_nfa)
            print("\nDigite palavras para testar no AFD convertido. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.run_word(w, verbose=True)

        # -------- Minimização --------
        elif choice == "9":
            if dfa is None:
                print("⚠️  Nenhum AFD definido/carregado.")
                continue
            dfa_min = minimize_dfa(dfa, verbose=True)

        elif choice == "10":
            if dfa_min is None:
                print("⚠️  Nenhum AFD minimizado ainda (use opção 9).")
                continue
            mef = MEFRun(dfa_min)
            print("\nDigite palavras para testar no AFD minimizado. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.run_word(w, verbose=True)

        elif choice == "11":
            print("Saindo... 👋")
            break

        else:
            print("⚠️  Opção inválida.")


if __name__ == "__main__":
    main()