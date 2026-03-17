import os
import io
from google import genai
from google.genai import types
from PIL import Image

# Load Google API key from environment
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    raise ValueError('GOOGLE_API_KEY is not set')

if not API_KEY or API_KEY == 'your_google_api_key_here':
    print("❌ ERROR: Please add your real GOOGLE_API_KEY to the .env file")
    print("Get it from: https://aistudio.google.com/apikey")
    exit(1)

# Initialize the official Google GenAI client
client = genai.Client(api_key=API_KEY)

# The Job we want to generate a template for
JOB_TITLE = "Doctor"
PROMPT = (
    f"A photorealistic portrait of an adult Saudi Arabian man working as a {JOB_TITLE}, "
    "wearing professional clothes related to the job, standing inside a real-world environment "
    "related to the job. The person has a neutral but professional expression. "
    "Cinematic lighting, hyper-detailed, 8k resolution, suitable for a photo booth template."
)

print(f"Testing Gemini Free Tier Image Generation with Imagen 3.0...")
print(f"Job: {JOB_TITLE}")
print(f"Prompt: {PROMPT}\n")
print("Waiting for Google API (usually takes 5-15 seconds)...")

try:
    # Use the specific Imagen model available
    result = client.models.generate_images(
        model='imagen-4.0-generate-001',
        prompt=PROMPT,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="1:1"
        )
    )
    
    # Save the generated image
    if result.generated_images:
        image_bytes = result.generated_images[0].image.image_bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        filename = f"template_{JOB_TITLE.lower()}.png"
        image.save(filename)
            
        print(f"SUCCESS! Generated image saved as: {filename}")
        print("You can now open the folder and check the quality of this template!")
    else:
        print("No images were returned.")
        
except Exception as e:
    import json
    with open("error_out.json", "w") as f:
        f.write(str(e))
    print(f"API Error: {str(e)[:50]}...")
    print("If you are getting a 404 error, make sure the API key is valid and has Image Generation enabled.")
