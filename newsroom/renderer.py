"""
=========================================================
Deck Renderer
---------------------------------------------------------
Sprint 12 - Processamento rápido de jornais

Monta o HTML do resumo em Python a partir do JSON da IA,
usando o modelo fixo (mesmo visual dos decks anteriores):

  templates/deck_head.html   <head> + estilos
  templates/slides.html.j2   capa, "em uma página",
                             divisórias, conteúdo, agenda
  templates/deck_tail.html   navegação e scripts

A verificação de layout (Playwright) detecta slides com
conteúdo transbordando e aplica modos compactos (dense,
dense2) até caber. Sem IA.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

import copy
import logging
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from newsroom.profiles import NewspaperProfile

logger = logging.getLogger(__name__)

TEMPLATES = Path(__file__).resolve().parent / "templates"

AGENDA_LABELS = {1: "Tecnologia", 2: "Economia", 3: "Política"}

LAYOUT_CHECK_JS = """
() => {
  // Mede cada slide ativo, como na apresentação, com as animações desligadas.
  const style = document.createElement('style');
  style.textContent = '*,*::before,*::after{animation:none!important;transition:none!important}';
  document.head.appendChild(style);
  const slides = [...document.querySelectorAll('main.deck > section.slide')];
  const out = [];
  slides.forEach(slide => {
    slides.forEach(s => s.classList.toggle('active', s === slide));
    const box = slide.getBoundingClientRect();
    const scale = box.width / 1600 || 1;
    const y = el => (el.getBoundingClientRect().bottom - box.top) / scale;
    let bad = false;
    const take = slide.querySelector(':scope > .takeaway');
    const limit = take ? (take.getBoundingClientRect().top - box.top) / scale + 2 : 846;
    slide.querySelectorAll('.card, .kcard, .step, .chart, .cards, .kgrid, .lr, .steps').forEach(el => {
      if (el.closest('.sfoot')) return;
      if (el.scrollHeight > el.clientHeight + 2) bad = true;
      if (y(el) > limit) bad = true;
      el.querySelectorAll(':scope > *').forEach(ch => { if (y(ch) > limit) bad = true; });
    });
    slide.querySelectorAll(':scope > *:not(.sfoot)').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width && ((r.bottom - box.top) / scale > 846 || (r.right - box.left) / scale > 1514)) bad = true;
    });
    out.push(bad);
  });
  return out;
}
"""


class DeckRenderer:

    # -------------------------------------------------

    def __init__(self, profile: NewspaperProfile):

        self.profile = profile

        self.env = Environment(

            loader=FileSystemLoader(TEMPLATES),

            autoescape=True,

            trim_blocks=False,

            lstrip_blocks=False,

        )

        self.head = self.env.get_template("deck_head.html")

        self.slides = self.env.get_template("slides.html.j2")

        self.tail = (TEMPLATES / "deck_tail.html").read_text(encoding="utf-8")

    # -------------------------------------------------

    def render(self, tiers: list[dict], cover: dict, density: dict = None) -> str:

        density = density or {}

        view = []

        for tier, block in zip(self.profile.tiers, tiers):

            block = self._normalize(block)

            view.append(SimpleNamespace(

                tier=SimpleNamespace(**tier.__dict__, agenda_label=AGENDA_LABELS[tier.number]),

                block=block,

                short_pages=self._short_pages(block["divider"]["pages"]),

            ))

        slides = self.slides.render(

            newspaper=self.profile.newspaper,

            tiers=view,

            cover=cover,

            processed=datetime.now().strftime("%d/%m/%Y"),

        )

        slides = self._apply_density(slides, density)

        head = self.head.render(

            title=f"Resumo {self.profile.newspaper} — {cover['edition_date']}",

            description=cover.get("description", ""),

            newspaper=self.profile.newspaper,

        )

        return head + "\n" + slides + "\n" + self.tail

    # -------------------------------------------------

    def render_checked(self, tiers: list[dict], cover: dict, html_path: Path) -> dict:

        """
        Renderiza, verifica o layout no navegador e corrige os slides
        que transbordam, em níveis: dense -> dense2 -> enxugar (remove
        o último card ou a linha fina). Retorna o relatório.
        """

        tiers = copy.deepcopy(tiers)

        density = {}

        html_path.write_text(self.render(tiers, cover, density), encoding="utf-8")

        try:

            from playwright.sync_api import sync_playwright

        except ImportError:

            logger.warning("Playwright não instalado: layout não verificado.")

            return {"checked": False, "tiers": tiers}

        report = {"checked": True, "dense": [], "dense2": [], "trimmed": [], "overflow": []}

        index = self._slide_index(tiers)

        with sync_playwright() as p:

            browser = p.chromium.launch()

            page = browser.new_page(viewport={"width": 1600, "height": 900})

            for level in ("dense", "dense2", "trim", "trim", "trim", None):

                page.goto(html_path.resolve().as_uri())

                page.wait_for_timeout(300)

                bad = [i for i, b in enumerate(page.evaluate(LAYOUT_CHECK_JS)) if b]

                if not bad or level is None:

                    report["overflow"] = bad

                    break

                for i in bad:

                    if level != "trim":

                        density[i] = level

                        report[level].append(i)

                    elif i in index and self._trim(tiers, *index[i]):

                        report["trimmed"].append(i)

                html_path.write_text(self.render(tiers, cover, density), encoding="utf-8")

            browser.close()

        report["tiers"] = tiers

        return report

    # -------------------------------------------------

    @staticmethod
    def _slide_index(tiers: list[dict]) -> dict:

        """Posição do slide no deck -> (destaque, slide)."""

        index, position = {}, 2  # capa e "em uma página"

        for t, block in enumerate(tiers):

            position += 1  # divisória

            for s in range(len(block["slides"])):

                index[position] = (t, s)

                position += 1

        return index

    # -------------------------------------------------

    @staticmethod
    def _trim(tiers: list[dict], t: int, s: int) -> bool:

        slide = tiers[t]["slides"][s]

        if len(slide["cards"]) > 1:

            slide["cards"].pop()

            return True

        for card in slide["cards"]:

            if card["bullets"] and len(card["bullets"]) > 2:

                card["bullets"].pop()

                return True

            if card["quote"] and card["text"]:

                card["quote"] = card["quote_by"] = ""

                return True

        if slide["lede"]:

            slide["lede"] = ""

            return True

        return False

    # -------------------------------------------------

    @staticmethod
    def _apply_density(slides_html: str, density: dict) -> str:

        if not density:

            return slides_html

        parts = re.split(r'(?=<section class="slide)', slides_html)

        head, sections = parts[0], parts[1:]

        for index, level in density.items():

            if index < len(sections):

                classes = "dense" if level == "dense" else "dense dense2"

                sections[index] = sections[index].replace(
                    '<section class="slide', f'<section class="slide {classes}', 1
                ).replace(f'slide {classes} ', f'slide {classes} ', 1)

        return head + "".join(sections)

    # -------------------------------------------------

    @staticmethod
    def _short_pages(pages: str) -> str:

        codes = [p.strip() for p in re.split(r"[,;]", pages) if p.strip()]

        return ", ".join(codes[:3]) + ("…" if len(codes) > 3 else "")

    # -------------------------------------------------

    @staticmethod
    def _normalize(block: dict) -> dict:

        """Corrige combinações que o modelo fixo não comporta."""

        block = copy.deepcopy(block)

        for slide in block["slides"]:

            layout = slide["layout"]

            bars = slide["chart"]["bars"]

            if layout == "chart" and len(bars) < 2:

                layout = "kpis_cards"

            if layout == "timeline" and len(slide["steps"]) < 2:

                layout = "kpis_cards"

            if layout == "kpis_cards" and not slide["kpis"] and len(slide["cards"]) >= 4:

                layout = "mosaic"

            slide["layout"] = layout

            if bars:

                top = max(abs(b["number"]) for b in bars) or 1

                for b in bars:

                    b["pct"] = round(max(abs(b["number"]) / top * 100, 2), 1)

                longest = max(len(b["label"]) for b in bars)

                slide["chart"]["label_width"] = min(max(110, longest * 9), 220)

            for k in slide["kpis"]:

                DeckRenderer._split_unit(k)

            slide["sources"] = slide["sources"][:3]

            if not slide["sources"]:

                slide["sources"] = [{"page": "", "section": block["divider"]["pages"]}]

        for k in block["overview_kpis"]:

            DeckRenderer._split_unit(k)

        return block

    # -------------------------------------------------

    @staticmethod
    def _split_unit(kpi: dict) -> None:

        """'62,65%' sem unidade vira valor '62,65' + unidade '%', como no visual original."""

        value = kpi["value"].strip()

        if not kpi["unit"] and value.endswith("%") and len(value) > 1:

            kpi["value"], kpi["unit"] = value[:-1].strip(), "%"
