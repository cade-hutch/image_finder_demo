import os
import json
import pickle
import faiss
import numpy as np

from datetime import datetime
from PIL import Image
from openai import OpenAI
from langchain_community.embeddings import OpenAIEmbeddings


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


def get_descriptions_from_json(json_description_file_path, get_images=False):
    #return str list(s)
    try:
        with open(json_description_file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []

    descriptions = []
    image_names = []
    if get_images:
        for element in data:
            descriptions.append(element['description'])
            image_names.append(element['file_name'])

        return image_names, descriptions
    else:
        for element in data:
            descriptions.append(element['description'])
        return descriptions


def retrieve_contents_from_json(json_file_path):
    #return list of dicts(keys = filename, descr)
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON file: {json_file_path}")
        return None


def get_new_descriptions(new_images, json_description_file_path):
    pass


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
    #print("file size: {}".format(file_size))

    if file_size < max_size:
        return

    with Image.open(file_path) as img:
        # resize the image here if you want
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
    #TODO: error code for invalid key is 401
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def get_image_count(images_dir):
    #pngs only
    images_count = 0
    for file in os.listdir(images_dir):
        if file.endswith('.png'):
            images_count += 1
    return images_count


def get_descr_filepath(images_dir):
    basename = os.path.basename(images_dir)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    descr_filepath = os.path.join(curr_dir, 'json', basename + '_descriptions.json')
    return descr_filepath


#token reducing utils
def remove_description_pretense(description):
    """
    outliers:
    The image is a photograph taken from a camera, possibly with an iPhone considering the initial context provided.
    The image depicts a close-up photo of
    The image is a portrait-oriented photo taken from a camera, showing a
    The image is taken from a camera and shows a
    """
    ss_prefix = ''
    if description.startswith("This is NOT a screenshot.\n\n"):
        ss_prefix = "This is NOT a screenshot.\n\n"
        description = description.split(ss_prefix)[1]
    elif description.startswith("This is a screenshot.\n\n"):
        ss_prefix = 'This is a screenshot.\n\n'
        description = description.split(ss_prefix)[1]

    if len(description) < 5:
        return description
    
    if 'from a camera' in description.lower():
        split1, split2 = description.split('from a camera')
        if len(split1) < 100: #TODO: not great
            description = split2
            if description.startswith('. ') or description.startswith(', '):
                description = description[2:]
            if description.startswith(' and shows '):
                description = description.replace(" and shows", "", 1).lstrip()
            elif description.startswith(' showing '):
                description = description.replace(" showing", "", 1).lstrip()
            return ss_prefix + description

        

    words = description.split()
    if words[1] == 'image' or words[1] == 'photo':
        third_words = ['shows', 'depicts', 'is', 'displays', 'features', 'captures', 'presents']
        if words[2] in third_words:
            words = words[3:]
            if words[0] == 'of':
                words = words[1:]
        elif words[2] == 'appears':
            words = words[5:]
        elif words[2] == 'provided' and words[3] == 'appears':
            words = words[6:]
    elif 'image' in words[2]:
        words = words[3:]
    elif words[3] == 'image' and words[4] == 'of':
        words = words[5:]
    elif words[3] == 'photo' and words[4] == 'of':
        words = words[5:]

    if words[0][0].isalpha():
        words[0] = words[0][0].upper() + words[0][1:]

    #TODO: inefficient to split whole description into list --> only need first
    new_description = ss_prefix + ' '.join(words)
    return new_description


def remove_description_pretenses_in_file(descr_file, output_file):
    descriptions_json = retrieve_contents_from_json(descr_file)
    for i, d in enumerate(descriptions_json):
        new_descr = remove_description_pretense(d['description'])
        descriptions_json[i]['description'] = new_descr

    with open(output_file, 'w') as file:
        json.dump(descriptions_json, file, indent=2)


#embeddings utils
def add_new_descr_to_embedding_pickle(embeddings_obj, pickle_file, descriptions):
    #one or multiple descr
    #NOTE: np array additions must have same amount of columns(1536)
    with open(pickle_file, 'rb') as file:
        existing_embeddings = pickle.load(file)
    print(len(existing_embeddings))
    if type(descriptions) == str:
        descriptions = [descriptions]
    new_rows = []
    for descr in descriptions:
        new_row = create_single_embedding(embeddings_obj, descr)
        new_rows.append(new_row)

    new_rows = np.array(new_rows).astype('float32')
    new_embeddings = np.vstack((existing_embeddings, new_rows))

    with open(pickle_file, 'wb') as file:
        pickle.dump(new_embeddings, file)


def create_single_embedding(embeddings_obj, description):
    return embeddings_obj.embed_query(description)


def create_and_store_embeddings_to_pickle(embeddings_obj, pickle_file, descriptions):
    """
    embeddings list(np.array(np.array)) - list of descriptions that are converted to embeddings np.arrays
    """
    embeddings_list = []
    for descr in descriptions:
        embeddings_list.append(embeddings_obj.embed_query(descr))

    embeddings_list = np.array(embeddings_list).astype('float32')

    with open(pickle_file, 'wb') as file:
        pickle.dump(embeddings_list, file)


def get_embeddings_from_pickle_file(pickle_file):
    with open(pickle_file, 'rb') as file:
        embeddings_list = pickle.load(file)
    return embeddings_list


def query_for_related_descriptions(api_key, query, embeddings_pickle_file, images_dir, k=10):
    json_descr_filepath = get_descr_filepath(images_dir)
    file_names, descriptions = get_descriptions_from_json(json_descr_filepath, get_images=True)
    if k == 0:
        k = len(file_names)

    embeddings_obj = OpenAIEmbeddings(api_key=api_key)
    embeddings_list = get_embeddings_from_pickle_file(embeddings_pickle_file)
    index = faiss.IndexFlatL2(1536)
    index.add(embeddings_list)

    query_embedding = embeddings_obj.embed_query(query)
    query_embedding = np.array([query_embedding]).astype('float32')

    distances, indices = index.search(query_embedding, k)

    images_ranked = np.array(file_names)[indices]
    search_ouput = np.array(descriptions)[indices]
    print(search_ouput)
    print(images_ranked)
    return images_ranked


#logging utils
def create_logging_entry(input, rephrased_input, output):
    current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {'time_stamp' : current_date_time, 'input' : input, 'rephrased_input' : rephrased_input, 'output' : output}


def store_logging_entry(logging_file, entry):
    try:
        with open(logging_file, 'r') as file:
            if os.path.getsize(logging_file) != 0:
              existing_data = json.load(file)
            else:
                existing_data = []
    except FileNotFoundError:
        existing_data = []
        print('logging store: error getting existing')

    existing_data.append(entry)

    #write the combined data back to the file
    with open(logging_file, 'w') as file:
        json.dump(existing_data, file, indent=2)