"""
=========================================================
Text Analyzer - Speech AI
---------------------------------------------------------
Sprint 8.5

Responsável por transformar o script bruto em um objeto
Presentation contendo Slides, Paragraphs, ListBlocks e
Statistics.

Author: Rodrigo Magalhães
=========================================================
"""

import logging
import re
from pathlib import Path

from config.config_manager import ConfigManager

from models import (
    Presentation,
    Slide,
    Statistics,
)

logger = logging.getLogger(__name__)


class TextAnalyzer:

    # -------------------------------------------------

    def __init__(self, cfg: ConfigManager, script_file=None):

        self.cfg = cfg

        self.script_file = script_file or cfg.script_file

        self.raw_text = ""

        self.presentation = Presentation()

    # -------------------------------------------------

    def load(self):

        logger.info("Loading script...")

        script = Path(self.script_file)

        if not script.exists():

            raise FileNotFoundError(script)

        self.raw_text = script.read_text(
            encoding="utf-8"
        )

    # -------------------------------------------------

    def normalize(self):

        logger.info("Normalizing text...")

        text = self.raw_text

        text = text.replace("\r\n", "\n")

        text = re.sub(r"[ \t]+", " ", text)

        text = re.sub(r"\n{3,}", "\n\n", text)

        self.raw_text = text.strip()

    # -------------------------------------------------

    def detect_slides(self):

        logger.info("Detecting slides...")

        slides = re.split(

            r"(?i)(?=slide\s+\d+)",

            self.raw_text

        )

        return [

            slide.strip()

            for slide in slides

            if slide.strip()

        ]

    # -------------------------------------------------

    def parse_slide(

        self,

        slide_text: str,

        number: int

    ) -> Slide:

        lines = slide_text.splitlines()

        title = lines[0].strip()

        slide = Slide(

            number=number,

            title=title

        )

        for line in lines[1:]:

            line = line.strip()

            if not line:

                continue

            if re.match(r"^[-•*]", line):

                slide.add_list([line])

            else:

                slide.add_paragraph(line)

        return slide

    # -------------------------------------------------

    def build_presentation(self):

        logger.info("Building Presentation...")

        for number, slide_text in enumerate(

            self.detect_slides(),

            start=1

        ):

            self.presentation.add_slide(

                self.parse_slide(

                    slide_text,

                    number

                )

            )

    # -------------------------------------------------

    def calculate_statistics(self):

        logger.info("Calculating statistics...")

        stats = Statistics()

        stats.characters = len(self.raw_text)

        stats.words = len(

            re.findall(

                r"\b[\w'-]+\b",

                self.raw_text

            )

        )

        stats.sentences = len(

            [

                s

                for s in re.split(

                    r"[.!?]+",

                    self.raw_text

                )

                if s.strip()

            ]

        )

        stats.paragraphs = len(

            [

                p

                for p in self.raw_text.split("\n\n")

                if p.strip()

            ]

        )

        stats.estimated_minutes = round(

            stats.words /

            self.cfg.words_per_minute,

            2

        )

        self.presentation.statistics = stats

    # -------------------------------------------------

    def run(self) -> Presentation:

        logger.info("Starting Text Analyzer")

        self.load()

        self.normalize()

        self.build_presentation()

        self.calculate_statistics()

        logger.info("Text Analyzer completed")

        return self.presentation