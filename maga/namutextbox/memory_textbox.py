from typing import Optional, Any
from PIL import Image, ImageDraw

import libs.utils.imageutil as imageutil
from libs.pilutils.label import LabelContainer
from libs.utils.vector import Vector2D

class MemoryTextbox():
    def __init__(self, avatar: Optional[Any], font: str, text: str, asterisk: bool, name: str, animated: bool):
        self.name = name
        self.avatar = avatar
        self.font = font
        self.text = text
        self.asterisk = asterisk
        self.animated = animated

    def render(self):
        avatar = self.avatar
        avatar = imageutil.force_thumbnail(avatar, (50, 50), resample=Image.BICUBIC)

        colors = [
            (0, 0, 0),
            (255, 0, 0),
            (252, 166, 0),
            (255, 255, 0),
            (0, 192, 0),
            (255, 255, 255),
            (0, 60, 255),
            (66, 252, 255),
            (213, 53, 217)
            ]

        # Flatten the palette and pad to 768 if needed
        flat_palette = []
        for r, g, b in colors:
            flat_palette.extend([r, g, b])

        # Pad the palette to 768 elements if it's shorter
        # This example pads with the last color's values
        if len(flat_palette) < 768:
            last_color_values = flat_palette[-3:] if flat_palette else [0, 0, 0] # Default to black if no colors
            flat_palette.extend(last_color_values * ((768 - len(flat_palette)) // 3))

        p_img = Image.new('P', (100, 100))
        p_img.putpalette(flat_palette)

        avatar = avatar.convert('RGB')
        avatar = avatar.quantize(palette=p_img)
        
        font = self.font
        text = self.text
        
        gradient = imageutil.gradient((54, 54, 103),(0, 0, 200),(50,50)).convert("RGBA")

        size = Vector2D(1280,0)

        avatar_pos: Vector2D = Vector2D(48,48)
        avatar = imageutil.force_thumbnail(avatar, (200, 200), resample=Image.NEAREST)
        avatar_size = Vector2D.from_tuple(avatar.size)
        
        text_pos = Vector2D(avatar_pos.x+avatar_size.x+32, avatar_pos.y)

        # FIX: FONT SIZE IS NOT DYNAMIC
        asterisk = LabelContainer(font, 64, (0,0), spacing=24)
        asterisk_raw = asterisk.render("* ")
        asterisk = asterisk_raw[0]
        asterisk_size = Vector2D.from_tuple(asterisk.size)
        shadows = Image.new("RGBA", asterisk_size.to_tuple())
        for line in range(len(asterisk_raw[2])):
            shadows.paste(gradient.resize((asterisk_size.x, asterisk_raw[2][line].line[1])), (0, asterisk_raw[2][line].line[0]))
        asterisk_shadows = imageutil.mask(asterisk, shadows)

        # FIX: FONT SIZE IS NOT DYNAMIC
        label = LabelContainer(font, 64, (size.x-(avatar_size.x+avatar_pos.x+asterisk_size.x+64+64), 0), spacing=24)
        text_raw = label.render(text)
        text = text_raw[0]
        text_size = Vector2D.from_tuple(text.size)

        size = Vector2D(1280,max(text_size.y, avatar_size.y+(48+49)))

        name = LabelContainer(font, 64, (0,0), spacing=24, wrap=False)
        name_raw = name.render(self.name)
        name = name_raw[0]
        name_size = Vector2D.from_tuple(name.size)
        shadows = Image.new("RGBA", name_size.to_tuple())
        for line in range(len(name_raw[2])):
            shadows.paste(gradient.resize((name_size.x, name_raw[2][line].line[1])), (0, name_raw[2][line].line[0]))
        name_shadows = imageutil.mask(name, shadows)

        nameplate_size = (name_size+Vector2D(86,48))
        nameplate = Image.new("RGBA", nameplate_size.to_tuple(), (0,0,0,255))
        name_pos = Vector2D(int((nameplate_size - name_size).x / 2),int((nameplate_size - name_size).y / 2))
        nameplate.paste(name_shadows, (name_pos + Vector2D(1,1)).to_tuple(), name_shadows)
        nameplate.paste(name, name_pos.to_tuple(), name)
        draw = ImageDraw.Draw(nameplate)
        draw.rectangle((0,0)+nameplate_size.to_tuple(), outline='white', width=12)

        main = Image.new("RGBA", size.to_tuple(), (0,0,0,255))
        draw = ImageDraw.Draw(main)
        draw.rectangle((0,0)+size.to_tuple(), outline='white', width=12)
        main.paste(asterisk_shadows, (text_pos.x+1, text_pos.y+1), asterisk_shadows)
        main.paste(asterisk, text_pos.to_tuple(), asterisk)
        try:
            main.paste(avatar, (avatar_pos.x, avatar_pos.y), avatar)
        except:  # noqa: E722
            main.paste(avatar, (avatar_pos.x, avatar_pos.y))
        
        img = Image.new("RGBA", (size.x, size.y+nameplate_size.y-11))
        img.paste(main, (0,0), main)
        img.paste(nameplate, (int((size.x - nameplate_size.x) / 2), size.y-11))

        shadows = Image.new("RGBA", text.size)
        shadows = imageutil.to_numpy(shadows)
        for line in range(len(text_raw[2])):
            if text_raw[2][line].line[1] > 0:
                shadows = imageutil.paste_rgba_array(shadows, gradient.resize((text_size.x, text_raw[2][line].line[1]), Image.NEAREST), 0, text_raw[2][line].line[0])
        shadows = Image.fromarray(shadows)
        shadow_text = imageutil.mask(text, shadows)

        composed_text = Image.new("RGBA", text.size)
        composed_text.paste(shadow_text, (1, 1), shadow_text)
        composed_text.paste(text, (0,0), text)

        c = imageutil.copy_mut(img)
        c.paste(composed_text, (text_pos.x + asterisk_size.x, text_pos.y), composed_text)
        imgs = [c]
        draw = ImageDraw.Draw(composed_text)
        if self.animated:
            text_raw[2].reverse()
            for line in text_raw[2]:
                for char in reversed(range(len(line.chars))):
                    chars = line.chars
                    draw.rectangle((chars[char][0], line.line[0], chars[min(len(chars)-1, char+1)][0]+chars[min(len(chars)-1, char+1)][1], line.line[0]+line.line[1]), (0,0,0,0))
                    c = imageutil.copy_mut(img)
                    c.paste(composed_text, (text_pos.x + asterisk_size.x, text_pos.y), composed_text)
                    imgs.append(c)
            imgs.reverse()

        return imgs

# img.paste(linestart, ( (text_pos[0] + asterisk_size[0]), text_pos[1]), linestart)

# linestart = Image.new("RGBA", text.size, (0,0,0,255))
# red = Image.new("RGBA", (50,50), (255,0,0,255))
# blue = Image.new("RGBA", (50,50), (0,255,0,255))
# for line in range(len(text_raw[2])):
#     passed = False
#     for px in range(text.size[0]):
#         if text.getpixel((px, text_raw[2][line][0]))[3] > 0:
#             passed = True
#             break
#     if passed: linestart.paste(blue.resize((text.size[0], 1)), (0, text_raw[2][line][0]))
#     else: linestart.paste(red.resize((text.size[0], 1)), (0, text_raw[2][line][0]))
