from typing import List, Union, Any, Optional
from dataclasses import dataclass, field
import toml
import json # only for toml workaround as of 08/2025

@dataclass(slots=True)
class Option:
    name: str
    title: str
    description: str
    extras: Optional[List[str]]

@dataclass(slots=True)
class Entry:
    name: str
    title: str
    description: str
    default: Any
    options: Union[bool, str, List[Option]]
    permissions: List[str]

@dataclass(slots=True)
class Page:
    name: str
    title: str
    description: str
    entries: List[Entry] = field(default_factory=list)

@dataclass(slots=True)
class Settings():
    name: str
    title: str
    description: str
    pages: List[Page] = field(default_factory=list)

class SettingManager():
    def __init__(self, path: str):
        self.settings = json.loads(json.dumps(toml.load(open(path, "r"))))

    def get(self, setting: str) -> Settings:
        setting = self.settings[setting]
        title = setting["title"]
        description = setting["description"]
        pages = []
        for page, settings in setting.items():
            if type(settings) is dict:
                page = Page(page, settings["title"], settings["description"])
                for s, p in settings.items():
                    if type(p) is dict:
                        op = p["options"]
                        if not (op == [True, False] or op == [False, True]):
                            if type(op) is dict:
                                options = []
                                for en, ep in op.items():
                                    options.append(Option(en, ep["title"], ep["description"], ep.get("extras", [])))
                        else:
                            options = bool
                        page.entries.append(Entry(s, p["title"], p["description"], p.get("default"), options, p.get("permissions", [])))

                pages.append(page)
        
        return Settings(setting, title, description, pages)