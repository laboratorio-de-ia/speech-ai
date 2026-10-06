"""
=========================================================
Skill Catalog
---------------------------------------------------------
Sprint 10 - Integração com Skills de Jornais

Resolve as skills disponíveis na pasta Skill/ a partir
da seção "skills.catalog" do settings.json.

Cada skill é um SKILL.md (instruções para o Claude) que
gera, na pasta de jornais, um HTML e um script.txt.

Author: Rodrigo Magalhães
=========================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config.config_manager import ConfigManager


@dataclass(frozen=True)
class SkillDefinition:

    name: str

    newspaper: str

    skill_file: Path

    aliases: tuple = field(default_factory=tuple)

    keywords: tuple = field(default_factory=tuple)


class SkillCatalog:

    # -------------------------------------------------

    def __init__(self, cfg: ConfigManager):

        self.cfg = cfg

        settings = cfg.skills

        self.skills_directory = (
            cfg.project_root
            / settings.get("directory", "Skill")
        )

        self.skills = {}

        for name, entry in settings.get("catalog", {}).items():

            self.skills[name] = SkillDefinition(

                name=name,

                newspaper=entry["newspaper"],

                skill_file=self.skills_directory / name / "SKILL.md",

                aliases=tuple(entry.get("aliases", [])),

                keywords=tuple(entry.get("keywords", []))

            )

    # -------------------------------------------------

    def get(self, name: str) -> SkillDefinition:

        key = name.strip().lower()

        for skill in self.skills.values():

            if key == skill.name or key in skill.aliases:

                if not skill.skill_file.exists():

                    raise FileNotFoundError(
                        f"SKILL.md not found:\n{skill.skill_file}"
                    )

                return skill

        available = ", ".join(self.skills)

        raise KeyError(
            f"Skill '{name}' not found. Available: {available}"
        )

    # -------------------------------------------------

    def all(self):

        return list(self.skills.values())
