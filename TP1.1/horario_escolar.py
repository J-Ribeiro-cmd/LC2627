# /// script
# dependencies = ["marimo"]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    # Trabalho Prático: Gerador de Horário Escolar

    ## 1. Introdução
    Este trabalho tem como objetivo a conceção e implementação de um sistema automático para geração de horários escolares semanais. O problema é formulado como um **Problema de Satisfação de Restrições (CSP)** e otimização inteira, utilizando a biblioteca **Google OR-Tools (CP-SAT)**.

    Para a manipulação dos dados de entrada, optou-se por utilizar o módulo nativo **`csv`** da biblioteca standard de Python (em vez de `pandas`), garantindo maior leveza, ausência de dependências externas e uma conversão direta para as estruturas nativas (listas e dicionários) que o solver manipula com facilidade.

    O sistema responde aos seguintes eixos principais:
    1. Respeito integral por todos os requisitos operacionais (**R1 a R8**).
    2. Minimização dos tempos mortos ("buracos") nos horários dos professores (**O1**).
    3. Capacidade de adaptação incremental estável face a alterações de recursos (**R9**).
    """)
    return


@app.cell
def _():
    import marimo as mo
    import time
    import os

    from ortools.sat.python import cp_model

    return cp_model, mo


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Leitura e Preparação dos Dados (R8)
    Os dados de entrada são lidos diretamente dos ficheiros CSV (`turmas.csv`, `disciplinas.csv`, `salas.csv` e `disponibilidade_excecoes.csv`), garantindo a total ausência de dados fixos (*hardcoded*) no código.

    A leitura é dividida em duas funções:
    - **`ler_csv_validado`**: Uma função utilitária e genérica que abre qualquer CSV com `csv.DictReader`, valida se os cabeçalhos obrigatórios existem e devolve o texto limpo.
    - **`carregar_dados`**: Orquestra o carregamento dos quatro ficheiros e converte os valores em tipos nativos de Python (inteiros para a carga horária e capacidades, booleanos para duplos períodos, etc.).

    A semana letiva é composta por 5 dias (`Seg` a `Sex`), com 5 tempos letivos diários (períodos 1 a 5).
    """)
    return


@app.cell
def _():
    import csv
    from pathlib import Path


    def _ler_csv_com_validacao(
        caminho_ficheiro: Path, colunas_obrigatorias: set[str]
    ) -> list[dict[str, str]]:
        """Abre um CSV, valida se as colunas obrigatórias existem no cabeçalho

        e devolve uma lista de dicionários com strings sem espaços nos extremos
        (strip).
        """
        if not caminho_ficheiro.exists():
            raise FileNotFoundError(
                f"Ficheiro obrigatório não encontrado: '{caminho_ficheiro}'"
            )

        linhas_limpas = []
        with open(caminho_ficheiro, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cabecalhos = set(col.strip() for col in (reader.fieldnames or []))

            # Validação do cabeçalho
            if not colunas_obrigatorias.issubset(cabecalhos):
                em_falta = colunas_obrigatorias - cabecalhos
                raise ValueError(
                    f"Ficheiro '{caminho_ficheiro.name}' inválido. "
                    f"Colunas em falta: {sorted(em_falta)}. Cabeçalho encontrado: {reader.fieldnames}"
                )

            for linha in reader:
                linhas_limpas.append({
                    k.strip(): (v.strip() if v is not None else "")
                    for k, v in linha.items()
                    if k is not None
                })

        return linhas_limpas


    def carregar_dados(diretoria_dados: str | Path = "dados") -> dict:
        """Lê e valida os 4 ficheiros CSV da diretoria indicada (R8)

        e adiciona a estrutura temporal da semana escolar (5 dias x 5 períodos).
        """
        pasta = Path(diretoria_dados)
        if not pasta.exists():
            raise FileNotFoundError(f"A diretoria '{pasta}' não foi encontrada.")

        # 1. Calendário escolar (5 dias x 5 períodos conforme o enunciado)
        dias = ["Seg", "Ter", "Qua", "Qui", "Sex"]
        periodos = [1, 2, 3, 4, 5]

        # 2. turmas.csv
        linhas_turmas = _ler_csv_com_validacao(
            pasta / "turmas.csv",
            colunas_obrigatorias={"turma"},
        )
        turmas = [l["turma"] for l in linhas_turmas if l["turma"]]

        # 3. salas.csv
        linhas_salas = _ler_csv_com_validacao(
            pasta / "salas.csv",
            colunas_obrigatorias={"sala", "tipo", "quantidade"},
        )
        salas = [
            {
                "sala": l["sala"],
                "tipo": l["tipo"].lower(),
                "quantidade": int(l["quantidade"]),
            }
            for l in linhas_salas
        ]

        # 4. disciplinas.csv
        linhas_disc = _ler_csv_com_validacao(
            pasta / "disciplinas.csv",
            colunas_obrigatorias={
                "disciplina",
                "professor",
                "carga_semanal",
                "duplo_periodo",
                "sala_especial",
            },
        )
        disciplinas = [
            {
                "disciplina": l["disciplina"],
                "professor": l["professor"],
                "carga_semanal": int(l["carga_semanal"]),
                "duplo_periodo": l["duplo_periodo"].lower() in ("sim", "true", "1"),
                "sala_especial": l["sala_especial"] or None,
            }
            for l in linhas_disc
        ]

        # 5. disponibilidade_excecoes.csv
        linhas_disp = _ler_csv_com_validacao(
            pasta / "disponibilidade_excecoes.csv",
            colunas_obrigatorias={"professor", "dia", "periodo"},
        )
        indisponibilidades = {
            (l["professor"], l["dia"], int(l["periodo"]))
            for l in linhas_disp
            if l["dia"] in dias and int(l["periodo"]) in periodos
        }

        return {
            "dias": dias,
            "periodos": periodos,
            "turmas": turmas,
            "salas": salas,
            "disciplinas": disciplinas,
            "indisponibilidades": indisponibilidades,
        }

    return


@app.cell
def _(cp_model, dados_h0):
    # 1. Iniciar o modelo CP-SAT
    model = cp_model.CpModel()

    # 2. Extrair listas a partir do dicionário retornado
    turmas = dados_h0["turmas"]
    disciplinas = [d["disciplina"] for d in dados_h0["disciplinas"]]
    dias = dados_h0["dias"]
    periodos = dados_h0["periodos"]

    # 3. Criar as variáveis de decisão booleanas x[turma, disciplina, dia, periodo]
    x = {}
    for t in turmas:
        for d in disciplinas:
            for dia in dias:
                for p in periodos:
                    x[t, d, dia, p] = model.NewBoolVar(f"x_{t}_{d}_{dia}_{p}")

    # 4. R1: Uma turma não pode ter duas aulas em simultâneo (no máx. 1 por tempo)
    for t in turmas:
        for dia in dias:
            for p in periodos:
                model.Add(sum(x[t, d, dia, p] for d in disciplinas) <= 1)

    print(f"Total de variáveis booleanas criadas: {len(x)}")
    print("R1 adicionada com sucesso ao modelo!")
    return dias, model, periodos, turmas, x


@app.cell
def _(dados_h0, dias, model, periodos, turmas, x):
    #R2: Cumprir exatamente a carga semanal de cada disciplina por turma
    for d_info in dados_h0["disciplinas"]:
        d_nome = d_info["disciplina"]
        carga = d_info["carga_semanal"]

        for t in turmas:
            # A soma de todos os tempos da disciplina 'd_nome' na semana para a turma 't' tem de ser igual à carga
            model.Add(
                sum(x[t, d_nome, dia, p] for dia in dias for p in periodos) == carga
            )

    print("R2 adicionada com sucesso ao modelo!")
    return


@app.cell
def _(dados, model, x):
    # Supondo: turmas, dias, periodos = [1, 2, 3, 4, 5]
    # e x[(t, d_nome, dia, p)] como variáveis booleanas já criadas

    for d in dados["disciplinas"]:
        d_nome = d["disciplina"]
        e_duplo = d["duplo_periodo"]

        for t in dados["turmas"]:
            for dia in dados["dias"]:

                if not e_duplo:
                    # R3 para disciplinas normais: no máximo 1 aula por dia
                    model.Add(
                        sum(x[(t, d_nome, dia, p)] for p in dados["periodos"]) <= 1
                    )

                else:
                    # R3 e R4 para disciplinas com duplo_periodo=sim:
                    # Criar variáveis booleanas para o início do bloco duplo (períodos 1 a 4)
                    bloco_inicio = {
                        p: model.NewBoolVar(f"bloco_{t}_{d_nome}_{dia}_{p}")
                        for p in [1, 2, 3, 4]
                    }

                    # R3: No máximo 1 bloco duplo por dia
                    model.Add(sum(bloco_inicio.values()) <= 1)

                    # R4: Ligar as variáveis x normais ao início do bloco
                    model.Add(x[(t, d_nome, dia, 1)] == bloco_inicio[1])
                    model.Add(
                        x[(t, d_nome, dia, 2)] == bloco_inicio[1] + bloco_inicio[2]
                    )
                    model.Add(
                        x[(t, d_nome, dia, 3)] == bloco_inicio[2] + bloco_inicio[3]
                    )
                    model.Add(
                        x[(t, d_nome, dia, 4)] == bloco_inicio[3] + bloco_inicio[4]
                    )
                    model.Add(x[(t, d_nome, dia, 5)] == bloco_inicio[4])
    return


if __name__ == "__main__":
    app.run()
