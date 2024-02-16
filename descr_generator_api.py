import os

import pic_description_generator as pdg
from create_owner_profile import create_owner_profile


def are_all_files_png(directory_path):
    if not os.path.isdir(directory_path):
        print(f"The path {directory_path} is not a valid directory.")
        return False

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        # Check if it's a file and if the extension is not .png
        if os.path.isfile(file_path) and not filename.lower().endswith('.png'):
            if not filename.endswith('.DS_Store'):
                
                return False
    return True


def create_file(path):
    if not os.path.exists(path):
        try:
            with open(path, 'w') as file:
                pass
            print(f"File created at {path}")
        except IOError as e:
            print(f"Failed to create file: {e}")


if __name__ == "__main__":
    images_path = os.getcwd()
    #TODO: verify dir has images
    if not are_all_files_png(images_path):
        print('invalid folder: contains files that are not pngs')
        exit()

    user_go = input(f"Generate descriptions for {os.path.basename(images_path)}. Press any key to continue:")
    create_profile_input = input('Generate image owner profile? [y/n]:')
    
    pdg.rename_files_in_directory(images_path)

    generate_total_time = pdg.generate_image_descrptions(images_path)

    print('done generating descriptions.')
    print(f"Total generation time: {generate_total_time}")
    if create_profile_input == 'y':
        print('Creating profile file.')
        create_owner_profile(images_path)
        print('Profile JSON file created.')
    