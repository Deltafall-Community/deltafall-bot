from dataclasses import replace
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import List

@dataclass
class CustomDataSet:
    name: str
    data: dict
@dataclass
class CustomData:
    name: str
    data: str

@dataclass
class Tag:
    name: str
    attributes: dict
    
@dataclass
class CustomString:
    text: str
    hide: bool = False
    id: int = -1
    link: str = None
    tags: List[Tag] = field(default_factory=list)
    headerlevel: int = -1
    listNumber: int = -1
    isNumberedList: bool = False
    isBulletPointList: bool = False

class ParsingSection(Enum):
    CustomData = 1
    InSection = 2

class WikitextParser():
    def __init__(self):
        self.globalTags = []
        self.lastList = None
        self.listCount = 1

    async def populatetWikitextUrlPath(self, string: CustomString, baseurl: str):
        components=string.text.split("|")
        path_components=components[0].split(":")
        if len(components)>1:
            if len(path_components)>1:
                match path_components[0]:
                    case "w":
                        string.text=components[1]
                        string.link=f"https://en.wikipedia.org/wiki/{path_components[1]}"
                    case "Image":
                        string.hide=True # we do not need in-line image for our use case
                    case "File":
                        string.hide=True # we do not need in-line file for our use case
            else:
                string.text=components[1]
                string.link=f"{baseurl}/{components[0]}"
        elif path_components[0] == "":
            string.text=string.text[1:]
            string.link=f"{baseurl}/{string.text}"
        else:
            string.link=f"{baseurl}/{string.text}"
    
    async def parseDirectLink(self, line: List[CustomString], baseUrl: str):
        index=0
        while index < len(line):
            section=line[index]
            while True:
                startref=section.text.find("[[")
                endref=section.text.find("]]")
                if startref==-1 or endref==-1:
                    break

                refLeft=section.text[:startref]
                refText=section.text[startref+2:][:endref-startref-2]
                section.text=section.text[endref+2:]

                if refLeft!="":
                    section_copy=replace(section)
                    section_copy.text=refLeft
                    line.insert(index, section_copy)
                    index+=1
                section_copy=replace(section)
                section_copy.text=refText
                await self.populatetWikitextUrlPath(section_copy, baseUrl)
                line.insert(index, section_copy)
                index+=1
                if section.text == "":
                    line.pop(index)
            index+=1

    async def parseHTMLTags(self, line: List[CustomString]):
        index=0
        while index < len(line):
            section=line[index]
            while True:
                startingtag=section.text.find("<")
                endtag=section.text.find(">")
                if startingtag==-1 or endtag==-1:
                    break

                tagcontent=section.text[startingtag+1:][:endtag-startingtag-1].strip().split(" ", 1)
                tagLeft=section.text[:startingtag]
                section.text = section.text[endtag+1:]

                tagname=None
                if tagcontent[0]!="":
                    tagname=tagcontent[0]

                if tagcontent[0]!="" and tagcontent[0][0] == "/":
                    if tagLeft!="":
                        section_copy=replace(section)
                        section_copy.text=tagLeft
                        section_copy.tags=self.globalTags.copy()
                        line.insert(index, section_copy)
                        index+=1
                    for tag in range(len(self.globalTags)):
                        if tagname[1:] == self.globalTags[tag].name:
                            self.globalTags.pop(tag)
                            break
                    continue
                if tagLeft!="":
                    section_copy=replace(section)
                    section_copy.text=tagLeft
                    section_copy.tags=self.globalTags.copy()
                    line.insert(index, section_copy)
                    index+=1

                attrs={}
                if len(tagcontent)>1:
                    attrcontent=tagcontent[1].split("=")
                    while len(attrcontent)>1:
                        attr=attrcontent[:2]
                        value=attr[1]

                        beginattr=-1
                        endattr=-1
                        splitterList=['"', "'", " "]
                        splitter=None
                        for s in splitterList:
                            beginattr=value.find(s)
                            if beginattr!=-1:
                                splitter=s
                                break
                        if splitter:
                            endattr=value.rfind(splitter)
                            value=value[beginattr+1:][:endattr-1]

                        attrs[attr[0].strip()]=value
                        if endattr==-1:
                            break
                        attrcontent.pop(0)
                        attrcontent.insert(1, attr[1][endattr+1:])

                self.globalTags.append(Tag(tagname, attrs))
                if section.text == "":
                    line.pop(index)

            if index < len(line):
                line[index].tags = self.globalTags.copy()
            index+=1
            
    async def parseHeader(self, line: List[CustomString]):
        if line:
            text=line[0].text
            if text.startswith("=") and text.endswith("="):
                startingheaderchar = None
                endingheaderchar = None
                for char, index in zip(text, range(len(text))):
                    if not startingheaderchar and char != "=" :
                        startingheaderchar = index
                    elif startingheaderchar and char == "=":
                        endingheaderchar = index
                        break
                header=text[:endingheaderchar][startingheaderchar:].strip()
                line[0].text = header
                line[0].headerlevel = len(text[:startingheaderchar])

    async def parseLists(self, line: List[CustomString]):
        if line:
            match line[0].text[:2]:
                case "# ":
                    if self.lastList and self.lastList.isNumberedList and (line[0].id - self.lastList.id == 1):
                        self.listCount += 1
                    else:
                        self.listCount = 1
                    line[0].text=line[0].text[2:].lstrip()
                    for text in line:
                        text.isNumberedList=True
                        text.listNumber=self.listCount
                    self.lastList = line[-1]
                case "* ":
                    line[0].text=line[0].text[2:].lstrip()
                    for text in line:
                        text.isBulletPointList=True
                    self.lastList = line[-1]

    async def parseWikitext(self, text: str, baseUrl: str, id: int):
        line=[CustomString(text, id=id)]
        await self.parseDirectLink(line, baseUrl)
        await self.parseHTMLTags(line)
        await self.parseHeader(line)
        await self.parseLists(line)
        return line

    async def parse(self, wikitext: str, baseURL: str):
        globalWorkingSection=None
        parsed=[]
        customdata={}
        # theres no reason to split headers into multiple arrays
        lines=wikitext.split("\n")
        for lineindex in range(len(lines)):
            line=lines[lineindex].strip()
            match globalWorkingSection:
                case ParsingSection.CustomData:
                    if line == "}}":
                        globalWorkingSection=None # wip (not a priorty)
                case _:
                    if line.startswith("{{") and line.endswith("}}"):
                        try:
                            splitted=line[:-2][2:].split(":")
                        except Exception:
                            continue
                        try:
                            customdata[splitted[0]]=[splitted[1]]
                        except Exception:
                            continue
                    elif line.startswith("{{"):
                        #tempvar = line[2:]
                        globalWorkingSection = ParsingSection.CustomData
                    else:
                        line=await self.parseWikitext(line, baseURL, lineindex)
                        if len(line)<1:
                            continue
                        line[-1].text+="\n"
                        parsed+=line
        return parsed,customdata