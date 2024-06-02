#EMBEDDINGS / IMAGE SHUFFLING VERSION

import os
import time
import numpy as np
import streamlit as st
import subprocess
from PIL import Image

from image_retriever_filtered import retrieve_and_return
from pic_description_generator import generate_image_descrptions, rename_files_in_directory, get_new_pics_dir, create_embeddings, update_embeddings, find_new_pic_files
from utils import validate_openai_api_key, get_image_count, get_descr_filepath, query_for_related_descriptions
#TODO: state for importing so firebase only inits once??
from fb_storage_utils import init_app, upload_images_from_list, upload_json_descriptions_file, download_descr_file, does_image_folder_exist, download_images

MAIN_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DESCRITPIONS_DIR = os.path.join(MAIN_DIR, 'json')
JSON_DESCR_SUFFIX = '_descriptions.json'
IMAGE_BASE_DIR = os.path.join(MAIN_DIR, 'image_base')
EMBEDDINGS_DIR = os.path.join(MAIN_DIR, 'embeddings')

DEPLOYED_PYTHON_PATH = '/home/adminuser/venv/bin/python'

FIXED_WIDTH = 300
FIXED_HEIGHT = 400


def sync_local_with_remote(api_key):#TODO: st state to kick off subprocess only once, rest of function checks completion to be ran repitative until processe complete
    basename = create_image_dir_name(api_key)
    json_descr_file = os.path.join(JSON_DESCRITPIONS_DIR, basename + JSON_DESCR_SUFFIX)
    local_images_folder = os.path.join(IMAGE_BASE_DIR, basename)
    print('SYNCING LOCAL WITH REMOTE')
    process = subprocess.Popen([DEPLOYED_PYTHON_PATH, 'fb_storage_utils.py', json_descr_file, local_images_folder], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # Check if the subprocess ended without errors
    if process.returncode == 0:
        return True
    else:
        st.error("Script encountered an error.")
        st.error(stderr.decode())  # Display the error message
        return False


def send_request(prompt):
    # Your function to send and receive data from an API
    #print('-----')
    #print('SEND REQUEST CALLED')
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
            json_file_path = os.path.join(descriptions_folder_path, base_name + JSON_DESCR_SUFFIX)
            if not os.path.exists(json_file_path):
                print('descriptions file not found, getting from firebase')
                download_descr_file(json_file_path)

            start_t = time.perf_counter()
            output_image_names = retrieve_and_return(json_file_path, prompt, st.session_state.user_openai_api_key)
            end_t = time.perf_counter()

            #print('RESPONSE RECEIVED')
            print('output images list:', output_image_names)
            retrieve_time = format(end_t - start_t, '.2f')

            st.session_state.history.append(('text', f"Found {len(output_image_names)} images in {retrieve_time} seconds"))
        except:
            print('error during request')
            output_image_names = []
            st.session_state.history.append(('text', f"Error in image retrieval, try again."))
        
        st.session_state.search_result_images = []
        for img in output_image_names:
            img_path = os.path.join(images_dir, img)
            if os.path.exists(img_path):
                st.session_state.search_result_images.append(img_path)


def create_image_dir_name(api_key):
    #TODO: check exists?
    return api_key[-5:]


def user_folder_exists_local(api_key):
    folder_name = create_image_dir_name(api_key)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    for f in os.listdir(image_base_dir):
        if f == folder_name:
            st.session_state.images_dir = os.path.join(image_base_dir, folder_name)
            print('user_folder_exists_loca: True')
            return True
    print('user_folder_exists_loca: False')
    return False


def user_folder_exists_remote(api_key):
    folder_name = create_image_dir_name(api_key)
    print('running user_folder_exists')
    if does_image_folder_exist(folder_name):
        print('exists_remote: True')
        return True
    else:
        print('exists_remote: False')
        return False


def resize_and_crop_image(image, fixed_width=FIXED_WIDTH, max_height=FIXED_HEIGHT):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(fixed_width * aspect_ratio)
    
    #resize the image to the fixed width while maintaining aspect ratio
    resized_image = image.resize((fixed_width, new_height))
    
    #crop the image if its height exceeds the max height
    if new_height > max_height:
        top = (new_height - max_height) // 2
        bottom = top + max_height
        resized_image = resized_image.crop((0, top, fixed_width, bottom))
    
    return resized_image


def resize_image(image, fixed_height=200):
    width, height = image.size
    aspect_ratio = width / height
    new_width = int(fixed_height * aspect_ratio)
    return image.resize((new_width, fixed_height))


def on_generate_button_submit(uploaded_images, from_uploaded=True, generate=True):
    #TODO keep folder as temp?
    image_dir_name = create_image_dir_name(st.session_state.user_openai_api_key)
    images_dir = os.path.join(IMAGE_BASE_DIR, image_dir_name)
    st.session_state.images_dir = images_dir
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        print('image folder created')
    
    if from_uploaded:
        uploads_to_firestore = []
        for uploaded_img in uploaded_images:
            file_path = os.path.join(images_dir, uploaded_img.name)
            uploads_to_firestore.append(file_path)
            #write the uploaded file to the file system
            with open(file_path, "wb") as f:
                f.write(uploaded_img.getbuffer())

        #TODO: One succuess bar, add images while looping?
        st.success(f"Images saved")
        
        rename_files_in_directory(images_dir)
        #FIREBASE - STORE IMAGES
        if uploads_to_firestore:
            print('uploading images to firebase')
            upload_images_from_list(uploads_to_firestore)
            print('finished uploading to firebase')

    #NOTE: dev-only param
    if generate:
        if not from_uploaded:
            #TODO: needed?
            rename_files_in_directory(images_dir)
        new_images = get_new_pics_dir(images_dir)
        new_descriptions = []
        api_key = st.session_state.user_openai_api_key
        generate_total_time = 0.0
        if new_images:
            for i, generation_result in enumerate(generate_image_descrptions(new_images, images_dir, api_key)):
                new_descr = generation_result[0]
                generation_time = generation_result[1]
                generate_total_time += generation_time
                st.write(f"({i+1}/{len(new_images)}) Finished generating for {new_images[i]} in {generation_time} seconds")
                new_descriptions.append(new_descr)

        if type(generate_total_time) == list: #unsuccesful generate/did not finish
            st.error('Error occured while generating... press generate to try again.')
            st.error(generate_total_time[0])
        else:
            generate_total_time = format(generate_total_time, '.2f')
            st.success(f"Finished generating descriptions in {generate_total_time} seconds")

            descr_filepath = get_descr_filepath(images_dir)

            #EMBEDDINGS - LOCAL
            embeddings_pickle_file = os.path.join(EMBEDDINGS_DIR, image_dir_name + '.pkl')
            t_start_embeddings = time.perf_counter()
            if os.path.exists(embeddings_pickle_file):
                #TODO: working correctly?
                update_embeddings(api_key, embeddings_pickle_file, new_descriptions)
            else:
                create_embeddings(api_key, embeddings_pickle_file, descr_filepath)
            t_end_embeddings = time.perf_counter()
            embeddings_time = round(t_end_embeddings - t_start_embeddings, 2)
            st.success(f"Finished generating embeddings in {embeddings_time} seconds")

            #FIREBASE - STORE JSON
            print('starting json upload')
            
            upload_json_descriptions_file(descr_filepath)
            print('finished json upload')

    return True #TODO: handle good/bad return


def retrieval_page():
    images_dir = st.session_state.images_dir
    images_count = get_image_count(images_dir)
    api_key = st.session_state.user_openai_api_key
    submit_more_images_button = st.button(label='Submit More Images')
    if submit_more_images_button:
        print('more images to submit')
        st.session_state.history = []
        st.session_state.show_retrieval_page = False
        st.session_state.upload_more_images = True
        return

    st.text("Search through {} images submitted by API Key: {}".format(images_count, api_key))

    with st.form('prompt_submission'):
        text_input_col, submit_btn_col = st.columns([5, 1])
        with text_input_col:
            user_input = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", placeholder="What would you like to find?")

        with submit_btn_col:
            submit_button = st.form_submit_button(label='Send')
    
    place_top_cols = False
    if submit_button:
        #create placeholder col2 for request results
        #sort by embeddings before sending request
        place_top_cols = True
        top_col1, top_col2 = st.columns(2)
        basename = os.path.basename(images_dir)
        embeddings_pickle_file = os.path.join(EMBEDDINGS_DIR, basename + '.pkl')
        t_start = time.perf_counter()
        images_ranked = query_for_related_descriptions(api_key, user_input, embeddings_pickle_file, images_dir, k=0)
        print('\n------------------------------NEW SEARCH------------------------------')
        #print(type(images_ranked))
        #if images_ranked.any() and len(images_ranked[0]) > 1:
        if len(images_ranked[0]) > 1:
            st.session_state.images_ranked = images_ranked[0].tolist()
            st.session_state.all_images = [os.path.join(st.session_state.images_dir, img) for img in st.session_state.images_ranked]

        t_end = time.perf_counter()
        print(f"Embeddings Ranking Time: {round(t_end - t_start, 2)}s")
        send_request(user_input)
    #NOTE: async works here
    images_to_display = []
    for item_type, content in st.session_state.history:
        if item_type == 'text':
            st.text(content)
        elif item_type == 'image':
            images_to_display.append(content)

    #for i in range(0, len(images_to_display), 2):
    for i in range(0, len(st.session_state.search_result_images), 2):
        col1, col2 = st.columns(2)
        res_img = resize_and_crop_image(Image.open(st.session_state.search_result_images[i]))
        col1.image(res_img, use_column_width=True, caption="top result")
        
        if i + 1 < len(st.session_state.search_result_images): #TODO: handle when appending non results
            res_img = resize_and_crop_image(Image.open(st.session_state.search_result_images[i+1]))
            col2.image(res_img, use_column_width=True, caption='top result')

    #display rest of images in ranked order
    remaining_images = [img for img in st.session_state.all_images if img not in st.session_state.search_result_images]
    for i in range(0, len(remaining_images), 4):
        col1, col2, col3, col4 = st.columns(4)

        i1 = Image.open(remaining_images[i])
        resized_i1 = resize_and_crop_image(i1)
        col1.image(resized_i1, use_column_width=True)
        
        if i + 1 < len(remaining_images):
            i2 = Image.open(remaining_images[i+1])
            resized_i2 = resize_and_crop_image(i2)
            col2.image(resized_i2, use_column_width=True)
        if i + 2 < len(remaining_images):
            i3 = Image.open(remaining_images[i+2])
            resized_i3 = resize_and_crop_image(i3)
            col3.image(resized_i3, use_column_width=True)
        if i + 3 < len(remaining_images):
            i4 = Image.open(remaining_images[i+3])
            resized_i4 = resize_and_crop_image(i4)
            col4.image(resized_i4, use_column_width=True)

        # col1.image(remaining_images[i], use_column_width=True)
        
        # if i + 1 < len(remaining_images):
        #     col2.image(remaining_images[i+1], use_column_width=True)
        # if i + 2 < len(remaining_images):
        #     col3.image(remaining_images[i+2], use_column_width=True)
        # if i + 3 < len(remaining_images):
        #     col4.image(remaining_images[i+3], use_column_width=True)

    # if place_top_cols:
    #     top_result1 = st.session_state.images_ranked[0]
    #     top_result2 = st.session_state.images_ranked[1]
    #     tr1_path = os.path.join(st.session_state.images_dir, top_result1)
    #     tr2_path = os.path.join(st.session_state.images_dir, top_result2)
        #top_col1.image(tr1_path, use_column_width=True, caption='a')
        #top_col2.image(tr2_path, use_column_width=True, caption='b')


def main():
    st.title('Image Finder')
    footer = """
     <style>
     .footer {
     position: fixed;
     left: 0;
     bottom: 0;
     width: 100%;
     background-color: #111;
     color: white;
     text-align: center;
     }
     </style>
     <div class="footer">
     <p>By Cade Hutcheson</p>
     </div>
     """
    st.markdown(footer, unsafe_allow_html=True)

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
                st.success('API key validated')
                #TODO: check for embeddings
                #remote_folder_exists = asyncio.run(user_folder_exists_remote(user_api_key_input))
                remote_folder_exists = user_folder_exists_remote(user_api_key_input) #firestore folder exists
                if user_folder_exists_local(user_api_key_input):
                    st.session_state.api_key_exists = True
                    #TODO: validate with remote?
                elif remote_folder_exists:
                    st.session_state.api_key_exists = True
                    if sync_local_with_remote(user_api_key_input):
                        print('passed syncing')
            else:
                st.error('Error occured while validating API key.... refresh page to try again.')

    #Image upload page
    #TODO: make own function? --> user has to click 'Submit More Images' twice for this to display
    if (st.session_state.submitted_api_key and not st.session_state.has_submitted_images and not st.session_state.api_key_exists) or st.session_state.upload_more_images:
        #TODO: button to skip upload for existing user/api_key
        if st.session_state.upload_more_images:
            st.write(f"Submit more images for {st.session_state.user_openai_api_key}")
        else:
            st.write('Submit images for description generation')

        uploaded_files = st.file_uploader("Choose images...", type=['png'], accept_multiple_files=True)

        if uploaded_files:
            generate_submit_button = st.button(label=f"Click here to generate descriptions for {len(uploaded_files)} images")
            if generate_submit_button:
                if on_generate_button_submit(uploaded_files):
                    st.session_state.upload_more_images = False
                    st.session_state.has_submitted_images = True
                    st.session_state.show_retrieval_page = True
                    #retrieval_page()
    
    if st.session_state.has_submitted_images or st.session_state.api_key_exists:
        if st.session_state.api_key_exists and st.session_state.display_infobar_for_existing_images:
            #one time info bar: tell user there are existing picture the submitted
            st.info('Found Existing images for submitted API Key.')
            st.session_state.display_infobar_for_existing_images = False
        if st.session_state.api_key_exists and not st.session_state.all_descriptions_generated:
            #if a previous api key is submitted, check if images/descriptions are matching
            if not st.session_state.images_dir:
                st.session_state.images_dir = os.path.join(IMAGE_BASE_DIR, create_image_dir_name(st.session_state.user_openai_api_key))
            pics_missing_descriptions = get_new_pics_dir(st.session_state.images_dir)
            if pics_missing_descriptions:
                print('images without descriptions found')
                #need to generated new pics
                continue_generating_button = st.button(label='Continue generating for {} images'.format(len(pics_missing_descriptions)))
                if continue_generating_button:
                    print('display continue generating page')
                    if on_generate_button_submit(pics_missing_descriptions, from_uploaded=False):
                        st.session_state.all_descriptions_generated = True
            else:
                st.session_state.all_descriptions_generated = True
        if st.session_state.show_retrieval_page:
            retrieval_page()


def make_st_vars():
    #app start point
    if 'firebase_init' not in st.session_state:
        print('initing app')
        st.session_state.firebase_init = True
        init_app()

    if 'submitted_api_key' not in st.session_state:
        st.session_state.submitted_api_key = False
        #st.session_state.user_openai_api_key = ""?

    if 'api_key_exists' not in st.session_state:
        st.session_state.api_key_exists = False

    if 'has_submitted_images' not in st.session_state:
        st.session_state.has_submitted_images = False

    if 'uploaded_images' not in st.session_state: #TODO: unused
        st.session_state.uploaded_images = []

    if 'upload_more_images' not in st.session_state: #TODO: unused
        st.session_state.upload_more_images = False

    if 'history' not in st.session_state:
        st.session_state.history = []

    if 'all_images' not in st.session_state:
        st.session_state.all_images = []

    if 'images_dir' not in st.session_state:
        st.session_state.images_dir = ""
    elif os.path.exists(st.session_state.images_dir):
        st.session_state.all_images = []
        for img in os.listdir(st.session_state.images_dir):
            if img.endswith('.png'):
                st.session_state.all_images.append(os.path.join(st.session_state.images_dir, img))

    if 'images_ranked' not in st.session_state:
        st.session_state.images_ranked  = []

    if 'all_descriptions_generated' not in st.session_state:
        st.session_state.all_descriptions_generated = False

    if 'display_infobar_for_existing_images' not in st.session_state:
        st.session_state.display_infobar_for_existing_images = True

    if 'show_retrieval_page' not in st.session_state:
        st.session_state.show_retrieval_page = True

    if 'search_result_images' not in st.session_state:
        st.session_state.search_result_images = []


make_st_vars()
main()
