from typing import List, Union, Any
from dataclasses import dataclass, field
import toml

@dataclass(slots=True)
class Entry:
    name: str
    title: str
    description: str
    default: Any
    options: Union[bool, List[Any]]

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
        self.settings = toml.load(open(path, "r"))

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
                        page.entries.append(Entry(s, p["title"], p["description"], p["default"], bool if (options := p["options"]) == [True, False] or options == [False, True] else options))
                pages.append(page)
        
        return Settings(setting, title, description, pages)