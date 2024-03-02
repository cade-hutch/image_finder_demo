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

    if 'button_pressed' not in st.session_state:
        st.session_state['button_pressed'] = False

    text_input_col, submit_btn_col = st.columns([5, 1])
    with text_input_col:
        user_input = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", on_change=lambda: st.session_state.update(button_pressed=True), placeholder="What would you like to find?")

    with submit_btn_col:
        #TODO: calls send_request twice
        if st.button(label='Send'):
            st.session_state['button_pressed'] = True

    if st.session_state.button_pressed and user_input:
        st.session_state.button_pressed = False
        send_request()

    for item_type, content in st.session_state.history:
        if item_type == 'text':
            st.text(content)
        elif item_type == 'image':
            image_name = os.path.basename(content)
            st.image(content, caption=image_name)


def on_text_input_change():
    print("on_text_input change")
    send_request()


def on_button_submit():
    print('submit button pressed')
    if not request_in_progress:
        print('running req via button press')
        send_request()
    else:
        print('already sent req')


def send_request():
    #global request_in_progress
    #request_in_progress = True
    print(f"CALLED SEND_REQUEST:")
    prompt = st.session_state.user_input
    print(prompt)

    if prompt:
        st.session_state.history = []
        # Append user query to history
        #TODO: make retriee function return that modified phrase, return that to be displayed
        st.session_state.history.append(('text', f"You: {prompt}"))
        
        # Get response from LLM (implement this function based on your LLM API)
        #llm_response = retrieve_and_return()
        try:
            start_t = time.perf_counter()
            output_image_names = retrieve_and_return(images_dir, json_file_path, prompt)
            print('output images lsit:', output_image_names)
            print('request successful')
            end_t = time.perf_counter()
            retrieve_time = format(end_t - start_t, '.2f')
            st.session_state.history.append(('text', f"Found {len(output_image_names)} images in {retrieve_time} seconds"))
        except:
            print('error during request')
            output_image_names = []
            st.session_state.history.append(('text', f"Error in image retrieval, try again."))
        # Append LLM response to history
        #st.session_state['history'].append(f"LLM: {llm_response}")
        
        for img in output_image_names:
            img_path = os.path.join(images_dir, img)
            if os.path.exists(img_path):
                st.session_state.history.append(('image', img_path))

        # Clear input box after sending
        #TODO: breaks
        #st.session_state.user_input = ""
    #request_in_progress = False

#main function
if 'history' not in st.session_state:
    print('clearing history')
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




