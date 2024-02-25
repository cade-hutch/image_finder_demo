import os
import json
import re

from openai import OpenAI


api_key = os.environ['IMAGE_FINDER_DEMO_KEY']
client = OpenAI(api_key=api_key)

OUTPUT_TEMPLATE = {
  "Interests": ["volleyball", "fishing", "pets", "finance", "stock market", "traveling", "sports events"],
  "Affiliations": ["Texas A&M University"],
  "Pet Ownership": ["cat", "dogs"],
  "Social Activities": ["casual dining", "beach outings", "parties"],
  "Travel Locations": ["Breckenridge", "Colorado", "Chicago"],
  "Life Events": ["graduation", "vehicle accident"]
}


def retrieve_contents_from_json(json_file_path):
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


def create_json_file_from_string(json_file_path, json_str):
    #pattern = "```(.*?)```"
    #TODO: how re findall/search works
    pattern = "```([^`]*)```"

    # Using re.findall to extract the content
    json_str = re.findall(pattern, json_str)
    if len(json_str) == 1:
        json_str = json_str[0]
    else:
        print(len(json_str))
        print(json_str)
        return

    if json_str.startswith('json'):
        json_str = json_str[4:]

    try:
        # Parse the JSON string
        data = json.loads(json_str)

        # Write to file
        with open(json_file_path, 'w') as file:
            json.dump(data, file, indent=4)

        print(f"Data written to {json_file_path}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
    except IOError as e:
        print(f"Error writing file: {e}")


def handle_faulty_response_format(res):
    res_list = []
    if "'''" in res:
        clean_res = res.replace('json', '', 1).strip()
        res_list = json.loads(clean_res)
    elif "-":
        pass
    
    return res_list


def create_profile(image_descriptions_file):
    image_descriptions = retrieve_contents_from_json(image_descriptions_file)
    #req_start_time = time.perf_counter()
    response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": """You are an assistant for finding generalizations about the owner of a collection of images.
                                        The following are filenames for images with corresponding image descriptions, given in JSON format: {}

                                        Your job is to analyze the image descriptions and make assumptions about the owner of the images. Condense your answer into a list of key-value pairs. Values can be singular strings or lists of multiple strings.

                                        Try to find values for the following keys: "Interests", "Affiliations", "Pet Ownership", "Social Activities", "Travel Locations", "Life Events".

                                        Give your final answer in JSON format.
                                    """.format(image_descriptions)},
        {"role": "user", "content": "Please provide correct output."},
    ]
    )
    res = response.choices[0].message.content
    return res


def create_profile_json_file(image_folder_name, json_folder_path, res):
    profile_json_file_name = image_folder_name + '_profile.json'
    profile_json_file_path = os.path.join(json_folder_path, profile_json_file_name)
    create_json_file_from_string(profile_json_file_path, res)


def create_owner_profile(images_folder_path):
    #same as main, for module
    images_folder_name = os.path.basename(images_folder_path)
    json_file_name = images_folder_name + '_descriptions.json'
    json_descriptions_folder = '/Users/cadeh/Desktop/MyCode/Workspace/finder/image_finder/json'
    json_descriptions_file = os.path.join(json_descriptions_folder, json_file_name)
    print(json_descriptions_file)
    res = create_profile(json_descriptions_file)
    create_profile_json_file(images_folder_name, json_descriptions_folder, res)


if __name__ == '__main__':
    images_folder_path = os.getcwd()
    images_folder_name = os.path.basename(images_folder_path)
    json_file_name = images_folder_name + '_descriptions.json'
    json_descriptions_folder = '/Users/cadeh/Desktop/MyCode/Workspace/finder/image_finder/json'
    json_descriptions_file = os.path.join(json_descriptions_folder, json_file_name)
    print(json_descriptions_file)
    res = create_profile(json_descriptions_file)
    print(res)
    create_profile_json_file(images_folder_name, json_descriptions_folder, res)
