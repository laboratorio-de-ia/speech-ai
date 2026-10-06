"""
=========================================================
Config Manager
---------------------------------------------------------
Centraliza o carregamento das configurações do projeto.

Também é responsável por disponibilizar o VoiceProfile
configurado para toda a aplicação.

Author: Rodrigo Magalhães
=========================================================
"""

import json
from pathlib import Path

from services.voice_manager import VoiceManager


class ConfigManager:

    # -------------------------------------------------

    def __init__(self):

        self.project_root = Path(__file__).resolve().parent.parent

        self.config_file = (
            self.project_root
            / "config"
            / "settings.json"
        )

        self.voices_file = (
            self.project_root
            / "config"
            / "voices.json"
        )

        self.data = {}

        self.load()

        # ---------------------------------------------
        # Voice Profiles
        # ---------------------------------------------

        self.voice_manager = VoiceManager(
            self.voices_file
        )

    # -------------------------------------------------

    def load(self):

        if not self.config_file.exists():

            raise FileNotFoundError(
                f"Configuration file not found:\n{self.config_file}"
            )

        with open(
            self.config_file,
            "r",
            encoding="utf-8"
        ) as f:

            self.data = json.load(f)

    # -------------------------------------------------

    def reload(self):

        self.load()

    # -------------------------------------------------

    def get(
        self,
        section,
        key=None
    ):

        if key is None:

            return self.data.get(section)

        return self.data.get(
            section,
            {}
        ).get(key)

    # =================================================
    # Provider
    # =================================================

    @property
    def provider(self):

        return self.get(
            "tts",
            "provider"
        )

    # =================================================
    # Voice Profiles
    # =================================================

    @property
    def voice_profile_name(self):

        return self.get(
            "tts",
            "voice_profile"
        )

    # -------------------------------------------------

    @property
    def voice_profile(self):

        return self.voice_manager.get(
            self.voice_profile_name
        )

    # =================================================
    # Backward Compatibility
    # (serão removidos na Sprint 9)
    # =================================================

    @property
    def voice(self):

        return self.voice_profile.voice

    # -------------------------------------------------

    @property
    def language(self):

        return self.voice_profile.language

    # -------------------------------------------------

    @property
    def locale(self):

        return self.voice_profile.locale

    # -------------------------------------------------

    @property
    def rate(self):

        return self.voice_profile.rate

    # -------------------------------------------------

    @property
    def pitch(self):

        return self.voice_profile.pitch

    # -------------------------------------------------

    @property
    def volume(self):

        return self.voice_profile.volume

    # =================================================
    # Input
    # =================================================

    @property
    def script_file(self):

        return self.get(
            "input",
            "script_file"
        )

    # =================================================
    # Output
    # =================================================

    @property
    def output_directory(self):

        return self.get(
            "output",
            "directory"
        )

    # -------------------------------------------------

    @property
    def output_filename(self):

        return self.get(
            "output",
            "filename"
        )

    # =================================================
    # Skills (Sprint 10 - integração com skills de jornais)
    # =================================================

    @property
    def skills(self):

        return self.get("skills") or {}

    # =================================================
    # Speech
    # =================================================

    @property
    def pause_short(self):

        return self.get(
            "speech",
            "pause_short"
        )

    # -------------------------------------------------

    @property
    def pause_long(self):

        return self.get(
            "speech",
            "pause_long"
        )

    # -------------------------------------------------

    @property
    def split_sentences(self):

        return self.get(
            "speech",
            "split_long_sentences"
        )

    # =================================================
    # Statistics
    # =================================================

    @property
    def words_per_minute(self):

        return 145

    # =================================================
    # Project
    # =================================================

    @property
    def project_name(self):

        return self.get(
            "project",
            "name"
        )

    # -------------------------------------------------

    @property
    def project_version(self):

        return self.get(
            "project",
            "version"
        )

    # =================================================

    def show(self):

        print()

        print("=" * 60)
        print(" Configuration")
        print("=" * 60)

        print(f"Project..........: {self.project_name}")
        print(f"Version..........: {self.project_version}")

        print()

        print(f"Provider.........: {self.provider}")
        print(f"Voice Profile....: {self.voice_profile_name}")
        print(f"Voice............: {self.voice}")
        print(f"Language.........: {self.language}")
        print(f"Locale...........: {self.locale}")
        print(f"Rate.............: {self.rate}")
        print(f"Pitch............: {self.pitch}")
        print(f"Volume...........: {self.volume}")

        print()

        print(f"Output Folder....: {self.output_directory}")
        print(f"Output File......: {self.output_filename}")

        print("=" * 60)