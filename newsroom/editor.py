"""
=========================================================
AI Editor
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

A IA entra só no trabalho editorial. Em vez de um agente
com dezenas de rodadas, são chamadas únicas (claude -p,
sem ferramentas, saída em JSON validado por schema):

  1. Três chamadas EM PARALELO, uma por destaque
     (tecnologia, economia, demais temas). Cada uma lê o
     texto do jornal e devolve slides + roteiro do bloco.
  2. Uma chamada curta de capa: título, subtítulo, data
     falada e abertura do áudio, a partir dos 3 blocos.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from newsroom.profiles import NewspaperProfile, Tier

logger = logging.getLogger(__name__)


# =====================================================
# Schemas
# =====================================================

def _s(description: str, **extra) -> dict:

    return {"type": "string", "description": description, **extra}


KPI = {

    "type": "object",

    "properties": {

        "value": _s("Número principal, curto (até 12 caracteres). Ex.: '47,03', 'R$ 33 bi', 'US$ 1,4 tri', '55'."),

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

        "quote": _s("Citação literal do jornal (até 200 caracteres) ou vazio."),

        "quote_by": _s("Autor da citação, ou vazio."),

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
            "Parágrafo do áudio sobre este slide (35 a 60 palavras), seguindo as regras de escrita para voz. "
            "Só fatos que estão no slide."
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

        "title": _s("Manchete-síntese curta e de efeito, parte 1 (até 38 caracteres), sobre o 1º destaque. Ex.: 'IA no banco dos réus, mercado em festa'."),

        "title_line2": _s("Parte 2 (até 42 caracteres), sobre o 2º e o 3º destaques. Ex.: 'e a direita na frente nas urnas'."),

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
- Confira cada percentual e valor contra o texto. Citações devem ser literais.
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
  Junte matérias relacionadas num mesmo slide.
- Escolha o layout que melhor conta cada história e preencha só os campos do layout escolhido
  (os demais ficam vazios: listas vazias, chart com bars vazia e textos vazios).
- Cada slide tem "Leitura do editor" (takeaway) nos assuntos principais e fontes com página e seção.
- Densidade (obrigatória): cada slide traz pelo menos 4 números do jornal (KPIs, barras ou texto dos cards)
  e, sempre que a matéria tiver, uma citação literal com autor. Prefira fatos concretos a frases genéricas.
- "script": um parágrafo por slide (35 a 55 palavras), com os mesmos fatos e números do slide.
- "divider.subtitle": {subtitle_rule} "divider.chips": um chip curto por slide.
- "overview_kpis": exatamente {kpis} números, os mais fortes deste bloco.
- "agenda": exatamente {agenda} item(ns) do que acompanhar, do tema deste bloco, com datas citadas no jornal.
- "watch_sentence": {watch_rule}
- O roteiro inteiro do resumo tem de 700 a 1.100 palavras: seja econômico em cada "script".
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

        self.claude = shutil.which(settings.get("claude_command", "claude"))

        if self.claude is None:

            raise FileNotFoundError("Claude Code CLI não encontrado.")

        self.model = settings.get("fast_model") or "claude-opus-5-5"

        self.cover_model = settings.get("fast_cover_model") or self.model

        # Nível de raciocínio (low, medium, high, xhigh, max); vazio = padrão da CLI.
        self.effort = settings.get("fast_effort") or ""

        # Segundos entre a 1ª chamada (que grava o cache) e as demais.
        self.cache_warmup = float(settings.get("fast_cache_warmup_seconds", 12))

        self.timeout = int(settings.get("fast_timeout_minutes", 8)) * 60

        self.retries = int(settings.get("fast_retries", 1))

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
              model: str = None, system_file: str = None) -> dict:

        system_args = ["--system-prompt-file", system_file] if system_file else ["--system-prompt", system]

        command = [

            self.claude, "-p", task,

            *system_args,

            "--tools", "",

            "--json-schema", json.dumps(schema, ensure_ascii=False),

            "--output-format", "json",

            "--model", model or self.model,

            "--no-session-persistence",

        ]

        if self.effort:

            command += ["--effort", self.effort]

        # Sem servidores MCP da conta: a chamada não usa ferramentas e inicia mais rápido.
        command += ["--strict-mcp-config"]

        last_error = None

        for attempt in range(1, self.retries + 2):

            started = time.time()

            # Diretório neutro: a chamada não carrega CLAUDE.md nem configurações do projeto.
            with tempfile.TemporaryDirectory() as cwd:

                try:

                    result = subprocess.run(

                        command, input=stdin_text, cwd=cwd,

                        capture_output=True, encoding="utf-8", errors="replace",

                        timeout=self.timeout

                    )

                except subprocess.TimeoutExpired:

                    last_error = f"{label}: tempo esgotado ({self.timeout // 60} min)"

                    continue

            seconds = time.time() - started

            try:

                payload = json.loads(result.stdout)

            except ValueError:

                last_error = f"{label}: resposta inválida (exit {result.returncode}) {result.stderr[-300:]}"

                continue

            if payload.get("is_error") or not isinstance(payload.get("structured_output"), dict):

                last_error = f"{label}: {payload.get('result') or payload.get('subtype')}"

                continue

            usage = payload.get("usage") or {}

            self.stats.append({

                "call": label,

                "seconds": round(seconds, 1),

                "cost_usd": payload.get("total_cost_usd"),

                "cache_write": usage.get("cache_creation_input_tokens"),

                "cache_read": usage.get("cache_read_input_tokens"),

                "output_tokens": usage.get("output_tokens"),

                "attempt": attempt,

            })

            logger.info("AI call %s finished in %.1fs", label, seconds)

            return payload["structured_output"]

        raise AIEditorError(last_error)

    # -------------------------------------------------

    def write_tier(self, tier: Tier, system_file: str, part: tuple = None) -> dict:

        hunt = (

            "Caça à tecnologia: " + self.profile.tech_hunt + " Se a edição tiver pouca tecnologia, "
            "faça ao menos 1 slide; nunca deixe o bloco vazio."

        ) if tier.number == 1 else ""

        if part is None:

            label = f"destaque {tier.number}"

            scope_line = f"o bloco do {tier.number}º destaque ({tier.name})."

            slides, kpis, agenda = tier.slides, 4, 2

            subtitle_rule = "resumo do bloco em 2 ou 3 frases (até 320 caracteres)."

            watch_rule = "uma frase falada sobre o que acompanhar neste destaque."

        else:

            name, scope, slides = part

            others = "; ".join(f"'{n}' ({sc})" for n, sc, _ in tier.parts if n != name)

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

        return self._call(label, "", task, TIER_SCHEMA, system_file=system_file)

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

    def write_tiers(self, paper_text: str) -> list[dict]:

        """
        Todas as chamadas compartilham o mesmo system prompt (regras + texto
        do jornal). A primeira grava o cache; as outras partem alguns segundos
        depois e leem o texto do cache, a uma fração do custo. Destaques com
        partes (economia, demais temas) rodam uma chamada por parte.
        """

        with tempfile.TemporaryDirectory() as tmp:

            system_file = str(Path(tmp) / "system.txt")

            Path(system_file).write_text(

                self._rules() + "\n\n=== TEXTO DA EDIÇÃO ===\n\n" + paper_text,

                encoding="utf-8"

            )

            jobs = []

            for tier in self.profile.tiers:

                for part in (tier.parts or (None,)):

                    jobs.append((tier, part))

            # Tecnologia parte primeiro e grava o cache: é a chamada mais demorada,
            # porque precisa caçar o tema no jornal inteiro.
            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:

                first_tier, first_part = jobs[0]

                futures = [pool.submit(self.write_tier, first_tier, system_file, first_part)]

                time.sleep(self.cache_warmup)

                futures += [pool.submit(self.write_tier, tier, system_file, part) for tier, part in jobs[1:]]

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

        return self._call("capa", self._rules(), task, COVER_SCHEMA, text, self.cover_model)
