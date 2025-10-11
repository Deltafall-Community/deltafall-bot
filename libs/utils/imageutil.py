import numpy
from PIL import Image

# fast to numpy
# special thanks to https://uploadcare.com/blog/fast-import-of-pillow-images-to-numpy-opencv-arrays/
def to_numpy(im: Image):
    im.load()
    # unumpyack data
    e = Image._getencoder(im.mode, 'raw', im.mode)
    e.setimage(im.im)
    # NumPy buffer for the result
    shape, typestr = Image._conv_type_shape(im)
    data = numpy.empty(shape, dtype=numpy.dtype(typestr))
    mem = data.data.cast('B', (data.data.nbytes,))
    bufsize, s, offset = 65536, 0, 0
    while not s:
        l, s, d = e.encode(bufsize)  # noqa: E741
        mem[offset:offset + len(d)] = d
        offset += len(d)
    if s < 0:
        raise RuntimeError("encoder error %d in tobytes" % s)
    return data

def copy(img: Image):
    img_array = to_numpy(img)
    img_array = numpy.ascontiguousarray(img_array) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.fromarray(img_array)

def copy_mut(img: Image):
    img_array = to_numpy(img)
    img_array = numpy.ascontiguousarray(img_array) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.frombytes(img.mode, img.size, memoryview(img_array))

def paste(bg_img, fg_img, x, y):
    bg_arr = to_numpy(bg_img)
    fg_arr = to_numpy(fg_img)
    h, w = fg_arr.shape[:2]
    bg_arr[y:y+h, x:x+w] = fg_arr
    img_array = numpy.ascontiguousarray(bg_arr) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.fromarray(img_array)

def paste_rgba(bg_img: Image.Image, fg_img: Image.Image, x: int, y: int) -> Image.Image:
    # Convert to numpy arrays
    bg_arr = to_numpy(bg_img)
    fg_arr = to_numpy(fg_img)

    h_fg, w_fg = fg_arr.shape[:2]
    h_bg, w_bg = bg_arr.shape[:2]

    # Clip paste region if it goes out of bounds
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w_fg, w_bg), min(y + h_fg, h_bg)

    if x1 >= x2 or y1 >= y2:
        return bg_img.copy()  # Nothing to paste

    # Adjust fg crop to match clipped area
    fg_crop_x1 = x1 - x
    fg_crop_y1 = y1 - y
    fg_crop_x2 = fg_crop_x1 + (x2 - x1)
    fg_crop_y2 = fg_crop_y1 + (y2 - y1)

    fg_sub = fg_arr[fg_crop_y1:fg_crop_y2, fg_crop_x1:fg_crop_x2]
    bg_sub = bg_arr[y1:y2, x1:x2]

    # Alpha blending
    alpha_fg = fg_sub[..., 3:4] / 255.0
    alpha_bg = 1.0 - alpha_fg

    blended = alpha_fg * fg_sub[..., :3] + alpha_bg * bg_sub[..., :3]
    out_alpha = fg_sub[..., 3:4] + alpha_bg * bg_sub[..., 3:4]

    # Combine color and alpha
    result = numpy.concatenate([blended, out_alpha], axis=-1)
    bg_arr[y1:y2, x1:x2] = result

    return Image.fromarray(bg_arr)

def paste_rgba_array(bg_arr: Image.Image, fg_img: Image.Image, x: int, y: int) -> Image.Image:
    fg_arr = to_numpy(fg_img)

    h_fg, w_fg = fg_arr.shape[:2]
    h_bg, w_bg = bg_arr.shape[:2]

    # Clip paste region if it goes out of bounds
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w_fg, w_bg), min(y + h_fg, h_bg)

    if x1 >= x2 or y1 >= y2:
        return bg_arr

#    # Adjust fg crop to match clipped area
    fg_crop_x1 = x1 - x
    fg_crop_y1 = y1 - y
    fg_crop_x2 = fg_crop_x1 + (x2 - x1)
    fg_crop_y2 = fg_crop_y1 + (y2 - y1)

    fg_sub = fg_arr[fg_crop_y1:fg_crop_y2, fg_crop_x1:fg_crop_x2].astype(numpy.uint16)
    bg_sub = bg_arr[y1:y2, x1:x2].astype(numpy.uint16)
    
    # Convert alpha to uint8 and broadcast
    alpha_fg = fg_sub[..., 3:4].astype(numpy.uint16)
    inv_alpha_fg = 255 - alpha_fg

    # Blend using integer math (no float32!)
    blended_rgb = ((fg_sub[..., :3] * alpha_fg +
                    bg_sub[..., :3] * inv_alpha_fg) // 255)

    # Alpha output
    blended_alpha = numpy.clip((fg_sub[..., 3:4] +
                             (bg_sub[..., 3:4] * inv_alpha_fg) // 255), 0, 255)

    # Combine
    result = numpy.concatenate([blended_rgb, blended_alpha], axis=-1)
    bg_arr[y1:y2, x1:x2] = result

    return bg_arr

def force_thumbnail(img: Image, target_size, resample=Image.NEAREST):
    img_ratio = img.width / img.height
    target_ratio = target_size[0] / target_size[1]

    if img_ratio > target_ratio:
        new_width = target_size[0]
        new_height = int(target_size[0] / img_ratio)
    else:
        new_height = target_size[1]
        new_width = int(target_size[1] * img_ratio)

    return img.resize((new_width, new_height), resample)

def gradient(color1: tuple, color2: tuple, size: tuple):
    gradient = numpy.zeros((size[0],size[1],3), numpy.uint8)
    gradient[:,:,0] = numpy.linspace(color1[0], color2[0], 50, dtype=numpy.uint8)[:, numpy.newaxis]
    gradient[:,:,1] = numpy.linspace(color1[1], color2[1], 50, dtype=numpy.uint8)[:, numpy.newaxis]
    gradient[:,:,2] = numpy.linspace(color1[2], color2[2], 50, dtype=numpy.uint8)[:, numpy.newaxis]
    return Image.fromarray(gradient)

def mask(image1: Image, image2: Image):
    image1_mask = (to_numpy(image1)[:, :, 3] == 0)
    image2_array = to_numpy(image2)
    image2_array[:, :, 3][image1_mask] = 0 
    masked_image_array = numpy.ascontiguousarray(image2_array) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.fromarray(masked_image_array)

def color_key(image: Image, color: tuple):
    image_array = to_numpy(image)
    keyed_image_array = get_color_key_mask_from_array(image_array, color)
    return mask_image_array(keyed_image_array, image_array)

def get_color_key_mask_from_array(image_array, color: tuple):
    keyed_image_array = (image_array[:, :, 0] == color[0]) & (image_array[:, :, 1] == color[1]) & (image_array[:, :, 2] == color[2])
    return keyed_image_array

def mask_image_array(mask, image):
    image[mask, 3] = 0
    masked_image_array = numpy.ascontiguousarray(image) # pillow creates a copy if the array isn't contiguous which is really slow
    return Image.fromarray(masked_image_array)