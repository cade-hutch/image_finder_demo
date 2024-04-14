import os
import sys
import time
import streamlit as st
import subprocess

from image_retriever import retrieve_and_return
from pic_description_generator import generate_image_descrptions, rename_files_in_directory, get_new_pics_dir, find_new_pic_files
from utils import validate_openai_api_key, get_image_count, get_descr_filepath
#TODO: state for importing so firebase only inits once??
from firebase_utils import init_app, upload_images_from_list, upload_json_descriptions_file, download_descr_file, does_image_folder_exist, download_images

MAIN_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DESCRITPIONS_DIR = os.path.join(MAIN_DIR, 'json')
JSON_DESCR_SUFFIX = '_descriptions.json'
IMAGE_BASE_DIR = os.path.join(MAIN_DIR, 'image_base')

DEPLOYED_PYTHON_PATH = '/home/adminuser/venv/bin/python'



def sync_local_with_remote(api_key):#TODO: st state to kick off subprocess only once, rest of function checks completion to be ran repitative until processe complete
    basename = create_image_dir_name(api_key)
    json_descr_file = os.path.join(JSON_DESCRITPIONS_DIR, basename + JSON_DESCR_SUFFIX)
    local_images_folder = os.path.join(IMAGE_BASE_DIR, basename)
    print('SYNCING LOCAL WITH REMOTE')
    if os.path.exists(DEPLOYED_PYTHON_PATH):
        process = subprocess.Popen([DEPLOYED_PYTHON_PATH, 'firebase_utils.py', json_descr_file, local_images_folder], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        process = subprocess.Popen(['python', 'firebase_utils.py', json_descr_file, local_images_folder], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # Check if the subprocess ended without errors
    if process.returncode == 0:
        return True
    else:
        st.error("sync_local_with_remote: erro during db sync subprocess")
        st.error(stderr.decode())  # Display the error message
        return False


def send_request(prompt):
    print('-----')
    print('SEND REQUEST CALLED')
    print(f"SENDING REQUEST: {prompt}")
    print('-----')

    if prompt:
        st.session_state.history = []
        #TODO: make retriee function return that modified phrase, return that to be displayed
        st.session_state.history.append(('text', f"You: {prompt}"))
        
        try:
            images_dir = st.session_state.images_dir
            base_name = os.path.basename(images_dir)
            base_dir = os.path.dirname(os.path.dirname(images_dir))
            descriptions_folder_path = os.path.join(base_dir, 'json')
            json_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')
            if not os.path.exists(json_file_path):
                print('descriptions file not found, getting from firebase')
                download_descr_file(json_file_path)

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
    return api_key[-5:]


def user_folder_exists_local(api_key):
    folder_name = create_image_dir_name(api_key)
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    for f in os.listdir(image_base_dir):
        if f == folder_name:
            st.session_state.images_dir = os.path.join(image_base_dir, folder_name)
            return True
    return False


def user_folder_exists_remote(api_key):
    folder_name = api_key[-5:]
    print('running user_folder_exists')
    if does_image_folder_exist(folder_name):
        print('exists_remote: True')
        return True
    else:
        print('exists_remote: False')
        return False


def on_generate_button_submit(uploaded_images, from_uploaded=True, generate=True):
    #TODO keep folder as temp?
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    image_dir_name = create_image_dir_name(st.session_state.user_openai_api_key)
    images_dir = os.path.join(image_base_dir, image_dir_name)
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
        generate_total_time = 0.0
        if new_images:
            for i, callback_tuple in enumerate(generate_image_descrptions(new_images, images_dir, st.session_state.user_openai_api_key)):
                generation_time = callback_tuple[1]
                generate_total_time += generation_time
                st.write(f"({i+1}/{len(new_images)}) Finished generating for {new_images[i]} in {generation_time} seconds")

        if type(generate_total_time) == list: #unsuccesful generate/did not finish
            st.error('Error occured while generating... press generate to try again.')
            st.error(generate_total_time[0])
        else:
            generate_total_time = format(generate_total_time, '.2f')
            st.success(f"Finished generating descriptions in {generate_total_time} seconds")
            #FIREBASE - STORE JSON
            print('starting json upload')
            descr_filepath = get_descr_filepath(images_dir)
            upload_json_descriptions_file(descr_filepath)
            print('finished json upload')

    st.session_state.all_descriptions_generated =True
    return True #TODO: handle good/bad return


def retrieval_page():
    images_count = get_image_count(st.session_state.images_dir)
    submit_more_images_button = st.button(label='Submit More Images')
    if submit_more_images_button:
        print('more images to submit')
        st.session_state.history = []
        st.session_state.show_retrieval_page = False
        st.session_state.upload_more_images = True
        st.session_state.display_uploader_page = True

    if st.session_state.show_retrieval_page:
        st.text("Search through {} images submitted by API Key: {}".format(images_count, st.session_state.user_openai_api_key))

        with st.form('prompt_submission'):
            text_input_col, submit_btn_col = st.columns([5, 1])
            with text_input_col:
                user_input = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", placeholder="What would you like to find?")

            with submit_btn_col:
                submit_button = st.form_submit_button(label='Send')
    
        if submit_button:
            send_request(user_input)
        #NOTE: async works here
        images_to_display = []
        for item_type, content in st.session_state.history:
            if item_type == 'text':
                st.text(content)
            elif item_type == 'image':
                images_to_display.append(content)
                #image_name = os.path.basename(content)
                #st.image(content, caption=image_name)
        for i in range(0, len(images_to_display), 2):
            col1, col2 = st.columns(2)
            col1.image(images_to_display[i], use_column_width=True)
            
            if i + 1 < len(images_to_display):
                col2.image(images_to_display[i+1], use_column_width=True)  


def image_upload_page():
    #TODO: button to skip upload for existing user/api_key
    if st.session_state.upload_more_images:
        st.write(f"Submit more images for {st.session_state.user_openai_api_key}")
    else:
        st.write('Submit images for description generation')

    uploaded_files = st.file_uploader("Choose images...", type=['png'], accept_multiple_files=True)

    if uploaded_files:
        generate_submission_page(uploaded_files)
        

def generate_submission_page(uploaded_files):
    generate_submit_button = st.button(label=f"Click here to generate descriptions for {len(uploaded_files)} images")
    if generate_submit_button:
        st.session_state.show_retrieval_page = True
        st.session_state.display_uploader_page = False
        if on_generate_button_submit(uploaded_files):
            st.session_state.upload_more_images = False
            st.session_state.has_submitted_images = True
            retrieval_page()
            

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
    #if (st.session_state.submitted_api_key and not st.session_state.has_submitted_images and not st.session_state.api_key_exists) or st.session_state.upload_more_images:
    if (st.session_state.submitted_api_key and not st.session_state.has_submitted_images and not st.session_state.api_key_exists):
        st.session_state.display_uploader_page = True
        #image_upload_page()
        
    
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
        #if st.session_state.show_retrieval_page:
        if st.session_state.all_descriptions_generated:
            retrieval_page()

    if st.session_state.display_uploader_page:
        image_upload_page()


#APP START POINT
if 'submitted_api_key' not in st.session_state:
    st.session_state.submitted_api_key = False
    #st.session_state.user_openai_api_key = ""?

if 'api_key_exists' not in st.session_state:
    st.session_state.api_key_exists = False

if 'has_submitted_images' not in st.session_state:
    st.session_state.has_submitted_images = False

if 'upload_more_images' not in st.session_state: #TODO: correct state?
    st.session_state.upload_more_images = False

if 'display_uploader_page' not in st.session_state:
    st.session_state.display_uploader_page = False

if 'history' not in st.session_state:
    st.session_state.history = []

if 'images_dir' not in st.session_state:
    st.session_state.images_dir = ""

if 'all_descriptions_generated' not in st.session_state:
    st.session_state.all_descriptions_generated = False

if 'display_infobar_for_existing_images' not in st.session_state:
    st.session_state.display_infobar_for_existing_images = True

if 'show_retrieval_page' not in st.session_state:
    st.session_state.show_retrieval_page = True

if 'listed' not in st.session_state:
    os.system('which pip')
    os.system('pip list')
    print(sys.executable)
    print(st.__version__)
    st.session_state.listed = True

main()
