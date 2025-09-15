import os
import json
import base64
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from utils.disease_detector import DiseaseDetector
from utils.redis_handler import RedisHandler
from utils.translator import Translator
from utils.pdf_generator import PDFGenerator
from gtts import gTTS # pyright: ignore[reportMissingImports]
import tempfile

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/audio', exist_ok=True)

# Initialize components
disease_detector = DiseaseDetector()
redis_handler = RedisHandler()
translator = Translator()
pdf_generator = PDFGenerator()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        language = request.form.get('language', 'en')
        
        if file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
        
        if file and allowed_file(file.filename):
            # Save uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Detect disease
            logger.info(f"Analyzing image: {filename}")
            disease_info = disease_detector.detect_disease(filepath)
            
            if disease_info['disease'] == 'Unknown':
                return jsonify({
                    'error': 'Could not identify the disease. Please try with a clearer image.'
                }), 400
            
            # Get treatment from Redis
            treatment = redis_handler.get_treatment(disease_info['disease'])
            
            # Translate if needed
            if language == 'te':
                disease_info['disease'] = translator.translate_to_telugu(disease_info['disease'])
                if treatment:
                    treatment['organic'] = translator.translate_to_telugu(treatment.get('organic', ''))
                    treatment['chemical'] = translator.translate_to_telugu(treatment.get('chemical', ''))
                    treatment['prevention'] = translator.translate_to_telugu(treatment.get('prevention', ''))
            
            # Clean up uploaded file
            os.remove(filepath)
            
            response_data = {
                'disease': disease_info['disease'],
                'confidence': disease_info['confidence'],
                'treatment': treatment,
                'language': language
            }
            
            return jsonify(response_data), 200
            
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        logger.error(f"Error in analyze_image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate audio
        tts = gTTS(text=text, lang='te' if language == 'te' else 'en', slow=False)
        
        # Save to temporary file
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', dir='static/audio')
        tts.save(audio_file.name)
        
        # Return the audio file path
        audio_url = f'/static/audio/{os.path.basename(audio_file.name)}'
        
        return jsonify({'audio_url': audio_url}), 200
        
    except Exception as e:
        logger.error(f"Error in generate_audio: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_report', methods=['POST'])
def generate_report():
    try:
        data = request.json
        
        # Generate PDF report
        pdf_path = pdf_generator.generate_report(
            disease=data.get('disease', 'Unknown'),
            treatment=data.get('treatment', {}),
            confidence=data.get('confidence', 0)
        )
        
        return send_file(pdf_path, as_attachment=True, download_name='agrisage_report.pdf')
        
    except Exception as e:
        logger.error(f"Error in generate_report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)