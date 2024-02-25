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


def bad_image_directory_page(error_message):
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

    text_input_col, submit_btn_col = st.columns([5, 1])
    with text_input_col:
        prompt = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", on_change=send_request, placeholder="What would you like to find?")

    with submit_btn_col:
        #TODO: calls send_request twice
        submit_button = st.button(label='Send', on_click=send_request)


    for item_type, content in st.session_state.history:
        if item_type == 'text':
            st.text(content)
        elif item_type == 'image':
            image_name = os.path.basename(content)
            st.image(content, caption=image_name)

#   {
#     "file_name": "C94B882D-806A-46BD-AC70-4B839480921D.png",
#     "description": "This is NOT a screenshot.\n\nThe image shows a young man in graduation attire, including a black cap and gown with a maroon stole adorned with the letters \"A&M,\" which likely signifies Texas A&M University. The person is smiling and giving a thumbs-up with his right hand. He is wearing a light shirt with a diagonal patterned tie. On his left hand, he has a gold ring which can be seen as part of the university tradition, typically known as an Aggie Ring, a symbol of pride and achievement among students and alumni of Texas A&M.\n\nThe subject is standing in a location with classic architectural features, such as tall columns behind him and ornate flooring underfoot, suggesting the photo may have been taken at a formal institution or a place with historical significance, possibly related to the university.\n\nIn the background, the texture and pattern of the floor, the base of the columns, and part of what appears to be a vaulted ceiling or large archways are visible, further contributing to the stately atmosphere of the setting. The focus and composition emphasize the graduate, celebrating an academic milestone with traditional graduation regalia."
#   }

def send_request():
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
            end_t = time.perf_counter()
            retrieve_time = format(end_t - start_t, '.2f')
            st.session_state.history.append(('text', f"Found {len(output_image_names)} images in {retrieve_time} seconds"))
        except:
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

if 'history' not in st.session_state:
    st.session_state.history = []


if is_valid_image_directory(images_dir):
    page = retrieve_or_generate(images_dir, json_file_path)
    if page == 'generate':
        description_generator_page()
    elif page == 'retrieve':
        retriever_page()
    #else error page with message
else:
    bad_image_directory_page('Error: Bad images directory path. Run this app within desired images directory with "image_finder_demo/image_base".')




