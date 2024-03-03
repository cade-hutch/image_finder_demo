import os
import time
import streamlit as st

from image_retriever import retrieve_and_return
from pic_description_generator import generate_image_descrptions, rename_files_in_directory

from utils import retrieve_or_generate, is_valid_image_directory

images_dir = os.getcwd()
base_name = os.path.basename(images_dir)
base_dir = os.path.dirname(os.path.dirname(images_dir))
descriptions_folder_path = os.path.join(base_dir, 'json')
json_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')

request_in_progress = None


def error_page(error_message):
    st.title(error_message)


def on_generate_button_submit():
    rename_files_in_directory(images_dir)
    generate_total_time = generate_image_descrptions(images_dir)
    st.write(f"Finished generating descriptions in {generate_total_time}")


def description_generator_page():
    st.title('Generate Descriptions')
    generate_button = st.button(label=f"Click here to generate descriptions for images in {base_name}", on_click=on_generate_button_submit)
    

def retriever_page():
    st.title('Image Retriever')
    st.write("find images from {}".format(base_name))

    with st.form('prompt_submission'):
        text_input_col, submit_btn_col = st.columns([5, 1])
        with text_input_col:
            user_input = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", placeholder="What would you like to find?")

        with submit_btn_col:
            submit_button = st.form_submit_button(label='Send')
 
    if submit_button:
        send_request(user_input)

    for item_type, content in st.session_state.history:
        if item_type == 'text':
            st.text(content)
        elif item_type == 'image':
            image_name = os.path.basename(content)
            st.image(content, caption=image_name)


def send_request(prompt=None):
    print(f"SENDING REQUEST: {prompt}")

    if prompt:
        st.session_state.history = []
        # Append user query to history
        #TODO: make retriee function return that modified phrase, return that to be displayed
        st.session_state.history.append(('text', f"You: {prompt}"))
        
        try:
            start_t = time.perf_counter()
            output_image_names = retrieve_and_return(images_dir, json_file_path, prompt)
            end_t = time.perf_counter()
            print('RESPONSE RECEIVED')
            print('output images list:', output_image_names)
            retrieve_time = format(end_t - start_t, '.2f')
            st.session_state.history.append(('text', f"Found {len(output_image_names)} images in {retrieve_time} seconds"))
        except:
            print('error during request')
            output_image_names = []
            st.session_state.history.append(('text', f"Error in image retrieval, try again."))
        
        for img in output_image_names:
            img_path = os.path.join(images_dir, img)
            if os.path.exists(img_path):
                st.session_state.history.append(('image', img_path))

#main function
if 'history' not in st.session_state:
    st.session_state.history = []

if is_valid_image_directory(images_dir):
    page = retrieve_or_generate(images_dir, json_file_path)
    if page == 'generate':
        description_generator_page()
    elif page == 'retrieve':
        retriever_page()
    else:
        error_page("Error: setup error - cannot determine correct page")
else:
    error_page('Error: Bad images directory path. Run this app within desired images directory with "image_finder_demo/image_base".')




