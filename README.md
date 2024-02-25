**Using python 3.11.5**

#STEP 1:  
Create an OpenAI api key. In terminal store as environment variable 'IMAGE_FINDER_DEMO_KEY':

```
export IMAGE_FINDER_DEMO_KEY="<api_key>"
```

#STEP 2:  
Install python requirements:

```
pip install -r requirements.txt
```

#STEP 3:  
Create a folder within 'image_base' folder to put PNG images in. Max image size is 20MB.

#STEP 4:  
cd into the created image folder and run:

```
streamlit run ../../app.py
```

There is a button to kick off description generation. If an error occurs, refresh page and click the button again, it will pick up where it left off.

After successful description generation, the page for image retrieval should come up.

NOTE: Some output will still be in terminal, currently working to display everything in app.
