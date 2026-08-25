from __future__ import annotations
"""
OTS Seed Language Support
"""
from ots.enums import SeedType, HandleType


class SeedLanguage:
    _instances: dict[str, 'SeedLanguage'] = {}

    def __init__(self, code: str, name: str, english_name: str):
        self._code = code.lower()
        self._name = name
        self._english_name = english_name
        self.handle = self

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def englishName(self) -> str:
        return self._english_name

    def supported(self, seed_type: SeedType) -> bool:
        if seed_type == SeedType.MONERO:
            return True
        if seed_type == SeedType.POLYSEED:
            return self._code in ('en', 'es')
        return True

    def isDefault(self, seed_type: SeedType) -> bool:
        return self._code == 'en'

    def __str__(self):
        return self._english_name

    def __repr__(self):
        return f"SeedLanguage({self._english_name})"

    def __eq__(self, other):
        if isinstance(other, str):
            return self._code == other.lower()
        if isinstance(other, SeedLanguage):
            return self._code == other._code
        return False

    def __hash__(self):
        return hash(self._code)

    @classmethod
    def fromCode(cls, code: str) -> 'SeedLanguage':
        code = code.lower()
        if code in cls._instances:
            return cls._instances[code]
        return cls._instances.get('en', SeedLanguage('en', 'English', 'English'))

    @classmethod
    def fromName(cls, name: str) -> 'SeedLanguage':
        for lang in cls._instances.values():
            if lang.name.lower() == name.lower():
                return lang
        return cls.fromCode('en')

    @classmethod
    def fromEnglishName(cls, english_name: str) -> 'SeedLanguage':
        for lang in cls._instances.values():
            if lang.englishName.lower() == english_name.lower():
                return lang
        return cls.fromCode('en')

    @classmethod
    def list(cls) -> set['SeedLanguage']:
        return set(cls._instances.values())

    @classmethod
    def listForType(cls, seed_type: SeedType) -> set['SeedLanguage']:
        return {l for l in cls._instances.values() if l.supported(seed_type)}

    @classmethod
    def defaultLanguage(cls, seed_type: SeedType) -> 'SeedLanguage':
        return cls.fromCode('en')

    @classmethod
    def setDefaultLanguage(cls, seed_type: SeedType, language: 'SeedLanguage') -> None:
        pass


# Register standard languages
_LANGS = [
    ('en', 'English', 'English'),
    ('de', 'Deutsch', 'German'),
    ('es', 'Español', 'Spanish'),
    ('fr', 'Français', 'French'),
    ('it', 'Italiano', 'Italian'),
    ('nl', 'Nederlands', 'Dutch'),
    ('pt', 'Português', 'Portuguese'),
    ('ru', 'Русский', 'Russian'),
    ('ja', '日本語', 'Japanese'),
    ('zh', '简体中文 (中国)', 'Chinese (simplified)'),
    ('eo', 'Esperanto', 'Esperanto'),
    ('jbo', 'Lojban', 'Lojban'),
]

for code, name, eng_name in _LANGS:
    SeedLanguage._instances[code] = SeedLanguage(code, name, eng_name)
