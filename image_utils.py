from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def crop_face(image, bounding_box):
    width, height = image.size
    left, top = int(bounding_box["Left"] * width), int(bounding_box["Top"] * height)
    box_width, box_height = int(bounding_box["Width"] * width), int(bounding_box["Height"] * height)
    return image.crop((left, top, left + box_width, top + box_height))

def draw_face_rectangle(image, bounding_box, similarity):
    img_width, img_height = image.size
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    left, top = img_width * bounding_box['Left'], img_height * bounding_box['Top']
    width, height = img_width * bounding_box['Width'], img_height * bounding_box['Height']

    draw.rectangle([left, top, left + width, top + height], outline="#00d400")
    draw.text((left, top), f"Similaridade: {similarity:.2f}%", font=font)

    return image
