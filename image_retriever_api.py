import os

from image_retriever import retrieve_and_open

CURR_DIR = os.path.dirname(os.path.dirname(os.getcwd()))
DESCRIPTIONS_FOLDER_PATH = os.path.join(CURR_DIR, 'json')

if __name__ == "__main__":
    images_dir = os.getcwd()
    base_name = os.path.basename(images_dir)
    json_file_path = os.path.join(DESCRIPTIONS_FOLDER_PATH, base_name + '_descriptions.json')
    print(json_file_path)
    if os.path.exists(json_file_path):
        retrieval_prompt = input("What would you like to find?::")
        retrieve_and_open(images_dir, json_file_path, retrieval_prompt)
    else:
        print("JSON descriptions file for this image folder does not exist.")