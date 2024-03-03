**Using python 3.11.5**

STEP 1:  
Create an OpenAI api key. In terminal store as environment variable 'IMAGE_FINDER_DEMO_KEY':

```
export IMAGE_FINDER_DEMO_KEY="<api_key>"
```

STEP 2:  
Install python requirements:

```
pip install -r requirements.txt
```

STEP 3:  
Create a folder within 'image_base' folder to put images in(must be PNGs). Max image size is 20MB.

- Recommend 20-50 images for a good sample size and an average image size of less than 10MB to keep API costs low.
- Function to automatically send reduced version of larger PNGs in progress, but a quick workaround is to take a screenshot of a large image and use that instead of the original.

STEP 4:  
cd into the created image folder and run:

```
streamlit run ../../app.py
```

- There is a button to kick off description generation. If an error occurs, refresh page and click the button again, it will pick up where it left off.

- After successful description generation, the page for image retrieval should come up.

NOTES: Some output will still be in terminal, currently working to display everything in app.
