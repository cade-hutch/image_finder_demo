import openai
import base64
import requests
import os
import json
import time

from langchain_community.embeddings import OpenAIEmbeddings

from utils import reduce_png_quality, get_descriptions_from_json, create_and_store_embeddings_to_pickle, add_new_descr_to_embedding_pickle, remove_description_pretense

IMAGE_QUESTION = 'As descriptive as possible, describe the contents of this image in a single sentence.'

def headers(api_key):
  return {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
  }


def default_payload(image_question):
  return {
    "model": "gpt-4-turbo",
    #"model": "gpt-4o",
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


def append_to_json_info_file(file_path, data):
    try:
        with open(file_path, 'r') as file:
            if os.path.getsize(file_path) != 0:
              existing_data = json.load(file)
            else:
                existing_data = []
    except FileNotFoundError:
        existing_data = []

    existing_data.append(data)

    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)


def append_to_json_file(file_path, data):
    try:
        with open(file_path, 'r') as file:
            if os.path.getsize(file_path) != 0:
              existing_data = json.load(file)
            else:
                existing_data = {}
    except FileNotFoundError as e:
        print(f"append_to_json_file: {e}")
        existing_data = {}

    if type(existing_data) == dict:
      existing_data.update(data)
    else:
        #TODO: old json format
        append_to_old_json_file(file_path, existing_data, data)
        assert False, "deprecated JSON description file format"

    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)


def append_to_old_json_file(file_path, existing_data, data):
    #depracted JSON format(list of dicts instead if single dict)
    if not list(data.keys()) or list(data.valuess()):
        assert False, "invalid or deprecated JSON description file format"

    new_data = {
        "file_name" : list(data.keys())[0],
        "description" : list(data.valuess())[0]
    }

    # Append the new data to the existing data
    existing_data.append(new_data)

    # Write the combined data back to the file
    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)


def get_file_names_from_json(json_file_path):
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

            # Check if the data is a dict or list of dicts
            if isinstance(data, dict):
                # if dictionary, search for "file_name" keys
                return data.keys()
            elif isinstance(data, list):
                # if list, search for "file_name" keys in each dictionary
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
    if not os.path.isdir(directory_path):
        print("The provided path is not a directory.")
        return

    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        if os.path.isfile(file_path):
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
    json_description_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')

    new_pics = find_new_pic_files(images_dir, json_description_file_path)
    return new_pics


def generate_image_descrptions(new_pics, images_dir, api_key):
    base_dir = os.path.dirname(os.path.dirname(images_dir))
    descriptions_folder_path = os.path.join(base_dir, 'json')
    base_name = os.path.basename(images_dir)
    json_info_file_path = os.path.join(descriptions_folder_path, 'info', base_name + '_info.json')
    json_description_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')

    for i, pic in enumerate(new_pics):
      start_time = time.perf_counter()
      print('({}/{}) Getting description for {}'.format(i+1, len(new_pics), pic))
      img_path = os.path.join(images_dir, pic)
      reduce_png_quality(img_path, img_path)
      base64_image = encode_image(img_path)
      start_time_req = time.perf_counter()
      payload = default_payload(IMAGE_QUESTION)
      payload['messages'][0]['content'][1]['image_url']['url'] = f"data:image/jpeg;base64,{base64_image}"
      try_again = False
      try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers(api_key), json=payload)
      except Exception as e:
          print(e)
          print('error, sleeping')
          time.sleep(15)
          try_again = True
      if try_again:
        print('trying again')
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers(api_key), json=payload)
          
      stop_time_req = time.perf_counter()
      request_time = round(stop_time_req - start_time_req, 2)
      print('response recieved for {} in {} seconds'.format(pic, request_time))
      append_to_json_info_file(json_info_file_path, response.json())
      try:
        response_description = response.json()["choices"][0]["message"]["content"]
        response_description = remove_description_pretense(response_description)

        description_obj = { f"{pic}" : f"{response_description}" }
        append_to_json_file(json_description_file_path, description_obj)
        end_time = time.perf_counter()

        yield (response_description, round(end_time - start_time, 2))

      except KeyError as e:
         print(f"KeyError occurred: {e}")
         print(response.json())
         yield 0


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