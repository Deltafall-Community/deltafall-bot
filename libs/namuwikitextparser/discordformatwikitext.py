from libs.namuwikitextparser import namuwikitextparser
from typing import List

async def make_superscript(text: str):
    superscript_map = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶",
        "7": "⁷", "8": "⁸", "9": "⁹", "a": "ᵃ", "b": "ᵇ", "c": "ᶜ", "d": "ᵈ",
        "e": "ᵉ", "f": "ᶠ", "g": "ᵍ", "h": "ʰ", "i": "ᶦ", "j": "ʲ", "k": "ᵏ",
        "l": "ˡ", "m": "ᵐ", "n": "ⁿ", "o": "ᵒ", "p": "ᵖ", "q": "۹", "r": "ʳ",
        "s": "ˢ", "t": "ᵗ", "u": "ᵘ", "v": "ᵛ", "w": "ʷ", "x": "ˣ", "y": "ʸ",
        "z": "ᶻ", "A": "ᴬ", "B": "ᴮ", "C": "ᶜ", "D": "ᴰ", "E": "ᴱ", "F": "ᶠ",
        "G": "ᴳ", "H": "ᴴ", "I": "ᴵ", "J": "ᴶ", "K": "ᴷ", "L": "ᴸ", "M": "ᴹ",
        "N": "ᴺ", "O": "ᴼ", "P": "ᴾ", "Q": "Q", "R": "ᴿ", "S": "ˢ", "T": "ᵀ",
        "U": "ᵁ", "V": "ⱽ", "W": "ᵂ", "X": "ˣ", "Y": "ʸ", "Z": "ᶻ", "+": "⁺",
        "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾"}

    trans = str.maketrans(
        ''.join(superscript_map.keys()),
        ''.join(superscript_map.values()))

    return text.translate(trans)

async def format(wiki: List[namuwikitextparser.CustomString]):
    lastgroupstring = None
    groups = {}

    linestr=""
    for string in wiki:
        if string.hide: continue

        formatted=string.text
        if string.link: formatted=f"[{string.text.strip()}]({string.link.replace(" ", "_")})"
        if string.headerlevel > 1: formatted=f"{''.join("#" for hashtag in range(string.headerlevel-1))} {string.text}"
        if string.isBulletPointList: formatted=f"- {string.text}"
        if string.isNumberedList: formatted=f"{string.listNumber}. {string.text}"

        if string.tags:
            for tag in string.tags:
                match tag.name:
                    case "sup":
                        formatted=await make_superscript(formatted)
                    case "blockquote":
                        formatted = f"-# {formatted}"
                    case "ref":
                        if "group" in tag.attributes:
                            if not tag.attributes["group"] in groups: groups[tag.attributes["group"]]=[]
                            if lastgroupstring and string.id == lastgroupstring.id:
                                groups[tag.attributes["group"]][-1] += formatted
                            else:
                                groups[tag.attributes["group"]].append(formatted)
                                formatted=f"**[footnote {len(groups[tag.attributes["group"]])}]**"

                            lastgroupstring = string
                            continue
                        if string.text.startswith("http") and not string.link: formatted = f" *[[ref]]({string.text})* "

        linestr+=formatted
    linestr=linestr.strip()

    for attr in groups:
        match attr:
            case "footnote":
                linestr+="\n\n### Footnotes\n"
                for item in range(len(groups[attr])):
                    linestr+=f"{item+1}. {groups[attr][item]}"

    return linestr