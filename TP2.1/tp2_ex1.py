import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Trabalho Prático 2 — Exercício 1
    ## *Game of Life* como máquina de estados finita

    ### Problema

    Modelar uma versão finita do *Game of Life* de Conway: uma grelha
    $N \times N$ ($N > 16$) de células normais, rodeada por uma borda de células
    constantes (aleatórias em cima e à esquerda, mortas em baixo e à direita),
    que evolui segundo a regra **B3/S23**.

    Pretende-se:

    1. construir uma **FSM** do autómato, com transições **síncronas** (todas as
       células mudam ao mesmo tempo) ou **assíncronas** (uma célula de cada vez);
    2. provar, ou obter contra-exemplos para:
        - **P1** — nunca se alcança o estado de erro (todas as células mortas);
        - **P2** — nenhuma célula fica permanentemente morta ou viva.

    ### Abordagem

    O autómato é modelado como um sistema de transição (como os FOTS das aulas),
    com o estado representado por variáveis booleanas do **Z3** e os predicados
    `init` e `trans`. A P1 é verificada com *bounded model checking* e
    *k-indução*; a P2 com *bounded model checking* com ciclo (*lasso*).
    """)
    return


@app.cell
def _():
    import marimo as mo
    from z3 import Bool, BoolVal, And, Or, Not, If, Sum, Solver, sat, unsat, is_true
    import random
    import time

    return (
        And,
        Bool,
        BoolVal,
        If,
        Not,
        Or,
        Solver,
        Sum,
        is_true,
        mo,
        random,
        sat,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Parâmetros

    - `N` — dimensão da grelha de células normais (o enunciado exige $N > 16$);
    - `SINCRONO` — escolhe a relação de transição, como pedido no enunciado:
      `True` para a síncrona, `False` para a assíncrona;
    - `SEED` — semente do gerador aleatório usado nas células iniciais, para que
      os resultados sejam **reprodutíveis**.
    """)
    return


@app.cell
def _():
    N = 17
    SINCRONO = True
    SEED = 42
    return N, SEED, SINCRONO


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Células iniciais e finais

    A grelha de células normais está rodeada por uma moldura de células com
    valores constantes:

    - **iniciais** — um dos índices é $0$ (e nenhum é $N+1$): $2N+1$ células,
      com valor sorteado com probabilidade $1/2$;
    - **finais** — as restantes com um índice igual a $N+1$: $2N+3$ células,
      sempre mortas.

    Estes valores são guardados na matriz `borda`, de dimensão $(N+2)\times(N+2)$,
    onde as posições das células normais ficam a `None`. Como nunca mudam, são
    usados no `declare` como constantes e não como variáveis do solver. A semente
    `SEED` garante que o sorteio é sempre o mesmo.
    """)
    return


@app.cell
def _(N, SEED, random):
    def gera_borda(N, seed):
        rng = random.Random(seed)
        borda = [[None] * (N + 2) for _ in range(N + 2)]
        for i in range(N + 2):
            for j in range(N + 2):
                if (i == 0 or j == 0) and i <= N and j <= N:
                    # célula inicial: 0 ou 1 sorteado com probabilidade 1/2
                    borda[i][j] = rng.randint(0, 1)
                elif i == N + 1 or j == N + 1:
                    # célula final: sempre morta
                    borda[i][j] = 0
                # caso contrário fica None: célula normal
        return borda

    borda = gera_borda(N, SEED) 
    return (borda,)


@app.cell
def _(N, borda):
    _normais = sum(1 for _l in borda for _v in _l if _v is None)
    _constantes = sum(1 for _l in borda for _v in _l if _v is not None)
    print("normais:", _normais, " esperado:", N * N)
    print("constantes:", _constantes, " esperado:", (2*N + 1) + (2*N + 3))

    for _linha in borda:
        print(" ".join("." if _v is None else str(_v) for _v in _linha))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Estado: células normais

    O estado do sistema é formado pelas $N^2$ células normais, cada uma
    representada por uma variável booleana do Z3 (viva = `True`, morta = `False`).

    Tal como na ficha 7, para descrever uma execução com vários passos precisamos
    de várias **cópias** das variáveis de estado: a função `declare(k)` cria a
    $k$-ésima cópia. Cada cópia é uma matriz $(N+2)\times(N+2)$: nas posições das
    células normais ficam variáveis `Bool`; nas das células iniciais e finais
    ficam as respetivas constantes `BoolVal`.
    """)
    return


@app.cell
def _(Bool, BoolVal, N, borda):
    #corre antes a função gera_borda, que cria a matriz borda em que as celulas normais são None e as celulas Iniciais/Finais são 0 ou 1

    def declare(k):  # cria o estado s no instante k (uma nova matriz s para cada k)
        s = [[None] * (N + 2) for _ in range(N + 2)]
        for i in range(N + 2):
            for j in range(N + 2):
                if borda[i][j] is None:
                    # célula normal: variável (ganham uma incógnita por célula e por instante),
                    # ainda sem valor — é o solver que lhe dá valor mais tarde, e fica a saber que vai ser do tipo BOOL
                    s[i][j] = Bool(f"c_{k}_{i}_{j}")
                else:
                    # célula inicial/final: constante, pois o seu valor nunca muda;
                    # o 0/1 vem do gera_borda (iniciais sorteadas, finais sempre 0)
                    # e o == 1 converte-o em True/False
                    s[i][j] = BoolVal(borda[i][j] == 1)
        return s

    return (declare,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Estado inicial e estado de erro

    - **Estado inicial** — todas as células normais estão mortas, exceto as que
      têm $i,j \le 3$, que estão vivas.
    - **Estado de erro** — todas as células normais estão mortas.

    Ambos são definidos como predicados sobre um estado $s$, que devolvem uma
    fórmula do Z3, tal como o `init` da ficha 7:

    $$init(s) \equiv \bigwedge_{i,j \le 3} s_{i,j} \;\wedge \bigwedge_{\text{restantes}} \neg s_{i,j}
    \qquad\qquad
    erro(s) \equiv \neg \bigvee_{i,j=1}^{N} s_{i,j}$$
    """)
    return


@app.cell
def _(And, N, Not, Or):
    def init(s):
        condicoes = []
        for i in range(1, N + 1):
            for j in range(1, N + 1):
                if i <= 3 and j <= 3:
                    condicoes.append(s[i][j])        # tem de estar viva
                else:
                    condicoes.append(Not(s[i][j]))   # tem de estar morta
        return And(condicoes)

    def erro(s):
        vivas = []
        for i in range(1, N + 1):
            for j in range(1, N + 1):
                vivas.append(s[i][j])
        return Not(Or(vivas))    #Or: "alguma está viva"; Not: "nenhuma está viva" (todas mortas)

    return erro, init


@app.cell
def _(Solver, declare, erro, init):
    _s = declare(0)
    _solver = Solver()
    _solver.add(init(_s))
    print("init é satisfazível:", _solver.check())   # esperado: sat
    _solver.add(erro(_s))
    print("init ∧ erro:", _solver.check())            # esperado: unsat
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Vizinhos e regra B3/S23

    Duas células são vizinhas sse $\max(|i_0-i_1|, |j_0-j_1|) = 1$, ou seja, cada
    célula tem 8 vizinhos (incluindo as diagonais). Graças às células iniciais e
    finais, todas as células normais têm os 8 vizinhos dentro da matriz.

    A regra **B3/S23** define o próximo valor de uma célula $c$ com $n$ vizinhos vivos:

    - **nasce** se está morta e $n = 3$;
    - **sobrevive** se está viva e $n \in \{2, 3\}$;
    - caso contrário fica (ou passa a) morta.
    """)
    return


@app.cell
def _(And, If, Not, Or, Sum):
    def vizinhos_vivos(s, i, j):
        # os 8 vizinhos da célula (i, j); a própria célula não conta
        vizinhos = [
            s[i-1][j-1], s[i-1][j], s[i-1][j+1],   # linha de cima
            s[i][j-1],              s[i][j+1],     # esquerda e direita
            s[i+1][j-1], s[i+1][j], s[i+1][j+1],   # linha de baixo
        ]
        # converte cada vizinho em 1 (vivo) ou 0 (morto) e soma
        numeros = []
        for v in vizinhos:
            numeros.append(If(v, 1, 0))
        return Sum(numeros)

    def regra_B3S23(s, i, j):
        viva = s[i][j]                    # a célula está viva agora?
        n = vizinhos_vivos(s, i, j)       # quantos vizinhos vivos tem?

        nasce = And(Not(viva), n == 3)            # B3: morta e com 3 vizinhos
        sobrevive = And(viva, Or(n == 2, n == 3)) # S23: viva e com 2 ou 3 vizinhos

        return Or(nasce, sobrevive)       # no próximo instante fica viva se nascer ou sobreviver

    return regra_B3S23, vizinhos_vivos


@app.cell
def _(Solver, declare, init, regra_B3S23, vizinhos_vivos):
    _s = declare(0)
    _solver = Solver()
    _solver.add(init(_s)) # exige que o estado _s seja o inicial, ou seja, quadrado 3×3 no canto, com 9 celulas vivas
    _solver.check()       # o solver procura valores que cumpram isso
    _m = _solver.model()  # o modelo: os valores que ele encontrou

    for (_i, _j) in [(2, 2), (3, 3), (4, 2), (2, 4), (10, 10)]:
        print((_i, _j),
              "| atual:", _m.eval(_s[_i][_j]),
              "| vizinhos vivos:", _m.eval(vizinhos_vivos(_s, _i, _j)),
              "| próximo:", _m.eval(regra_B3S23(_s, _i, _j)))

    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Transição síncrona

    Em cada transição **todas** as células normais transitam simultaneamente: o
    valor de cada célula no estado seguinte $t$ é dado pela regra B3/S23 aplicada
    ao estado atual $s$:

    $$trans_{sinc}(s, t) \equiv \bigwedge_{i,j=1}^{N} \big(t_{i,j} = regra(s, i, j)\big)$$

    Como cada célula tem um único valor seguinte possível, esta transição é
    **determinista**: cada estado tem exatamente um sucessor.
    """)
    return


@app.cell
def _(And, N, regra_B3S23):
    def trans_sincrono(s, t):
        condicoes = []
        for i in range(1, N + 1):
            for j in range(1, N + 1):
                # a célula (i,j) no estado seguinte tem o valor que a regra
                # calcula a partir do estado atual
                condicoes.append(t[i][j] == regra_B3S23(s, i, j))
        return And(condicoes)

    return (trans_sincrono,)


@app.cell
def _(N, borda, is_true):
    def mostra_estado(m, s):
        # desenha a grelha completa (N+2)x(N+2):
        #   células normais:         ■ viva   . morta
        #   células iniciais/finais: + viva   - morta
        linhas = []
        for i in range(N + 2):
            linha = ""
            for j in range(N + 2):
                if borda[i][j] is None:
                    # célula normal: o valor vem do modelo encontrado pelo solver
                    if is_true(m.eval(s[i][j])):
                        linha += "■ "
                    else:
                        linha += ". "
                else:
                    # célula inicial/final: o valor é a constante da borda
                    if borda[i][j] == 1:
                        linha += "+ "
                    else:
                        linha += "- "
            linhas.append(linha)
        return "\n".join(linhas)

    return (mostra_estado,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Transição assíncrona

    Em cada transição **uma e só uma** célula normal transita: existe uma célula
    $(a,b)$ que aplica a regra B3/S23, e todas as outras mantêm o seu valor:

    $$trans_{assinc}(s, t) \equiv \bigvee_{a,b=1}^{N} \Big( t_{a,b} = regra(s,a,b) \;\wedge
    \bigwedge_{(i,j) \neq (a,b)} t_{i,j} = s_{i,j} \Big)$$

    A escolha da célula é feita pelo solver, o que torna esta transição
    **não-determinista**: um estado pode ter vários sucessores.

    Interpretamos "transitar" como *aplicar a regra*: se a regra mantiver o valor
    da célula escolhida, o estado seguinte é igual ao atual. Assim todos os estados
    têm pelo menos um sucessor, como é habitual exigir num sistema de transição.
    """)
    return


@app.cell
def _(And, N, Or, regra_B3S23):
    def trans_assincrono(s, t):
        #lista todas as opções de celulas (a,b) que podem ser escolhidas
        opcoes = []
        for a in range(1, N + 1):
            for b in range(1, N + 1):
                #condicoes para a opcao escolhida
                condicoes = []
                for i in range(1, N + 1):
                    for j in range(1, N + 1):
                        if i == a and j == b:
                            # a célula escolhida aplica a regra
                            condicoes.append(t[i][j] == regra_B3S23(s, i, j))
                        else:
                            # todas as outras mantêm o valor
                            condicoes.append(t[i][j] == s[i][j])
                # juntas as condições: "(a,b) aplica a regra as outras ficam iguais"
                opcoes.append(And(condicoes))
        # basta que uma das opções se verifique, para o solver a escolher
        return Or(opcoes)

    return (trans_assincrono,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Seleção da relação de transição

    A função `trans` escolhe a relação de transição de acordo com o parâmetro
    `SINCRONO`, como pedido no enunciado: `True` para a transição síncrona,
    `False` para a assíncrona. As funções seguintes (traços e verificação das
    propriedades) usam sempre `trans`, pelo que basta mudar o parâmetro para
    trocar de interpretação.
    """)
    return


@app.cell
def _(SINCRONO, trans_assincrono, trans_sincrono):
    def trans(s, t):
        # escolhe a relação de transição de acordo com o parâmetro SINCRONO
        if SINCRONO:
            return trans_sincrono(s, t)     # todas as células transitam ao mesmo tempo
        else:
            return trans_assincrono(s, t)   # uma e só uma célula transita

    return (trans,)


@app.cell
def _(N, Solver, declare, init, is_true, mostra_estado, sat, trans):
    # Teste: gera um traço de execução com _K estados, a partir do estado inicial,
    # usando a transição escolhida pelo parâmetro SINCRONO

    _K = 4   # número de estados do traço
    _estados = [declare(k) for k in range(_K)]   # cria _K cópias do estado com o declare

    _solver = Solver()
    _solver.add(init(_estados[0]))   # o primeiro estado tem de ser o inicial

    # liga os estados uns aos outros com transições: se há _K estados existem _K-1 ligações
    for _k in range(_K - 1):
        _solver.add(trans(_estados[_k], _estados[_k + 1]))

    # pede ao solver valores para todas as incógnitas que cumpram as condições acima
    #check(), o solver procura valores para todas as incógnitas dos estados 1, 2 e 3 de forma a que todas as condições sejam verdadeiras
    if _solver.check() == sat:
        _m = _solver.model()   # o modelo: os valores encontrados 
        for _k in range(_K):
            print(f"Estado {_k}:")
            print(mostra_estado(_m, _estados[_k]))
            if _k > 0:
                # conta quantas células normais mudaram em relação ao estado anterior
                _mudaram = 0
                for _i in range(1, N + 1):
                    for _j in range(1, N + 1):
                        _agora = is_true(_m.eval(_estados[_k][_i][_j]))
                        _antes = is_true(_m.eval(_estados[_k - 1][_i][_j]))
                        if _agora != _antes:
                            _mudaram += 1
                print("células que mudaram:", _mudaram)
            print()
    else:
        # unsat: não existe nenhuma execução com _K estados
        print("Nenhum traço encontrado")
    return


if __name__ == "__main__":
    app.run()
