import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os
import glob
import json

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

files = glob.glob(r'templates\kids_dream_jobs\*.png')
new_characters_dict = {}

print("Uploading to Cloudinary...")

for file_path in files:
    filename = os.path.basename(file_path).replace('.png', '')
    # e.g., doctor_boy_template_123456
    
    # We want a cleaner key name like "doctor_boy"
    parts = filename.split('_')
    job = parts[0]
    gender = parts[1]
    char_key = f"{job}_{gender}"
    
    try:
        print(f"Uploading {file_path} as {char_key}...")
        result = cloudinary.uploader.upload(
            file_path,
            folder='templates/dream_jobs',
            public_id=char_key,
            overwrite=True,
            resource_type='image'
        )
        
        url = result['secure_url']
        
        new_characters_dict[char_key] = {
            'prompt': f'A photorealistic portrait of a young Saudi Arabian child ({gender}), working as a {job}, cinematic lighting.',
            'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
            'template_image': url
        }
        
    except Exception as e:
        print(f"Error uploading {file_path}: {e}")

# Save the dictionary to a json file for easy copy pasting
with open('new_dream_jobs_config.json', 'w') as f:
    json.dump(new_characters_dict, f, indent=4)

print("\nFinished uploading! Check new_dream_jobs_config.json")
