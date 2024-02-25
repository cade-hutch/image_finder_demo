import os
import json

def is_valid_image_directory(images_dir_path):
    is_dir = os.path.isdir(images_dir_path)
    is_all_pngs = are_all_files_png(images_dir_path)
    is_correct_path = os.path.dirname(images_dir_path).endswith('image_finder_demo/image_base')
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
