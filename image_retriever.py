import os
import json
import ast
import time
import re

from openai import OpenAI

from utils import create_logging_entry, store_logging_entry


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
            if line.startswith('-'):
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
        #remove the surrounding brackets and strip whitespace
        stripped_string = res.strip('[] \n')
        lines = stripped_string.split('\n')

        parsed_list = []

        for line in lines:
            #strip leading/trailing whitespace, commas, and quotes
            cleaned_line = line.strip(' ,"\n')
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
            {"role": "system", "content": ("You are an assistant for rephrasing image search prompts. You need to convert queries for images that are in form of statements into equivalent questions.\n"
                                            "#RULES:\n"
                                            "- Your output should only be the converted prompt, nothing extra.\n"
                                            "- If the input is already in question form, improve it to be better suited for a search query.\n"
                                            "- Try to remove possessive pronouns and replace with generic determiners.\n"
                                            "#EXAMPLES:\n"
                                            "- If the input is 'animals', your output should be 'What images contain animals?'.\n"
                                            "- If the input is 'My family on Christmas', your output should be 'What images contain a family on Christmas?'.\n"
                                            "- If the input is 'Graduation pics', your output should be 'What images are related to graduation?'.\n")},
            {"role": "user", "content": "Based on the given rules and examples, please rephrase the following: {}".format(orig_prompt)},
        ]
    )
    new_prompt = response.choices[0].message.content
    return new_prompt


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
                                        Here are image filenames as keys and corresponding image descriptions as values in JSON format: {}

                                        The user will ask you for names of one or multiple photos that match a description. You are to output the filename(s) based on the interpreting the respective description given for each photo.

                                        For example, if a user asks you for the file names of pcitures that have animals in them, find and output all image file names that contain a reference to an animal in their description.
                                        For each image you output, provide a justification for choosing it.
                                    """.format(image_descriptions)},
        {"role": "user", "content": f"{retrieval_prompt}"},
    ]
    )
    res = response.choices[0].message.content
    res = res.replace("'", "\"")
    print(res)


def retrieve_and_return(images_dir, image_descriptions_file, retrieval_prompt, api_key, rephrase=True):
    client = OpenAI(api_key=api_key)
    image_descriptions = retrieve_contents_from_json(image_descriptions_file)
    req_start_time = time.perf_counter()
    retrieval_prompt_orig = retrieval_prompt
    if rephrase:
        retrieval_prompt = rephrase_prompt(api_key, retrieval_prompt)
        print(f"Prompt rephrased to: {retrieval_prompt}")
    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": (f"You are an assistant for finding image file names based on the associated image descriptions given for each photo."
                                            f"Here are image filenames as keys and corresponding image descriptions as values in JSON format: {image_descriptions}"
                                            "The user will ask you for names of one or multiple photos that match a description. You are to output the filename(s) based on the interpreting the respective description given for each photo."
                                            "For example, if a user asks you for the file names of pictures that have animals in them, find and output all picture file names that contain a reference to an animal in their description."
                                            "Provide your answer as a list of strings. Simply provide the desired output list, do not include additional explanation. If there are no valid answer, simply output 'None'.")},
            {"role": "user", "content": f"{retrieval_prompt}"},
        ]
    )
    res = response.choices[0].message.content
    res = res.replace("'", "\"")

    req_stop_time = time.perf_counter()
    
    output_images = []
    try:
        print(res)
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
    if type(output_images) == str:
        print('got output as string instead of list')
        output_images = [output_images]
    print(f"{len(output_images)} images")

    #store to logs
    logging_entry = create_logging_entry(retrieval_prompt_orig, retrieval_prompt, str(output_images))
    logging_file = os.path.join('.', 'query_logs', api_key[-5:] + '_logs.json')
    store_logging_entry(logging_file, logging_entry)

    print(output_images)
    return output_images