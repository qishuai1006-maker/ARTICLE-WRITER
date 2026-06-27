import sys
from PIL import Image

def crop_center_16_9(input_path, output_path):
    img = Image.open(input_path).convert('RGB')
    w, h = img.size
    # Target is 1024x576 for 1024x1024 input
    target_w = w
    target_h = int(w * 9 / 16)
    
    top = (h - target_h) // 2
    bottom = top + target_h
    
    img_cropped = img.crop((0, top, w, bottom))
    img_cropped.save(output_path, quality=95)
    print(f"Saved {output_path} with size {img_cropped.size}")

if __name__ == "__main__":
    crop_center_16_9(sys.argv[1], sys.argv[2])
