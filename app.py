from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sys
import base64
import binascii
import cv2
import numpy as np
from dotenv import load_dotenv

# Import our helper modules
import cloudinary_helper
import replicate_helper

# Fix Windows console encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Disable output buffering
os.environ['PYTHONUNBUFFERED'] = '1'

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Store active predictions in memory (for polling)
active_predictions = {}
FACE_TARGET_SIZE = int(os.getenv('FACE_TARGET_SIZE', '1024'))
FACE_CROP_SCALE = float(os.getenv('FACE_CROP_SCALE', '2.4'))
_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')


def decode_base64_image(image_input):
    """Decode a data URL or raw base64 image string into bytes."""
    if not isinstance(image_input, str):
        raise ValueError('child_photo must be a base64 string')

    payload = image_input.strip()
    if not payload:
        raise ValueError('child_photo is empty')

    if payload.startswith('data:'):
        if ',' not in payload:
            raise ValueError('child_photo data URL is malformed')
        payload = payload.split(',', 1)[1].strip()

    if not payload:
        raise ValueError('child_photo base64 content is empty')

    # Accept inputs missing trailing padding to handle browser/client variations.
    payload += '=' * (-len(payload) % 4)

    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError('Invalid child_photo base64 payload')


def preprocess_child_photo(image_bytes):
    """
    Improve face-swap input quality by centering on face and resizing to fixed square.
    Falls back to centered square crop if no face is detected.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Unable to decode child_photo image bytes')

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(50, 50)
    )

    if len(faces) > 0:
        # Use the largest detected face for reliable framing.
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        center_x = x + w // 2
        center_y = y + h // 2
        crop_size = int(max(w, h) * FACE_CROP_SCALE)
    else:
        center_x = width // 2
        center_y = height // 2
        crop_size = int(min(width, height))

    # Keep crop within image bounds.
    crop_size = max(256, min(crop_size, width, height))
    half = crop_size // 2
    left = max(0, center_x - half)
    top = max(0, center_y - half)
    right = left + crop_size
    bottom = top + crop_size

    if right > width:
        right = width
        left = width - crop_size
    if bottom > height:
        bottom = height
        top = height - crop_size

    cropped = image[top:bottom, left:right]
    if cropped.size == 0:
        raise ValueError('Failed to crop child photo for preprocessing')

    interpolation = cv2.INTER_CUBIC if crop_size < FACE_TARGET_SIZE else cv2.INTER_AREA
    final_image = cv2.resize(cropped, (FACE_TARGET_SIZE, FACE_TARGET_SIZE), interpolation=interpolation)

    ok, encoded = cv2.imencode('.jpg', final_image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok:
        raise ValueError('Failed to encode preprocessed child photo')

    used_face_crop = len(faces) > 0
    return encoded.tobytes(), used_face_crop


@app.before_request
def log_request_info():
    """Log details of every incoming request"""
    try:
        if request.path != '/health':
            print(f"\n[REQUEST] {request.method} {request.path}", flush=True)
            if request.content_length:
                print(f"[REQUEST] Content Length: {request.content_length} bytes", flush=True)
    except Exception as e:
        print(f"[ERROR] Error in before_request: {e}", flush=True)


@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler for all unhandled exceptions"""
    print(f"\n[CRITICAL ERROR] Unhandled Exception: {str(e)}", flush=True)
    import traceback
    tb = traceback.format_exc()
    print(tb, flush=True)
    
    # Save to file immediately
    try:
        with open('crash_log.txt', 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {datetime.now()}\n")
            f.write(f"PATH: {request.path}\n")
            f.write(f"ERROR: {str(e)}\n")
            f.write(f"TRACEBACK:\n{tb}\n")
    except:
        pass
        
    return jsonify({'error': f'Server Error: {str(e)}'}), 500


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/swap-face', methods=['POST'])
def swap_face():
    """
    Start face swap process:
    1. Upload child photo to Cloudinary
    2. Start Replicate prediction using selected template image
    3. Return prediction ID for polling
    """
    print("=" * 60, flush=True)
    print("FACE SWAP REQUEST RECEIVED", flush=True)
    print("=" * 60, flush=True)
    
    try:
        data = request.get_json(silent=True)
        
        if not data or 'child_photo' not in data or 'character' not in data:
            print("[ERROR] Missing required fields", flush=True)
            return jsonify({'error': 'Missing required fields: child_photo and character'}), 400
        
        # Decode child photo from base64 (data URL or raw base64)
        try:
            child_image_bytes = decode_base64_image(data['child_photo'])
        except ValueError as decode_error:
            return jsonify({'error': str(decode_error)}), 400

        character = data['character']
        
        print(f"[INFO] Character: {character}", flush=True)
        print(f"[INFO] Original image size: {len(child_image_bytes)} bytes", flush=True)

        # Preprocess photo for better face-swap quality
        processed_image_bytes, used_face_crop = preprocess_child_photo(child_image_bytes)
        print(
            f"[INFO] Preprocessed image size: {len(processed_image_bytes)} bytes "
            f"(face_crop={'yes' if used_face_crop else 'no'})",
            flush=True
        )
        
        # Step 1: Upload child photo to Cloudinary
        print("[STEP 1] Uploading child photo to Cloudinary...", flush=True)
        upload_result = cloudinary_helper.upload_temp_image(processed_image_bytes)
        
        if not upload_result:
            return jsonify({'error': 'Failed to upload image to cloud storage'}), 500
        
        child_image_url = upload_result['url']
        child_public_id = upload_result['public_id']
        
        print(f"[SUCCESS] Child image uploaded: {child_image_url[:50]}...", flush=True)
        
        # Step 2: Start Replicate prediction with template target image
        print("[STEP 2] Starting AI face swap...", flush=True)
        prediction_info = replicate_helper.start_face_generation(
            child_image_url=child_image_url,
            character=character
        )
        
        if not prediction_info:
            # Cleanup uploaded images
            cloudinary_helper.delete_temp_image(child_public_id)
            return jsonify({'error': 'Failed to start AI processing'}), 500
        
        prediction_id = prediction_info['prediction_id']
        
        # Store prediction info for cleanup later
        active_predictions[prediction_id] = {
            'child_cloudinary_id': child_public_id,
            'character': character,
            'status': 'processing'
        }
        
        print(f"[SUCCESS] Prediction started: {prediction_id}", flush=True)
        print("=" * 60, flush=True)
        
        return jsonify({
            'prediction_id': prediction_id,
            'status': 'processing',
            'message': 'Face blending started. Poll /check-status to get updates.'
        })
        
    except Exception as e:
        print(f"[ERROR] Exception in swap_face: {str(e)}", flush=True)
        import traceback
        tb_str = traceback.format_exc()
        print(tb_str, flush=True)
        
        # Also write to error log file
        with open('error_log.txt', 'a', encoding='utf-8') as f:
            from datetime import datetime
            f.write(f"\n{'='*50}\n")
            f.write(f"Time: {datetime.now()}\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Traceback:\n{tb_str}\n")
        
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/check-status/<prediction_id>', methods=['GET'])
def check_status(prediction_id):
    """
    Check the status of a face generation prediction.
    In sync mode, results are returned immediately.
    """
    try:
        print(f"[POLL] Checking status for: {prediction_id}", flush=True)
        
        if prediction_id not in active_predictions:
            return jsonify({'error': 'Prediction not found'}), 404
        
        # Check Replicate status
        status_info = replicate_helper.check_prediction_status(prediction_id)
        
        if not status_info:
            return jsonify({'error': 'Failed to check prediction status'}), 500
        
        status = status_info['status']
        prediction_data = active_predictions[prediction_id]
        
        # Update stored status
        prediction_data['status'] = status
        
        if status == 'succeeded':
            print(f"[SUCCESS] Prediction completed: {prediction_id}", flush=True)
            result_url = status_info.get('result_url')
            
            # Validate that we have a result URL
            if not result_url:
                print(f"[ERROR] No result URL in status_info: {status_info}", flush=True)
                return jsonify({
                    'error': 'Failed to generate result - no output URL received from AI model'
                }), 500
            
            print(f"[SUCCESS] Result URL: {result_url}", flush=True)
            
            # Cleanup Cloudinary child image
            child_id = prediction_data.get('child_cloudinary_id')
            
            if child_id:
                print(f"[CLEANUP] Deleting child image...", flush=True)
                cloudinary_helper.delete_temp_image(child_id)
            
            # Remove from active predictions
            del active_predictions[prediction_id]
            
            return jsonify({
                'status': 'succeeded',
                'result_url': result_url
            })
        
        elif status == 'failed':
            print(f"[FAILED] Prediction failed: {prediction_id}", flush=True)
            error_msg = status_info.get('error', 'Unknown error')
            
            # Cleanup
            child_id = prediction_data.get('child_cloudinary_id')
            
            if child_id:
                cloudinary_helper.delete_temp_image(child_id)
            
            del active_predictions[prediction_id]
            
            return jsonify({
                'status': 'failed',
                'error': error_msg
            })
        
        else:
            # Shouldn't happen in sync mode, but handle it
            return jsonify({
                'status': status
            })
        
    except Exception as e:
        print(f"[ERROR] Exception in check_status: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500




@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    """
    Generate QR code for the result image URL.
    Returns QR code as base64-encoded PNG image.
    """
    try:
        data = request.get_json()
        
        if not data or 'image_url' not in data:
            return jsonify({'error': 'Missing image_url parameter'}), 400
        
        image_url = data['image_url']
        print(f"[QR] Generating QR code for: {image_url[:50]}...", flush=True)
        
        # Generate QR code
        import qrcode
        from io import BytesIO
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(image_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        print(f"[QR] QR code generated successfully", flush=True)
        
        return jsonify({
            'qr_code': f'data:image/png;base64,{qr_base64}'
        })
        
    except Exception as e:
        print(f"[ERROR] QR generation failed: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'QR generation failed: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'cloudinary': 'configured' if os.getenv('CLOUDINARY_API_KEY') else 'not configured',
        'replicate': 'configured' if os.getenv('REPLICATE_API_TOKEN') else 'not configured'
    })


@app.route('/test-cloudinary', methods=['GET'])
def test_cloudinary():
    """Detailed test of Cloudinary configuration"""
    try:
        import cloudinary.api
        
        # Check credentials (masked)
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        config_report = {
            'cloud_name': cloud_name if cloud_name else 'MISSING',
            'api_key': f"{api_key[:4]}***" if api_key else 'MISSING',
            'api_secret': 'ALREADY_SET' if api_secret else 'MISSING'
        }
        
        # Test ping
        try:
            ping_result = cloudinary.api.ping()
            ping_status = "Success"
        except Exception as ping_err:
            ping_status = f"Failed: {str(ping_err)}"
            
        return jsonify({
            'config': config_report,
            'ping': ping_status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("DREAM JOB PHOTO BOOTH - yan-ops/face_swap")
    print("=" * 60)
    print("Using:")
    print("  - Cloudinary for temporary image storage")
    print("  - replicate: yan-ops/face_swap")
    print("  - Seamless face replacement pipeline")
    print("=" * 60)
    print("Server starting at: http://localhost:5000")
    print("=" * 60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
