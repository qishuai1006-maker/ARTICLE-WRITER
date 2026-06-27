from PIL import Image
import sys

def crop_to_16_9(input_path, output_path):
    img = Image.open(input_path)
    w, h = img.size
    target_ratio = 16.0 / 9.0
    current_ratio = w / float(h)
    
    if current_ratio > target_ratio:
        # Image is too wide
        new_w = int(target_ratio * h)
        offset = (w - new_w) // 2
        crop_box = (offset, 0, w - offset, h)
    else:
        # Image is too tall (e.g., 1:1 square)
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        crop_box = (0, offset, w, h - offset)
        
    cropped_img = img.crop(crop_box)
    cropped_img.save(output_path)
    print(f"Cropped successfully to {output_path}")

input_img = "/Users/ltn/.gemini/antigravity-ide/brain/12792960-52e4-4e48-9e14-9cb25799c62f/fridge_cover_raw_1781604558087.png"
output_img = "/Users/ltn/Library/CloudStorage/GoogleDrive-qishuai1006@gmail.com/我的云端硬盘/Super Writer/outputs/封面图_16比9头条定制版.png"

try:
    crop_to_16_9(input_img, output_img)
except Exception as e:
    print(f"Error: {e}")
