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

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Trabalho Prático: Sudoku Genérico como CSP

    ## 1. Introdução

    Neste trabalho construímos um gerador/resolvedor de Sudoku $n^2 \times n^2$, com $n$ parametrizável ($n=3$ corresponde ao Sudoku clássico $9 \times 9$).

    O Sudoku é tratado como um **Problema de Satisfação de Restrições (CSP)**. A regra é sempre a mesma: um grupo de células tem de ter valores todos diferentes. O que muda entre linhas, colunas e blocos é apenas que células pertencem ao grupo. Por isso o trabalho assenta numa única abstração, a classe `box`, a partir da qual se constrói tudo o resto.

    Para resolver o CSP usamos o **CP-SAT** da biblioteca **Google OR-Tools**, por duas razões: permite ter uma variável inteira por célula, com valores em $[1, n^2]$, e já inclui a restrição "todos diferentes" (`AddAllDifferent`), que é exatamente a regra do Sudoku.

    O notebook está organizado da seguinte forma:

    1. Introdução
    2. `box`: grupo genérico de células (**R1**)
    3. `cube` e `path`: blocos, linhas e colunas (**R2, R3**)
    4. Geração aleatória de pistas (**R4**)
    5. Modelo CSP e resolução (**R5, R6**)
    6. Testes e validação
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. `box`: grupo genérico de células (R1)

    A classe `box` representa um conjunto qualquer de células da grelha às quais se aplica a restrição "todos diferentes". Não sabe nada sobre linhas, colunas, blocos ou Sudoku.

    **Estrutura de dados.** As células são guardadas num dicionário `(linha, coluna) → valor`, em que `None` indica uma célula livre e um inteiro indica uma célula fixa a esse valor. Escolhemos um dicionário porque um grupo tem poucas células em relação à grelha toda, e assim só guardamos as que pertencem ao grupo.

    A classe tem:

    - o construtor `box(n, celulas=None)`, que recebe o $n$ da grelha e, opcionalmente, um dicionário inicial de células. O $n$ é passado ao construtor para que nada fique fixo a $9 \times 9$;
    - o método `add(i, j, val=None)`, que acrescenta a célula $(i, j)$ ao grupo e levanta `ValueError` se as coordenadas estiverem fora da grelha ou o valor fora de $[1, n^2]$;
    - o método `matriz()`, que devolve o grupo como matriz $n^2 \times n^2$, com zeros nas células que não pertencem ao grupo ou não estão fixas.
    """)
    return


@app.class_definition
#R1: Grupo genérico de celulas com a restrição "todos diferentes"

class box: #classe model-> que vai permitir criar vários grupos
    
    # Construtor: guarda o n e o dicionário (linha, coluna) -> valor ou None
    def __init__(self, n, celulas=None):
        self.n = n
        self.celulas = {}
        if celulas is not None:
            for (i,j) in celulas: #percorre as chaves do dicionario que são passadas
                self.add(i,j,celulas[(i,j)]) #adiciona o valor corresponde à chave

    #R1: Acrescenta a célula (i,j) ao grupo, depois de verificar as coordenadas e o valor
    def add(self, i, j, val=None):
        N = self.n * self.n
        
        #rejeita coordenadas fora da grelhas
        if i < 0 or i >= N or j < 0 or j >=N:
            raise ValueError("coordenadas fora da grelha")
            
        #rejeita valores fora do intervalo[1, n^2]
        if val is not None:
            if val < 1 or val > N:
                raise ValueError("valor fora do intervalo")
        self.celulas[(i,j)] = val

    #R1: devolve o grupo como matriz n^2 x n^2 (0 = célula livre ou fora do grupo)
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. `cube` e `path`: blocos, linhas e colunas (R2, R3)

    `cube` e `path` são duas especializações de `box`. Herdam os métodos `add` e `matriz` e só definem o construtor, que decide que células pertencem ao grupo. Todas as células são acrescentadas livres (sem valor fixo).

    - **`cube(n, i, j)`** representa o bloco $n \times n$ de índices $(i, j)$, com $0 \le i, j < n$, cujo canto superior esquerdo é a célula $(i \cdot n,\ j \cdot n)$.
    - **`path(n, inicio, fim)`** representa o troço reto, horizontal ou vertical, entre as células `inicio` e `fim`, inclusive. Funciona nos dois sentidos, porque o grupo é o mesmo conjunto de células quer se vá de `inicio` para `fim` quer ao contrário.

    Como as células são acrescentadas com o `add` do `box`, a verificação das coordenadas é reaproveitada: um bloco ou um troço fora da grelha levanta `ValueError`.
    """)
    return


@app.cell
def _():
    # R2: bloco n x n cujo canto superior esquerdo é a célula (i*n, j*n)
    class cube(box):

        # Construtor: cria um grupo vazio e acrescenta as n*n células do bloco (i, j)
        def __init__(self, n, i, j): #i e j indices do bloco(linha e coluna do bloco)
            super().__init__(n) #cria o grupo e fica vazio
            for a in range(n):
                for b in range(n):
                    self.add(i * n + a, j * n + b)


    # R3: troço reto (horizontal ou vertical) entre as células inicio e fim, inclusive
    class path(box):

        # Construtor: cria um grupo vazio e acrescenta as células entre inicio e fim
        def __init__(self, n, inicio, fim):
            super().__init__(n)
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

    return


if __name__ == "__main__":
    app.run()
