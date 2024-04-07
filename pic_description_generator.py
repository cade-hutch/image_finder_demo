import openai
import base64
import requests
import os
import json
import time

from langchain_community.embeddings import OpenAIEmbeddings

from utils import reduce_png_quality, get_descriptions_from_json, create_and_store_embeddings_to_pickle, add_new_descr_to_embedding_pickle, remove_description_pretense


# IMAGE_QUESTION = """The following is an image from an Apple iPhone camera roll. First, determine if the image is a screenshot or was taken from the camera. If the image is a screenshot, describes it's contents and determine what application is being displayed.
# If the image is taken from a camera, describe all of it's contents and include elements (if appplicable) such as the main subject, what is in the foreground and background, and the location of the image.
# The first sentence of your output should be either "This is a screenshot." or "This is NOT a screenshot." Then, provide the rest of your answer.
# """

IMAGE_QUESTION = 'As descriptive as possible, describe the contents of this image in a single sentence.'

def headers(api_key):
  return {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
  }


def default_payload(image_question):
  return {
    "model": "gpt-4-vision-preview",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": f"{image_question}"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": ""
            }
          }
        ]
      }
    ],
    "max_tokens": 400
  }


def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')


def append_to_json_file(file_path, data):
    try:
        #load existing data from the file
        with open(file_path, 'r') as file:
            if os.path.getsize(file_path) != 0:
              existing_data = json.load(file)
            else:
                existing_data = []
    except FileNotFoundError:
        existing_data = []

    existing_data.append(data)

    #write the combined data back to the file
    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)


def get_file_names_from_json(json_file_path):
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

            # Check if the data is a dictionary or a list of dictionaries
            if isinstance(data, dict):
                # If it's a dictionary, search for "file_name" keys
                return [data.get("file_name", None)]
            elif isinstance(data, list):
                # If it's a list, search for "file_name" keys in each dictionary
                return [item.get("file_name", None) for item in data]
            else:
                print("Invalid JSON format. Expected a dictionary or a list of dictionaries.")
                return None

    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


def find_new_pic_files(images_dir, descriptions_file):
    print('descr_file:', descriptions_file)
    existing_pictures = get_file_names_from_json(descriptions_file)
    if existing_pictures is None:
        existing_pictures = []

    print(f"Descriptions exist for {len(existing_pictures)} images.")
    new_images = []
    for pic in os.listdir(images_dir):
       if pic not in existing_pictures and pic.endswith('.png') and '.ignore' not in pic:
           new_images.append(pic)
    print(f"Found {len(new_images)} new images.")
    return new_images


def rename_files_in_directory(directory_path):
    """
    Renames all files in the specified directory by replacing spaces with underscores.

    Args:
    directory_path (str): The path to the directory whose files need to be renamed.
    """
    print('renaming uploaded images')
    # Check if the provided path is indeed a directory
    if not os.path.isdir(directory_path):
        print("The provided path is not a directory.")
        return

    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        # Check if it's a file and not a directory
        if os.path.isfile(file_path):
            # Replace spaces with underscores in the filename
            new_filename = filename.replace(' ', '_')
            new_file_path = os.path.join(directory_path, new_filename)

            # Rename the file
            #TODO: need for all????
            os.rename(file_path, new_file_path)
            if file_path != new_file_path:
                print(f"Renamed '{filename}' to '{new_filename}'")


def get_new_pics_dir(images_dir):#TODO: rename
    base_dir = os.path.dirname(os.path.dirname(images_dir))
    descriptions_folder_path = os.path.join(base_dir, 'json')

    base_name = os.path.basename(images_dir)
    json_info_file_path = os.path.join(descriptions_folder_path, base_name + '_info.json')
    json_description_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')

    new_pics = find_new_pic_files(images_dir, json_description_file_path)
    return new_pics


def generate_image_descrptions(new_pics, images_dir, api_key):
    base_dir = os.path.dirname(os.path.dirname(images_dir))
    descriptions_folder_path = os.path.join(base_dir, 'json')
    base_name = os.path.basename(images_dir)
    json_info_file_path = os.path.join(descriptions_folder_path, base_name + '_info.json')
    json_description_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')
    #client = openai.OpenAI(api_key=api_key) #TODO: which method is faster?

    for i, pic in enumerate(new_pics):
      start_time = time.perf_counter()
      print('({}/{}) Getting description for {}'.format(i+1, len(new_pics), pic))
      img_path = os.path.join(images_dir, pic)
      reduce_png_quality(img_path, img_path)
      base64_image = encode_image(img_path)
      start_time_req = time.perf_counter()
      payload = default_payload(IMAGE_QUESTION)
      payload['messages'][0]['content'][1]['image_url']['url'] = f"data:image/jpeg;base64,{base64_image}"
      response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers(api_key), json=payload)
      stop_time_req = time.perf_counter()
      request_time = round(stop_time_req - start_time_req, 2)
      print('response recieved for {} in {} seconds'.format(pic, request_time))
      append_to_json_file(json_info_file_path, response.json())
      try:
        response_description = response.json()["choices"][0]["message"]["content"]
        response_description = remove_description_pretense(response_description)
        description_obj = {
          "file_name" : f"{pic}",
          "description" : f"{response_description}"
        }
        append_to_json_file(json_description_file_path, description_obj)
        end_time = time.perf_counter()
        yield (response_description, round(end_time - start_time, 2))

      except KeyError as e:
         print(f"KeyError occurred: {e}")
         print(response.json())
         yield 0
         #return [e] yield this?


def update_embeddings(api_key, embeddings_pickle_file, new_descriptions):
    print('updating embeddings')
    embeddings_obj = OpenAIEmbeddings(api_key=api_key)
    add_new_descr_to_embedding_pickle(embeddings_obj, embeddings_pickle_file, new_descriptions)
    

def create_embeddings(api_key, embeddings_pickle_file, json_description_file_path):
    print('creating embeddings')
    embeddings_obj = OpenAIEmbeddings(api_key=api_key)
    descriptions = get_descriptions_from_json(json_description_file_path)
    create_and_store_embeddings_to_pickle(embeddings_obj, embeddings_pickle_file, descriptions)


def handle_embeddings(api_key, base_name, new_descriptions, json_description_file_path):
    start_time_pickle = time.perf_counter()
    embeddings_obj = OpenAIEmbeddings(api_key=api_key)
    embedding_pickles_folder_path = os.path.join(os.path.dirname(os.path.dirname(json_description_file_path)), 'embeddings')
    pickle_file = os.path.join(embedding_pickles_folder_path, base_name + '.pkl')
    if os.path.exists(pickle_file):
        add_new_descr_to_embedding_pickle(embeddings_obj, pickle_file, new_descriptions)
    else:
        descriptions = get_descriptions_from_json(json_description_file_path)
        create_and_store_embeddings_to_pickle(embeddings_obj, pickle_file, descriptions)
    end_time_pickle = time.perf_counter()
    print(f"finished creating/adding embeddings in {round(end_time_pickle - start_time_pickle, 2)}")