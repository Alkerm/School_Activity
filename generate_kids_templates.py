import os
import io
import time
from google import genai
from google.genai import types
from PIL import Image

API_KEY = 'AIzaSyD-Oyn8zHdVAqqU1xDvE0IFtWtT_ebOsLk'

client = genai.Client(api_key=API_KEY)

jobs = [
    "doctor",
    "nurse",
    "engineer",
    "teacher",
    "fire fighter",
    "software engineer",
    "police officer",
    "astronaut",
    "lawyer",
    "pilot"
]

genders = ['boy', 'girl']

output_dir = "templates_kids"
os.makedirs(output_dir, exist_ok=True)

for job in jobs:
    for gender in genders:
        filename = os.path.join(output_dir, f"template_{job.replace(' ', '_')}_{gender}.png")
        if os.path.exists(filename):
            print(f"Skipping {filename}, already exists.")
            continue
            
        print(f"Generating template for {gender} {job}...")
        
        # Child prompt with generic face
        prompt = (
            f"A photorealistic portrait of a young Saudi Arabian child ({gender}), about 8-10 years old, "
            f"working as a {job}, wearing realistic and highly detailed professional clothes related to the {job} profession. "
            f"The background is a real-world environment appropriate for a {job}. "
            f"The child is looking directly at the camera with a neutral, clear face to allow for easy and high-accuracy face swapping. "
            f"The child's face should be as generic and well-lit as possible, directly facing forward (passport style angle) "
            "with no hair obscuring the forehead or face. "
            "Cinematic lighting, hyper-detailed, 8k resolution, photo booth style."
        )
        
        try:
            result = client.models.generate_images(
                model='imagen-3.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="1:1"
                )
            )
            
            if result.generated_images:
                image_bytes = result.generated_images[0].image.image_bytes
                image = Image.open(io.BytesIO(image_bytes))
                image.save(filename)
                print(f"SUCCESS: Saved {filename}")
            else:
                print(f"FAILED: No image returned for {gender} {job}")
                
        except Exception as e:
            print(f"ERROR generating {gender} {job}: {e}")
        
        # Avoid rate limits
        time.sleep(5)

print("Finished generating templates.")
