import os
import streamlit as st

from image_retriever import retrieve_and_return

images_dir = os.getcwd()
base_name = os.path.basename(images_dir)
base_dir = os.path.dirname(os.path.dirname(images_dir))
descriptions_folder_path = os.path.join(base_dir, 'json')
json_file_path = os.path.join(descriptions_folder_path, base_name + '_descriptions.json')


st.title('Image Retriever')
st.write("find images from {}".format(base_name))

if 'history' not in st.session_state:
    st.session_state.history = []


def send_request():
    prompt = st.session_state.user_input

    if prompt:
        st.session_state.history = []
        # Append user query to history

        #TODO: make retriee function return that modified phrase, return that to be displayed
        st.session_state.history.append(('text', f"You: {prompt}"))
        
        # Get response from LLM (implement this function based on your LLM API)
        #llm_response = retrieve_and_return()
        try:
            output_image_names = retrieve_and_return(images_dir, json_file_path, prompt)
            st.session_state.history.append(('text', f"Found {len(output_image_names)} images"))
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

text_input_col, submit_btn_col = st.columns([5, 1])
with text_input_col:
    prompt = st.text_input(label="why is this required", label_visibility='collapsed', key="user_input", on_change=send_request, placeholder="What would you like to find?")

with submit_btn_col:
    submit_button = st.button(label='Send', on_click=send_request)


for item_type, content in st.session_state.history:
    if item_type == 'text':
        st.text(content)
    elif item_type == 'image':
        image_name = os.path.basename(content)
        st.image(content, caption=image_name)