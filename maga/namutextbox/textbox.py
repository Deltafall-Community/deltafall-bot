import toml
from PIL import Image, ImageDraw
from typing import Optional, Any

from libs.pilutils.nineslicescaling import NineSliceScaling
from libs.pilutils.label import LabelContainer
from libs.utils.vector import Vector2D
import libs.utils.imageutil as imageutil

class Textbox():
    def __init__(self, config_path: str, avatar: Optional[Any], font: str, text: str, asterisk: bool, animated: bool):
        self.config = toml.load(open(config_path, "r"))
        self.avatar = avatar
        self.font = font
        self.text = text
        self.asterisk = asterisk
        self.animated = animated

    def render(self):
        config = self.config
        avatar = self.avatar
        font = self.font
        text = self.text
        
        gradient = imageutil.gradient((54, 54, 103),(0, 0, 200),(50,50)).convert("RGBA")

        textbox_texture = Image.open(config["texture"])
        size = Vector2D(config["size"]["x"],config["size"]["y"])
        scale = config["scale"]
        
        margins = config["margins"]
        margin_left = margins["left"]
        margin_right = margins["right"]
        margin_top = margins["top"]
        margin_bottom = margins["bottom"]

        text_position = config["text_position"]
        text_position = Vector2D(text_position["x"], text_position["y"])

        avatar_pos: Vector2D = Vector2D(0,0)
        avatar_size: Vector2D = Vector2D(0,0)
        if avatar:
            padding = Vector2D((margin_left + scale) * 2.0, (margin_bottom * scale) * 2.5)
            avatar = imageutil.force_thumbnail(avatar, (int(size.y - padding.y), int(size.y - padding.y)), resample=Image.NEAREST)
            avatar_size = Vector2D.from_tuple(avatar.size)
            avatar_pos = Vector2D(int(padding.x), int((size.y - avatar_size.y) / 2 ))
        
        text_pos = Vector2D(int(text_position.x * scale), int(text_position.y * scale))
        if avatar:
            text_pos = Vector2D(int( ((text_position.x - margin_left) * scale) + (avatar_size.x + avatar_pos.x)), int(text_position.y * scale))

        asterisk: bool = self.asterisk
        asterisk_size: Vector2D = Vector2D(0,0)
        if asterisk:
            # FIX: FONT SIZE IS NOT DYNAMIC
            asterisk = LabelContainer(font, 32, (0,0), spacing=8)
            asterisk_raw = asterisk.render("* ")
            asterisk = asterisk_raw[0]
            asterisk_size = Vector2D.from_tuple(asterisk.size)

            shadows = Image.new("RGBA", asterisk_size.to_tuple())
            for line in range(len(asterisk_raw[2])):
                shadows.paste(gradient.resize((asterisk_size.x, asterisk_raw[2][line].line[1])), (0, asterisk_raw[2][line].line[0]))
            asterisk_shadows = imageutil.mask(asterisk, shadows)

        # FIX: FONT SIZE IS NOT DYNAMIC
        # - 32 in x offset is from font size
        label = LabelContainer(font, 32, (( size.x - int((margin_left + margin_right) * scale) ) - asterisk_size.x - (avatar_size.y + avatar_pos.y) - 32, size.y - text_pos.y - margin_bottom), spacing=8)
        text_raw = label.render(text)
        text = text_raw[0]
        text_size = Vector2D.from_tuple(text.size)

        overflow = text_size.y - (size.y - margin_bottom - text_pos.y)
        size.y += max(0,overflow)
        if overflow > 0:
            size.y += margin_bottom + 8 + 6 # 6 is arbitary number from font rendering (would be nice to have this apply dynamically)

        nineslice = NineSliceScaling((margin_left, margin_top, margin_right, margin_bottom), (size.x, size.y), scale)
        box = nineslice.render(textbox_texture)
        box_size = Vector2D.from_tuple(box.size)
        img = Image.new("RGBA", box.size, (0,0,0,255))
        if asterisk:
            img.paste(asterisk_shadows, (text_pos.x+1, text_pos.y+1), asterisk_shadows)
            img.paste(asterisk, text_pos.to_tuple(), asterisk)
        if avatar:
            try:
                img.paste(avatar, (avatar_pos.x, int(avatar_pos.y + (box_size.y - config["size"]["y"] + 1) / 2.0)), avatar)
            except:  # noqa: E722
                img.paste(avatar, (avatar_pos.x, int(avatar_pos.y + (box_size.y - config["size"]["y"] + 1) / 2.0)))

        shadows = Image.new("RGBA", text.size)
        shadows = imageutil.to_numpy(shadows)
        for line in range(len(text_raw[2])):
            if text_raw[2][line].line[1] > 0:
                shadows = imageutil.paste_rgba_array(shadows, gradient.resize((text_size.x, text_raw[2][line].line[1]), Image.NEAREST), 0, text_raw[2][line].line[0])
        shadows = Image.fromarray(shadows)
        shadow_text = imageutil.mask(text, shadows)
        
        img.paste(box, (0,0), box)

        # using the red "border" from the box to mask out the excess part
        box_array = imageutil.to_numpy(box)
        image_array = imageutil.to_numpy(img)
        keyed_box_array = imageutil.get_color_key_mask_from_array(box_array, (255,0,0))
        composed = imageutil.mask_image_array(keyed_box_array, image_array)
        
        composed_text = Image.new("RGBA", text.size)
        composed_text.paste(shadow_text, (1, 1), shadow_text)
        composed_text.paste(text, (0,0), text)

        c = imageutil.copy_mut(composed)
        c.paste(composed_text, (text_pos.x + asterisk_size.x, text_pos.y), composed_text)
        imgs = [c]
        draw = ImageDraw.Draw(composed_text)
        if self.animated:
            text_raw[2].reverse()
            for line in text_raw[2]:
                for char in reversed(range(len(line.chars))):
                    chars = line.chars
                    draw.rectangle((chars[char][0], line.line[0], chars[min(len(chars)-1, char+1)][0]+chars[min(len(chars)-1, char+1)][1], line.line[0]+line.line[1]), (0,0,0,0))
                    c = imageutil.copy_mut(composed)
                    c.paste(composed_text, (text_pos.x + asterisk_size.x, text_pos.y), composed_text)
                    imgs.append(c)
            imgs.reverse()

        return imgs