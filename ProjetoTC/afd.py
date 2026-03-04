from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set, Tuple, List, Optional, FrozenSet

Estado = str
Simbolo = str

# ============================================================
# Helpers: parsing/inputs
# ============================================================
# PROMPTS PARA TRATATIVAS DE VALIDAÇÃO DE ENTRADAS DO USUARIO
def parsear_conjunto_csv(entrada_usuario: str) -> Set[str]:
    itens = [x.strip() for x in entrada_usuario.split(",")]
    return {x for x in itens if x != ""}


def solicitar_nao_vazio(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("⚠️  Entrada vazia. Tente novamente.")


def solicitar_conjunto_csv(prompt: str) -> Set[str]:
    while True:
        raw = solicitar_nao_vazio(prompt)
        s = parsear_conjunto_csv(raw)
        if s:
            return s
        print("⚠️  Precisa informar pelo menos 1 item.")


def solicitar_escolha(prompt: str, permitido: Set[str]) -> str:
    permitido_ordenado = ", ".join(sorted(permitido))
    while True:
        s = solicitar_nao_vazio(f"{prompt} (opções: {permitido_ordenado}): ")
        if s in permitido:
            return s
        print("⚠️  Valor inválido. Escolha uma das opções.")


def solicitar_sim_nao(prompt: str) -> bool:
    while True:
        s = solicitar_nao_vazio(prompt + " [s/n]: ").lower()
        if s in ("s", "sim"):
            return True
        if s in ("n", "nao", "não"):
            return False
        print("⚠️  Responda com 's' ou 'n'.")


# ============================================================
#  AFD
# ============================================================

#DEFINIÇAO DO AFD
ChaveTransicao = Tuple[Estado, Simbolo]
FuncaoTransicao = Dict[ChaveTransicao, Estado]


@dataclass(frozen=True)
class AFD:
    alfabeto: Set[Simbolo]
    estados: Set[Estado]
    delta: FuncaoTransicao
    inicial: Estado
    finais: Set[Estado]

    # VALIDACAO DA ESTRUTURA DO AFD/TRATATIVAS DE ERRO
    def validar_estrutura(self) -> List[str]:
        erros: List[str] = []
        if not self.alfabeto:
            erros.append("Alfabeto Σ está vazio.")
        if not self.estados:
            erros.append("Conjunto de estados Q está vazio.")
        if self.inicial not in self.estados:
            erros.append(f"Estado inicial '{self.inicial}' não pertence a Q.")
        if not self.finais.issubset(self.estados):
            erros.append("Conjunto de finais F contém estados que não pertencem a Q.")

        for (q, a), q2 in self.delta.items():
            if q not in self.estados:
                erros.append(f"Transição usa estado origem inválido: '{q}'.")
            if a not in self.alfabeto:
                erros.append(f"Transição usa símbolo fora do alfabeto: '{a}'.")
            if q2 not in self.estados:
                erros.append(f"Transição aponta para estado inválido: '{q2}'.")
        return erros

    def eh_total(self) -> bool:
        for q in self.estados:
            for a in self.alfabeto:
                if (q, a) not in self.delta:
                    return False
        return True

    def transicoes_faltantes(self) -> List[Tuple[Estado, Simbolo]]:
        faltando: List[Tuple[Estado, Simbolo]] = []
        for q in self.estados:
            for a in self.alfabeto:
                if (q, a) not in self.delta:
                    faltando.append((q, a))
        return faltando

#EXECUTA A AFD (FAZ LEITURA DA PALAVRA)
@dataclass
class ExecucaoMEF:
    afd: AFD

    def executar_palavra(self, w: str, verbose: bool = True) -> bool:
        fita = list(w)
        estado_controle = self.afd.inicial

        if verbose:
            print("\n=== MEF: INÍCIO DA EXECUÇÃO ===")
            print(f"Entrada (w): {w!r}")
            print(f"Fita: {fita}")
            print(f"Estado inicial (q0): {estado_controle}")
            print(f"Finais (F): {sorted(self.afd.finais)}")
            print("================================\n")

        for i, simbolo in enumerate(fita):
            if simbolo not in self.afd.alfabeto:
                if verbose:
                    print(f"[PASSO {i}] Símbolo '{simbolo}' NÃO pertence a Σ. Rejeita ❌")
                return False

            chave = (estado_controle, simbolo)
            if chave not in self.afd.delta:
                if verbose:
                    print(f"[PASSO {i}] Não existe δ({estado_controle}, '{simbolo}'). Rejeita ❌")
                return False

            proximo_estado = self.afd.delta[chave]
            if verbose:
                print(f"[PASSO {i}] Estado atual (UC): {estado_controle}")
                print(f"          Lê símbolo: '{simbolo}'")
                print(f"          δ({estado_controle}, '{simbolo}') = {proximo_estado}")
                print(f"          Próximo estado -> {proximo_estado}\n")

            estado_controle = proximo_estado

        aceitou = estado_controle in self.afd.finais
        if verbose:
            print("=== MEF: FIM DA EXECUÇÃO ===")
            print(f"Estado final alcançado: {estado_controle}")
            print(f"Resultado: {'ACEITA ✅' if aceitou else 'REJEITA ❌'}")
            print("============================\n")
            print("\n")
            print("\n")
        return aceitou


# ============================================================
# Visualização: rótulos S0,S1,... para estados compostos
# ============================================================

def _parse_conjunto_estado(nome: str) -> List[str]:
    """
    Converte "{q0,q1}" -> ["q0","q1"], "{}" -> []
    Se não estiver no formato, retorna [nome].
    """
    nome = nome.strip()
    if nome == "{}":
        return []
    if nome.startswith("{") and nome.endswith("}"):
        conteudo = nome[1:-1].strip()
        if not conteudo:
            return []
        return [x.strip() for x in conteudo.split(",") if x.strip()]
    return [nome]


def imprimir_legenda_rotulos(rotulos: Dict[Estado, str]) -> None:
    """
    Exibe legenda Sx = { ... } e marca se é simples/composto.
    rotulos: dict {nome_estado_original -> "Sx"}
    """
    # ordenar por índice numérico do S
    def idx(s: str) -> int:
        try:
            return int(s[1:])
        except Exception:
            return 10**9

    print("Legenda (no AFD, cada Sx é UM ÚNICO estado):")
    for nome_estado, rot in sorted(rotulos.items(), key=lambda kv: idx(kv[1])):
        elems = _parse_conjunto_estado(nome_estado)
        tipo = "composto" if len(elems) >= 2 else "simples"
        print(f"  {rot} ({tipo}) = {nome_estado}")
    print()



# IMPRIME AFD MINIMIZADO
def exibe_afd_minimizado_pretty(afd: AFD, legenda_blocos: Dict[str, List[str]]) -> None:
    print("\n--- AFD MINIMIZADO ---")
    simbolos = sorted(afd.alfabeto)
    estados = sorted(afd.estados)

    for q in estados:
        prefixo = ""
        if q == afd.inicial:
            prefixo += "->"
        if q in afd.finais:
            prefixo += "*"

        linha = f"{prefixo}{q:<10} | "
        for a in simbolos:
            linha += f"{a}: {afd.delta[(q, a)]} "
        print(linha)

    print("\nLegenda (blocos da minimização):")
    for g in sorted(legenda_blocos.keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else x):
        print(f"{g} = {legenda_blocos[g]}")


# IMPRIME RESUMO DO AFD ATUAL
def exibe_resumo_afd(afd: AFD) -> None:
    """
    Exibe o AFD. Se os estados forem no formato "{...}", renomeia visualmente para S0,S1,...
    Mantém o estado inicial como S0 e imprime uma legenda.
    """
    print("\n=== RESUMO DO AFD ===")
    print(f"Σ (alfabeto): {sorted(afd.alfabeto)}")

    # Detecta se parece AFD vindo de AFND->AFD (estados com chaves)
    parece_conjunto = any(st.startswith("{") and st.endswith("}") for st in afd.estados)

    if parece_conjunto:
        # Ordenação: inicial primeiro; depois por tamanho do conjunto; "{}" por último
        def chave_ordem(nome: str):
            if nome == "{}":
                return (10**9, nome)
            return (len(_parse_conjunto_estado(nome)), nome)

        estados_ordenados = sorted(afd.estados, key=chave_ordem)
        if afd.inicial in estados_ordenados:
            estados_ordenados.remove(afd.inicial)
            estados_ordenados = [afd.inicial] + estados_ordenados

        rotulos: Dict[Estado, str] = {}
        for i, nome in enumerate(estados_ordenados):
            rotulos[nome] = f"S{i}"

        print(f"Q (estados): {[rotulos[e] for e in estados_ordenados]}")
        print(f"q0 (inicial): {rotulos[afd.inicial]}")
        print(f"F (finais): {sorted(rotulos[f] for f in afd.finais)}")
        print()
        imprimir_legenda_rotulos(rotulos)

        simbolos = sorted(afd.alfabeto)

        cabecalho = "Estado  "
        for s in simbolos:
            cabecalho += f"|  {s}  "
        print(cabecalho)
        print("-" * len(cabecalho))

        for q in estados_ordenados:
            linha = f"{rotulos[q]:<7}"
            for s in simbolos:
                prox = afd.delta.get((q, s), "-")
                prox_str = rotulos.get(prox, prox) if prox != "-" else "-"
                linha += f"| {prox_str:<4}"
            print(linha)

        print("=====================\n")
        print("\n")
        print("\n")
        return

    # AFD "normal" (estados simples)
    estados = [afd.inicial] + sorted(afd.estados - {afd.inicial})
    print(f"Q (estados): {estados}")
    print(f"q0 (inicial): {afd.inicial}")
    print(f"F (finais): {sorted(afd.finais)}")
    print()

    simbolos = sorted(afd.alfabeto)

    cabecalho = "Estado  "
    for s in simbolos:
        cabecalho += f"|  {s}  "
    print(cabecalho)
    print("-" * len(cabecalho))

    for q in estados:
        linha = f"{q:<7}"
        for s in simbolos:
            proximo_estado = afd.delta.get((q, s), "-")
            linha += f"| {proximo_estado:<4}"
        print(linha)

    print("=====================\n")
    print("\n")
    print("\n")

# ============================================================
# AFND -> AFD
# ============================================================

DeltaAFN = Dict[Tuple[Estado, Simbolo], Set[Estado]]
EPS = "eps"


@dataclass(frozen=True)
class AFN:
    alfabeto: Set[Simbolo]
    estados: Set[Estado]
    delta: DeltaAFN
    inicial: Estado
    finais: Set[Estado]
    usa_epsilon: bool = False

    def validar_estrutura(self) -> List[str]:
        erros: List[str] = []
        if self.inicial not in self.estados:
            erros.append(f"Estado inicial '{self.inicial}' não pertence a Q.")
        if not self.finais.issubset(self.estados):
            erros.append("Conjunto de finais F contém estados que não pertencem a Q.")
        for (q, a), destinos in self.delta.items():
            if q not in self.estados:
                erros.append(f"Transição usa estado origem inválido: '{q}'.")
            if a != EPS and a not in self.alfabeto:
                erros.append(f"Transição usa símbolo fora do alfabeto: '{a}'.")
            for d in destinos:
                if d not in self.estados:
                    erros.append(f"Transição aponta para estado inválido: '{d}'.")
        return erros


# DEFINIÇAO DE AFND PELO USUARIO
def criar_afn_do_usuario() -> AFN:
    print("\n==============================")
    print("  DEFINIÇÃO DE UM AFND (NFA)")
    print("==============================")

    alfabeto = solicitar_conjunto_csv("Digite o alfabeto Σ (vírgulas). Ex: a,b: ")
    estados = solicitar_conjunto_csv("Digite os estados Q (vírgulas). Ex: q0,q1: ")
    inicial = solicitar_escolha("Digite o estado inicial q0", estados)

    finais_raw = solicitar_conjunto_csv("Digite os estados finais F (vírgulas). Ex: q1: ")
    finais = {f for f in finais_raw if f in estados}
    if finais_raw and not finais:
        print("⚠️  Você informou finais, mas nenhum estava em Q. (F ficou vazio)")

    usa_eps = solicitar_sim_nao("Seu AFND usa transições ε (epsilon)? (use 'eps')")

    print("\nAgora vamos definir δ do AFND.")
    print("Para cada (q, símbolo), você pode informar VÁRIOS destinos separados por vírgula.")
    if usa_eps:
        print("Para ε, você também definirá destinos para o símbolo especial: eps")
    print("Se não houver transição, basta digitar: - (hífen)\n")

    delta: DeltaAFN = {}

    simbolos = sorted(alfabeto) + ([EPS] if usa_eps else [])
    for q in sorted(estados):
        for a in simbolos:
            raw = solicitar_nao_vazio(f"δ({q}, '{a}') = (destinos por vírgula ou '-' ) ")
            if raw.strip() == "-":
                continue
            destinos = parsear_conjunto_csv(raw)
            destinos = {d for d in destinos if d in estados}
            if destinos:
                delta[(q, a)] = destinos
            else:
                print("⚠️  Nenhum destino válido em Q; essa transição será ignorada.")

    afn = AFN(
        alfabeto=alfabeto,
        estados=estados,
        delta=delta,
        inicial=inicial,
        finais=finais,
        usa_epsilon=usa_eps,
    )
    errs = afn.validar_estrutura()
    if errs:
        print("\n❌ Erros na definição do AFND:")
        for e in errs:
            print(" -", e)
        print("➡️  Você pode redefinir pelo menu.")
    else:
        print("\n✅ AFND definido com sucesso!")
    return afn


def fecho_epsilon(afn: AFN, estados_iniciais: Set[Estado]) -> Set[Estado]:
    if not afn.usa_epsilon:
        return set(estados_iniciais)

    pilha = list(estados_iniciais)
    fechado = set(estados_iniciais)
    while pilha:
        q = pilha.pop()
        destinos = afn.delta.get((q, EPS), set())
        for d in destinos:
            if d not in fechado:
                fechado.add(d)
                pilha.append(d)
    return fechado


def mover(afn: AFN, estados: Set[Estado], simbolo: Simbolo) -> Set[Estado]:
    saida: Set[Estado] = set()
    for q in estados:
        saida |= afn.delta.get((q, simbolo), set())
    return saida


def nome_subconjunto(conjunto_estados: FrozenSet[Estado]) -> str:
    if not conjunto_estados:
        return "{}"
    return "{" + ",".join(sorted(conjunto_estados)) + "}"



# CONVERSAO AFND PARA AFD
def afn_para_afd(afn: AFN, verbose: bool = True) -> AFD:
    """
    Conversão AFND -> AFD por subconjuntos.
    Durante a conversão, exibe S0,S1,... como rótulos visuais.
    Internamente, o AFD final usa estados como "{q0,q1}", "{}" etc.

    """
    if verbose:
        print("\n=== AFND → AFD: CONSTRUÇÃO POR SUBCONJUNTOS ===")

    # estado inicial do AFD é fecho-epsilon({q0})
    inicio_set = fecho_epsilon(afn, {afn.inicial})
    inicio_fs: FrozenSet[Estado] = frozenset(inicio_set)

    descobertos: Set[FrozenSet[Estado]] = {inicio_fs}
    fila: List[FrozenSet[Estado]] = [inicio_fs]

    delta_afd: Dict[Tuple[str, Simbolo], str] = {}
    finais_afd: Set[str] = set()

    # INSERE Rótulos S0,S1,... para exibição durante a conversão
    rotulo_por_fs: Dict[FrozenSet[Estado], str] = {}
    contador = 0

    def rotulo(fs: FrozenSet[Estado]) -> str:
        nonlocal contador
        if fs not in rotulo_por_fs:
            rotulo_por_fs[fs] = f"S{contador}"
            contador += 1
        return rotulo_por_fs[fs]

    rotulo(inicio_fs)  # garante S0

    while fila:
        T = fila.pop(0)
        T_nome = nome_subconjunto(T)
        T_rot = rotulo(T)

        if verbose:
            print(f"\nProcessando estado AFD T = {T_rot} = {T_nome}")

        # final do AFD se contém algum final do AFND
        if any(q in afn.finais for q in T):
            finais_afd.add(T_nome)

        for a in sorted(afn.alfabeto):
            U = mover(afn, set(T), a)
            U = fecho_epsilon(afn, U)
            U_fs = frozenset(U)

            U_nome = nome_subconjunto(U_fs)
            U_rot = rotulo(U_fs)

            if verbose:
                print(f"  Para símbolo '{a}': move(T,'{a}') -> {sorted(U)} => {U_rot} = {U_nome}")

            delta_afd[(T_nome, a)] = U_nome

            if U_fs not in descobertos:
                descobertos.add(U_fs)
                fila.append(U_fs)
                if verbose:
                    print(f"    Novo estado do AFD descoberto: {U_rot} = {U_nome}")

    estados_afd = {nome_subconjunto(fs) for fs in descobertos}

    afd = AFD(
        alfabeto=set(afn.alfabeto),
        estados=estados_afd,
        delta=delta_afd,
        inicial=nome_subconjunto(inicio_fs),
        finais=finais_afd,
    )

    if verbose:
        print("\n=== FIM DA CONVERSÃO AFND→AFD ===")
        print("\n")
        exibe_resumo_afd(afd)

        # legenda adicional (Sx -> {...}) conforme a conversão ocorreu
        # (ordena por S0,S1,...)
        def idx(s: str) -> int:
            try:
                return int(s[1:])
            except Exception:
                return 10**9

        print("Legenda da conversão (ordem de descoberta):")
        for fs, r in sorted(rotulo_por_fs.items(), key=lambda kv: idx(kv[1])):
            print(f"  {r} = {nome_subconjunto(fs)}")
        print()

    return afd


# IMPRIME RESUMO DO AFND ATUAL
def exibe_resumo_afn(afn: AFN) -> None:
    print("\n=== RESUMO DO AFND ===")
    print(f"Σ (alfabeto): {sorted(afn.alfabeto)}")
    print(f"Q (estados): {sorted(afn.estados)}")
    print(f"q0 (inicial): {afn.inicial}")
    print(f"F (finais): {sorted(afn.finais)}")
    print()

    simbolos = sorted(afn.alfabeto)
    if afn.usa_epsilon:
        simbolos = simbolos + [EPS]

    estados = sorted(afn.estados)

    cabecalho = "Estado  "
    for s in simbolos:
        cabecalho += f"| {s:^10} "
    print(cabecalho)
    print("-" * len(cabecalho))

    for q in estados:
        linha = f"{q:<7}"
        for s in simbolos:
            destinos = afn.delta.get((q, s), set())
            if not destinos:
                celula = "-"
            else:
                celula = "{" + ",".join(sorted(destinos)) + "}"
            linha += f"| {celula:<10} "
        print(linha)

    print("======================\n")
    print("\n")


# ============================================================
# INICIO MINIMIZAÇÃO DO AFD
# ============================================================

def estados_alcancaveis(afd: AFD) -> Set[Estado]:
    visitados = {afd.inicial}
    pilha = [afd.inicial]
    while pilha:
        q = pilha.pop()
        for a in afd.alfabeto:
            q2 = afd.delta.get((q, a))
            if q2 is not None and q2 not in visitados:
                visitados.add(q2)
                pilha.append(q2)
    return visitados

#TORNANDO AFD TOTAL = SIMBOLO ARTIFICIAL A
def tornar_total_com_sumidouro(afd: AFD, nome_sumidouro: str = "A") -> AFD:
    estados = set(afd.estados)
    delta = dict(afd.delta)
    finais = set(afd.finais)
    alfabeto = set(afd.alfabeto)

    precisa_sumidouro = False
    for q in list(estados):
        for a in alfabeto:
            if (q, a) not in delta:
                precisa_sumidouro = True

    if not precisa_sumidouro:
        return afd

    base = nome_sumidouro
    i = 0
    while nome_sumidouro in estados:
        i += 1
        nome_sumidouro = f"{base}{i}"

    estados.add(nome_sumidouro)

    for a in alfabeto:
        delta[(nome_sumidouro, a)] = nome_sumidouro

    for q in list(estados):
        for a in alfabeto:
            if (q, a) not in delta:
                delta[(q, a)] = nome_sumidouro

    return AFD(alfabeto=alfabeto, estados=estados, delta=delta, inicial=afd.inicial, finais=finais)


def remover_inalcancaveis(afd: AFD) -> AFD:
    alc = estados_alcancaveis(afd)
    delta2: FuncaoTransicao = {}
    for (q, a), q2 in afd.delta.items():
        if q in alc and q2 in alc:
            delta2[(q, a)] = q2
    finais2 = set(afd.finais) & alc
    return AFD(alfabeto=set(afd.alfabeto), estados=alc, delta=delta2, inicial=afd.inicial, finais=finais2)


def minimizar_afd(afd: AFD, verbose: bool = True) -> AFD:
    if verbose:
        print("\n=== MINIMIZAÇÃO DE AFD ===")
        print("Passo 1) Remover estados inalcançáveis...")
    afd1 = remover_inalcancaveis(afd)

    if verbose:
        print(f"  Estados alcançáveis: {sorted(afd1.estados)}")

    if verbose:
        print("Passo 2) Garantir δ total (estado artificial/sink se necessário)...")
    afd2 = tornar_total_com_sumidouro(afd1, nome_sumidouro="A")

    if verbose:
        print(f"  δ total? {'SIM' if afd2.eh_total() else 'NÃO'}")
        if not afd2.eh_total():
            print("  Faltantes:", afd2.transicoes_faltantes())

    Q = set(afd2.estados)
    F = set(afd2.finais)
    naoF = Q - F

    P: List[Set[Estado]] = []
    if F:
        P.append(set(F))
    if naoF:
        P.append(set(naoF))

    if verbose:
        print("Passo 3) Partições iniciais:")
        for i, bloco in enumerate(P, start=1):
            print(f"  B{i} = {sorted(bloco)}")

    def indice_bloco_de(estado: Estado, particoes: List[Set[Estado]]) -> int:
        for i, b in enumerate(particoes):
            if estado in b:
                return i
        raise RuntimeError(f"Estado {estado} não encontrado em partições.")

    mudou = True
    iteracao = 0

    if verbose:
        print("\nPasso 4) Refinamento de partições...")
        print("Ideia: estados permanecem no mesmo bloco somente se")
        print("      tiverem o MESMO comportamento para todos os símbolos.\n")

    while mudou:
        mudou = False
        iteracao += 1
        novaP: List[Set[Estado]] = []

        if verbose:
            print(f"\n==============================")
            print(f"Iteração {iteracao}")
            print(f"==============================\n")

        for bloco in P:

            if verbose:
                print(f"Analisando bloco: {sorted(bloco)}")
                print("Comparando comportamento dos estados:\n")

            grupos: Dict[Tuple[int, ...], Set[Estado]] = {}

            for q in bloco:
                destinos_descritos = []
                assinatura = []

                for a in sorted(afd2.alfabeto):
                    destino = afd2.delta[(q, a)]
                    indice_bloco = indice_bloco_de(destino, P)
                    assinatura.append(indice_bloco)

                    destinos_descritos.append(
                        f"  com '{a}' → {destino} (está no bloco {indice_bloco})"
                    )

                assinatura = tuple(assinatura)

                if verbose:
                    print(f"Estado {q}:")
                    for linha in destinos_descritos:
                        print(linha)
                    print()

                grupos.setdefault(assinatura, set()).add(q)

            if len(grupos) == 1:
                novaP.append(bloco)
                if verbose:
                    print("→ Todos os estados deste bloco têm comportamento equivalente.")
                    print("  Bloco permanece unido.\n")
            else:
                mudou = True
                if verbose:
                    print("→ Estados possuem comportamentos diferentes.")
                    print("  Bloco será dividido em:\n")

                for i, (sig, g) in enumerate(grupos.items(), start=1):
                    novaP.append(g)
                    if verbose:
                        print(f"  Sub-bloco {i}: {sorted(g)}")
                    print()

            print("--------------------------------------------------\n")

        P = novaP

    if verbose:
        print("\nPasso 5) Montar AFD mínimo a partir das partições finais...")
        for i, bloco in enumerate(P, start=1):
            print(f"  C{i} = {sorted(bloco)}")

    # --- Nomes curtos para os blocos na minimização ---
    # Ordena os blocos para tornar a numeração estável/reprodutível
    blocos_ordenados = sorted(P, key=lambda b: (len(b), sorted(b)))

    nome_por_bloco: Dict[frozenset, Estado] = {}
    for i, bloco in enumerate(blocos_ordenados):
        nome_por_bloco[frozenset(bloco)] = f"P{i}"

    def nome_bloco(bloco: Set[Estado]) -> Estado:
        return nome_por_bloco[frozenset(bloco)]

    bloco_de: Dict[Estado, Set[Estado]] = {}
    for bloco in P:
        for q in bloco:
            bloco_de[q] = bloco

    novos_estados = {nome_bloco(b) for b in P}
    novo_inicial = nome_bloco(bloco_de[afd2.inicial])
    novos_finais = {nome_bloco(bloco_de[q]) for q in afd2.finais}

    novo_delta: FuncaoTransicao = {}
    for bloco in P:
        rep = next(iter(bloco))  # representante do bloco
        de_nome = nome_bloco(bloco)
        for a in afd2.alfabeto:
            para_estado = afd2.delta[(rep, a)]
            para_bloco = bloco_de[para_estado]
            novo_delta[(de_nome, a)] = nome_bloco(para_bloco)

    # (Opcional) legenda Gx -> estados originais do bloco
    legenda_blocos = {nome_bloco(bloco): sorted(bloco) for bloco in P}

    minimizado = AFD(
        alfabeto=set(afd2.alfabeto),
        estados=novos_estados,
        delta=novo_delta,
        inicial=novo_inicial,
        finais=novos_finais,
    )

    if verbose:
        print("\n✅ AFD minimizado:")
        exibe_afd_minimizado_pretty(minimizado, legenda_blocos)
        print("\n")
    return minimizado


# DEFINICAO DE AFD PELO USUARIO
def criar_afd_do_usuario() -> AFD:
    print("\n==============================")
    print("  DEFINIÇÃO DE UM AFD (M = Σ,Q,δ,q0,F)")
    print("==============================")

    alfabeto = solicitar_conjunto_csv("Digite o alfabeto Σ (vírgulas). Ex: a,b: ")
    estados = solicitar_conjunto_csv("Digite os estados Q (vírgulas). Ex: q0,q1: ")
    inicial = solicitar_escolha("Digite o estado inicial q0", estados)

    finais_raw = solicitar_conjunto_csv("Digite os estados finais F (vírgulas). Ex: q1: ")
    finais = {f for f in finais_raw if f in estados}
    if finais_raw and not finais:
        print("⚠️  Você informou finais, mas nenhum estava em Q. (F ficou vazio)")

    print("\nDefinindo δ(q,a) para TODO q∈Q e a∈Σ (AFD total).")
    delta: FuncaoTransicao = {}
    for q in sorted(estados):
        for a in sorted(alfabeto):
            prox = solicitar_escolha(f"δ({q}, '{a}') =", estados)
            delta[(q, a)] = prox

    afd = AFD(alfabeto=alfabeto, estados=estados, delta=delta, inicial=inicial, finais=finais)
    errs = afd.validar_estrutura()
    if errs:
        print("\n❌ Erros na definição do AFD:")
        for e in errs:
            print(" -", e)
        print("➡️  Você pode redefinir pelo menu.")
    else:
        print("\n✅ AFD definido com sucesso!")
    return afd


# ============================================================
# Menu principal
# ============================================================

def principal():
    afd: Optional[AFD] = None
    afn: Optional[AFN] = None
    afd_do_afn: Optional[AFD] = None
    afd_min: Optional[AFD] = None

    while True:
        print("============== MENU ==============")
        print("AFD")
        print("  1) Definir novo AFD (via console)")
        print("  2) Mostrar resumo do AFD atual")
        print("  3) Validar palavra no AFD (MEF)")
        print("")
        print("AFND → AFD")
        print("  4) Definir novo AFND (via console)")
        print("  5) Mostrar resumo do AFND atual")
        print("  6) Converter AFND → AFD (subconjuntos)")
        print("  7) Validar palavra no AFD convertido (MEF)")
        print("  8) Usar AFD convertido como AFD atual")
        print("")
        print("Minimização")
        print("  9) Minimizar AFD atual")
        print(" 10) Validar palavra no AFD minimizado (MEF)")
        print("")
        print(" 11) Sair")
        print("==================================")

        escolha = solicitar_nao_vazio("Escolha uma opção: ")

        # -------- AFD --------
        if escolha == "1":
            afd = criar_afd_do_usuario()
            afd_min = None

        elif escolha == "2":
            if afd is None:
                print("⚠️  Nenhum AFD definido.")
            else:
                exibe_resumo_afd(afd)

        elif escolha == "3":
            if afd is None:
                print("⚠️  Nenhum AFD definido.")
                continue
            mef = ExecucaoMEF(afd)
            print("\nDigite palavras para testar. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.executar_palavra(w, verbose=True)

        # -------- AFND → AFD --------
        elif escolha == "4":
            afn = criar_afn_do_usuario()
            afd_do_afn = None

        elif escolha == "5":
            if afn is None:
                print("⚠️  Nenhum AFND definido.")
            else:
                exibe_resumo_afn(afn)

        elif escolha == "6":
            if afn is None:
                print("⚠️  Nenhum AFND definido. Use a opção 4 primeiro.")
                continue
            afd_do_afn = afn_para_afd(afn, verbose=True)

        elif escolha == "7":
            if afd_do_afn is None:
                print("⚠️  Você ainda não converteu AFND→AFD (use opção 6).")
                continue
            mef = ExecucaoMEF(afd_do_afn)
            print("\nDigite palavras para testar no AFD convertido. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.executar_palavra(w, verbose=True)

        elif escolha == "8":
            if afd_do_afn is None:
                print("⚠️  Ainda não existe AFD convertido (use opção 6).")
                continue
            afd = afd_do_afn
            afd_min = None
            print("✅ AFD atual agora é o AFD convertido do AFND.")
            print("   (Agora você pode usar a opção 9 para minimizar.)")

        # -------- Minimização --------
        elif escolha == "9":
            if afd is None:
                print("⚠️  Nenhum AFD definido.")
                continue
            afd_min = minimizar_afd(afd, verbose=True)

        elif escolha == "10":
            if afd_min is None:
                print("⚠️  Nenhum AFD minimizado ainda (use opção 9).")
                continue
            mef = ExecucaoMEF(afd_min)
            print("\nDigite palavras para testar no AFD minimizado. (Enter vazio volta)")
            while True:
                w = input("w = ").strip()
                if w == "":
                    break
                mef.executar_palavra(w, verbose=True)

        elif escolha == "11":
            print("Saindo... 👋")
            break

        else:
            print("⚠️  Opção inválida.")


if __name__ == "__main__":
    principal()
