import os
import time
import streamlit as st

from image_retriever import retrieve_and_return
from pic_description_generator import generate_image_descrptions, rename_files_in_directory

from utils import retrieve_or_generate, is_valid_image_directory




# base_name = os.path.basename(images_dir)
# base_dir = os.path.dirname(os.path.dirname(images_dir))
# descriptions_folder_path = os.path.join(base_dir, 'json')
# json_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')





def send_request(input_data):
    # Your function to send and receive data from an API
    print('-----')
    print('SEND REQUEST CALLED')
    print(input_data)
    print('-----')


def on_generate_button_submit(uploaded_images):
    image_dir_name = 'user_demo_images'
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    image_base_dir = os.path.join(curr_dir, 'image_base')
    images_dir = os.path.join(image_base_dir, image_dir_name)
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    for uploaded_img in uploaded_images:
    # Define the full file path
        file_path = os.path.join(images_dir, uploaded_img.name)
        
        # Write the uploaded file to the file system
        with open(file_path, "wb") as f:
            f.write(uploaded_img.getbuffer())
        st.success(f"Saved file: {uploaded_img.name}")
        print('image folder created')

        json_descriptions_dir = os.path.join(curr_dir, 'json')
        #generate_total_time = generate_image_descrptions(images_dir)
        #st.write(f"Finished generating descriptions in {generate_total_time}")

#main
uploaded_files = st.file_uploader("Choose images...", type=['png'], accept_multiple_files=True)

if uploaded_files:
    generate_submit_button = st.button(label=f"Click here to generate descriptions for {len(uploaded_files)} images")
    print(type(uploaded_files))
    for i in uploaded_files:
        print(i)
    if generate_submit_button:
        on_generate_button_submit(uploaded_files)


# # Use a form to batch the input and button interactions
# with st.form("my_form"):
#     input_data = st.text_input("Enter your data")
#     submit_button = st.form_submit_button("Submit")

# # When the user presses the submit button, the code below the form is executed.
# if submit_button:
#     response = send_request(input_data)
#     st.write(response)