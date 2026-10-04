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

    dados_h0 = carregar_dados("dados/")
    dados_h1 = carregar_dados("dados_v2/")
    return dados_h0, dados_h1


@app.cell
def _(cp_model):
    def construir_modelo(dados):
        """Constrói o modelo CP-SAT com as restrições R1 a R7 para os `dados`

        indicados e devolve o par (model, x), onde x[turma, disciplina, dia,
        periodo] são as variáveis de decisão booleanas.
        """
        # 1. Iniciar o modelo CP-SAT
        model = cp_model.CpModel()

        # 2. Extrair listas a partir do dicionário retornado
        turmas = dados["turmas"]
        disciplinas = [_d["disciplina"] for _d in dados["disciplinas"]]
        dias = dados["dias"]
        periodos = dados["periodos"]

        # 3. Criar as variáveis de decisão booleanas x[turma, disciplina, dia, periodo]
        x = {}
        for _t in turmas:
            for _d in disciplinas:
                for _dia in dias:
                    for _p in periodos:
                        x[_t, _d, _dia, _p] = model.NewBoolVar(f"x_{_t}_{_d}_{_dia}_{_p}")

        # 4. R1: Uma turma não pode ter duas aulas em simultâneo (no máx. 1 por tempo)
        for _t in turmas:
            for _dia in dias:
                for _p in periodos:
                    model.Add(sum(x[_t, _d, _dia, _p] for _d in disciplinas) <= 1)

        #R2: Cumprir exatamente a carga semanal de cada disciplina por turma
        for d_info in dados["disciplinas"]:
            _d_nome = d_info["disciplina"]
            carga = d_info["carga_semanal"]

            for _t in turmas:
                # A soma de todos os tempos da disciplina 'd_nome' na semana para a turma 't' tem de ser igual à carga
                model.Add(
                    sum(x[_t, _d_nome, _dia, _p] for _dia in dias for _p in periodos) == carga
                )

        # R3 e R4: aulas por dia e blocos duplos
        for _d in dados["disciplinas"]:
            _d_nome = _d["disciplina"]
            e_duplo = _d["duplo_periodo"]

            for _t in turmas:
                for _dia in dias:

                    if not e_duplo:
                        # R3 para disciplinas normais: no máximo 1 aula por dia
                        model.Add(
                            sum(x[(_t, _d_nome, _dia, _p)] for _p in periodos) <= 1
                        )

                    else:
                        # R3 e R4 para disciplinas com duplo_periodo=sim:
                        # Criar variáveis booleanas para o início do bloco duplo (períodos 1 a 4)
                        bloco_inicio = {
                            _p: model.NewBoolVar(f"bloco_{_t}_{_d_nome}_{_dia}_{_p}")
                            for _p in [1, 2, 3, 4]
                        }

                        # R3: No máximo 1 bloco duplo por dia
                        model.Add(sum(bloco_inicio.values()) <= 1)

                        # R4: Ligar as variáveis x normais ao início do bloco
                        model.Add(x[(_t, _d_nome, _dia, 1)] == bloco_inicio[1])
                        model.Add(
                            x[(_t, _d_nome, _dia, 2)] == bloco_inicio[1] + bloco_inicio[2]
                        )
                        model.Add(
                            x[(_t, _d_nome, _dia, 3)] == bloco_inicio[2] + bloco_inicio[3]
                        )
                        model.Add(
                            x[(_t, _d_nome, _dia, 4)] == bloco_inicio[3] + bloco_inicio[4]
                        )
                        model.Add(x[(_t, _d_nome, _dia, 5)] == bloco_inicio[4])

        #R5 Um professor não pode dar duas aulas em simultâneo, mesmo que sejam a turmas ou disciplinas diferentes.
        professores = set(_d["professor"] for _d in dados["disciplinas"])
        disciplinas_prof = {_prof:[] for _prof in professores}

        for _d in dados["disciplinas"]:
            disciplinas_prof[_d["professor"]].append(_d["disciplina"])

        for _prof in professores:
            disc_prof = disciplinas_prof[_prof]
            for _dia in dias:
                for _p in periodos:
                    model.Add(
                        sum(
                            x[_t, _d, _dia, _p]
                            for _t in turmas
                            for _d in disc_prof
                        )<=1
                    )

        # R6: Um professor só pode dar aulas nos tempos em que está disponível
        for _prof, _dia, _p in dados["indisponibilidades"]:
            # Se o professor lecionar disciplinas no sistema
            if _prof in disciplinas_prof:
                for _d in disciplinas_prof[_prof]:
                    for _t in turmas:
                        # Força a variável booleana a ser 0 naquele período
                        model.Add(x[_t, _d, _dia, _p] == 0)

        # R7: Capacidade de Salas (Especiais e Normais)
        discs_normais=[]
        discs_especiais_sala= {}
        for _d in dados["disciplinas"]:
            sala_esp = _d.get("sala_especial")
            _d_nome = _d["disciplina"]

            if sala_esp and sala_esp.strip() != "":
                if sala_esp not in discs_especiais_sala:
                    discs_especiais_sala[sala_esp] = []
                discs_especiais_sala[sala_esp].append(_d_nome)
            else: discs_normais.append(_d_nome)

        cap_salas = {s["sala"]: s["quantidade"] for s in dados["salas"]}
        qtd_salas_normais = cap_salas.get("Sala Normal")

        for _dia in dias:
            for _p in periodos:
                # A) Capacidade para cada sala especial
                for sala_esp, discs_esp in discs_especiais_sala.items():
                    cap_esp = cap_salas.get(sala_esp)
                    model.Add(
                        sum(
                            x[_t, _d, _dia, _p]
                            for _t in turmas
                            for _d in discs_esp
                        ) <= cap_esp
                    )

                # B) Capacidade para salas normais
                model.Add(
                    sum(
                        x[_t, _d, _dia, _p]
                        for _t in turmas
                        for _d in discs_normais
                    ) <= qtd_salas_normais
                )

        return model, x

    return (construir_modelo,)


@app.cell
def _(construir_modelo, cp_model):
    def resolver(dados, base=None):
        # 1. Modelo novo: cada chamada tem o seu modelo e as suas variáveis

        model, x = construir_modelo(dados)

        # 3. Parte incremental: só existe quando é dado um horário base
        if base is not None:
            # Pares (turma, disciplina) que já existiam no horário base
            pares_base = set()
            for t, d_nome, dia, p in base:
                pares_base.add((t, d_nome))

            # 3a. Hint: sugerir ao solver os valores que as variáveis tinham no base
            for chave in x:
                t, d_nome, dia, p = chave
                if (t, d_nome) in pares_base:
                    if chave in base:
                        model.AddHint(x[chave], 1)
                    else:
                        model.AddHint(x[chave], 0)

            # 3b. Objetivo: (1 - x) vale 0 se a aula fica no seu tempo e 1 se muda
            mudancas = []
            for chave in base:
                if chave in x:          # só conta se a aula ainda existir nos dados novos
                    mudancas.append(1 - x[chave])
            model.Minimize(sum(mudancas))

        # 4. Resolver (com limite de tempo)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30
        status = solver.Solve(model)
        tempo = solver.WallTime()

        # 5. Sem solução: devolve None no lugar do horário
        if status != cp_model.OPTIMAL and status != cp_model.FEASIBLE:
            return None, tempo

        # 6. Passar a solução para um set de tuplos
        horario = set()
        for chave in x:
            if solver.Value(x[chave]) == 1:
                horario.add(chave)
        return horario, tempo

    return (resolver,)


@app.function
def mostrar_horario(dados, horario, titulo):
    turmas = dados["turmas"]
    disciplinas = [_d["disciplina"] for _d in dados["disciplinas"]]
    dias = dados["dias"]
    periodos = dados["periodos"]

    # 1. Mapeamento auxiliar de disciplina -> professor a partir dos dados
    prof_por_disciplina = {
        _d["disciplina"]: _d["professor"] for _d in dados["disciplinas"]
    }

    # 2. Tratar o resultado da resolução
    if horario is not None:
        print(f"=== {titulo}: solução encontrada com sucesso! ===\n")

        # Largura de cada coluna da grelha para garantir alinhamento perfeito
        col_w = 34

        for _t in turmas:
            # Cabeçalho dos dias da semana
            cabecalho = f"{'Tempo':^12}|" + "".join(
                f"{_d:^{col_w}}|" for _d in dias
            )
            separador = "-" * len(cabecalho)

            print("=" * len(cabecalho))
            print(f" HORÁRIO SEMANAL {titulo}: TURMA {_t}")
            print("=" * len(cabecalho))
            print(cabecalho)
            print(separador)

            # Linhas correspondentes a cada período letivo
            for _p in periodos:
                linha_conteudo = [f"{f'{_p}º Período':^12}|"]

                for _dia in dias:
                    aula_str = "---"
                    for _d_nome in disciplinas:
                        # Verifica se a aula está atribuída a este tempo
                        if (_t, _d_nome, _dia, _p) in horario:
                            _prof = prof_por_disciplina.get(_d_nome, "Prof. ?")
                            aula_str = f"{_d_nome} ({_prof})"
                            break

                    linha_conteudo.append(f"{aula_str:^{col_w}}|")

                print("".join(linha_conteudo))

            print(separador)
            print("\n")

    else:
        print(f"ERRO: {titulo} sem solução (modelo INVIÁVEL ou tempo esgotado).")


@app.cell
def _(dados_h0, resolver):
    h0, t_h0 = resolver(dados_h0)
    mostrar_horario(dados_h0, h0, "H0")
    return (h0,)


@app.cell
def _(dados_h1, resolver):
    h1_zero, t_zero = resolver(dados_h1)
    mostrar_horario(dados_h1, h1_zero, "H1 do zero")
    return h1_zero, t_zero


@app.cell
def _(dados_h1, h0, resolver):
    h1_inc, t_inc = resolver(dados_h1, base=h0)
    mostrar_horario(dados_h1, h1_inc, "H1 incremental")
    return h1_inc, t_inc


@app.cell
def _(h0, h1_inc, h1_zero, t_inc, t_zero):
    print(f"H1 do zero:      {t_zero:.4f} s, {len(h0 - h1_zero)} aulas alteradas")
    print(f"H1 incremental:  {t_inc:.4f} s, {len(h0 - h1_inc)} aulas alteradas")
    return


if __name__ == "__main__":
    app.run()
