
import os
import sys

# Mocking variables to test logic
BASE_DIR = '/home/mario/Escritorio/dockerlabs'
MACHINE_LOGOS_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')
LOGO_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'logos')

def test_path_logic(origen):
    if origen == 'bunker':
        upload_folder = os.path.join(BASE_DIR, 'static', 'bunkerlabs', 'images', 'logos-bunkerlabs')
        db_path_prefix = "bunkerlabs/images/logos-bunkerlabs"
    else:
        upload_folder = LOGO_UPLOAD_FOLDER
        db_path_prefix = "dockerlabs/images/logos"
    
    print(f"Origen: {origen}")
    print(f"Upload Folder: {upload_folder}")
    print(f"DB Path Prefix: {db_path_prefix}")

print("Testing DockerLabs logic:")
test_path_logic('docker')
print("-" * 20)
print("Testing BunkerLabs logic:")
test_path_logic('bunker')
