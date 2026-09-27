# /// script
# dependencies = ["marimo"]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


app._unparsable_cell(
    r"""
    # Trabalho Prático: Gerador de Horário Escolar

    ## 1. Introdução
    Este trabalho tem como objetivo a conceção e implementação de um sistema automático para geração de horários escolares semanais. O problema é formulado como um **Problema de Satisfação de Restrições (CSP)** e otimização inteira, utilizando a biblioteca **Google OR-Tools (CP-SAT)** e **pandas** para a manipulação dos dados de entrada.

    O sistema responde aos seguintes eixos principais:
    1. Respeito integral por todos os requisitos operacionais (**R1 a R8**).
    2. Minimização dos tempos mortos ("buracos") nos horários dos professores (**O1**).
    3. Capacidade de adaptação incremental estável face a alterações de recursos (**R9**).
    """,
    name="setup"
)


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import time
    import os

    from ortools.sat.python import cp_model

    return cp_model, os, pd


app._unparsable_cell(
    r"""
    ## 2. Leitura e Preparação dos Dados (R8)
    Os dados de entrada são lidos diretamente de ficheiros CSV (`turmas.csv`, `disciplinas.csv`, `salas.csv` e `disponibilidade_excecoes.csv`), garantindo a total ausência de dados fixos (*hardcoded*) no código.

    A semana letiva é composta por 5 dias (`Seg` a `Sex`), com 5 tempos letivos diários (períodos 1 a 5).
    """,
    name="_"
)


@app.cell
def _(os, pd):

    # Definição do espaço temporal do horário escolar
    DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex"]
    PERIODOS_DIA = [1, 2, 3, 4, 5]


    def carregar_dados_horario(pasta="dados"):
        """Lê os ficheiros CSV de uma diretoria, normaliza campos de texto

        e valida a coerência temporal com os dias e períodos definidos.
        """
        caminho = lambda nome: os.path.join(pasta, nome)

        # 1. Carregamento dos ficheiros CSV
        df_turmas = pd.read_csv(caminho("turmas.csv"))
        df_disciplinas = pd.read_csv(caminho("disciplinas.csv"))
        df_salas = pd.read_csv(caminho("salas.csv"))
        df_excecoes = pd.read_csv(caminho("disponibilidade_excecoes.csv"))

        # 2. Limpeza e normalização de dados de texto
        df_disciplinas["disciplina"] = df_disciplinas["disciplina"].astype(str).str.strip()
        df_disciplinas["professor"] = df_disciplinas["professor"].astype(str).str.strip()
        df_disciplinas["duplo_periodo"] = (
            df_disciplinas["duplo_periodo"].astype(str).str.strip().str.lower()
        )
        df_disciplinas["sala_especial"] = (
            df_disciplinas["sala_especial"].fillna("").astype(str).str.strip()
        )

        df_salas["sala"] = df_salas["sala"].astype(str).str.strip()
        df_salas["tipo"] = df_salas["tipo"].astype(str).str.strip().str.lower()

        df_excecoes["professor"] = df_excecoes["professor"].astype(str).str.strip()
        df_excecoes["dia"] = df_excecoes["dia"].astype(str).str.strip()
        df_excecoes["periodo"] = df_excecoes["periodo"].astype(int)

        # 3. Filtragem de segurança: garantir que as exceções pertencem aos dias e períodos válidos
        df_excecoes = df_excecoes[
            df_excecoes["dia"].isin(DIAS_SEMANA)
            & df_excecoes["periodo"].isin(PERIODOS_DIA)
        ]

        return {
            "turmas": df_turmas,
            "disciplinas": df_disciplinas,
            "salas": df_salas,
            "excecoes": df_excecoes,
            "dias": DIAS_SEMANA,
            "periodos": PERIODOS_DIA,
        }

    return (carregar_dados_horario,)


@app.cell
def _(carregar_dados_horario):
    dados_h0 = carregar_dados_horario("dados")

    print("Turmas:", dados_h0["turmas"]["turma"].tolist())
    print("Dias letivos:", dados_h0["dias"])
    print("Períodos por dia:", dados_h0["periodos"])
    print("Total de exceções de professores:", len(dados_h0["excecoes"]))
    return (dados_h0,)


@app.cell
def _(cp_model, dados_h0):
    # 1. Iniciar o modelo CP-SAT
    model = cp_model.CpModel()

    # 2. Extrair os dados da variável dados_h0 
    turmas = dados_h0["turmas"]["turma"].tolist()
    disciplinas = dados_h0["disciplinas"]["disciplina"].tolist()
    dias = dados_h0["dias"]
    periodos = dados_h0["periodos"]

    # 3. Criar as variáveis booleanas x[turma, disciplina, dia, periodo]
    x = {}
    for t in turmas:
        for d in disciplinas:
            for dia in dias:
                for p in periodos:
                    x[t, d, dia, p] = model.NewBoolVar(f"x_{t}_{d}_{dia}_{p}")

    # 4. R1 (No máximo 1 aula por turma em cada tempo)
    for t in turmas:
        for dia in dias:
            for p in periodos:
                model.Add(sum(x[t, d, dia, p] for d in disciplinas) <= 1)

    print(f"Total de variáveis booleanas x criadas: {len(x)}")
    print("R1 adicionado com sucesso ao modelo!")
    return


if __name__ == "__main__":
    app.run()
