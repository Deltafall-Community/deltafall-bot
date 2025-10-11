import numpy
from typing import Tuple
from PIL import Image, ImageFile

import libs.utils.imageutil as imageutil 

def scale(img: ImageFile, size: Tuple[int, int]):
    pixels = imageutil.to_numpy(img)
    pixels = __scale_and_repeat(pixels, (size[0], size[1]))
    pixels = numpy.ascontiguousarray(pixels) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.fromarray(pixels)

def __scale_and_repeat(img, new_size):
    old_h, old_w = img.shape[:2]
    new_w, new_h = new_size
    repeat_h = (new_h // old_h) + 1
    repeat_w = (new_w // old_w) + 1

    tiled_img = numpy.tile(img, (repeat_h, repeat_w, 1))
    return tiled_img[:new_h, :new_w]