import math
from PIL import ImageFont, Image, ImageDraw

from typing import Tuple, List, Union
from libs.utils.vector import Vector2D

class LineBounds():
    def __init__(self, line: Tuple, chars: List[Tuple]):
        self.line = line
        self.chars = chars

    def __repr__(self):
        return f"LineBounds({self.line}: {self.chars})"

class LabelContainer():
    def __init__(self, font: str, font_size: int, size: Tuple[int, int], expand: bool = True, wrap: bool = True, spacing: int = 10):
        self.font = font
        self.size = size
        self.font_size = font_size

        self.is_expandable = expand
        self.is_wrappable = wrap
        self.spcaing = spacing

    def wrap(self, text: str, font) -> list:
        chars = []
        lines = [text]
        bbox = Vector2D(0,0)
        workingIndex = 0
        last_end = 0

        x_char_cache = {}
        
        metrics = font.getmetrics()
        while True:
            if lines[-1] == "":
                lines.pop()
                break
            
            autoCut = False
            x_ends = []
            char_index = 0
            max_index = len(lines[workingIndex])
            while char_index < max_index:
                b = ""
                if char_index < max_index-1:
                    a = lines[workingIndex][char_index]
                    b = lines[workingIndex][char_index+1]
                else:
                    a = lines[workingIndex][char_index]
                check_pair = a+b
                length = x_char_cache.get(check_pair)
                if not length:
                    l1 = font.getlength(check_pair)
                    l2 = 0
                    if b != "":
                        l2 = font.getlength(b)
                    length = l1 - l2
                    x_char_cache[check_pair] = length
                if x_ends:
                    x_ends.append((x_ends[-1][0]+x_ends[-1][1], length))
                else:
                    x_ends.append((0.0, length))
                if x_ends[-1][0] > self.size[0] and self.is_wrappable:
                    autoCut = True
                    break
                char_index += 1
            length = char_index

            newline = lines[workingIndex][:length+1].find("\n")
            if newline > -1:
                autoCut = False
                while newline > -1:
                    length = newline-1
                    lines.append(lines[workingIndex][newline+1:])
                    newline = lines[workingIndex][:length+1].find("\n")
            else:
                lines.append(lines[workingIndex][length+1:])

            lines[workingIndex] = lines[workingIndex][:length+1]

            spacerange = 10
            if len(lines[workingIndex]) >= spacerange and lines[workingIndex+1] and autoCut and self.is_wrappable:
                if " " in lines[workingIndex][len(lines[workingIndex])-spacerange:]:
                    for char in range(len(lines[workingIndex]) - 1, len(lines[workingIndex])-spacerange, -1):
                        if lines[workingIndex][char] == " ":
                            lines[workingIndex+1] = lines[workingIndex][char+1:]+lines[workingIndex+1]
                            lines[workingIndex] = lines[workingIndex][:char]
                            break
            
            text_size = font.getbbox(lines[workingIndex])

            if chars:
                offset = 0
                # get highest value when comparing last_end offset to current offset
                if text_size == (0,0,0,0):
                    y_end = (chars[-1].line[0]+chars[-1].line[1] + metrics[1] + self.spcaing, metrics[0]-metrics[1])
                else:
                    if last_end[1]-text_size[1] != 0 and last_end[-1]-text_size[-1] == 0:
                        offset = max(-((last_end[1]) - metrics[1]), (text_size[1]) - metrics[1], key=abs)
                        if abs(offset) < metrics[1]-1:
                            offset = 0
                        else:
                            sign = int(math.copysign(1, offset))
                            if offset not in (1,-1):
                                offset = sign*abs(offset)
                            else:
                                offset = 0
                    elif (last_end[-1]-text_size[-1] != 0 and last_end[1]-text_size[1] == 0) or (last_end[1]-text_size[1] != 0 and last_end[-1]-text_size[-1] != 0):
                        offset = text_size[-1]-last_end[-1]
                    y_end = (chars[-1].line[0]+chars[-1].line[1] + (text_size[1]-text_size[-1])+metrics[0] + self.spcaing+offset, text_size[-1]-text_size[1])
                    last_end = text_size
            else:
                y_end = (text_size[1], text_size[-1]-text_size[1])
                last_end = text_size

            bbox.x = max(bbox.x, text_size[2])
            chars.append(LineBounds(y_end, x_ends))
            workingIndex += 1

        if len(chars) > 0:
            bbox.y = (chars[-1].line[0]+chars[-1].line[1]) + metrics[1]-1
        return (lines, chars, bbox)

    def render(self, text: str) -> Union[Image.Image, List]:
        font = ImageFont.truetype(self.font, self.font_size)
        wrapped_text = self.wrap(text, font)
        lines = wrapped_text[0]
        size = wrapped_text[2]

        img = Image.new("RGBA", self.size, (0,0,0,0))

        text = '\n'.join(lines)
        if self.is_expandable:
            img = img.resize((max(size.x,self.size[0]), max(size.y,self.size[1])))
        
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), text, (255,255,255), font=font, spacing=self.spcaing)
        
        return (img,) + wrapped_text