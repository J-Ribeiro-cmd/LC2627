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
    import os

    DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex"]
    PERIODOS_DIA = [1, 2, 3, 4, 5]

    def ler_csv_validado(caminho, colunas_obrigatorias):
        """Lê um CSV e valida as colunas obrigatórias."""
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Ficheiro não encontrado: {caminho}")

        with open(caminho, mode="r", encoding="utf-8") as f:
            leitor = csv.DictReader(f)
            colunas_reais = set(col.strip() for col in (leitor.fieldnames or []))
            em_falta = set(colunas_obrigatorias) - colunas_reais
            if em_falta:
                raise ValueError(f"Ficheiro {caminho} inválido: faltam as colunas {em_falta}")

            return [{k.strip(): (v.strip() if v else "") for k, v in row.items()} for row in leitor]

    def carregar_dados(pasta="dados"):
        """Carrega e tipifica os dados do problema a partir da pasta indicada."""
        turmas_raw = ler_csv_validado(os.path.join(pasta, "turmas.csv"), ["turma"])
        disciplinas_raw = ler_csv_validado(
            os.path.join(pasta, "disciplinas.csv"),
            ["disciplina", "professor", "carga_semanal", "duplo_periodo", "sala_especial"],
        )
        salas_raw = ler_csv_validado(os.path.join(pasta, "salas.csv"), ["sala", "tipo", "quantidade"])
        excecoes_raw = ler_csv_validado(
            os.path.join(pasta, "disponibilidade_excecoes.csv"),
            ["professor", "dia", "periodo"],
        )

        turmas = [r["turma"] for r in turmas_raw]

        disciplinas = [
            {
                "disciplina": r["disciplina"],
                "professor": r["professor"],
                "carga_semanal": int(r["carga_semanal"]),
                "duplo_periodo": r["duplo_periodo"].lower() == "sim",
                "sala_especial": r["sala_especial"] if r["sala_especial"] != "" else None,
            }
            for r in disciplinas_raw
        ]

        salas = [
            {
                "sala": r["sala"],
                "tipo": r["tipo"].lower(),
                "quantidade": int(r["quantidade"]),
            }
            for r in salas_raw
        ]

        # Filtra exceções para garantir que pertencem ao calendário válido
        excecoes = [
            {
                "professor": r["professor"],
                "dia": r["dia"],
                "periodo": int(r["periodo"]),
            }
            for r in excecoes_raw
            if r["dia"] in DIAS_SEMANA and int(r["periodo"]) in PERIODOS_DIA
        ]

        return {
            "turmas": turmas,
            "disciplinas": disciplinas,
            "salas": salas,
            "excecoes": excecoes,
            "dias": DIAS_SEMANA,
            "periodos": PERIODOS_DIA,
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


if __name__ == "__main__":
    app.run()
