import math
from enum import Enum
from typing import Tuple
from PIL import Image

import libs.pilutils.repeatscaling as repeatscaling

class ScalingMode(Enum):
    STRETCH = 1
    REPEAT = 2
    MIRROR = 3
    BLANK = 4

class NineSliceScaling():
    def __init__(self, margins: Tuple[int, int, int, int], size: Tuple[int, int], scale: float = 1.0):
        self.margins = margins
        self.size = size
        self.scale = scale

    def render(self, texture: Image):
        margin_left = math.floor(self.margins[0] * self.scale)
        margin_top = math.floor(self.margins[1] * self.scale)
        margin_right = math.floor(self.margins[2] * self.scale)
        margin_bottom = math.floor(self.margins[3] * self.scale)

        image = texture
        image = image.resize((math.floor(image.size[0] * self.scale), math.floor(image.size[1] * self.scale)), Image.Resampling.NEAREST)
        size = image.size

        top_left = image.crop((0,0,margin_left,margin_top))
        top_center = image.crop(( math.floor( (size[0] - margin_top) / 2 ), 0, math.floor( (size[0] + margin_top) / 2), margin_top ))
        top_right = image.crop((size[0] - margin_right,0,size[0],margin_right))
        center_left = image.crop((0, margin_left, math.floor( (size[0] + margin_left) / 2), size[1] - margin_left ))
        center = image.crop( (margin_left, margin_top, (size[0] - margin_right), (size[1] - margin_bottom) ) )
        center_right = image.crop( (size[0] - margin_right, math.floor( (size[1] - margin_top) / 2 ), size[0], math.floor( (size[1] + margin_top) / 2 ) ) )
        bottom_left = image.crop( (0, size[1] - margin_left, margin_left, size[1]) )
        bottom_center = image.crop(( math.floor( (size[0] - margin_bottom) / 2 ), size[1] - margin_bottom, math.floor( (size[0] + margin_bottom) / 2), size[1] ))
        bottom_right = image.crop((size[0] - margin_right, size[1] - margin_bottom, size[0], size[1]))

        img = Image.new("RGBA", self.size)
        size = img.size

        img.paste(top_left, (0, 0))
        img.paste(repeatscaling.scale(top_center, (size[0] - top_left.size[0], top_center.size[1])), (top_left.size[0], 0))
        img.paste(top_right, (size[0] - top_right.size[0], 0))
        img.paste(repeatscaling.scale(center_left, (center_left.size[0], size[1] - top_left.size[1])), (0, top_left.size[1]))
        img.paste(repeatscaling.scale(center, (size[0] - top_left.size[0] - bottom_left.size[0] - top_right.size[0] - bottom_right.size[0],  size[1] - top_left.size[1] - bottom_left.size[1] - top_right.size[1] - bottom_right.size[1])), (top_left.size[0],top_left.size[1]))
        img.paste(repeatscaling.scale(center_right, (center_right.size[0], size[1] - bottom_left.size[1])), (size[0] - center_right.size[0], top_right.size[1]))
        img.paste(bottom_left, (0,size[1] - bottom_left.size[1]))
        img.paste(repeatscaling.scale(bottom_center, (size[0] - bottom_left.size[0], bottom_center.size[1] ) ), (bottom_left.size[0], size[1] - bottom_center.size[1]))
        img.paste(bottom_right, (size[0] - bottom_right.size[0],size[1] - bottom_left.size[1]))

        return img