"""
Replicate API Helper Module - IP-Adapter Face Inpaint
Handles face blending using lucataco/ip_adapter-face-inpaint model.
"""

import replicate
import os
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Replicate API
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
if REPLICATE_API_TOKEN:
    os.environ['REPLICATE_API_TOKEN'] = REPLICATE_API_TOKEN

def _clamp_weight(value: float) -> float:
    return max(0.5, min(1.0, value))


def _parse_weight_overrides(raw: str) -> Dict[str, float]:
    """
    Parse FACE_SWAP_WEIGHT_OVERRIDES in the format:
    "doctor_boy=0.82,teacher_girl=0.84,default=0.85"
    """
    overrides: Dict[str, float] = {}
    if not raw:
        return overrides

    for chunk in raw.split(','):
        item = chunk.strip()
        if not item or '=' not in item:
            continue
        key, value = item.split('=', 1)
        key = key.strip().lower()
        if not key:
            continue
        try:
            parsed = float(value.strip())
        except ValueError:
            continue
        overrides[key] = _clamp_weight(parsed)
    return overrides


def _get_swap_weight(character: Optional[str] = None, style_config: Optional[Dict[str, Any]] = None) -> float:
    """Get swap weight with override priority: style_config -> env override -> env default."""
    raw_weight = os.getenv('FACE_SWAP_WEIGHT', '0.85')
    try:
        parsed = float(raw_weight)
    except ValueError:
        parsed = 0.85
    selected = _clamp_weight(parsed)

    raw_overrides = os.getenv('FACE_SWAP_WEIGHT_OVERRIDES', '')
    overrides = _parse_weight_overrides(raw_overrides)
    character_key = (character or '').strip().lower()
    if character_key and character_key in overrides:
        selected = overrides[character_key]
    elif 'default' in overrides:
        selected = overrides['default']

    if style_config and isinstance(style_config.get('swap_weight'), (int, float)):
        selected = _clamp_weight(float(style_config['swap_weight']))

    return selected


# Character style mapping for SDXL IP-Adapter FaceID
CHARACTER_STYLES = {
    'superman': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed,
brown costume, gray costume, desaturated colors, muted colors''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768395277/templates/superman_template_vibrant_v4.png'
    },
    'batman': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768659434/templates/batman_template_backend.jpg'
    },
    'spiderman': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768659435/templates/spiderman_template_backend.jpg'
    },
    'wonderwoman': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768659435/templates/wonderwoman_template_backend.jpg'
    },
    'ironman': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768659436/templates/ironman_template_backend.jpg'
    },
    'captainamerica': {
        'prompt': '''Preserve the superhero's original head shape, jawline, skull structure,
hair, hairstyle, costume, pose, and lighting exactly as in the base image.

Subtly blend the child's facial characteristics into the face,
including eyes, eyebrows, nose, mouth, and expression.

Child face, young facial proportions, soft facial features.

No face swap. No replacement of head shape. Maintain superhero identity.

Photorealistic. Cinematic lighting. Clean studio background. High detail.''',
        
        'negative_prompt': '''face swap, different jawline, different hair, adult face, aging,
distorted face, cartoon, anime, exaggerated features, deformed''',
        
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1768659437/templates/captainamerica_template_backend.jpg'
    },
    'saudi_central_male': {
        'prompt': 'Saudi man wearing traditional bisht and thobe, photorealistic, cinematic lighting',
        'negative_prompt': 'cartoon, drawing, anime, low quality',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/templates/saudi_central_male_v7.png'
    },
    'saudi_traditional_daglah': {
        'prompt': 'Saudi man wearing traditional daglah with golden embroidered patterns and black bandolier, white shemagh with black agal, photorealistic, cinematic lighting, traditional Saudi heritage setting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1770104351/templates/saudi_traditional_daglah.jpg'
    },
    'jeddah_character_updated_1770487272655': {
        'prompt': 'Young Saudi man wearing white bisht over black thobe, white shemagh with gold-striped agal, clean-shaven face with very light mustache, Jeddah cityscape background, photorealistic, professional photography, natural lighting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, old man, elderly, goatee, beard, heavy mustache',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1770487272/templates/jeddah_character_updated.jpg'
    },
    'daglah_child_character_1770488439465': {
        'prompt': 'Saudi Arabian boy child aged 8-12 years old wearing traditional daglah with golden embroidery and black bandolier, white shemagh with black agal, child face, young boy, photorealistic, professional photography, natural lighting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, adult, teenager, facial hair, beard, mustache',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1770488439/templates/daglah_child_character.jpg'
    },
    'sharqawi_dress_character_1770578762613': {
        'prompt': 'Saudi Arabian woman wearing traditional Eastern Province (Sharqiyah) black dress with intricate gold embroidery, black hijab with gold trim, elegant appearance, photorealistic, professional photography, natural lighting, traditional Saudi heritage setting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, niqab',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1770578762/templates/sharqawi_dress_character.jpg'
    },
    'jeddah_character_updated_1770660835227': {
        'prompt': 'Fit athletic Saudi Arabian man wearing traditional white bisht over black thobe, white shemagh with gold-striped agal, well-groomed full light beard with mustache, natural neutral expression, historical Saudi heritage architecture background (old Jeddah Al-Balad style), photorealistic, professional photography, natural lighting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, smile, goatee only, clean shaven',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/templates/jeddah_updated_v2.jpg'
    },
    'northern_woman_v1_1770658383334': {
        'prompt': 'Saudi Arabian woman wearing traditional Northern Saudi dress with burgundy/maroon embroidered vest featuring vertical striped patterns and gold coin necklace decorations, black hijab with burgundy and gold coin headband, black waist sash, elegant appearance, photorealistic, professional photography, natural lighting, traditional Saudi heritage setting',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, niqab',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/templates/northern_woman_v1.jpg'
    },
    'sharqawi_girl_child': {
        'prompt': 'Beautiful 8-12 year old Saudi Arabian girl wearing a traditional black Sharqawi dress with intricate gold embroidery and a matching sheer veil, gentle closed-mouth smile, photorealistic, cinematic lighting, traditional Saudi heritage architecture background',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, teeth, open mouth',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1771073577/templates/sharqawi_girl_child.jpg'
    },
    'southern_asiri_adult': {
        'prompt': 'Beautiful 25-32 year old Saudi Arabian woman with elegant features and fit body shape, wearing traditional Southern Saudi (Asiri) black dress with vibrant colorful geometric embroidery on the chest and sleeves, yellow headscarf, large ornate golden coin bib necklace, gentle closed-mouth smile, photorealistic, cinematic lighting, historical Saudi courtyard background',
        'negative_prompt': 'cartoon, drawing, anime, low quality, modern clothing, western clothing, teeth, open mouth, overweight, bulky',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1771073578/templates/southern_asiri_adult.jpg'
    },
    'astronaut_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a astronaut, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625719/templates/dream_jobs/astronaut_boy.png'
    },
    'astronaut_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a astronaut, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625721/templates/dream_jobs/astronaut_girl.png'
    },
    'doctor_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a doctor, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625722/templates/dream_jobs/doctor_boy.png'
    },
    'doctor_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a doctor, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625723/templates/dream_jobs/doctor_girl.png'
    },
    'engineer_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a engineer, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625724/templates/dream_jobs/engineer_boy.png'
    },
    'engineer_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a engineer, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625725/templates/dream_jobs/engineer_girl.png'
    },
    'firefighter_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a firefighter, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625726/templates/dream_jobs/firefighter_boy.png'
    },
    'firefighter_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a firefighter, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625727/templates/dream_jobs/firefighter_girl.png'
    },
    'lawyer_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a lawyer, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625728/templates/dream_jobs/lawyer_boy.png'
    },
    'nurse_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a nurse, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625729/templates/dream_jobs/nurse_boy.png'
    },
    'nurse_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a nurse, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625730/templates/dream_jobs/nurse_girl.png'
    },
    'police_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a police, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625731/templates/dream_jobs/police_boy.png'
    },
    'police_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a police, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625732/templates/dream_jobs/police_girl.png'
    },
    'software_engineer': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (engineer), working as a software, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625732/templates/dream_jobs/software_engineer.png'
    },
    'teacher_boy': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (boy), working as a teacher, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625734/templates/dream_jobs/teacher_boy.png'
    },
    'teacher_girl': {
        'prompt': 'A photorealistic portrait of a young Saudi Arabian child (girl), working as a teacher, cinematic lighting.',
        'negative_prompt': 'cartoon, drawing, anime, low quality, adult face, aging, distorted, ugly',
        'template_image': 'https://res.cloudinary.com/dfcqp8igu/image/upload/v1773625735/templates/dream_jobs/teacher_girl.png'
    },
}


def start_face_generation(
    child_image_url: str,
    character: str = 'superman'
) -> Optional[Dict[str, Any]]:
    """
    Start face swap using yan-ops/face_swap model.
    
    Args:
        child_image_url: URL of child's photo (source face)
        character: Character name
        
    Returns:
        Dict with prediction_id and status, or None if failed
    """
    try:
        print(f"[Replicate] Starting Face Swap for character: {character}", flush=True)
        print(f"[Replicate] Child/Source image: {child_image_url[:50]}...", flush=True)
        
        # Get character-specific settings
        style_config = CHARACTER_STYLES.get(character.lower(), CHARACTER_STYLES['superman'])
        
        # Get template image URL (target face)
        template_url = style_config.get('template_image')
        if not template_url:
            print(f"[Replicate] ERROR: No template image for character: {character}", flush=True)
            return None
        
        print(f"[Replicate] Template/Target: {template_url[:50]}...", flush=True)
        
        # Use yan-ops/face_swap - true face swapping with weight control
        # Model expects: source_image (face to swap FROM) and target_image (image to swap TO)
        swap_weight = _get_swap_weight(character=character, style_config=style_config)
        input_params = {
            "source_image": child_image_url,    # The user's face to swap FROM
            "target_image": template_url,       # The character template to swap TO
            "weight": swap_weight
        }
        
        print(f"[Replicate] Using yan-ops/face_swap model", flush=True)
        print(f"  Source (child): {child_image_url[:50]}...", flush=True)
        print(f"  Target (template): {template_url[:50]}...", flush=True)
        print(f"  Weight: {swap_weight}", flush=True)
        
        # Use yan-ops/face_swap model (true face swapping)
        model_name = "yan-ops/face_swap"
        
        print(f"[Replicate] Getting model version...", flush=True)
        model = replicate.models.get(model_name)
        version = model.latest_version
        
        print(f"[Replicate] Sending request to {model_name} (version: {version.id[:12]}...)", flush=True)
        
        # Create prediction using VERSION (not model name)
        prediction = replicate.predictions.create(
            version=version.id,
            input=input_params
        )
        
        prediction_id = prediction.id
        print(f"[Replicate] Prediction started: {prediction_id}", flush=True)
        
        return {
            'prediction_id': prediction_id,
            'status': prediction.status,
            'created_at': time.time()
        }
        
    except Exception as e:
        print(f"[Replicate] Failed to start prediction: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return None


def check_prediction_status(prediction_id: str) -> Optional[Dict[str, Any]]:
    """
    Check the status of a face generation prediction.
    
    Args:
        prediction_id: The prediction ID from start_face_generation
        
    Returns:
        Dict with status and result URL if complete, None if failed
    """
    try:
        # Check status via API
        prediction = replicate.predictions.get(prediction_id)
        
        status = prediction.status
        
        result = {
            'prediction_id': prediction_id,
            'status': status,
        }
        
        if status == 'succeeded':
            output = prediction.output
            print(f"[Replicate] Raw output type: {type(output).__name__}", flush=True)
            print(f"[Replicate] Raw output value: {output}", flush=True)
            
            if output:
                # yan-ops/face_swap returns a dictionary with 'cache_url' and 'msg'
                # Other models might return a URL string or list of URLs
                if isinstance(output, dict):
                    # Dictionary format: {'cache_url': 'https://...', 'msg': 'succeed'}
                    # Try multiple possible key names
                    result_url = (output.get('cache_url') or 
                                output.get('url') or 
                                output.get('output_url') or
                                output.get('image') or
                                output.get('result'))
                    if not result_url:
                        print(f"[Replicate] ERROR: No URL found in output dict. Keys: {list(output.keys())}", flush=True)
                        print(f"[Replicate] Full output: {output}", flush=True)
                        result_url = None
                    else:
                        print(f"[Replicate] Extracted URL from dict: {result_url}", flush=True)
                elif isinstance(output, list):
                    # List format: ['https://...']
                    result_url = output[0] if output else None
                    print(f"[Replicate] Extracted URL from list: {result_url}", flush=True)
                else:
                    # String format: 'https://...'
                    result_url = output
                    print(f"[Replicate] URL is string: {result_url}", flush=True)
                
                if result_url:
                    result['result_url'] = result_url
                    print(f"[Replicate] ✓ Result URL ready: {result_url[:50]}...", flush=True)
                else:
                    print(f"[Replicate] ✗ ERROR: Could not extract URL from output", flush=True)
                
        elif status == 'failed':
            result['error'] = prediction.error
            print(f"[Replicate] Prediction failed: {prediction.error}", flush=True)
            
        return result
        
    except Exception as e:
        print(f"[Replicate] Failed to check status: {str(e)}", flush=True)
        return None


def test_connection() -> bool:
    """
    Test Replicate API connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        # Try to list models (requires valid API token)
        models = replicate.models.list()
        print("[Replicate] Connection successful!", flush=True)
        return True
    except Exception as e:
        print(f"[Replicate] Connection failed: {str(e)}", flush=True)
        print("[Replicate] Please check REPLICATE_API_TOKEN in .env file", flush=True)
        return False


if __name__ == "__main__":
    # Test the connection
    print("Testing Replicate connection...")
    test_connection()
