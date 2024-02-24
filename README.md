Using python 3.11.5

#STEP 1:
Create OpenAI api key. In terminal store as environment variable 'OPENAI_DEMO_KEY':
  export OPENAI_DEMO_KEY="<api key>"

#STEP 2:
Install python requirements with "pip install -r requirements.txt".

#STEP 3:
Create a folder within 'image_base' folder and to put PNG images in. Max file size is 20MB.

#STEP 4:
In terminal, cd into created image folder, run description generator script(descr_generatory_api.py).
If an error occurs before finishing all images, run the script again. It will pick up where it left off.

#STEP 5:
After description generation is successful, image retrieval app(retriever_app.py) can be run in same image folder.
Run with "streamlit run /path/to/retriever_app.py"
