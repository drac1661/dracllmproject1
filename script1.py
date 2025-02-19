import os
from PIL import Image

# Ensuring the image and output paths are within permitted './data' directory
def secure_path(path):
    return os.path.join('./data', os.path.basename(path))

# Input and output paths
input_path = secure_path('credit_card.png')
output_path = secure_path('cmp.png')

# Compress and save the image
def compress_image(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            img.save(output_path, optimize=True, quality=65)
    except Exception as e:
        print(f'Error compressing image: {e}')

compress_image(input_path, output_path)