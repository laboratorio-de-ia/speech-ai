"""
=========================================================
Newspaper Profiles
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

Regras editoriais de cada jornal (vindas das skills em
Skill/<nome>/SKILL.md), usadas nos prompts da IA.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:

    number: int

    name: str            # "Tecnologia e IA"

    title: str           # título da divisória

    spoken: str          # como é anunciado no áudio

    scope: str           # o que entra neste destaque

    slides: tuple        # (mínimo, máximo) de slides de conteúdo

    parts: tuple = ()    # divisão do destaque em chamadas paralelas: (nome, escopo, (mín, máx), keywords)

    keywords: tuple = () # termos usados para selecionar as páginas relevantes (IA local, sem parts)


@dataclass(frozen=True)
class NewspaperProfile:

    skill: str

    newspaper: str

    spoken_name: str     # "Valor Econômico", "Estadão"

    footer_label: str    # "Seção" ou "Página e caderno"

    tech_hunt: str

    sections_map: str

    tiers: tuple


TIER_SCOPES = {

    1: "Tecnologia: inteligência artificial, chips, big techs, startups, regulação de IA, "
       "computação quântica, ciência e espaço, cibersegurança, IPOs de tecnologia e IA aplicada "
       "(saúde, Justiça, segurança, agro, consumo, empresas).",

    2: "Economia e mercados: bolsa, ações, câmbio, juros e Banco Central, petróleo e energia, "
       "fiscal, empresas, bancos, crédito, agro, consumo e regulação econômica.",

    3: "Outros temas: política, eleições, Congresso, Estados, Judiciário, legislação e tributos, "
       "editoriais e opinião, internacional, cidade, saúde, sociedade, esportes e cultura.",

}


# Termos usados para selecionar, em Python, só as páginas relevantes de cada destaque
# antes de enviar à IA local. O modelo roda com contexto limitado (GPU de 6 GB): não é
# possível mandar o jornal inteiro em cada chamada, como era feito com a IA paga.
TIER1_KEYWORDS = (
    "inteligência artificial", " ia ", "ia,", "ia.", "ia:", "ia e ", "chatgpt", "openai", "chip",
    "chips", "semicondutor", "nvidia", "amd", "intel", "tsmc", "big tech", "startup", "startups",
    "data center", "computação quântica", "quântica", "cibersegurança", "hacker", "ransomware",
    "ia generativa", "aprendizado de máquina", "machine learning", "algoritmo", "robótica",
    "nuvem", "cloud", "software", "aplicativo", "tecnologia", "digital", "llm",
    "modelo de linguagem", "google", "microsoft", "meta", "amazon", "apple", "tesla", "gemini",
    "claude", "copilot", "ia aplicada",
)

TIER2_PART_KEYWORDS = {

    "Mercados e macroeconomia": (
        "bolsa", "ibovespa", "câmbio", "dólar", "juros", "selic", "copom", "banco central",
        "inflação", "ipca", "igp-m", "fiscal", "dívida pública", "indicadores", "pib",
        "crédito", "taxa de juros", "b3", "ações", "renda fixa", "títulos públicos", "tesouro",
    ),

    "Empresas e setores": (
        "empresa", "empresas", "resultado trimestral", "balanço", "varejo", "indústria",
        "petróleo", "petrobras", "energia", "agro", "agronegócio", "commodities", "consumo",
        "fusão", "aquisição", "ipo", "setor", "exportação", "importação", "banco", "bancos",
    ),

}

TIER3_PART_KEYWORDS = {

    "Política e eleições": (
        "eleição", "eleições", "candidato", "candidata", "partido", "congresso", "senado",
        "câmara dos deputados", "governo", "presidente", "ministro", "governador",
        "judiciário", "stf", "supremo", "urna", "pesquisa eleitoral", "campanha",
    ),

    "Demais temas": (
        "internacional", "editorial", "opinião", "legislação", "tributos", "imposto",
        "reforma tributária", "sociedade", "saúde", "hospital", "sus", "cidade", "trânsito",
        "segurança pública", "esporte", "futebol", "campeonato", "cultura", "cinema", "livro",
    ),

}


# Economia e demais temas são divididos em duas partes, escritas em paralelo:
# cada chamada escreve menos slides e o tempo total cai sem reduzir o raciocínio.
TIER_PARTS = {

    2: (

        ("Mercados e macroeconomia",
         "bolsa, câmbio, juros e Banco Central, inflação, fiscal e dívida, indicadores, bancos e crédito",
         (2, 3), TIER2_PART_KEYWORDS["Mercados e macroeconomia"]),

        ("Empresas e setores",
         "empresas e resultados, varejo, indústria, petróleo e energia, agro, consumo, regulação setorial",
         (2, 3), TIER2_PART_KEYWORDS["Empresas e setores"]),

    ),

    3: (

        ("Política e eleições",
         "eleições, partidos, Congresso, governo, Estados, Judiciário e STF",
         (2, 4), TIER3_PART_KEYWORDS["Política e eleições"]),

        ("Demais temas",
         "internacional, editoriais e opinião, legislação e tributos, sociedade, saúde, cidade, "
         "esportes e cultura; o último slide pode ser um mosaico de temas menores",
         (2, 3), TIER3_PART_KEYWORDS["Demais temas"]),

    ),

}


def _tiers(t2_slides, t3_slides):

    return (

        Tier(1, "Tecnologia e IA", "Tecnologia e inteligência artificial",
             "Primeiro destaque: tecnologia e inteligência artificial.", TIER_SCOPES[1], (2, 4),
             keywords=TIER1_KEYWORDS),

        Tier(2, "Economia e mercados", "Economia e mercados",
             "Segundo destaque: economia e mercados.", TIER_SCOPES[2], t2_slides, TIER_PARTS[2]),

        Tier(3, "Política e demais temas", "Política e demais temas",
             "Terceiro destaque: política e demais temas.", TIER_SCOPES[3], t3_slides, TIER_PARTS[3]),

    )


PROFILES = {

    "valor-economico": NewspaperProfile(

        skill="valor-economico",

        newspaper="Valor Econômico",

        spoken_name="Valor Econômico",

        footer_label="Seção",

        tech_hunt=(
            "A tecnologia costuma estar espalhada: procure em B (Empresas › Tecnologia, colunas de IA), "
            "C (Finanças › Mercados, IPOs), A (Opinião, Brasil › ciência) e em citações de IA dentro "
            "de matérias de empresas."
        ),

        sections_map=(
            "Cadernos do Valor: A = Política, Brasil (conjuntura, indicadores), Internacional, Opinião; "
            "B = Empresas (Tecnologia, Marketing, Saúde, Carreira…) e Agronegócios; "
            "C = Finanças (Ativos, Mercados, Bancos, Investimentos, Indicadores); E = Legislação & Tributos."
        ),

        tiers=_tiers((4, 6), (4, 7)),

    ),

    "estado-de-sp": NewspaperProfile(

        skill="estado-de-sp",

        newspaper="O Estado de S. Paulo",

        spoken_name="Estadão",

        footer_label="Página e caderno",

        tech_hunt=(
            "No Estadão a tecnologia raramente tem caderno próprio: procure em Internacional (A9–A11, "
            "ex.: 'Tecnologia e voto'), Metrópole ('Futuro e Inovação', ciência e espaço), E&N (B1–B2: "
            "IA, data centers), E-Investidor (B6–B7: IA, Nvidia), Broadcast Agro (B8: startups), "
            "A Fundo (C6–C7: ciência), Especial (promessas de IA de candidatos) e Política (pesquisas)."
        ),

        sections_map=(
            "Cadernos do Estadão: A (A2 Coluna do Estadão, A3 Notas e Informações = editoriais do jornal, "
            "A4–A6 Espaço Aberto, A8 Política, A9–A11 Internacional, A12–A16 Metrópole, A18–A19 Esportes, "
            "A20 'Para fechar'); B = Economia & Negócios (B4 tem a tabela Broadcast Mercados: use-a para "
            "os números de mercado; B6–B7 E-Investidor; B8 Broadcast Agro); C = Cultura & Comportamento "
            "(C6–C7 A Fundo); D = Especial. 'Notas e Informações' é opinião do jornal: atribua ao editorial."
        ),

        tiers=_tiers((3, 5), (4, 7)),

    ),

}


def get_profile(skill_name: str) -> NewspaperProfile:

    return PROFILES[skill_name]
