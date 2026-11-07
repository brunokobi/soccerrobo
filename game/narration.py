# -*- coding: utf-8 -*-
"""Narracao da partida: falas curtas do NARRADOR (Tonho) e da COMENTARISTA (Cleide) numa faixa de TV.

Substitui os antigos letreiros da torcida ("GOOOL!", "UHHH!", "CLAP CLAP"...). O soccer.Game chama
`event(...)` nos lances (so escreve estado: fila de falas) e desenha a faixa com `draw(...)`.

Regras de desempenho e determinismo (as mesmas da torcida):
- RNG PRIVADO (`random.Random`): nunca o random global nem a simulacao (goldens intactos).
- Zero Surface por quadro: todo texto vira imagem no inicio da partida (`Narration(...)` busca via
  Game.text_img e GUARDA as imagens; o LRU do text_img pode esquecer sem problema). Uma fala e uma
  tupla de imagens prontas (trechos fixos + nomes de times/robos/numeros), blitadas lado a lado.
- O fundo da faixa (com a etiqueta NARRADOR / COMENTARISTA) e criado uma vez por sessao (`_BG`).

Fila sem spam: uma fala por vez (2,0-4,2 s conforme o tamanho), no maximo QUEUE_MAX esperando; lance
grande (gol, fim) corta o que estiver passando; lance pequeno (desarme, drible, skill, chute) so entra
com a faixa livre e respeitando o intervalo por tipo (MINOR_COOLDOWN). Sem lance por IDLE_GAP s, um dos
dois puxa assunto (estatistica, piada, analise). Relogio proprio: so anda fora da pausa.

Fichas nas falas: {T} time do lance, {O} o outro time, {R} robo do lance, {K} skill, {GT}/{GO} gols de
T/O, {N}/{M} numero da estatistica de T/O, {MIN} minuto. Tudo Latin-1 (Font(None)).
"""
import random

import pygame

QUEUE_MAX = 3
IDLE_GAP = 8.5                  # s sem fala -> conversa de calmaria
MINOR_GAP = 1.2                 # s livres antes de aceitar um lance pequeno
MINOR_COOLDOWN = {"steal": 7.0, "dribble": 5.0, "skill": 6.0, "chance": 2.5}
PRIO = {"end_win": 5, "end_draw": 5, "goal": 4, "equalize": 4, "turn": 4, "own": 4, "start": 3, "save": 3,
        "post": 3, "chance": 2, "skill": 1, "dribble": 1, "steal": 1, "idle": 0, "score": 4, "stat": 0}
FOLLOW = {"goal": 1.0, "equalize": 1.0, "turn": 1.0, "own": 1.0, "end_win": 1.0, "end_draw": 1.0,
          "start": 0.8, "save": 0.6, "post": 0.7, "chance": 0.25, "skill": 0.3, "dribble": 0.3, "steal": 0.2}
DUR = (2.0, 4.2)                # s por fala (min, max), cresce com a largura
GOAL_KINDS = ("goal", "equalize", "turn", "own")

# faixa (lower third): etiqueta do falante a esquerda, texto a direita
BAND_W, BAND_H = 860, 46
TAG_W = 168
TEXT_SIZE, ROLE_SIZE, NAME_SIZE = 25, 16, 24
TEXT_X = TAG_W + 14
MAX_TEXT_W = BAND_W - TEXT_X - 14
SPEAKERS = {"N": ("NARRADOR", "TONHO", (255, 214, 90)), "C": ("COMENTARISTA", "CLEIDE", (255, 140, 200))}
TEXT_COL = (240, 246, 250)
NAME_COL = (255, 226, 120)      # robos e skills em destaque
NUM_COL = (150, 235, 255)

# nomes de robo para quem nao tem nome (amistoso): so na narracao
FALLBACK_ROBOTS = (("Rodinha", "Turbinho", "Escovão", "Filtrinho", "Bocal"),
                   ("Ciclone", "Vassourão", "Suga-Pó", "Esfregão", "Pano Lento"))
TEAM_ALIAS = {"VOCÊ": "SEU TIME"}

LINES = {
    "start": {
        "N": ("Rola a bola! {T} e {O} ligam os motores!",
              "Começa o jogo! Filtro limpo e bateria no talo!",
              "Apita o juiz! {T} dá a saída contra o {O}!",
              "Bola no centro, poeira no ar: valendo!",
              "Começou! {T} contra {O}, que faxina vem aí!",
              "Saída de bola! Ninguém varre a sala hoje!",
              "Partida iniciada! Que vença o mais limpinho!"),
        "C": ("O {O} chega com as escovas novinhas, Tonho.",
              "Tonho, o tapete foi passado agora há pouco.",
              "Olho no {T}: treinou a semana toda no corredor.",
              "Cheiro de cera nova no ar, Tonho!",
              "Aposto num jogo de muito pó levantado."),
    },
    "chance": {
        "N": ("Lá vem o {R}... chutou!",
              "{R} arrisca de longe!",
              "Olha o chute do {R}!",
              "Bomba do {R}! Vai pro gol!",
              "{T} chega com perigo!",
              "Aspirou e soltou a bomba, {R}!",
              "Tentativa do {T}, olha lá!"),
        "C": ("Chute com vontade, Tonho.",
              "Esse veio com sucção máxima!",
              "O {T} gosta de finalizar de fora.",
              "Já são {N} finalizações do {T}."),
    },
    "save": {
        "N": ("Que defesa do {R}!",
              "PEGOU! {R} fecha o gol!",
              "Defesaça! O {R} não deixa passar nada!",
              "Espalmou o {R}! Que reflexo!",
              "{R} voa e salva o {T}!",
              "Não passa! Muralha do {T}!",
              "Na luva do {R}! Que segurança!"),
        "C": ("Goleiro com ímã nas luvas, Tonho.",
              "Esse não deixa passar nem migalha.",
              "Defesa de quem leu o manual inteiro.",
              "Já é a {N}ª defesa do {T} no jogo.",
              "O {O} vai ter que caprichar mais."),
    },
    "post": {
        "N": ("NA TRAVE! Por um fio de cabelo!",
              "Trave! O {T} quase abre o placar!",
              "Bateu na trave! Que susto!",
              "No poste! {R} não acredita!",
              "UHHH! A trave salvou o {O}!",
              "Carimbou a trave, {R}!",
              "Quase! A bola beijou o metal!"),
        "C": ("Fez barulho de panela, Tonho!",
              "A trave hoje joga pelo {O}.",
              "Mais um milímetro e era festa.",
              "O {R} vai sonhar com esse lance.",
              "Fio de cabelo ele aspira, Tonho!"),
    },
    "goal": {
        "N": ("GOOOL! {R} manda pro fundo da rede!",
              "É GOL DO {T}! {R} não perdoa!",
              "GOL! Pode varrer a rede, {R}!",
              "Entrou! {R} faz a sala inteira vibrar!",
              "GOLAÇO do {R}! Que categoria!",
              "É DELE! {R} marca para o {T}!",
              "GOOOL! Nenhum grão de pó resistiu!"),
        "C": ("Que lance, Tonho! O {O} dormiu no ponto.",
              "Finalização limpinha, sem deixar resíduo.",
              "O {R} estava calibrado hoje!",
              "Tonho, o chinelo ainda está no lugar?",
              "A defesa do {O} ficou só olhando."),
    },
    "equalize": {
        "N": ("GOL DE EMPATE! {R} deixa tudo igual!",
              "Empatou! {T} busca o {GT} a {GO}!",
              "GOOOL! {R} empata pro {T}!",
              "Tudo igual! {R} recoloca o {T} no jogo!",
              "É o empate! A torcida do {T} explode!",
              "Igualou! {R} não desiste nunca!"),
        "C": ("Agora é outro jogo, Tonho!",
              "O {O} relaxou e pagou caro.",
              "Empate justo pelo que se viu.",
              "Bateria nova no {T} depois desse gol!"),
    },
    "turn": {
        "N": ("VIRADA! {R} coloca o {T} na frente!",
              "VIROU! VIROU! O {T} vira o jogo!",
              "Que virada! {R} faz o {GT} a {GO}!",
              "GOOOL DA VIRADA! {R} é o herói!",
              "O {T} estava atrás e agora lidera!",
              "Virada histórica! {R} decide!"),
        "C": ("Isso é que é recarga, Tonho!",
              "O {O} vai ter que sair do cantinho.",
              "Virada de quem não desliga nunca.",
              "Tonho, guarda esse lance no pen drive!"),
    },
    "own": {
        "N": ("Gol contra! {R} mandou pro próprio gol!",
              "Ih! {R} se enrola e marca contra!",
              "Contra! O {T} agradece o presente!",
              "Que azar! {R} aspira pro lado errado!",
              "Gol contra! A sala inteira fica muda!",
              "Desviou no {R} e entrou! Gol do {T}!"),
        "C": ("Sensor de direção desregulado, Tonho.",
              "Acontece até com os melhores robôs.",
              "Alguém reinicia o {R}, por favor!",
              "Esse vai pro programa de erros."),
    },
    "score": {
        "C": ("Placar: {T} {GT} x {GO} {O}.",
              "Agora é {T} {GT}, {O} {GO}.",
              "{GT} a {GO} pro {T}, aos {MIN} minutos.",
              "Atualizando: {T} {GT} x {GO} {O}.",
              "Tá {GT} a {GO}, Tonho, e o jogo segue."),
    },
    "steal": {
        "N": ("Roubou! {R} toma a bola!",
              "Desarme do {R}!",
              "{R} aspira a bola do adversário!",
              "Que carrinho do {R}! Bola do {T}!",
              "Recuperou o {T}! {R} no desarme!",
              "{R} chega firme e leva a bola!"),
        "C": ("Marcação de rodo, Tonho.",
              "Já são {N} desarmes do {T}.",
              "Limpeza total no meio-campo.",
              "O {R} não deixa a bola respirar."),
    },
    "dribble": {
        "N": ("Que drible do {R}! Olé!",
              "{R} gira e deixa o marcador no chão!",
              "Passou! {R} faz o marcador de cone!",
              "Drible giratório do {R}! Que coisa!",
              "Olé! {R} dança no meio da defesa!",
              "Rodopiou e saiu, {R}!"),
        "C": ("Esse drible foi de máquina de lavar!",
              "O marcador ficou tonto, Tonho.",
              "Escovinha girando a mil por hora!",
              "Isso não se ensina, Tonho, se instala."),
    },
    "skill": {
        "N": ("{R} ativa {K}!",
              "Olha o {K} do {R}!",
              "{K}! O {R} apertou o botão!",
              "{R} solta {K}! Lá vai!",
              "Habilidade do {T}: {K}!",
              "{K} ligado! {R} acelera!"),
        "C": ("Gastou bateria, mas valeu, Tonho.",
              "O {T} sabe usar as peças novas.",
              "Upgrade bem feito na garagem!",
              "Essa skill custa caro na loja, viu?"),
    },
    "end_win": {
        "N": ("Acabou! Vitória do {T}!",
              "Fim de papo! O {T} vence por {GT} a {GO}!",
              "Apita o juiz! {T} leva a melhor!",
              "Termina o jogo! Festa do {T}!",
              "É do {T}! {GT} a {GO} e casa limpa!",
              "Fim! O {T} varreu o {O} hoje!"),
        "C": ("Missão cumprida, sala impecável.",
              "O {O} vai pro conserto e volta mais forte.",
              "Vitória merecida, Tonho, sem sujeira.",
              "Hoje a torcida do {T} limpa a casa.",
              "Pode recarregar as baterias, {T}!"),
    },
    "end_draw": {
        "N": ("Fim de jogo: empate!",
              "Acabou! {T} e {O} ficam no {GT} a {GO}!",
              "Termina igual! Ninguém varreu ninguém!",
              "Apito final! Tudo empatado!",
              "Fim! Empate entre {T} e {O}!",
              "Fim de papo, cada um com seu ponto!"),
        "C": ("Cada um varreu metade da sala, Tonho.",
              "Empate que não agrada ninguém.",
              "Faltou bateria pros dois no fim.",
              "Vamos ter revanche, pode escrever!"),
    },
    "idle": {
        "N": ("Bola rolando no meio-campo...",
              "O {T} troca passes com calma.",
              "Jogo estudado aqui na sala.",
              "{T} e {O} se estudam, Cleide.",
              "Aos {MIN} minutos, tudo muito disputado.",
              "Muita correria e pouca poeira até agora."),
        "C": ("Gramado sem um farelo sequer, Tonho.",
              "Recado do patrocinador: aspire com moderação!",
              "Até os robôs do vô estão de pé!",
              "O {T} precisa acelerar esse jogo.",
              "Tonho, alguém esqueceu um chinelo na área.",
              "Rodinhas do Vô: desde 1987 no futebol.",
              "Quem limpa a sala depois, Tonho?"),
    },
    "stat": {
        "C": ("O {T} já finalizou {N} vezes, o {O} {M}.",
              "{T}: {N} chutes. {O}: {M}. Tá na cara.",
              "Estatística, Tonho: {N} finalizações do {T}.",
              "O {T} chuta mais: {N} contra {M}."),
    },
}

_BG = {}                        # (falante) -> Surface da faixa (uma vez por sessao)
_FRAG = {}                      # (texto, tamanho, cor) -> Surface (trechos fixos, uma vez por sessao)


def parse(line):
    """'Gol do {T}!' -> [("t", "Gol do "), ("k", "T"), ("t", "!")]."""
    out, i = [], 0
    while i < len(line):
        j = line.find("{", i)
        if j < 0:
            out.append(("t", line[i:]))
            break
        if j > i:
            out.append(("t", line[i:j]))
        k = line.index("}", j)
        out.append(("k", line[j + 1:k]))
        i = k + 1
    return out


TOKENS = ("T", "O", "R", "K", "GT", "GO", "N", "M", "MIN")


def all_lines():
    for kind, by in LINES.items():
        for spk, lines in by.items():
            for line in lines:
                yield kind, spk, line


def all_strings():
    """Strings fixas que a narracao pode mostrar (Latin-1, testes)."""
    out = {t for _, _, line in all_lines() for k, t in parse(line) if k == "t"}
    for role, name, _ in SPEAKERS.values():
        out |= {role, name}
    return out


def _band_bg(spk, txt):
    bg = _BG.get(spk)
    if bg is not None:
        return bg
    role, name, col = SPEAKERS[spk]
    bg = pygame.Surface((BAND_W, BAND_H), pygame.SRCALPHA)
    pygame.draw.rect(bg, (4, 12, 28, 222), (0, 0, BAND_W, BAND_H), border_radius=6)
    pygame.draw.line(bg, (0, 220, 255, 255), (TAG_W, 0), (BAND_W - 6, 0), 2)
    pygame.draw.rect(bg, col + (255,), (0, 0, TAG_W, BAND_H), border_radius=6)
    pygame.draw.rect(bg, (20, 20, 30, 255), (TAG_W - 6, 0, 6, BAND_H))
    dark = (16, 18, 30)
    r = txt(role, ROLE_SIZE, dark)
    n = txt(name, NAME_SIZE, dark)
    bg.blit(r, ((TAG_W - 6 - r.get_width()) // 2, 5))
    bg.blit(n, ((TAG_W - 6 - n.get_width()) // 2, BAND_H - n.get_height() - 4))
    _BG[spk] = bg
    return bg


def _frag(txt, s, size, col):
    key = (s, size, col)
    img = _FRAG.get(key)
    if img is None:
        img = _FRAG[key] = txt(s, size, col)
    return img


def _light(c):
    c = tuple(c)
    m = max(c)
    if m < 200:
        k = 230.0 / max(m, 1)
        c = tuple(min(255, int(v * k + 25)) for v in c)
    return c


class Narration:
    """Fila de falas de uma partida. teams = [(nome, cor, [nomes dos 5 robos])] (casa, fora).
    skill_names = {sid: nome}. txt = Game.text_img. clock = segundos (padrao: relogio proprio pelo
    `tick`)."""

    def __init__(self, teams, txt, seed=0, skill_names=None):
        self.rng = random.Random(seed)
        self.txt = txt
        self.t = 0.0
        self.cur = None             # [falante, imgs, largura, inicio, duracao, prio, tipo]
        self.queue = []
        self.last_end = -99.0
        self.last_any = 0.0
        self.minor_t = {}
        self.last_pick = {}         # (tipo, falante) -> indice da ultima fala (nao repete)
        self.used = {}              # (tipo, falante) -> falas ja ditas nesta volta (saco embaralhado)
        self.stats = {"chance": [0, 0], "save": [0, 0], "steal": [0, 0]}
        self.score = [0, 0]
        self.minute = 1
        self.idle_turn = 0
        self.n_lines = 0
        self.bg = {k: _band_bg(k, txt) for k in SPEAKERS}
        # fragmentos fixos (cache da sessao) e por linha: lista de partes ja com imagem
        self.parts, self.tok = {}, {}
        for kind, spk, line in all_lines():
            ps = parse(line)
            self.parts.setdefault((kind, spk), []).append(
                [(_frag(txt, s, TEXT_SIZE, TEXT_COL), None) if k == "t" else (None, s) for k, s in ps])
            self.tok.setdefault((kind, spk), []).append({s for k, s in ps if k == "k"})
        # nomes desta partida
        self.team_img, self.robot_img = [], []
        for i, (name, color, robots) in enumerate(teams):
            nm = TEAM_ALIAS.get(name, name)
            self.team_img.append(txt(nm.upper(), TEXT_SIZE, _light(color)))
            imgs = []
            for k in range(5):
                rn = robots[k] if k < len(robots) and robots[k] else FALLBACK_ROBOTS[i % 2][k]
                imgs.append(txt(rn, TEXT_SIZE, NAME_COL))
            self.robot_img.append(imgs)
        self.skill_img = {sid: txt(n, TEXT_SIZE, NAME_COL) for sid, n in (skill_names or {}).items()}
        self.num_img = [_frag(txt, str(n), TEXT_SIZE, NUM_COL) for n in range(100)]

    # ------------------------------------------------------------------ eventos
    def event(self, kind, team=None, robot=None, skill=None, score=None, minute=None):
        """Lance da partida (so escreve estado). kind: start, chance, save, post, goal, equalize, turn,
        own, steal, dribble, skill, end_win, end_draw. team = time do lance (gol: quem marcou; save:
        quem defendeu; end_win: vencedor). robot = indice 0..4 do robo do lance no time `team` (gol
        contra: indice no time que errou)."""
        if score is not None:
            self.score = list(score)
        if minute is not None:
            self.minute = minute
        if kind in self.stats and team in (0, 1):
            self.stats[kind][team] += 1
        if kind not in LINES:
            return False
        prio = PRIO[kind]
        t = self.t
        if prio <= 2:                                           # lance pequeno: so com a faixa livre
            if self.queue or t - self.minor_t.get(kind, -99.0) < MINOR_COOLDOWN.get(kind, 3.0):
                return False
            cur = self.cur
            if cur is not None and cur[5] >= prio:
                return False
            if cur is None and t - self.last_end < MINOR_GAP and kind != "chance":
                return False
            self.minor_t[kind] = t
        else:                                                   # lance grande: corta o que for menor
            self.queue = [q for q in self.queue if q[5] >= prio]
        if self.cur is not None and self.cur[5] < prio:
            self._end()
        ctx = self._ctx(kind, team, robot, skill)
        self._push("N", kind, prio, ctx)
        if self.rng.random() < FOLLOW.get(kind, 0.0):
            if kind in GOAL_KINDS and self.rng.random() < 0.5:
                lead = 0 if self.score[0] >= self.score[1] else 1
                self._push("C", "score", prio, self._ctx("score", lead, None, None))
            else:
                self._push("C", kind, prio, ctx)
        return True

    def _ctx(self, kind, team, robot, skill):
        tm = team if team in (0, 1) else 0
        own = kind == "own"
        rt = 1 - tm if own else tm                              # gol contra: o robo e do outro time
        st = self.stats.get(kind, self.stats["chance"])        # {N}/{M}: a estatistica do proprio lance
        return {"T": self.team_img[tm], "O": self.team_img[1 - tm],
                "R": self.robot_img[rt][robot] if robot is not None and 0 <= robot < 5 else self.team_img[tm],
                "K": self.skill_img.get(skill, self.team_img[tm]),
                "GT": self._num(self.score[tm]), "GO": self._num(self.score[1 - tm]),
                "N": self._num(st[tm]), "M": self._num(st[1 - tm]), "MIN": self._num(self.minute), "n": st[tm]}

    def _num(self, n):
        return self.num_img[max(0, min(99, int(n)))]

    def _line(self, kind, spk, ctx):
        """Escolhe (RNG privado, sem repetir a ultima) uma fala que caiba na faixa; devolve (imgs, w)."""
        opts = self.parts[(kind, spk)]
        n = len(opts)
        last = self.last_pick.get((kind, spk))
        start = self.rng.randrange(n)
        toks = self.tok[(kind, spk)]
        few = ctx.get("n", 2) < 2                               # estatistica so com 2 ou mais
        order = [(start + d) % n for d in range(n)]
        used = self.used.setdefault((kind, spk), set())
        if len(used) >= n:
            used.clear()                                        # volta nova: todas de novo
        ok = [i for i in order if not (i == last and n > 1) and not (few and "N" in toks[i])] or order
        pref = [i for i in ok if i not in used] or ok           # primeiro as que ainda nao sairam
        best = None
        for i in pref:
            imgs = tuple(img if img is not None else ctx[key] for img, key in opts[i])
            w = sum(im.get_width() for im in imgs)
            if w <= MAX_TEXT_W:
                best = (i, imgs, w)
                break
            if best is None or w < best[2]:
                best = (i, imgs, w)
        self.last_pick[(kind, spk)] = best[0]
        used.add(best[0])
        return best[1], best[2]

    def _push(self, spk, kind, prio, ctx):
        if (kind, spk) not in self.parts:
            return
        imgs, w = self._line(kind, spk, ctx)
        dur = max(DUR[0], min(DUR[1], 1.3 + w / 230.0))
        item = [spk, imgs, w, None, dur, prio, kind]
        q = self.queue
        while len(q) >= QUEUE_MAX:
            low = min(range(len(q)), key=lambda i: q[i][5])
            q.pop(low)
        q.append(item)

    def _end(self):
        self.cur = None
        self.last_end = self.t

    # ------------------------------------------------------------------ tempo
    def tick(self, dt):
        """Avanca o relogio (dt real, 0 na pausa), troca de fala e puxa conversa na calmaria."""
        if dt > 0:
            self.t += min(dt, 0.1)
        t = self.t
        cur = self.cur
        if cur is not None and t >= cur[3] + cur[4]:
            self._end()
            cur = None
        if cur is None and self.queue:
            cur = self.cur = self.queue.pop(0)
            cur[3] = t
            self.last_any = t
            self.n_lines += 1
        if cur is None and not self.queue and t - max(self.last_end, self.last_any) >= IDLE_GAP:
            self.idle_turn += 1
            if self.idle_turn % 3 == 0 and sum(self.stats["chance"]) >= 2:
                c = self.stats["chance"]
                self._push("C", "stat", 0, self._ctx("stat", 0 if c[0] >= c[1] else 1, None, None))
            else:
                spk = "C" if self.idle_turn % 2 else "N"
                self._push(spk, "idle", 0, self._ctx("idle", self.rng.randrange(2), None, None))
            self.last_any = t
        return self.cur

    # ------------------------------------------------------------------ desenho
    def draw(self, scr, x, y):
        """Faixa da fala atual com topo-esquerdo em (x, y). So blits e pygame.draw."""
        cur = self.cur
        if cur is None:
            return False
        scr.blit(self.bg[cur[0]], (x, y))
        el = self.t - cur[3]
        cx = x + TEXT_X
        if el < 0.18:                                           # entra deslizando um pouco
            cx += int((0.18 - el) / 0.18 * 24)
        cy = y + BAND_H // 2 + 1
        for img in cur[1]:
            scr.blit(img, (cx, cy - img.get_height() // 2))
            cx += img.get_width()
        f = max(0.0, 1.0 - el / cur[4])                         # tempo restante da fala
        pygame.draw.line(scr, SPEAKERS[cur[0]][2], (x + TAG_W, y + BAND_H - 2),
                         (x + TAG_W + int((BAND_W - TAG_W - 6) * f), y + BAND_H - 2), 2)
        return True
