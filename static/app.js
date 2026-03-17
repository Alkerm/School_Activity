// State management
let currentScreen = 'camera';
let capturedPhoto = null;
let selectedCharacter = null;
let videoStream = null;

// DOM elements
const cameraScreen = document.getElementById('camera-screen');
const characterScreen = document.getElementById('character-screen');
const processingScreen = document.getElementById('processing-screen');
const resultScreen = document.getElementById('result-screen');

const cameraFeed = document.getElementById('camera-feed');
const photoCanvas = document.getElementById('photo-canvas');
const captureBtn = document.getElementById('capture-btn');
const cameraError = document.getElementById('camera-error');

const capturedPreview = document.getElementById('captured-preview');
const characterCards = document.querySelectorAll('.character-card');
const retakeBtn1 = document.getElementById('retake-btn-1');
const retakeBtn2 = document.getElementById('retake-btn-2');

const resultImage = document.getElementById('result-image');


const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const faceDetector = ('FaceDetector' in window)
    ? new FaceDetector({ fastMode: true, maxDetectedFaces: 1 })
    : null;

const BURST_FRAME_COUNT = 3;
const BURST_FRAME_DELAY_MS = 140;

// Initialize camera on page load
window.addEventListener('DOMContentLoaded', () => {
    initCamera();
    setupEventListeners();
});

function isValidImageDataUrl(value) {
    return typeof value === 'string' && /^data:image\/[a-zA-Z0-9.+-]+;base64,/.test(value);
}

async function parseJsonResponse(response) {
    const responseText = await response.text();
    if (!responseText) {
        return null;
    }

    try {
        return JSON.parse(responseText);
    } catch (parseError) {
        throw new Error(`Server returned invalid JSON (HTTP ${response.status})`);
    }
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function computeImageQualityMetrics(imageData) {
    const data = imageData.data;
    const width = imageData.width;
    const height = imageData.height;

    const gray = new Float32Array(width * height);
    let brightnessSum = 0;

    for (let i = 0, p = 0; i < data.length; i += 4, p++) {
        const value = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        gray[p] = value;
        brightnessSum += value;
    }

    const brightness = brightnessSum / gray.length;
    let sharpnessSum = 0;
    let count = 0;

    for (let y = 1; y < height; y += 2) {
        for (let x = 1; x < width; x += 2) {
            const idx = y * width + x;
            const dx = Math.abs(gray[idx] - gray[idx - 1]);
            const dy = Math.abs(gray[idx] - gray[idx - width]);
            sharpnessSum += dx + dy;
            count++;
        }
    }

    const sharpness = count > 0 ? sharpnessSum / count : 0;
    return { brightness, sharpness };
}

async function detectFaceMetrics(canvas) {
    if (!faceDetector) {
        return { available: false, detected: false };
    }

    try {
        const faces = await faceDetector.detect(canvas);
        if (!faces || faces.length === 0) {
            return { available: true, detected: false };
        }

        const box = faces[0].boundingBox;
        const frameWidth = canvas.width;
        const frameHeight = canvas.height;
        const faceAreaRatio = (box.width * box.height) / (frameWidth * frameHeight);

        const faceCenterX = box.x + box.width / 2;
        const faceCenterY = box.y + box.height / 2;
        const dx = Math.abs(faceCenterX - frameWidth / 2) / frameWidth;
        const dy = Math.abs(faceCenterY - frameHeight / 2) / frameHeight;
        const centerOffset = Math.sqrt(dx * dx + dy * dy);

        return {
            available: true,
            detected: true,
            faceAreaRatio,
            centerOffset
        };
    } catch (error) {
        console.warn('FaceDetector failed, continuing without face-gate:', error);
        return { available: false, detected: false };
    }
}

async function evaluateCanvasQuality(canvas) {
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const basic = computeImageQualityMetrics(imageData);
    const face = await detectFaceMetrics(canvas);

    const brightnessPenalty = Math.abs(basic.brightness - 128) / 128 * 18;
    let score = basic.sharpness - brightnessPenalty;

    if (face.available) {
        if (!face.detected) {
            score -= 30;
        } else {
            score += 14;
            score -= face.centerOffset * 15;
        }
    }

    return {
        score,
        brightness: basic.brightness,
        sharpness: basic.sharpness,
        face
    };
}

function drawCurrentFrameToCanvas(canvas, video) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
}

async function captureBestFrameFromBurst(video, frameCount = BURST_FRAME_COUNT) {
    const canvas = photoCanvas;
    const frames = [];

    for (let i = 0; i < frameCount; i++) {
        drawCurrentFrameToCanvas(canvas, video);
        const metrics = await evaluateCanvasQuality(canvas);
        const dataUrl = canvas.toDataURL('image/png');
        frames.push({ dataUrl, metrics });

        if (i < frameCount - 1) {
            await wait(BURST_FRAME_DELAY_MS);
        }
    }

    frames.sort((a, b) => b.metrics.score - a.metrics.score);
    return frames[0];
}

// Initialize camera
async function initCamera() {
    console.log('initCamera called');

    // Check if the origin is secure (Localhost or HTTPS)
    const isSecureOrigin = location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
    if (!isSecureOrigin) {
        console.warn('Camera may not work on non-secure origin:', location.origin);
        alert('⚠️ Camera access requires a secure connection (HTTPS or Localhost). Please check your browser address bar.');
    }

    try {
        // Try with more basic constraints first for better compatibility
        const constraints = {
            video: true
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);

        console.log('Camera stream obtained:', stream.id);
        videoStream = stream;
        cameraFeed.srcObject = stream;

        // Explicitly set muted again by code
        cameraFeed.muted = true;

        // Explicitly call play to handle browsers that block autoplay
        cameraFeed.onloadedmetadata = () => {
            console.log('Video metadata loaded, playing...');
            cameraFeed.play().catch(e => console.error('Error playing video:', e));
        };

        cameraError.style.display = 'none';
        captureBtn.disabled = false;

    } catch (error) {
        console.error('Camera access error:', error);
        cameraError.style.display = 'block';

        let errorMsg = '⚠️ Camera access denied. Please allow camera permissions and refresh.';
        if (error.name === 'NotAllowedError') {
            errorMsg = '⚠️ Camera access denied by user. Please enable it in browser settings and refresh.';
        } else if (error.name === 'NotFoundError') {
            errorMsg = '⚠️ No camera found on this device.';
        } else if (error.name === 'NotReadableError') {
            errorMsg = '⚠️ Camera is already in use by another application.';
        }

        cameraError.innerHTML = `<p>${errorMsg}</p>`;
        captureBtn.disabled = true;
    }
}

// Setup event listeners
function setupEventListeners() {
    // Capture photo
    captureBtn.addEventListener('click', capturePhoto);

    // Character selection
    characterCards.forEach(card => {
        card.addEventListener('click', () => selectCharacter(card));
    });

    // Retake buttons
    retakeBtn1.addEventListener('click', retakePhoto);
    retakeBtn2.addEventListener('click', retakePhoto);



    // File upload
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
}

// Handle file upload fallback
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (event) {
        capturedPhoto = event.target.result;
        capturedPreview.src = capturedPhoto;

        // Stop camera stream if active
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }

        // Switch to character selection screen
        switchScreen('character');
    };
    reader.readAsDataURL(file);
}

// Capture photo from video stream
async function capturePhoto() {
    const video = cameraFeed;

    if (!video.videoWidth || !video.videoHeight) {
        alert('Camera is not ready yet. Please wait a second and try again.');
        return;
    }

    const originalLabel = captureBtn.innerHTML;
    captureBtn.disabled = true;
    captureBtn.innerHTML = '<span class="btn-icon">...</span> Capturing...';

    try {
        const bestFrame = await captureBestFrameFromBurst(video);

        capturedPhoto = bestFrame.dataUrl;
        capturedPreview.src = capturedPhoto;

        // Stop camera stream
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
        }

        // Switch to character selection screen
        switchScreen('character');
    } catch (error) {
        console.error('Capture failed:', error);
        alert('Could not capture photo. Please try again.');
    } finally {
        captureBtn.innerHTML = originalLabel;
        captureBtn.disabled = false;
    }
}

// Select character
function selectCharacter(card) {
    // Remove previous selection
    characterCards.forEach(c => c.classList.remove('selected'));

    // Mark as selected
    card.classList.add('selected');
    selectedCharacter = card.dataset.character;

    // Start face swap process after short delay
    setTimeout(() => {
        performFaceSwap();
    }, 500);
}

// Perform face swap with polling
async function performFaceSwap() {
    console.log('performFaceSwap called');
    console.log('capturedPhoto:', capturedPhoto ? 'exists' : 'null');
    console.log('selectedCharacter:', selectedCharacter);

    if (!capturedPhoto || !selectedCharacter) {
        alert('Please capture a photo and select a character');
        return;
    }

    if (!isValidImageDataUrl(capturedPhoto)) {
        alert('Your photo data is invalid. Please retake or upload the photo again.');
        return;
    }

    // Switch to processing screen
    switchScreen('processing');
    updateLoadingText('Uploading your photo...');

    try {
        // Step 1: Start face swap (upload to Cloudinary + start Replicate)
        console.log('Sending request to /swap-face...');
        const response = await fetch('/swap-face', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                child_photo: capturedPhoto,
                character: selectedCharacter
            })
        });

        console.log('Response received:', response.status);

        const data = await parseJsonResponse(response);

        if (!response.ok) {
            throw new Error((data && data.error) || `Face swap failed (HTTP ${response.status})`);
        }

        if (!data || !data.prediction_id) {
            throw new Error('Server did not return a prediction id');
        }
        const predictionId = data.prediction_id;
        console.log('Prediction ID:', predictionId);

        // Step 2: Poll for completion
        updateLoadingText('Creating your traditional photo...');
        const resultUrl = await pollForResult(predictionId);

        if (resultUrl) {
            // Display result
            resultImage.src = resultUrl;

            // Generate QR code
            generateQRCode(resultUrl);

            switchScreen('result');
        } else {
            throw new Error('Failed to generate result');
        }

    } catch (error) {
        console.error('Face swap error:', error);

        let message = error && error.message ? error.message : 'Unknown error';
        if (message === 'Failed to fetch') {
            message = 'Cannot connect to the server. Check that Flask is running on http://localhost:5000 and try again.';
        }

        alert(`Sorry, something went wrong: ${message}\nPlease try again.`);
        switchScreen('character');
    }
}

// Poll for prediction result
async function pollForResult(predictionId, maxAttempts = 60) {
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/check-status/${predictionId}`);

            if (!response.ok) {
                throw new Error('Failed to check status');
            }

            const data = await parseJsonResponse(response);
            if (!data) {
                throw new Error('Empty status response from server');
            }

            const status = data.status;

            console.log(`[Poll ${attempts + 1}] Status: ${status}`);

            if (status === 'succeeded') {
                console.log('Generation complete!');
                return data.result_url;
            } else if (status === 'failed') {
                throw new Error(data.error || 'Generation failed');
            }

            // Update loading text based on progress
            const elapsed = attempts * 2;
            if (elapsed < 10) {
                updateLoadingText('Starting AI processing...');
            } else if (elapsed < 20) {
                updateLoadingText('Analyzing your face...');
            } else {
                updateLoadingText('Almost done, creating your traditional photo...');
            }

            // Wait 2 seconds before next poll
            await new Promise(resolve => setTimeout(resolve, 2000));
            attempts++;

        } catch (error) {
            console.error('Polling error:', error);
            throw error;
        }
    }

    throw new Error('Timeout: Generation took too long');
}

// Update loading text
function updateLoadingText(text) {
    const loadingText = document.querySelector('.loading-text');
    if (loadingText) {
        loadingText.textContent = text;
    }
}

// Generate QR code for result image
async function generateQRCode(imageUrl) {
    try {
        console.log('Generating QR code for:', imageUrl);

        const response = await fetch('/generate-qr', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                image_url: imageUrl
            })
        });

        if (!response.ok) {
            throw new Error('Failed to generate QR code');
        }

        const data = await response.json();
        const qrCodeImg = document.getElementById('qr-code');

        if (qrCodeImg && data.qr_code) {
            qrCodeImg.src = data.qr_code;
            qrCodeImg.style.display = 'block';
            console.log('QR code displayed successfully');
        }

    } catch (error) {
        console.error('QR code generation error:', error);
        // Don't show error to user, QR is optional feature
    }
}

// Retake photo
function retakePhoto() {
    // Reset state
    capturedPhoto = null;
    selectedCharacter = null;

    // Remove character selections
    characterCards.forEach(c => c.classList.remove('selected'));

    // Restart camera
    initCamera();

    // Switch back to camera screen
    switchScreen('camera');
}



// Switch between screens
function switchScreen(screen) {
    // Hide all screens
    cameraScreen.classList.remove('active');
    characterScreen.classList.remove('active');
    processingScreen.classList.remove('active');
    resultScreen.classList.remove('active');

    // Show selected screen
    switch (screen) {
        case 'camera':
            cameraScreen.classList.add('active');
            break;
        case 'character':
            characterScreen.classList.add('active');
            break;
        case 'processing':
            processingScreen.classList.add('active');
            break;
        case 'result':
            resultScreen.classList.add('active');
            break;
    }

    currentScreen = screen;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
});

// Gender Toggle Logic
function setGender(gender) {
    const btnBoy = document.getElementById('btn-boy');
    const btnGirl = document.getElementById('btn-girl');
    const gridBoy = document.getElementById('grid-boy');
    const gridGirl = document.getElementById('grid-girl');
    
    if (gender === 'boy') {
        btnBoy.className = 'btn btn-primary';
        btnGirl.className = 'btn btn-secondary';
        gridBoy.style.display = 'grid';
        gridGirl.style.display = 'none';
    } else {
        btnBoy.className = 'btn btn-secondary';
        btnGirl.className = 'btn btn-primary';
        gridBoy.style.display = 'none';
        gridGirl.style.display = 'grid';
    }
}
