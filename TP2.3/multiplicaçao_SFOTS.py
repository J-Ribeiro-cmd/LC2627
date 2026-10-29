import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import z3

    return (z3,)


@app.cell
def _(z3):
    class Multiplicacao:

        def __init__(self, n):
            self.n = n

            self.INIT = 0
            self.SKIP = 1
            self.LEFT = 2
            self.RIGHT = 3
            self.ERROR = 4
            self.STOP = 5

            self.NOMES = {
                    self.INIT: 'init',
                    self.SKIP: 'skip',
                    self.LEFT: 'left',
                    self.RIGHT: 'right',
                    self.ERROR: 'error',
                    self.STOP: 'stop',
                }

        def declare(self, i):
            state = {}
            state['pc'] = z3.Int('pc' + str(i))
            state['x'] = z3.BitVec('x' + str(i), self.n)
            state['y'] = z3.BitVec('y' + str(i), self.n)
            state['z'] = z3.BitVec('z' + str(i), self.n)
            state['a'] = z3.BitVec('a' + str(i), self.n)
            state['b'] = z3.BitVec('b' + str(i), self.n)
            return state

        def init(self, s):
            return z3.And(
            s['pc'] == self.INIT,
            z3.UGE(s['a'], 0),   # a >= 0, trivial sem sinal
            z3.UGE(s['b'], 0),   # b >= 0, trivial sem sinal
            )

        def overflow_shift(self, x):
            # x << 1 perde o bit mais alto se ele for 1
            return z3.Extract(self.n - 1, self.n - 1, x) == 1

        def overflow_soma(self, z, x):
            # z + x deu a volta se o resultado ficou menor que z
            return z3.ULT(z + x, z)


        def iguais(self, s, p, mudam=()):
            assert all(v in s for v in mudam), f"nome desconhecido em {mudam}"
            # todas as variáveis que NÃO estão em "mudam" ficam iguais
            return z3.And([p[v] == s[v] for v in s if v not in mudam])

        def trans(self, s, p):
            init_skip = z3.And(
                s['pc'] == self.INIT,
                p['pc'] == self.SKIP,
                p['x'] == s['a'],
                p['y'] == s['b'],
                p['z'] == 0,
                self.iguais(s, p, ('pc', 'x', 'y', 'z')),
            )
            skip_stop = z3.And(
                s['pc'] == self.SKIP,
                s['y'] == 0,
                p['pc'] == self.STOP,
                self.iguais(s, p, ('pc',)),
            )
            skip_left = z3.And(
                s['pc'] == self.SKIP,
                s['y'] != 0,
                (s['y'] & 1) == 0,
                p['pc'] == self.LEFT,
                self.iguais(s, p, ('pc',)),
            )
            skip_right = z3.And(
                s['pc'] == self.SKIP,
                s['y'] != 0,
                (s['y'] & 1) == 1,
                p['pc'] == self.RIGHT,
                self.iguais(s, p, ('pc',)),
            )
            left_skip = z3.And(
                s['pc'] == self.LEFT,
                z3.Not(self.overflow_shift(s['x'])),
                p['pc'] == self.SKIP,
                p['x'] == s['x'] << 1,
                p['y'] == z3.LShR(s['y'], 1),
                self.iguais(s, p, ('pc', 'x', 'y')),
            )
            left_error = z3.And(
                s['pc'] == self.LEFT,
                self.overflow_shift(s['x']),
                p['pc'] == self.ERROR,
                self.iguais(s, p, ('pc',)),
            )
            right_skip = z3.And(
                s['pc'] == self.RIGHT,
                z3.Not(self.overflow_soma(s['z'], s['x'])),
                p['pc'] == self.SKIP,
                p['y'] == s['y'] - 1,
                p['z'] == s['z'] + s['x'],
                self.iguais(s, p, ('pc', 'y', 'z')),
            )
            right_error = z3.And(
                s['pc'] == self.RIGHT,
                self.overflow_soma(s['z'], s['x']),
                p['pc'] == self.ERROR,
                self.iguais(s, p, ('pc',)),
            )
            stop_stop = z3.And(
                s['pc'] == self.STOP,
                p['pc'] == self.STOP,
                self.iguais(s, p, ('pc',)),
            )
            error_error = z3.And(
                s['pc'] == self.ERROR,
                p['pc'] == self.ERROR,
                self.iguais(s, p, ('pc',)),
            )
            return z3.Or(init_skip, skip_stop, skip_left, skip_right,
                         left_skip, left_error, right_skip, right_error,
                         stop_stop, error_error)
        def error(self, s):
            return s['pc'] == self.ERROR

    return (Multiplicacao,)


@app.cell
def _(z3):
    def gera_traco(declare, init, trans, k, extra=None, nomes=None):
        solver = z3.Solver()
        states = [declare(i) for i in range(k)]

        solver.add(init(states[0]))
        for i in range(k - 1):
            solver.add(trans(states[i], states[i + 1]))
        if extra is not None:
            solver.add(extra(states))

        if solver.check() == z3.sat:
            model = solver.model()
            for i, st in enumerate(states):
                partes = []
                for v in st:
                    val = model.eval(st[v], model_completion=True)
                    if v == 'pc' and nomes is not None:
                        val = nomes[val.as_long()]
                    partes.append(f"{v} = {val}")
                print(f"Estado {i}: " + ", ".join(partes))
        else:
            print("Não há solução")
            

    return (gera_traco,)


@app.cell
def _(Multiplicacao, gera_traco, z3):
    m4t = Multiplicacao(4)

    gera_traco(m4t.declare, m4t.init, m4t.trans, 12,
               lambda st: z3.And(st[0]['a'] == 3, st[0]['b'] == 5),
               nomes=m4t.NOMES)

    print("\n15 x 15:")
    gera_traco(m4t.declare, m4t.init, m4t.trans, 8,
               lambda st: z3.And(st[0]['a'] == 15, st[0]['b'] == 15), nomes = m4t.NOMES)
    return


if __name__ == "__main__":
    app.run()
