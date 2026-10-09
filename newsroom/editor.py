"""
=========================================================
AI Editor
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais
Sprint 13 - IA local (Ollama, custo zero)

A IA entra só no trabalho editorial. Em vez de um agente
com dezenas de rodadas, são chamadas únicas à IA local
(Ollama, sem ferramentas, saída em JSON validado por
schema):

  1. Três chamadas EM PARALELO, uma por destaque
     (tecnologia, economia, demais temas). Cada uma lê um
     recorte do jornal (as páginas mais relevantes para o
     destaque) e devolve slides + roteiro do bloco.
  2. Uma chamada curta de capa: título, subtítulo, data
     falada e abertura do áudio, a partir dos 3 blocos.

O modelo local roda com contexto bem menor que a IA paga
usava (GPU de poucos GB, contra as centenas de milhares de
tokens de cache da Claude API). Por isso, em vez de mandar
o jornal inteiro em cada chamada, newsroom/profiles.py
define termos por destaque e _select_pages() abaixo escolhe
só as páginas mais relevantes, dentro de um orçamento de
palavras (settings.fast_max_input_words).

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from newsroom.ollama_client import OllamaClient, OllamaError
from newsroom.profiles import NewspaperProfile, Tier

logger = logging.getLogger(__name__)


# A data da edição (às vezes um único dia, às vezes um fim de semana inteiro,
# ex.: "Sábado, domingo e segunda-feira, 3, 4 e 5 de outubro de 2026") já vem
# impressa por extenso na capa do jornal. Em vez de pedir para a IA escrever
# essa data de novo — o que, com o modelo local, já produziu "Oitavo de
# outubro" (ordinal errado) e datas copiadas do exemplo do schema —, ela é
# lida direto do texto da primeira página. Só cai para a data de hoje se a
# capa não tiver esse padrão (ex.: outro jornal, outro layout de capa).
_MASTHEAD_DATE = re.compile(

    r"(?P<weekdays>[A-ZÀ-Ú][a-zà-ú]+(?:-feira)?(?:,\s*[A-ZÀ-Úa-zà-ú]+(?:-feira)?)*"
    r"(?:\s+e\s+[A-ZÀ-Úa-zà-ú]+(?:-feira)?)?)"
    r",\s*(?P<date>\d{1,2}(?:,\s*\d{1,2})*(?:\s+e\s+\d{1,2})?\s+de\s+"
    r"(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
    r"\s+de\s+\d{4})"

)

_WEEKDAYS_PT = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
_MONTHS_PT = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
              "setembro", "outubro", "novembro", "dezembro")


def _edition_dates(front_page: str) -> tuple[str, str]:

    """(edition_date, spoken_date) lidos da capa, ou calculados a partir de hoje."""

    match = _MASTHEAD_DATE.search(front_page)

    if match:

        edition_date = match.group("date")

        weekdays = match.group("weekdays")

        spoken_date = f"{weekdays[0].lower()}{weekdays[1:]}, {edition_date}"

        return edition_date, spoken_date

    now = datetime.now()

    edition_date = f"{now.day} de {_MONTHS_PT[now.month - 1]} de {now.year}"

    spoken_date = f"{_WEEKDAYS_PT[now.weekday()]}, {edition_date}"

    return edition_date, spoken_date


# =====================================================
# Schemas
# =====================================================

def _s(description: str, **extra) -> dict:

    return {"type": "string", "description": description, **extra}


KPI = {

    "type": "object",

    "properties": {

        "value": _s("Número REAL do jornal (nunca um dos exemplos deste schema). Curto, até 12 caracteres, "
                    "no formato impresso: 'NN,NN', 'R$ NN bi', 'US$ N,N tri', 'NN' são formatos, não valores."),

        "unit": _s("Unidade pequena após o número, ex.: '%', 'pp'. Vazio se já está no valor."),

        "label": _s("O que o número mede (até 80 caracteres)."),

        "sub": _s("Contexto curto com a página no fim, ex.: 'Recorde: 87,6% · A18' (até 60 caracteres)."),

        "tone": {"type": "string", "enum": ["accent", "positive", "neutral"]},

    },

    "required": ["value", "unit", "label", "sub", "tone"],

    "additionalProperties": False,

}

CARD = {

    "type": "object",

    "properties": {

        "tag": _s("Rótulo do card (até 45 caracteres), ex.: 'Luciano Telo · UBS' ou 'Agronegócios'."),

        "page": _s("Página de origem, ex.: 'B7'."),

        "text": _s("Texto do card, denso e factual (até 300 caracteres). Pode ser vazio se houver bullets."),

        "bullets": {"type": "array", "items": _s("Item curto (até 110 caracteres)."), "description": "0 a 4 itens."},

        "quote": _s("A FRASE dita ou escrita por alguém, copiada literalmente do texto (até 200 caracteres) ou vazio. "
                    "Nunca um nome: é sempre uma frase completa, entre aspas no jornal ou claramente atribuída a alguém."),

        "quote_by": _s("SÓ o nome e cargo de quem disse a frase do campo 'quote' (ex.: 'Fulano, diretor da Empresa'), "
                        "ou vazio. Nunca uma frase."),

    },

    "required": ["tag", "page", "text", "bullets", "quote", "quote_by"],

    "additionalProperties": False,

}

SLIDE = {

    "type": "object",

    "properties": {

        "nav_title": _s("Título curto para a navegação (até 45 caracteres)."),

        "eyebrow": _s("Chapéu: tema · páginas, ex.: 'Finanças › Ativos · C1' (até 60 caracteres)."),

        "headline": _s("Título jornalístico do slide (até 115 caracteres)."),

        "lede": _s("Linha fina opcional (até 300 caracteres) ou vazio."),

        "layout": {

            "type": "string",

            "enum": ["kpis_cards", "timeline", "chart", "mosaic"],

            "description": (
                "kpis_cards: 2 a 4 KPIs + 2 a 3 cards. "
                "timeline: 3 a 4 passos (sequência de fatos) + até 2 KPIs + até 2 cards. "
                "chart: barras comparando 3 a 7 valores numéricos do jornal + até 2 KPIs + até 2 cards. "
                "mosaic: 4 a 6 cards de temas diferentes, sem KPIs."
            ),

        },

        "kpis": {"type": "array", "items": KPI},

        "steps": {

            "type": "array",

            "items": {

                "type": "object",

                "properties": {

                    "badge": _s("1 a 3 caracteres, ex.: '28', 'AU', '!'."),

                    "title": _s("Até 50 caracteres."),

                    "text": _s("Até 170 caracteres."),

                    "alert": {"type": "boolean"},

                },

                "required": ["badge", "title", "text", "alert"],

                "additionalProperties": False,

            },

        },

        "steps_title": _s("Título da coluna de passos (até 50 caracteres) ou vazio."),

        "chart": {

            "type": "object",

            "properties": {

                "title": _s("Até 70 caracteres."),

                "subtitle": _s("Unidade e fonte (até 90 caracteres)."),

                "bars": {

                    "type": "array",

                    "items": {

                        "type": "object",

                        "properties": {

                            "label": _s("Até 24 caracteres."),

                            "display": _s("Valor como aparece, ex.: '47,03%' (até 10 caracteres)."),

                            "number": {"type": "number", "description": "Valor numérico para o tamanho da barra."},

                            "highlight": {"type": "boolean"},

                        },

                        "required": ["label", "display", "number", "highlight"],

                        "additionalProperties": False,

                    },

                },

                "note": _s("Nota curta (até 150 caracteres) ou vazio."),

            },

            "required": ["title", "subtitle", "bars", "note"],

            "additionalProperties": False,

        },

        "cards": {"type": "array", "items": CARD},

        "takeaway": _s("'Leitura do editor': análise curta e factual, sem opinião partidária (até 280 caracteres)."),

        "sources": {

            "type": "array",

            "items": {

                "type": "object",

                "properties": {

                    "page": _s("Código da página ou intervalo, ex.: 'B1–B2'."),

                    "section": _s("Caderno › seção, ex.: 'Finanças › Ativos'."),

                },

                "required": ["page", "section"],

                "additionalProperties": False,

            },

        },

        "script": _s(
            "Parágrafo do áudio sobre este slide (45 a 65 palavras — nunca menos de 45), seguindo as regras de "
            "escrita para voz. Só fatos que estão no slide."
        ),

    },

    "required": [

        "nav_title", "eyebrow", "headline", "lede", "layout", "kpis", "steps",
        "steps_title", "chart", "cards", "takeaway", "sources", "script",

    ],

    "additionalProperties": False,

}

TIER_SCHEMA = {

    "type": "object",

    "properties": {

        "slides": {"type": "array", "items": SLIDE},

        "divider": {

            "type": "object",

            "properties": {

                "pages": _s("Páginas usadas no bloco, ex.: 'B2, B6, B7, C2'."),

                "subtitle": _s("Resumo do bloco em 2 ou 3 frases (até 320 caracteres)."),

                "chips": {"type": "array", "items": _s("Até 28 caracteres."), "description": "Um chip por slide."},

            },

            "required": ["pages", "subtitle", "chips"],

            "additionalProperties": False,

        },

        "overview_kpis": {"type": "array", "items": KPI, "description": "Exatamente 4 números do bloco."},

        "cover": {

            "type": "object",

            "properties": {

                "headline": _s("Manchete do bloco para a capa (até 105 caracteres)."),

                "source": _s("Página › seção da manchete, ex.: 'B7 · Empresas › Tecnologia'."),

            },

            "required": ["headline", "source"],

            "additionalProperties": False,

        },

        "agenda": {

            "type": "array",

            "description": "Exatamente 2 itens do que acompanhar nas próximas semanas.",

            "items": {

                "type": "object",

                "properties": {

                    "when": _s("Quando, ex.: '6/out', 'hoje', 'esta semana', ou vazio."),

                    "lead": _s("Assunto em negrito, ex.: 'Copom de novembro' (até 35 caracteres)."),

                    "text": _s("O que acompanhar (até 170 caracteres)."),

                },

                "required": ["when", "lead", "text"],

                "additionalProperties": False,

            },

        },

        "watch_sentence": _s("Uma frase falada sobre o que acompanhar neste destaque (até 40 palavras)."),

    },

    "required": ["slides", "divider", "overview_kpis", "cover", "agenda", "watch_sentence"],

    "additionalProperties": False,

}

COVER_SCHEMA = {

    "type": "object",

    "properties": {

        "title": _s("Manchete-síntese curta e de efeito, parte 1 (até 38 caracteres), sobre o 1º destaque desta "
                    "edição — escrita a partir dos fatos reais abaixo, nunca copiada de exemplo."),

        "title_line2": _s("Parte 2 (até 42 caracteres), sobre o 2º e o 3º destaques desta edição — mesma regra do título: "
                          "fatos reais abaixo, nunca um exemplo."),

        "subtitle": _s("Abertura da capa (até 330 caracteres) seguindo a ordem dos destaques."),

        "edition_date": _s("Data da edição como impressa, ex.: '3, 4 e 5 de outubro de 2026'."),

        "edition_meta": {"type": "array", "items": _s("Dado curto, ex.: 'Ano 27 · nº 6603', 'Cadernos A, B, C e E'.")},

        "spoken_date": _s("Data falada, ex.: 'sábado, domingo e segunda-feira, 3, 4 e 5 de outubro de 2026'."),

        "script_opening": _s(
            "Parágrafo de abertura do áudio (40 a 70 palavras): começa com 'Bom dia. Este é o resumo', "
            "cita os três destaques na ordem e o pano de fundo da edição."
        ),

        "description": _s("Meta description do HTML (até 250 caracteres)."),

    },

    "required": [

        "title", "title_line2", "subtitle", "edition_date", "edition_meta",
        "spoken_date", "script_opening", "description",

    ],

    "additionalProperties": False,

}


# =====================================================
# Prompts
# =====================================================

COMMON_RULES = """\
Você é um jornalista com mais de 30 anos de profissão e edita o resumo diário do jornal {newspaper}.
Você recebe o texto integral da edição, extraído do PDF. Cada página começa com um marcador
"=== [CÓDIGO · Seção] ===". Use esses códigos de página nas fontes.

{sections_map}

Hierarquia de destaques (obrigatória, mesmo que a manchete do jornal seja de outro tema):
1º destaque: {t1}
2º destaque: {t2}
3º destaque: {t3}

Precisão (obrigatória):
- Use só números, nomes e citações que estão no texto. Não invente nem complete com memória.
- Confira cada percentual e valor contra o texto. Citações devem ser cópia exata, palavra por palavra,
  de uma frase do texto da edição — nunca um resumo ou paráfrase apresentado como citação.
- Os "Ex.:" nas instruções de cada campo mostram só o FORMATO esperado, nunca um valor para copiar.
  Copiar um exemplo literalmente é um erro grave: o valor de cada campo vem sempre do texto da edição.
- Se o jornal trouxer números divergentes, use o da matéria principal.
- Opinião e editoriais são atribuídos ao autor ou ao jornal, nunca apresentados como fato.
- A "Leitura do editor" é análise sua: curta, factual, sem opinião partidária.
- Prefira números e citações a adjetivos. Escreva tudo em português do Brasil.
- Respeite os limites de caracteres indicados no schema: o conteúdo precisa caber no slide.

Regras do campo "script" (texto para ser lido em voz alta):
- Texto corrido, sem markdown, marcadores, emojis, links ou códigos de página (A9, B7...).
- Frases curtas (até 25 palavras).
- Números escritos para a fala: "47,03%" vira "47,03 por cento"; "R$ 30 bi" vira "30 bilhões de reais";
  "US$ 55,7 mi" vira "55,7 milhões de dólares"; "−0,5 pp" vira "meio ponto percentual";
  "130 pb" vira "130 pontos-base"; "5/out" vira "5 de outubro".
- Proibido usar os símbolos % R$ US$ × → • * # < > e as abreviações "bi", "mi", "pp".
- Siglas conhecidas (PT, PL, STF, PIB, Selic) podem ficar; siglas obscuras vão por extenso.
- Pode incluir "Na leitura do editor, ..." nos assuntos principais.
"""

TIER_TASK = """TAREFA DESTA CHAMADA: produza SOMENTE {scope_line}
Outros editores cuidam do restante do resumo; não use matérias que pertencem a eles.
{hunt}
- Faça de {min_slides} a {max_slides} slides de conteúdo, do assunto mais importante para o menos importante.
  Prefira o teto da faixa: só faça menos que {max_slides} se a edição realmente não tiver assunto suficiente.
  Junte matérias relacionadas num mesmo slide.
- Escolha o layout que melhor conta cada história e preencha só os campos do layout escolhido
  (os demais ficam vazios: listas vazias, chart com bars vazia e textos vazios).
- "kpis_cards" e "mosaic" exigem pelo menos 2 cards preenchidos (tag, texto ou bullets) — nunca a lista vazia.
- Cada slide tem "Leitura do editor" (takeaway) nos assuntos principais e fontes com página e seção.
- Densidade (obrigatória): cada slide traz pelo menos 4 números do jornal (KPIs, barras ou texto dos cards)
  e, sempre que a matéria tiver, uma citação literal com autor. Prefira fatos concretos a frases genéricas.
- "script": um parágrafo por slide (45 a 65 palavras, nunca menos de 45), com os mesmos fatos e números do slide.
- "divider.subtitle": {subtitle_rule} "divider.chips": um chip curto por slide.
- "overview_kpis": exatamente {kpis} números, os mais fortes deste bloco.
- "agenda": exatamente {agenda} item(ns) do que acompanhar, do tema deste bloco, com datas citadas no jornal.
- "watch_sentence": {watch_rule}
- O roteiro inteiro do resumo tem de 700 a 1.100 palavras: cada "script" denso, mas sempre dentro da faixa pedida
  (nunca mais curto que o mínimo só para economizar).
"""

COVER_TASK = """\
Você edita a capa do resumo do jornal {newspaper}. Os três blocos já foram escritos e estão abaixo
(manchete e resumo de cada destaque), seguidos do texto da primeira página do jornal.
Escreva a capa e a abertura do áudio. A manchete-síntese cita os três destaques NA ORDEM:
tecnologia, economia, demais temas. Use só fatos que aparecem abaixo.
A abertura do áudio segue as regras de escrita para voz (sem símbolos, números por extenso falado).
"""


class AIEditorError(RuntimeError):

    pass


class AIEditor:

    # -------------------------------------------------

    def __init__(self, profile: NewspaperProfile, settings: dict):

        self.profile = profile

        self.model = settings.get("ollama_model") or "gemma3:4b"

        self.cover_model = settings.get("ollama_cover_model") or self.model

        self.timeout = int(settings.get("ollama_timeout_minutes", 15)) * 60

        self.retries = int(settings.get("ollama_retries", 1))

        # Segundos entre a 1ª chamada (carrega o modelo na GPU) e as demais.
        self.warmup = float(settings.get("ollama_warmup_seconds", 5))

        # Orçamento de palavras do recorte do jornal enviado por chamada (contexto limitado).
        self.max_input_words = int(settings.get("fast_max_input_words", 6000))

        self.client = OllamaClient(

            host=settings.get("ollama_host") or "http://localhost:11434",

            timeout=self.timeout,

            num_ctx=int(settings.get("ollama_num_ctx", 16384)),

            keep_alive=settings.get("ollama_keep_alive", "30m"),

        )

        self.client.ensure_model(self.model)

        if self.cover_model != self.model:

            self.client.ensure_model(self.cover_model)

        self.stats = []

    # -------------------------------------------------

    def _rules(self) -> str:

        tiers = {t.number: t.scope for t in self.profile.tiers}

        return COMMON_RULES.format(

            newspaper=self.profile.newspaper,

            sections_map=self.profile.sections_map,

            t1=tiers[1], t2=tiers[2], t3=tiers[3],

        )

    # -------------------------------------------------

    def _call(self, label: str, system: str, task: str, schema: dict, stdin_text: str = "",
              model: str = None) -> dict:

        prompt = f"{task}\n\n{stdin_text}" if stdin_text else task

        last_error = None

        for attempt in range(1, self.retries + 2):

            started = time.time()

            try:

                result = self.client.generate(model or self.model, system, prompt, schema)

            except OllamaError as error:

                last_error = f"{label}: {error}"

                logger.warning(last_error)

                continue

            seconds = time.time() - started

            self.stats.append({

                "call": label,

                "seconds": round(seconds, 1),

                "cost_usd": 0.0,

                "cache_write": None,

                "cache_read": None,

                "output_tokens": None,

                "attempt": attempt,

            })

            logger.info("AI call %s finished in %.1fs", label, seconds)

            return result

        raise AIEditorError(last_error)

    # -------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:

        """minúsculo e sem acento, para casar palavras-chave sem depender de ortografia exata."""

        return "".join(

            c for c in unicodedata.normalize("NFD", text.lower())

            if unicodedata.category(c) != "Mn"

        )

    # -------------------------------------------------

    def _select_pages(self, pages: list, keywords: tuple) -> str:

        """
        Escolhe, entre as páginas do jornal, as mais relevantes para um destaque,
        dentro do orçamento de palavras em self.max_input_words. O modelo local não
        tem contexto para receber o jornal inteiro (eram ~176 mil tokens por chamada
        com a IA paga), então o recorte é feito aqui, em Python, por palavra-chave.
        """

        patterns = [re.compile(r"\b" + re.escape(self._normalize(k.strip())) + r"\b") for k in keywords]

        scored = []

        for page in pages:

            normalized = self._normalize(page.text)

            hits = sum(len(pattern.findall(normalized)) for pattern in patterns)

            scored.append((hits, page))

        scored.sort(key=lambda item: item[0], reverse=True)

        chosen, words = [], 0

        for hits, page in scored:

            if chosen and words >= self.max_input_words:

                break

            # depois de 60% do orçamento, só entram páginas com alguma palavra-chave.
            if hits == 0 and words >= self.max_input_words * 0.6:

                continue

            chosen.append(page)

            words += page.words

        chosen.sort(key=lambda page: page.number)

        blocks = []

        for page in chosen:

            label = " · ".join(x for x in (page.code, page.section) if x) or f"p.{page.number}"

            blocks.append(f"=== [{label}] ===\n{page.text}")

        return "\n\n".join(blocks)

    # -------------------------------------------------

    # "Nome Sobrenome, cargo": todas as 1 a 4 palavras antes da vírgula começam
    # maiúsculas (nome próprio) — diferente de uma frase comum, que começa
    # maiúscula só na primeira palavra.
    _NAME_LIKE = re.compile(r"^[A-ZÀ-Ú][\wà-ú.'-]*(\s+[A-ZÀ-Ú][\wà-ú.'-]*){0,3},\s")

    @classmethod
    def _fix_swapped_quote(cls, card: dict) -> None:

        """O modelo às vezes inverte os campos: põe 'Fulano, cargo' em quote e a
        frase de verdade em quote_by. Detecta o padrão típico (quote curto e com
        cara de "Nome, cargo"; quote_by longo e com cara de frase) e desfaz."""

        quote = (card.get("quote") or "").strip()

        by = (card.get("quote_by") or "").strip()

        if not quote or not by:

            return

        if cls._NAME_LIKE.match(quote) and not cls._NAME_LIKE.match(by):

            card["quote"], card["quote_by"] = by, quote

    # -------------------------------------------------

    def _drop_fake_quotes(self, result: dict, excerpt: str) -> None:

        """
        O modelo local às vezes parafraseia e apresenta a paráfrase como citação
        literal. Em vez de confiar nisso, confere cada "quote" contra o texto do
        jornal que foi realmente enviado nesta chamada; o que não aparece lá,
        palavra por palavra (ignorando só espaços), deixa de ser citação.
        """

        source = self._normalize_spaces(excerpt)

        dropped = 0

        for slide in result.get("slides", []):

            for card in slide.get("cards", []):

                self._fix_swapped_quote(card)

                quote = (card.get("quote") or "").strip()

                if quote and self._normalize_spaces(quote) not in source:

                    card["quote"] = ""

                    card["quote_by"] = ""

                    dropped += 1

        if dropped:

            logger.info("Quotes descartadas por não serem literais: %d", dropped)

    # -------------------------------------------------

    @staticmethod
    def _normalize_spaces(text: str) -> str:

        return re.sub(r"\s+", " ", text)

    # -------------------------------------------------

    def write_tier(self, tier: Tier, pages: list, part: tuple = None) -> dict:

        hunt = (

            "Caça à tecnologia: " + self.profile.tech_hunt + " Se a edição tiver pouca tecnologia, "
            "faça ao menos 1 slide; nunca deixe o bloco vazio."

        ) if tier.number == 1 else ""

        if part is None:

            label = f"destaque {tier.number}"

            scope_line = f"o bloco do {tier.number}º destaque ({tier.name})."

            slides, kpis, agenda, keywords = tier.slides, 4, 2, tier.keywords

            subtitle_rule = "resumo do bloco em 2 ou 3 frases (até 320 caracteres)."

            watch_rule = "uma frase falada sobre o que acompanhar neste destaque."

        else:

            name, scope, slides, keywords = part

            others = "; ".join(f"'{n}' ({sc})" for n, sc, _, _ in tier.parts if n != name)

            label = f"destaque {tier.number} · {name}"

            scope_line = (

                f"a parte '{name}' do {tier.number}º destaque ({tier.name}): {scope}. "
                f"Outro editor escreve a outra parte deste destaque: {others}."

            )

            kpis, agenda = 2, 1

            subtitle_rule = "resumo desta parte em 1 ou 2 frases (até 160 caracteres)."

            watch_rule = "meia frase falada (até 20 palavras) sobre o que acompanhar nesta parte."

        task = TIER_TASK.format(

            scope_line=scope_line, hunt=hunt, min_slides=slides[0], max_slides=slides[1],

            kpis=kpis, agenda=agenda, subtitle_rule=subtitle_rule, watch_rule=watch_rule,

        )

        excerpt = self._select_pages(pages, keywords)

        system = self._rules() + "\n\n=== TEXTO DA EDIÇÃO (recorte relevante para este destaque) ===\n\n" + excerpt

        result = self._call(label, system, task, TIER_SCHEMA)

        self._drop_fake_quotes(result, excerpt)

        return result

    # -------------------------------------------------

    @staticmethod
    def _merge(blocks: list[dict]) -> dict:

        """Junta as partes de um destaque num único bloco, na ordem das partes."""

        if len(blocks) == 1:

            return blocks[0]

        pages = []

        for block in blocks:

            for page in block["divider"]["pages"].split(","):

                if page.strip() and page.strip() not in pages:

                    pages.append(page.strip())

        watch = " ".join(b["watch_sentence"].strip().rstrip(".") + "." for b in blocks)

        return {

            "slides": [slide for b in blocks for slide in b["slides"]],

            "divider": {

                "pages": ", ".join(pages),

                "subtitle": " ".join(b["divider"]["subtitle"].strip() for b in blocks),

                "chips": [chip for b in blocks for chip in b["divider"]["chips"]],

            },

            "overview_kpis": [k for b in blocks for k in b["overview_kpis"][:2]][:4],

            "cover": blocks[0]["cover"],

            "agenda": [a for b in blocks for a in b["agenda"][:1]][:2],

            "watch_sentence": watch,

        }

    # -------------------------------------------------

    def write_tiers(self, pages: list) -> list[dict]:

        """
        Uma chamada por destaque (ou por parte dele), cada uma com o recorte
        de páginas relevante (ver _select_pages). O modelo local roda numa
        única GPU: as chamadas em paralelo disputam o mesmo recurso, mas o
        Ollama faz a fila sozinho. A pequena pausa antes das demais só evita
        que todas disputem o carregamento do modelo ao mesmo tempo.
        """

        jobs = []

        for tier in self.profile.tiers:

            for part in (tier.parts or (None,)):

                jobs.append((tier, part))

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:

            first_tier, first_part = jobs[0]

            futures = [pool.submit(self.write_tier, first_tier, pages, first_part)]

            if self.warmup:

                time.sleep(self.warmup)

            futures += [pool.submit(self.write_tier, tier, pages, part) for tier, part in jobs[1:]]

            results = [future.result() for future in futures]

        merged = []

        for tier in self.profile.tiers:

            merged.append(self._merge([r for (t, _), r in zip(jobs, results) if t is tier]))

        return merged

    # -------------------------------------------------

    def write_cover(self, tiers: list[dict], front_page: str) -> dict:

        summary = []

        for tier, block in zip(self.profile.tiers, tiers):

            summary.append(

                f"{tier.number}º destaque · {tier.name}\n"
                f"Manchete: {block['cover']['headline']} ({block['cover']['source']})\n"
                f"Resumo: {block['divider']['subtitle']}\n"
                f"Slides: " + "; ".join(s["headline"] for s in block["slides"])

            )

        text = "\n\n".join(summary) + "\n\n=== PRIMEIRA PÁGINA ===\n" + front_page[:6000]

        task = COVER_TASK.format(newspaper=self.profile.newspaper)

        result = self._call("capa", self._rules(), task, COVER_SCHEMA, text, self.cover_model)

        # A data é determinística (está impressa na capa): não depende da IA acertar.
        result["edition_date"], result["spoken_date"] = _edition_dates(front_page)

        return result
