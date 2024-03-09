import os
import time
import streamlit as st

from image_retriever import retrieve_and_return
from pic_description_generator import generate_image_descrptions, rename_files_in_directory

from utils import retrieve_or_generate, is_valid_image_directory, validate_openai_api_key

def list_image_dirs():
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    for f in os.listdir(image_base_dir):
        st.title(f)


def send_request(prompt):
    # Your function to send and receive data from an API
    print('-----')
    print('SEND REQUEST CALLED')
    print(f"SENDING REQUEST: {prompt}")
    print('-----')

    if prompt:
        st.session_state.history = []
        # Append user query to history
        #TODO: make retriee function return that modified phrase, return that to be displayed
        st.session_state.history.append(('text', f"You: {prompt}"))
        
        try:
            images_dir = st.session_state.images_dir
            base_name = os.path.basename(images_dir)
            base_dir = os.path.dirname(os.path.dirname(images_dir))
            descriptions_folder_path = os.path.join(base_dir, 'json')
            json_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')

            start_t = time.perf_counter()
            output_image_names = retrieve_and_return(images_dir, json_file_path, prompt, st.session_state.user_openai_api_key)
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


def create_image_dir_name(api_key):
    #TODO: name after api_key
    #TODO: check exists?
    return api_key[-5:]


def user_folder_exists(api_key):
    folder_name = api_key[-5:]
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    for f in os.listdir(image_base_dir):
        if f == folder_name:
            st.session_state.images_dir = os.path.join(image_base_dir, folder_name)
            return True
    return False


def on_generate_button_submit(uploaded_images, generate=True):
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    image_dir_name = create_image_dir_name(st.session_state.user_openai_api_key)
    images_dir = os.path.join(image_base_dir, image_dir_name)
    st.session_state.images_dir = images_dir
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        print('image folder created')
    
    for uploaded_img in uploaded_images:
        file_path = os.path.join(images_dir, uploaded_img.name)
        #write the uploaded file to the file system
        with open(file_path, "wb") as f:
            f.write(uploaded_img.getbuffer())

        st.success(f"Saved file: {uploaded_img.name}")
        

    if generate:
        rename_files_in_directory(images_dir)
        generate_total_time = generate_image_descrptions(images_dir, api_key=st.session_state.user_openai_api_key)
        if type(generate_total_time) == list: #unsuccesful generate/did not finish
            st.error('Error occured while generating... press generate to try again.')
            st.error(generate_total_time[0])
        else:
            generate_total_time = format(generate_total_time, '.2f')
            st.success(f"Finished generating descriptions in {generate_total_time} seconds")

    return True #TODO: handle good/bad return


def retrieval_page():
    st.text("Search for images submitted by API Key: {}".format(st.session_state.user_openai_api_key))
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


def main():
    st.title('Image Finder') #TODO: align center
    #list_image_dirs()

    #API key submission page
    if not st.session_state.submitted_api_key:
        st.write('Submit an OpenAI API Key to begin')

        with st.form('api_key_submission'):
            api_key_text_input_col, api_key_submit_btn_col = st.columns([5, 1])
            with api_key_text_input_col:
                user_api_key_input = st.text_input(label="why is this required", label_visibility='collapsed', key="user_api_key_input", placeholder="Enter OpenAI API key")

            with api_key_submit_btn_col:
                submit_api_key_button = st.form_submit_button(label='Submit')
    
        if submit_api_key_button:
            if validate_openai_api_key(user_api_key_input):
                st.session_state.user_openai_api_key = user_api_key_input
                st.session_state.submitted_api_key = True
                if user_folder_exists(user_api_key_input):
                    st.session_state.api_key_exists = True
                st.success('API key validated')
            else:
                st.error('Error occured while validating API key.... refresh page to try again.')

    #Image upload page
    if st.session_state.submitted_api_key and not st.session_state.has_submitted_images and not st.session_state.api_key_exists:
        #TODO: button to skip upload for existing user/api_key
        st.write('Submit Images for description generation')

        uploaded_files = st.file_uploader("Choose images...", type=['png'], accept_multiple_files=True)

        if uploaded_files:
            generate_submit_button = st.button(label=f"Click here to generate descriptions for {len(uploaded_files)} images")
            if generate_submit_button:
                if on_generate_button_submit(uploaded_files):
                    st.session_state.has_submitted_images = True
                    #retrieval_page()
    
    if st.session_state.has_submitted_images or st.session_state.api_key_exists:
        if st.session_state.api_key_exists and st.session_state.show_existing_images_info:
            st.info('Found Existing images for submitted API Key.')
            st.session_state.show_existing_images_info = False
        retrieval_page()



#app start point
if 'submitted_api_key' not in st.session_state:
    st.session_state.submitted_api_key = False
    #st.session_state.user_openai_api_key = ""?

if 'api_key_exists' not in st.session_state:
    st.session_state.api_key_exists = False

if 'has_submitted_images' not in st.session_state:
    st.session_state.has_submitted_images = False

if 'uploaded_images' not in st.session_state:
    st.session_state.uploaded_images = []

if 'history' not in st.session_state:
    st.session_state.history = []

if 'images_dir' not in st.session_state:
    st.session_state.images_dir = ""

if 'show_existing_images_info' not in st.session_state:
    st.session_state.show_existing_images_info = True

main()
