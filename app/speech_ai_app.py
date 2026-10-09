"""
=========================================================
Speech AI Application
---------------------------------------------------------
Application Kernel

Responsável por:

- Inicialização da aplicação
- Configuração
- Logging
- Execução da Pipeline
- Orquestração dos Services

Author: Rodrigo Magalhães
=========================================================
"""

import logging
from datetime import datetime
from pathlib import Path

from config.config_manager import ConfigManager

from pipeline import (
    NarrationBuilder,
    SpeechBuilder,
    TextAnalyzer,
)

from services.speech_service import SpeechService
from services.speech_intelligence import SpeechIntelligenceEngine

class SpeechAIApp:

    # -------------------------------------------------

    def __init__(self):

        self.cfg = ConfigManager()

        self.project_root = Path(__file__).resolve().parent.parent

        self.logger = logging.getLogger(__name__)

        self._configure_logging()

        self._show_banner()

    # -------------------------------------------------

    def _configure_logging(self):

        logs = self.project_root / "logs"

        logs.mkdir(
            exist_ok=True
        )

        logging.basicConfig(

            filename=logs / "app.log",

            level=logging.INFO,

            format="%(asctime)s | %(levelname)s | %(message)s",

            force=True

        )

    # -------------------------------------------------

    def _show_banner(self):

        print()

        print("=" * 60)

        print(f" {self.cfg.project_name}")

        print("=" * 60)

        print(f"Version : {self.cfg.project_version}")

        print("=" * 60)

    # -------------------------------------------------

    def show_configuration(self):

        self.cfg.show()

    # -------------------------------------------------

    @staticmethod
    def audio_filename(base_name: str) -> str:

        """
        Nome do mp3: nome do arquivo processado (sem extensão) + data e hora.
        Ex.: script_agentes -> script_agentes_2026-10-05_18-30-00.mp3
        """

        return f"{base_name}_{datetime.now():%Y-%m-%d_%H-%M-%S}.mp3"

    # -------------------------------------------------

    def run(self, script_file=None, output_filename=None, output_dir=None):

        script_file = Path(script_file or self.project_root / self.cfg.script_file)

        output_filename = output_filename or self.audio_filename(script_file.stem)

        audio_dir = Path(output_dir) if output_dir else (self.project_root / self.cfg.output_directory)

        print()

        print(f"Script............. {script_file}")

        print("Starting pipeline...")

        print()

        self.logger.info("Pipeline started")

        # =====================================================
        # TEXT ANALYZER
        # =====================================================

        analyzer = TextAnalyzer(self.cfg, script_file)

        presentation = analyzer.run()

        # ==========================================================
        # Speech Intelligence
        # ==========================================================

        intelligence = SpeechIntelligenceEngine(self.cfg)

        speech_profile = intelligence.build_profile(
            presentation
        )

        print()
        print("=" * 60)
        print(" Speech Intelligence")
        print("=" * 60)

        print(f"Language........... {speech_profile.language}")
        print(f"Voice.............. {speech_profile.voice}")
        print(f"Reading Style...... {speech_profile.reading_style}")
        print(f"Complexity......... {speech_profile.complexity}")
        print(f"Pacing............ {speech_profile.pacing}")
        print(f"Recommended WPM.... {speech_profile.recommended_wpm}")
        print(f"Rate............... {speech_profile.rate}")
        print(f"Pitch.............. {speech_profile.pitch}")
        print(f"Confidence......... {speech_profile.confidence}")

        print("=" * 60)
        print()



        # =====================================================
        # NARRATION BUILDER
        # =====================================================

        narrator = NarrationBuilder(self.cfg)

        narrator.load(presentation)

        narrator.build()

        narration_file = (

            self.project_root

            / self.cfg.output_directory

            / "narration.txt"

        )

        narrator.export_text(

            str(narration_file)

        )

        # =====================================================
        # SPEECH BUILDER
        # =====================================================

        speech = SpeechBuilder(self.cfg)

        speech.load(presentation)

        speech.build()

        speech_file = (

            self.project_root

            / self.cfg.output_directory

            / "speech.txt"

        )

        speech.export(

            str(speech_file)

        )

        # =====================================================
        # TTS SERVICE
        # =====================================================

        speech_service = SpeechService()

        audio_dir.mkdir(parents=True, exist_ok=True)

        audio_file = audio_dir / output_filename

        speech_service.synthesize(

            speech_profile=speech_profile,

            narration_file=speech_file,

            output_file=audio_file

        )

        # =====================================================
        # SUMMARY
        # =====================================================

        print()

        print("=" * 60)

        print(" Pipeline Finished")

        print("=" * 60)

        print(f"Slides............. {presentation.total_slides}")

        print(f"Words.............. {presentation.statistics.words}")

        print(
            f"Sentences.......... {presentation.statistics.sentences}"
        )

        print(
            f"Paragraphs......... {presentation.statistics.paragraphs}"
        )

        print(
            f"Characters......... {presentation.statistics.characters}"
        )

        print(
            f"Estimated Duration. {presentation.statistics.estimated_minutes:.2f} min"
        )

        print()

        print(f"Narration.......... {narration_file}")

        print(f"Speech............. {speech_file}")

        print(f"Audio.............. {audio_file}")

        print()

        self.logger.info("Pipeline finished")

        return audio_file

    # -------------------------------------------------

    @property
    def config(self):

        return self.cfg