import os
import platform
import subprocess
import json
import ast
import time
import re

from openai import OpenAI

OPEN_PNG_CMD = 'open'


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


def handle_faulty_response_format(res):
    print("FAULTY RESPONSE:")
    print(res)
    res_list = []
    if "'''" in res:
        clean_res = res.replace('json', '', 1).strip()
        res_list = json.loads(clean_res)

    if not res_list and "- " in res: #handle dashed list
        print("trying format fix 2")
        lines = res.split('\n')
        file_names = []

        for line in lines:
            # Check if the line represents a file name
            if line.startswith('-'):
                # Strip the unnecessary characters and add to the list
                if '"' in line or "'" in line:
                    file_name = line.strip('- `\'"') 
                    
                file_names.append(file_name)

        return file_names
    
    elif not res_list: #handle plaintext or with []
        if type(res) == str:
            print('trying format fix 2.5')
            extract_pattern = re.compile(r"(?:^|[\s\"'])([^\"'\s]+)\.png")
            res_list = extract_pattern.findall(res)
            return [s + '.png' for s in res_list]

        print("trying format fix 3")
        # Remove the surrounding brackets and strip whitespace
        stripped_string = res.strip('[] \n')

        # Split the string into lines
        lines = stripped_string.split('\n')

        parsed_list = []

        # Iterate over each line
        for line in lines:
            # Strip leading/trailing whitespace, commas, and quotes
            cleaned_line = line.strip(' ,"\n')
            # Add the cleaned line to the list
            parsed_list.append(cleaned_line)

        return parsed_list
        
    print("handle faulty response attempted")
    #TODO: add other faulty formats
    return res_list


def rephrase_prompt(api_key, orig_prompt):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": """You are an assistant for rephrasing image search prompts. You need to convert queries for images that are in form of statements into equivalent questions.
                                        
                                        #RULES:
                                        - Your output should only be the converted prompt, nothing extra.
                                        - If the input is already in question form, improve it to be better suited for a search query.
                                        - Try to remove possessive pronouns and replace with generic determiners.
                                        #EXAMPLES:
                                        - If the input is "animals", your output should be "What images contain animals?".
                                        - If the input is "My family on Christmas", your output should be "What images contain a family on Christmas?".
                                        - If the input is "Graduation pics", your output should be "What images are related to graduation?".

                                    """},
        {"role": "user", "content": "Based on the given rules and examples, please rephrase the following: {}".format(orig_prompt)},
    ]
    )
    new_prompt = response.choices[0].message.content
    return new_prompt


def retrieve_and_open(images_dir, image_descriptions_file, retrieval_prompt, api_key, rephrase=True):
    client = OpenAI(api_key=api_key)
    image_descriptions = retrieve_contents_from_json(image_descriptions_file)
    req_start_time = time.perf_counter()
    if rephrase:
        retrieval_prompt = rephrase_prompt(api_key, retrieval_prompt)
        print(f"Prompt rephrased to: {retrieval_prompt}")
    response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": """You are an assistant for finding image file names based on the associated image descriptions given for each photo.
                                        Here are image file names and corresponding image descriptions in JSON format: {}

                                        The user will ask you for names of one or multiple photos that match a description. You are to output the filename(s) based on the interpreting the respective description given for each photo.

                                        For example, if a user asks you for the file names of pictures that have animals in them, find and output all picture file names that contain a reference to an animal in their description.
                                        Provide your answer as a list of strings. Simply provide the desired out list, do not include additional explaination.
                                    """.format(image_descriptions)},
        {"role": "user", "content": f"{retrieval_prompt}"},
    ]
    )
    res = response.choices[0].message.content
    # Replace single quotes with double quotes
    res = res.replace("'", "\"")
    # Safely evaluate the string to get a list
    req_stop_time = time.perf_counter()
    
    output_images = []
    try:
        output_images = ast.literal_eval(res)
    except ValueError:
        print("ValueError: The input is not a valid Python literal.")
    except SyntaxError:
        print("SyntaxError: The input string contains a syntax error.")
        formatted_output = handle_faulty_response_format(res)
        print(type(res))
        print(res)
        print("NEW OUT")
        print(formatted_output)
        if type(formatted_output) == list: #TODO: needed?
            output_images = []
            for s in formatted_output:
                if s.endswith('.png'):
                    output_images.append(s)

    print(f"Got response in {req_stop_time - req_start_time} seconds")
    print(f"{len(output_images)} images")
    print(output_images)
    for pic in output_images:
        if pic.endswith('.png'):
            if platform.system() == 'Darwin':
                try:
                    subprocess.run([OPEN_PNG_CMD, os.path.join(images_dir, pic)])
                except Exception as e:
                    print(f"Error opening the image: {e}")


def retrieve_and_explain(images_dir, image_descriptions_file, retrieval_prompt, api_key, rephrase=False):
    client = OpenAI(api_key=api_key)
    image_descriptions = retrieve_contents_from_json(image_descriptions_file)
    req_start_time = time.perf_counter()
    if rephrase:
        retrieval_prompt = rephrase_prompt(api_key, retrieval_prompt)
        print(f"Prompt rephrased to: {retrieval_prompt}")
    response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": """You are an assistant for finding image file names based on the associated image descriptions given for each photo.
                                        Here are image file names and corresponding image descriptions in JSON format: {}

                                        The user will ask you for names of one or multiple photos that match a description. You are to output the filename(s) based on the interpreting the respective description given for each photo.

                                        For example, if a user asks you for the file names of pcitures that have animals in them, find and output all image file names that contain a reference to an animal in their description.
                                        For each image you output, provide a justification for choosing it.
                                    """.format(image_descriptions)},
        {"role": "user", "content": f"{retrieval_prompt}"},
    ]
    )
    res = response.choices[0].message.content
    # Replace single quotes with double quotes
    res = res.replace("'", "\"")
    print(res)


def retrieve_and_return(images_dir, image_descriptions_file, retrieval_prompt, api_key, rephrase=True):
    client = OpenAI(api_key=api_key)
    image_descriptions = retrieve_contents_from_json(image_descriptions_file)
    req_start_time = time.perf_counter()
    if rephrase:
        retrieval_prompt = rephrase_prompt(api_key, retrieval_prompt)
        print(f"Prompt rephrased to: {retrieval_prompt}")
    response = client.chat.completions.create(
    model="gpt-4-1106-preview",
    messages=[
        {"role": "system", "content": """You are an assistant for finding image file names based on the associated image descriptions given for each photo.
                                        Here are image file names and corresponding image descriptions in JSON format: {}

                                        The user will ask you for names of one or multiple photos that match a description. You are to output the filename(s) based on the interpreting the respective description given for each photo.

                                        For example, if a user asks you for the file names of pictures that have animals in them, find and output all picture file names that contain a reference to an animal in their description.
                                        Provide your answer as a list of strings. Simply provide the desired output list, do not include additional explaination.
                                    """.format(image_descriptions)},
        {"role": "user", "content": f"{retrieval_prompt}"},
    ])

    res = response.choices[0].message.content
    # Replace single quotes with double quotes
    res = res.replace("'", "\"")
    # Safely evaluate the string to get a list
    req_stop_time = time.perf_counter()
    
    output_images = []
    try:
        output_images = ast.literal_eval(res)
    except ValueError:
        print("ValueError: The input is not a valid Python literal.")
    except SyntaxError:
        print("SyntaxError: The input string contains a syntax error.")
        formatted_output = handle_faulty_response_format(res)
        print(type(res))
        print(res)
        print("NEW OUT")
        print(formatted_output)
        if type(formatted_output) == list: #TODO: needed?
            output_images = []
            for s in formatted_output:
                if s.endswith('.png'):
                    output_images.append(s)

    print(f"Got response in {round(req_stop_time - req_start_time, 2)} seconds")
    print(f"{len(output_images)} images")
    print(output_images)
    return output_images