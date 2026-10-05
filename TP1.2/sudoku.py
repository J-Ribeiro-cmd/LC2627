# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.24.2",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import random

    return mo, random


@app.cell
def _(mo):
    mo.md(r"""
    # Trabalho Prático: Sudoku Genérico como CSP

    ## 1. Introdução

    Neste trabalho construímos um gerador/resolvedor de Sudoku $n^2 \times n^2$, com $n$ parametrizável ($n=3$ corresponde ao Sudoku clássico $9 \times 9$).

    O Sudoku é tratado como um **Problema de Satisfação de Restrições (CSP)**. A regra é sempre a mesma: um grupo de células tem de ter valores todos diferentes. O que muda entre linhas, colunas e blocos é apenas que células pertencem ao grupo. Por isso o trabalho assenta numa única abstração, a classe `box`, a partir da qual se constrói tudo o resto.

    Para resolver o CSP usamos o **CP-SAT** da biblioteca **Google OR-Tools**, por duas razões: permite ter uma variável inteira por célula, com valores em $[1, n^2]$, e já inclui a restrição "todos diferentes" (`AddAllDifferent`), que é exatamente a regra do Sudoku.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. `box`: grupo genérico de células (R1)

    A classe `box` representa um conjunto qualquer de células da grelha às quais se aplica a restrição "todos diferentes". Não sabe nada sobre linhas, colunas, blocos ou Sudoku.

    **Estrutura de dados.** As células são guardadas num dicionário `(linha, coluna) → valor`, em que `None` indica uma célula livre e um inteiro indica uma célula fixa a esse valor. Escolhemos um dicionário por duas razões. Primeiro, permite distinguir três casos: a célula não pertence ao grupo (a chave não existe), pertence e está livre (None), ou pertence e está fixa (um inteiro). Segundo, um grupo tem poucas células em relação à grelha toda (por exemplo, 9 em 81 quando $n=3$), e assim só guardamos as que pertencem ao grupo.

    A classe tem:

    - o construtor `box(celulas=None, n=3)`, que recebe opcionalmente um dicionário inicial de células e o $n$ da grelha. O $n$ é um parâmetro, com valor por omissão 3 (Sudoku clássico), para que nada fique fixo a $9 \times 9$;
    - o método `add(i, j, val=None)`, que acrescenta a célula $(i, j)$ ao grupo e levanta `ValueError` se as coordenadas estiverem fora da grelha ou o valor fora de $[1, n^2]$. Se a célula já existir no grupo, um valor novo substitui o anterior, mas acrescentá-la sem valor não altera o que lá estava;
    - o método `matriz()`, que devolve o grupo como matriz $n^2 \times n^2$, com zeros nas células que não pertencem ao grupo ou não estão fixas.
    """)
    return


@app.class_definition
#R1: Grupo genérico de celulas com a restrição "todos diferentes"

class box: # vai permitir criar vários grupos

    # Construtor: guarda o n e o dicionário (linha, coluna) -> valor ou None
    def __init__(self, celulas=None, n=3):
        self.n = n
        self.celulas = {}
        if celulas is not None:
            for (i,j) in celulas: #percorre as chaves do dicionario que são passadas
                self.add(i,j,celulas[(i,j)]) #adiciona o valor corresponde à chave

    # Add: Acrescenta a célula (i,j) ao grupo, depois de verificar as coordenadas e o valor
    def add(self, i, j, val=None):
        N = self.n * self.n
    
        #rejeita coordenadas fora da grelhas
        if i < 0 or i >= N or j < 0 or j >=N:
            raise ValueError("coordenadas fora da grelha")
        
        #rejeita valores fora do intervalo[1, n^2]
        if val is not None:
            if val < 1 or val > N:
                raise ValueError("valor fora do intervalo")

        #acrescentar uma célula sem valor, que já exista, não altera nada
        if val is None and (i,j) in self.celulas:
            return
            
        self.celulas[(i,j)] = val

    # Matriz: devolve o grupo como matriz n^2 x n^2 (0 = célula livre ou fora do grupo)
    def matriz(self):
        N = self.n * self.n

        #faz uma matriz só de zeros
        m = []
        for i in range(N):
            linha = []
            for j in range(N):
                linha.append(0)
            m.append(linha)

        #percorre as celulas do grupo, nas que têm valor fixo escreve esse valor
        for (i,j) in self.celulas:
            if self.celulas[(i,j)] is not None:
                m[i][j] = self.celulas[(i,j)]
        return m


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. `cube` e `path`: blocos, linhas e colunas (R2, R3)

    `cube` e `path` são duas especializações de `box`. Herdam os métodos `add` e `matriz` e só definem o construtor, que decide que células pertencem ao grupo. Todas as células são acrescentadas livres (sem valor fixo).

    - **`cube(i, j, n=3)`** representa o bloco $n \times n$ de índices $(i, j)$, com $0 \le i, j < n$, cujo canto superior esquerdo é a célula $(i \cdot n,\ j \cdot n)$.
    - **`path(inicio, fim, n=3)`** representa o troço reto, horizontal ou vertical, entre as células `inicio` e `fim`, inclusive. Funciona nos dois sentidos, porque o grupo é o mesmo conjunto de células quer se vá de `inicio` para `fim` quer ao contrário.

    Como as células são acrescentadas com o `add` do `box`, a verificação das coordenadas é reaproveitada: um bloco ou um troço fora da grelha levanta `ValueError`.
    """)
    return


@app.cell
def _():
    # R2: bloco n x n cujo canto superior esquerdo é a célula (i*n, j*n)
    class cube(box):

        # Construtor: cria um grupo vazio e acrescenta as n*n células do bloco (i, j)
        def __init__(self, i, j, n=3): #i e j indices do bloco(linha e coluna do bloco)
            super().__init__(None,n) #cria o grupo vazio
            for a in range(n):
                for b in range(n):
                    self.add(i * n + a, j * n + b)


    # R3: troço reto (horizontal ou vertical) entre as células inicio e fim, inclusive
    class path(box):

        # Construtor: cria um grupo vazio e acrescenta as células entre inicio e fim
        def __init__(self, inicio, fim, n=3):
            super().__init__(None,n)
            (i1, j1) = inicio
            (i2, j2) = fim

            # troço horizontal: mesma linha, percorre as colunas
            if i1 == i2:
                for j in range(min(j1, j2), max(j1, j2) + 1):
                    self.add(i1, j)

            # troço vertical: mesma coluna, percorre as linhas
            elif j1 == j2:
                for i in range(min(i1, i2), max(i1, i2) + 1):
                    self.add(i, j1)

            # rejeita troços que não são retos
            else:
                raise ValueError("inicio e fim não estão na mesma linha nem na mesma coluna")

    return cube, path


@app.cell
def _(cube, path):
    # Exemplos de utilização de box, cube e path/ Gerado por LLM

    # box: uma célula fixa a 5 não perde o valor se for acrescentada outra vez sem valor
    _b = box()
    _b.add(0, 0, 5)
    _b.add(0, 0)
    print(_b.celulas)

    # cube: bloco do meio de um Sudoku 9x9 (linhas 3 a 5, colunas 3 a 5)
    print(cube(1, 1).celulas)

    # path: linha 0 inteira, dada do fim para o início
    print(path((0, 8), (0, 0)).celulas)

    # cube com n=2: bloco de baixo à esquerda de uma grelha 4x4
    print(cube(1, 0, n=2).celulas)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Geração aleatória de pistas (R4)

    A função `pistas(k=None, n=3)` devolve um `box` com $k$ células escolhidas aleatoriamente na grelha, cada uma fixa a um valor aleatório em $[1, n^2]$. Não foi precisa nenhuma classe nova: o resultado é apenas um `box`, preenchido com o `add`.

    - Se $k$ não for dado, usa-se $k = n$ (3 pistas no Sudoku clássico).
    - Se $k$ for negativo ou maior do que o número de células da grelha, a função levanta `ValueError`.
    - As células são sorteadas com `random.sample` sobre a lista de todas as células da grelha, o que garante $k$ células diferentes.
    - O valor de cada célula é sorteado com `random.randint`, de forma independente das outras, por isso podem se repetir.

    Como os valores são sorteados de forma independente, duas pistas podem ficar com o mesmo valor. O modelo trata o grupo das pistas como qualquer outro grupo (todos diferentes), por isso nesse caso o puzzle fica impossível. Essa situação é tratada na secção 5(R5,R6).
    "\"\")
    """)
    return


@app.cell
def _(random):
    # R4: devolve um box com k células escolhidas ao acaso, cada uma fixa a um valor ao acaso
    def pistas(k=None, n=3):
        # tamanho da grelha
        N = n*n

        # se o k não for dado, fica igual a n
        if k is None:
            k = n
        # rejeita um k negativo ou maior do que o número de células
        if k < 0 or k > N * N:
            raise ValueError("k tem de estar entre 0 e o número de células da grelha")
        
        # lista com todas as células (i, j) da grelha
        lista = []
        for i in range(N):
            for j in range(N):
                lista.append((i,j))

        # sorteia k células diferentes dessa lista
        escolhidas = random.sample(lista, k)

        # cria um grupo vazio com este n
        grupo = box(n=n)

        # acrescenta cada célula sorteada ao grupo, com um valor ao acaso entre 1 e N
        for (i,j) in escolhidas:
            grupo.add(i, j, random.randint(1, N))

        # devolve o grupo
        return grupo

    return (pistas,)


@app.cell
def _(pistas):
    # Exemplo: 3 pistas aleatórias numa grelha 9x9
    _g = pistas()
    print(_g.celulas)
    for _linha in _g.matriz():
        print(_linha)
    return


if __name__ == "__main__":
    app.run()
