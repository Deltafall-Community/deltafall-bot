from dataclasses import dataclass
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
    link: str | None
    headerlevel: int
    tags: List[Tag]
    id: int

class ParsingSection(Enum):
    CustomData = 1
    InSection = 2

class WikitextParser():
    def __init__(self):
        self.globalTags = []

    async def formatWikitextUrlPath(self, text: str, baseurl: str, id: int):
        components=text.split("|")
        path_components=components[0].split(":")
        if len(components)>1:
            match path_components[0]:
                case "w": return CustomString(components[1], f"https://en.wikipedia.org/wiki/{path_components[1]}", -1, None, id)
                case ":": return CustomString(text[1:], f"{baseurl}/{text}", -1, None, id)
                case "Image": return None # we do not need in-line image for our use case
                case "File": return None # we do not need in-line file for our use case
        elif path_components[0] == "": return CustomString(text[1:], f"{baseurl}/{text[1:]}", -1, None, id)
        return CustomString(text, f"{baseurl}/{text}", -1, None, id)
    
    async def parseDirectLink(self, text: str, baseUrl: str, id: int):
        line = []
        directrefstr=None
        directref=text.find("[[")
        while directref!=-1:
            directrefLeft=text[:directref]
            if directrefLeft!="": line.append(CustomString(directrefLeft, None, -1, None, id))

            directrefstr=text[directref+2:][:text.find("]]")-directref-2]
            text=text[directref+2+len(directrefstr)+2:]

            directrefstrformatted=await self.formatWikitextUrlPath(directrefstr,baseUrl,id)
            if directrefstrformatted: line.append(directrefstrformatted)

            directref=text.find("[[")

        if directrefstr:
            if text!="": line.append(CustomString(text, None, -1, None, id))
        else: line.append(CustomString(text, None, -1, None, id))
        return line
    async def parseHTMLTags(self, line: List[CustomString], activeTags: List[Tag], id: int):
        index=0
        while index < len(line):
            section=line[index]
            while True:
                startingtag=section.text.find("<")
                endtag=section.text.find(">")
                if not (startingtag!=-1 and endtag!=-1): break

                tagcontent=section.text[startingtag+1:][:endtag-startingtag-1].strip().split(" ", 1)
                tagLeft=section.text[:startingtag]
                section.text = section.text[endtag+1:]

                tagname=None
                if tagcontent[0]!="":tagname=tagcontent[0]

                if tagcontent[0]!="" and tagcontent[0][0] == "/":
                    if tagLeft!="":
                        line.insert(index, CustomString(tagLeft, section.link, section.headerlevel, activeTags.copy(), id))
                        index+=1
                    for tag in range(len(activeTags)):
                        if tagname[1:] == activeTags[tag].name:
                            activeTags.pop(tag)
                            break
                    continue
                if tagLeft!="":
                    line.insert(index, CustomString(tagLeft, section.link, section.headerlevel, activeTags.copy(), id))
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
                        if endattr==-1: break
                        attrcontent.pop(0)
                        attrcontent.insert(1, attr[1][endattr+1:])

                activeTags.append(Tag(tagname, attrs))
                if section.text == "": line.pop(index)

            if index < len(line): line[index].tags = activeTags.copy()
            index+=1

        return (line, activeTags)
    async def parseHeader(self, line: List[CustomString]):
        if len(line)>0:
            text=line[0].text
            if text.startswith("=") and text.endswith("="):
                header=text.split(" ")
                line[0].text = header[1]
                line[0].headerlevel = len(header[0])

        return line

    async def parseWikitext(self, text: str, baseUrl: str, id: int):
        line= await self.parseDirectLink(text, baseUrl, id)
        line, self.globalTags = await self.parseHTMLTags(line, self.globalTags, id)
        line= await self.parseHeader(line)
        return line

    async def parse(self, wikitext: str):
        globalWorkingSection=None
        parsed=[]
        customdata={}
        # theres no reason to split headers into multiple arrays
        lines=wikitext.split("\n")
        for line in range(len(lines)): # 
            line=lines[line].strip()
            match globalWorkingSection:
                case ParsingSection.CustomData:
                    if line == "}}": globalWorkingSection=None # wip (not a priorty)
                case _:
                    if line.startswith("{{") and line.endswith("}}"):
                        try: splitted=line[:-2][2:].split(":")
                        except: continue
                        try: customdata[splitted[0]]=[splitted[1]]
                        except: continue
                    elif line.startswith("{{"):
                        tempvar = line[2:]
                        globalWorkingSection = ParsingSection.CustomData
                    else:
                        line=await self.parseWikitext(line, "https://deltafall.miraheze.org/wiki", line)
                        if len(line)<1: continue    
                        line[-1].text+="\n"
                        parsed+=line
        return parsed,customdata