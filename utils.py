import os
import json

from PIL import Image
from openai import OpenAI

_10_MB = 10*1024*1024

def is_valid_image_directory(images_dir_path):
    is_dir = os.path.isdir(images_dir_path)
    is_all_pngs = are_all_files_png(images_dir_path)
    is_correct_path = os.path.dirname(images_dir_path).endswith(os.path.join('image_finder_demo','image_base'))
    if is_dir and is_all_pngs and is_correct_path:
        return True
    else:
        #TODO: Error messages
        return False


def are_all_files_png(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        # Check if it's a file and if the extension is not .png
        if os.path.isfile(file_path) and not filename.lower().endswith('.png'):
            if not filename.endswith('.DS_Store'):
                print('invalid folder: contains files that are not pngs')
                return False
    return True


def descriptions_file_up_to_date(images_dir, json_file_path):
    json_file_names = []
    with open(json_file_path, 'r') as file:
        data = json.load(file)
        for element in data:
            if 'file_name' in element:
                json_file_names.append(element['file_name'])
    
    png_names = []
    for entry in os.listdir(images_dir):
        # Construct the full path of the entry
        full_path = os.path.join(images_dir, entry)
        # Check if the entry is a file and has a .png extension
        if os.path.isfile(full_path) and entry.lower().endswith('.png'):
            png_names.append(entry)

    if len(png_names) != len(json_file_names):
        return False
    
    return sorted(json_file_names) == sorted(png_names)


def retrieve_or_generate(images_dir, json_file_path):
    if not os.path.exists(json_file_path):
        return 'generate'
    if not descriptions_file_up_to_date(images_dir, json_file_path):
        return 'generate'
    else:
        return 'retrieve'
    #compare length of descriptions with number of photos


def validate_openai_api_key(openai_api_key):
    print(f"validating api key: {openai_api_key}")
    #TODO: send request
    return True


def reduce_png_quality(file_path, output_path, quality_level=50, max_size=_10_MB, scale_factor=0.6):
    """
    Reduces the quality of a PNG file.
    first attempt with Image.save(), then use Image.resize()
    """
    file_size = os.path.getsize(file_path)
    print("file size: {}".format(file_size))

    if file_size < max_size:
        return

    with Image.open(file_path) as img:
        # Optionally, resize the image here if you want
        # img = img.resize((new_width, new_height))

        # Convert to P mode which is more efficient for PNGs
        img = img.convert('P', palette=Image.ADAPTIVE)

        #TODO: does quality_level do anything?
        img.save(output_path, quality=quality_level, optimize=True)

    file_size = os.path.getsize(output_path)
    if file_size > max_size:
        img = Image.open(output_path)

        while file_size > max_size:
            new_width = int(img.size[0] * scale_factor)
            new_height = int(img.size[1] * scale_factor)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save the image over itself
            img.save(output_path, format='PNG', optimize=True)

            file_size = os.path.getsize(output_path)
            print(f"Resized file size: {file_size / 1024**2:.2f} MB")

            # Break if the image becomes too small
            if img.size[0] < 200 or img.size[1] < 200:
                break
    

def validate_openai_api_key(openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    try:
        response = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=2
        )
        if response.choices[0].message.content:
            return True
    #TODO: erro code for invalid key is 401
    except Exception as e:
        print(f"An error occurred: {e}")
        return False