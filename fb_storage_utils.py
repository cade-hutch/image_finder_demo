import os
import sys
import time
import json
import io
import requests
import datetime
import firebase_admin

from firebase_admin import credentials, firestore, storage
from PIL import Image

curr_dir = os.path.dirname(os.path.realpath(__file__))
keyfile_path = os.path.join(curr_dir, 'image-finder-demo-firebase-adminsdk-3kvua-934cc33dbb.json')
if os.path.exists(keyfile_path):
    cred_input = keyfile_path
else:
    cred_input = {
        "type": os.environ.get("FIREBASE_TYPE"),
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        "auth_uri": os.environ.get("FIREBASE_AUTH_URI"),
        "token_uri": os.environ.get("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.environ.get("FIREBASE_UNIVERSE_DOMAIN")
    }

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(cred_input)
    print('initing app....')
    firebase_admin.initialize_app(cred, {'storageBucket': 'image-finder-demo.appspot.com'})
    print('firebase initialized')

db = firestore.client()
bucket = storage.bucket('image-finder-demo.appspot.com')


def init_app(init_name='app'):
    print('init app dud')


def upload_images_from_list(image_paths, skip_upload=False):
    """
    store images from list of paths to folder in firebase
    """
    if not skip_upload:
        bucket = storage.bucket('image-finder-demo.appspot.com')
        folder_name = os.path.basename(os.path.dirname(image_paths[0]))
        num_imgs = len(image_paths)
        for i, image_pathname in enumerate(image_paths):
            if image_pathname.endswith((".png")):
                image_name = os.path.basename(image_pathname)
                t_start = time.perf_counter()
                blob = bucket.blob(os.path.join('images', folder_name, image_name))
                t_end1 = time.perf_counter()
                print('finished db connection in {}s'.format(round(t_end1 - t_start, 2)))
                try_again = False
                try:
                    blob.upload_from_filename(image_pathname)
                except Exception as e:
                    print(e)
                    print('file upload failed...sleeping and trying again')
                    time.sleep(15)
                    try_again = True
                    print('trying again')
                if try_again:
                    blob.upload_from_filename(image_pathname)
                    #t_end = time.perf_counter() - 15 TODO: keep sleep in time calc??

                t_end = time.perf_counter()
                print('({}/{}) finished {} upload in {}s'.format(i+1, num_imgs, image_name, round(t_end - t_start, 2)))


def upload_images_from_dir(folder_path):
    """
    store images in a folder to folder in firebase
    """
    bucket = storage.bucket('image-finder-demo.appspot.com')
    folder_name = os.path.basename(folder_path)
    for filename in os.listdir(folder_path):
        if filename.endswith((".png")):
            t_start = time.perf_counter()
            blob = bucket.blob(os.path.join('images', folder_name, filename))
            t_end1 = time.perf_counter()
            print('finished db connection in {}s'.format(round(t_end1 - t_start, 2)))
            blob.upload_from_filename(os.path.join(folder_path, filename))
            t_end = time.perf_counter()
            print('finished {} upload in {}s'.format(filename, round(t_end - t_start, 2)))


def fetch_and_process_images(blobs):
    for blob in blobs:
        #the blob's content is read into memory as bytes
        image_bytes = blob.download_as_bytes()
        
        #the bytes are converted into a PIL Image object
        image = Image.open(io.BytesIO(image_bytes))
        
        #process the image (e.g., resize, crop, save, etc.)
        print(f"Image format: {image.format}, Image size: {image.size}")
        #You can use image.show() to display the image, or perform other processing tasks.


def upload_json_descriptions_file(json_descriptions_file):
    """
    upload JSON file to firebase
    """
    bucket = storage.bucket('image-finder-demo.appspot.com')
    json_descriptions_filename = os.path.basename(json_descriptions_file)
    if json_descriptions_file.endswith((".json")):
        blob = bucket.blob(os.path.join('json', json_descriptions_filename))
        blob.upload_from_filename(json_descriptions_file)


def get_file_url(filename):
    bucket = storage.bucket('image-finder-demo.appspot.com')
    blob = bucket.blob(filename)
    return blob.generate_signed_url(version="v4", expiration=datetime.timedelta(minutes=15), method="GET")


def fetch_image_descriptions(file_url, api_key=None):
    response = requests.get(file_url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch file: HTTP {response.status_code}")


def list_files_in_folder(folder_name, search_pngs=True):
    bucket = storage.bucket('image-finder-demo.appspot.com')
    blobs = bucket.list_blobs(prefix=folder_name)
    if search_pngs and blobs:
        #WARNING: line below causes async issue with streamlit
        return [blob.name for blob in blobs if blob.name.endswith('.png')]
    elif blobs:
        return [blob.name for blob in blobs]
    else:
        return []


def does_image_folder_exist(folder_name):
    images_dir = "images/{}".format(folder_name)
    bucket = storage.bucket('image-finder-demo.appspot.com')
    blobs = list(bucket.list_blobs(prefix=images_dir))
    if len(blobs) > 1:
        print('found user image folder in firebase')
        return True
    else:
        print('no user image folder in firebase')
        return False


def does_descriptions_file_exist(api_key='', filename=None):
    """
    search for JSON descriptions file in firebase with either an api key or filename
    """
    if filename:
        search = filename
    else:
        search = api_key
    blobs = list_files_in_folder('json', search_pngs=False)
    if not blobs:
        return False
    for b in blobs:
        if filename in b.name:
            return True
    return False


def download_images(remote_folder, local_folder):
    if not remote_folder.startswith('images/'):
        remote_folder = os.path.join('images', remote_folder)
    print('a')
    bucket = storage.bucket('image-finder-demo.appspot.com')
    #blobs = list_files_in_folder(remote_folder)
    blobs = bucket.list_blobs(prefix=remote_folder)
    print('b')
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)

    for blob in blobs:
        print('c')
        if blob.name.lower().endswith('.png'):
            print('d')
            file_path = os.path.join(local_folder, os.path.basename(blob.name))
            blob.download_to_filename(file_path)
            print(f"Downloaded {blob.name} to {file_path}")


def download_descr_file(local_descr_filepath):
    bucket = storage.bucket('image-finder-demo.appspot.com')
    basename = os.path.basename(local_descr_filepath)
    print('passed in descr filepath', local_descr_filepath)
    blobs = bucket.list_blobs(prefix='json/')
    print('got blobs')
    print(blobs)

    for blob in list(blobs):
        print(blob.name)
        if blob.name.endswith(basename):
            blob.download_to_filename(local_descr_filepath)
            return


def fetch_images_as_bytes(blobs):
    #TODO: get bytes to skip downloading
    images_bytes = []
    for blob in blobs:
        blob.download_bytes()


if __name__ == "__main__":
    descr_file = sys.argv[1]
    image_folder = sys.argv[2]
    remote_image_folder_name = image_folder[-5:]

    t_start = time.perf_counter()
    download_descr_file(descr_file)
    download_images(remote_image_folder_name, image_folder)
    t_end = time.perf_counter()

    print('finished in {}s'.format(t_end - t_start))
