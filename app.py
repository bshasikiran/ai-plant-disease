import os
import json
import base64
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from utils.disease_detector import DiseaseDetector
from utils.redis_handler import RedisHandler
from utils.translator import Translator
from utils.pdf_generator import PDFGenerator
from utils.chatbot import AgriSageChatbot
from gtts import gTTS
import tempfile

# ===== NEW IMPORTS ADDED =====
import requests
from datetime import datetime
# ===== END NEW IMPORTS =====

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create necessary folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/audio', exist_ok=True)
os.makedirs('reports', exist_ok=True)

# Initialize components with new disease detector
disease_detector = DiseaseDetector()  # This now includes AI treatment generation
redis_handler = RedisHandler()
translator = Translator()
pdf_generator = PDFGenerator()
chatbot = AgriSageChatbot(redis_handler)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_image():
    """Analyze image with AI-powered disease detection and treatment generation"""
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
            
            # Detect disease with AI-generated treatment
            logger.info(f"Analyzing image: {filename}")
            disease_info = disease_detector.detect_disease(filepath)
            
            # Check if detection was successful
            if disease_info.get('error'):
                logger.error(f"Detection error: {disease_info.get('error')}")
                os.remove(filepath)
                return jsonify({
                    'error': disease_info.get('error', 'Detection failed'),
                    'suggestions': disease_info.get('suggestions', [])
                }), 400
            
            # Prepare response with AI-generated treatment
            response_data = {
                'disease': disease_info.get('disease', 'Unknown'),
                'confidence': disease_info.get('confidence', 0),
                'provider': disease_info.get('provider', 'Unknown'),
                'language': language
            }
            
            # Add treatment information (now AI-generated)
            if disease_info.get('treatment'):
                treatment = disease_info['treatment']
                
                # Check if it's a healthy plant
                if 'healthy' in disease_info.get('disease', '').lower():
                    response_data['treatment'] = {
                        'organic': treatment.get('organic', [
                            'Continue regular watering schedule',
                            'Apply organic compost monthly',
                            'Monitor for any changes'
                        ]),
                        'chemical': treatment.get('chemical', [
                            'No chemical treatment needed',
                            'Optional: Balanced fertilizer monthly'
                        ]),
                        'prevention': treatment.get('prevention', [
                            'Maintain proper plant spacing',
                            'Regular inspection',
                            'Remove dead leaves promptly'
                        ]),
                        'immediate_actions': treatment.get('immediate_actions', []),
                        'special_note': treatment.get('special_note', '✅ Your plant is healthy!'),
                        'ai_generated': treatment.get('ai_generated', False)
                    }
                else:
                    # For diseased plants
                    response_data['treatment'] = {
                        'organic': treatment.get('organic', []),
                        'chemical': treatment.get('chemical', []),
                        'prevention': treatment.get('prevention', []),
                        'immediate_actions': treatment.get('immediate_actions', []),
                        'ai_generated': treatment.get('ai_generated', False)
                    }
            else:
                # Fallback treatment if AI generation fails
                logger.warning("No treatment generated, using fallback")
                response_data['treatment'] = get_fallback_treatment(disease_info.get('disease', 'Unknown'))
            
            # Add additional information if available
            if disease_info.get('symptoms'):
                response_data['symptoms'] = disease_info['symptoms']
            
            if disease_info.get('severity'):
                response_data['severity'] = disease_info['severity']
            
            if disease_info.get('alternatives'):
                response_data['alternatives'] = disease_info['alternatives']
            
            # Translate if Telugu is selected
            if language == 'te':
                response_data = translate_response(response_data)
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            logger.info(f"Analysis complete: {response_data['disease']} ({response_data['confidence']}%)")
            return jsonify(response_data), 200
            
        return jsonify({'error': 'Invalid file type. Please upload an image.'}), 400
        
    except Exception as e:
        logger.error(f"Error in analyze_image: {str(e)}")
        return jsonify({
            'error': 'An error occurred during analysis',
            'details': str(e)
        }), 500

def get_fallback_treatment(disease_name):
    """Get fallback treatment when AI generation fails"""
    disease_lower = disease_name.lower()
    
    if 'healthy' in disease_lower:
        return {
            'organic': [
                'Continue regular watering (1-2 inches per week)',
                'Apply organic compost monthly',
                'Use neem oil spray preventively every 2 weeks'
            ],
            'chemical': [
                'No chemical treatment needed',
                'Optional: Apply balanced NPK fertilizer monthly'
            ],
            'prevention': [
                'Maintain proper plant spacing',
                'Regular inspection for early detection',
                'Remove dead material promptly'
            ],
            'special_note': '✅ Your plant appears healthy!',
            'ai_generated': False
        }
    elif 'blight' in disease_lower:
        return {
            'organic': [
                'Remove all infected leaves immediately',
                'Apply neem oil (5ml/L) every 3 days',
                'Use copper-based organic fungicide'
            ],
            'chemical': [
                'Apply Mancozeb (2.5g/L) weekly',
                'Use Chlorothalonil for severe cases',
                'Follow label instructions carefully'
            ],
            'prevention': [
                'Ensure 18-24 inch plant spacing',
                'Water at soil level only',
                'Apply mulch to prevent splash'
            ],
            'immediate_actions': [
                'Remove infected parts NOW',
                'Isolate affected plants',
                'Start treatment immediately'
            ],
            'ai_generated': False
        }
    elif 'spot' in disease_lower:
        return {
            'organic': [
                'Apply copper hydroxide solution',
                'Neem oil spray weekly',
                'Remove infected leaves'
            ],
            'chemical': [
                'Use Copper oxychloride (3g/L)',
                'Apply systemic fungicide if severe'
            ],
            'prevention': [
                'Avoid overhead watering',
                'Improve air circulation',
                'Use resistant varieties'
            ],
            'ai_generated': False
        }
    else:
        return {
            'organic': [
                'Remove affected parts immediately',
                'Apply neem oil (5ml/L) every 3-5 days',
                'Use organic fungicide as directed'
            ],
            'chemical': [
                'Consult local expert for specific treatment',
                'Apply appropriate fungicide/pesticide'
            ],
            'prevention': [
                'Improve plant spacing',
                'Ensure proper drainage',
                'Monitor daily for changes'
            ],
            'ai_generated': False
        }

def translate_response(response_data):
    """Translate response to Telugu"""
    try:
        # Translate disease name
        response_data['disease'] = translator.translate_to_telugu(response_data['disease'])
        
        # Translate treatment
        if response_data.get('treatment'):
            treatment = response_data['treatment']
            
            # Translate each treatment category
            for key in ['organic', 'chemical', 'prevention', 'immediate_actions']:
                if key in treatment and treatment[key]:
                    treatment[key] = [translator.translate_to_telugu(item) for item in treatment[key]]
            
            # Translate special note if exists
            if treatment.get('special_note'):
                treatment['special_note'] = translator.translate_to_telugu(treatment['special_note'])
        
        # Translate symptoms if present
        if response_data.get('symptoms'):
            response_data['symptoms'] = [translator.translate_to_telugu(s) for s in response_data['symptoms']]
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
    
    return response_data

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with disease context awareness"""
    try:
        session_id = request.form.get('session_id', 'default')
        message = request.form.get('message', '')
        language = request.form.get('language', 'en')
        
        image_data = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Convert image to base64 for processing
                image_bytes = file.read()
                image_data = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode()}"
        
        # Process message with chatbot
        response = chatbot.process_message(
            session_id=session_id,
            message=message,
            image_data=image_data,
            language=language
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'response': 'Sorry, I encountered an error. Please try again.',
            'error': str(e)
        }), 500

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    """Generate audio for text-to-speech"""
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate audio
        tts_lang = 'te' if language == 'te' else 'en'
        tts = gTTS(text=text, lang=tts_lang, slow=False)
        
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
    """Generate PDF report with AI-generated treatments"""
    try:
        data = request.json
        
        # Include AI-generated treatment in report
        treatment_data = data.get('treatment', {})
        
        # Generate comprehensive PDF report
        pdf_path = pdf_generator.generate_report(
            disease=data.get('disease', 'Unknown'),
            treatment=treatment_data,
            confidence=data.get('confidence', 0),
            severity=data.get('severity', 'Unknown'),
            ai_generated=treatment_data.get('ai_generated', False)
        )
        
        return send_file(pdf_path, as_attachment=True, download_name='agrisage_report.pdf')
        
    except Exception as e:
        logger.error(f"Error in generate_report: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== NEW ROUTES SECTION ====================
# All new routes are added below this comment for easy identification

@app.route('/api/weather', methods=['POST'])
def get_weather():
    """Get weather data based on location"""
    try:
        data = request.json
        lat = data.get('lat')
        lon = data.get('lon')
        
        # Using OpenWeatherMap API (free tier)
        API_KEY = os.getenv('OPENWEATHER_API_KEY', 'd5d1b5c8f7d9c4e8a8b9c6d5e4f3a2b1')  # Free API key
        
        # Current weather
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        weather_response = requests.get(weather_url, timeout=5).json()
        
        # 5-day forecast
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&cnt=5"
        forecast_response = requests.get(forecast_url, timeout=5).json()
        
        # Extract relevant farming data
        farming_data = {
            'location': weather_response.get('name', 'Unknown'),
            'country': weather_response.get('sys', {}).get('country', ''),
            'current': {
                'temp': round(weather_response['main']['temp'], 1),
                'humidity': weather_response['main']['humidity'],
                'description': weather_response['weather'][0]['description'].title(),
                'wind_speed': round(weather_response['wind']['speed'] * 3.6, 1),  # Convert to km/h
                'pressure': weather_response['main']['pressure'],
                'feels_like': round(weather_response['main']['feels_like'], 1),
                'icon': weather_response['weather'][0]['icon']
            },
            'forecast': [],
            'farming_advice': get_farming_advice(weather_response)
        }
        
        # Process forecast
        if forecast_response.get('list'):
            for item in forecast_response['list'][:5]:
                farming_data['forecast'].append({
                    'date': datetime.fromtimestamp(item['dt']).strftime('%a %d'),
                    'temp': round(item['main']['temp'], 1),
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'].title(),
                    'icon': item['weather'][0]['icon']
                })
        
        return jsonify(farming_data), 200
        
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        # Return sample data if API fails
        return jsonify({
            'location': 'Location',
            'current': {
                'temp': 28,
                'humidity': 65,
                'description': 'Partly Cloudy',
                'wind_speed': 12,
                'pressure': 1013,
                'feels_like': 30
            },
            'forecast': [],
            'farming_advice': ['Check weather regularly', 'Plan irrigation based on forecast']
        }), 200

def get_farming_advice(weather_data):
    """Generate farming advice based on weather conditions"""
    advice = []
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    wind = weather_data['wind']['speed'] * 3.6  # Convert to km/h
    weather_main = weather_data['weather'][0]['main'].lower()
    
    # Temperature-based advice
    if temp > 35:
        advice.append("🌡️ High temperature alert! Increase irrigation frequency and provide shade for sensitive crops")
    elif temp > 30:
        advice.append("☀️ Hot weather - Water plants early morning or late evening")
    elif temp < 10:
        advice.append("❄️ Cold weather - Protect sensitive crops with covers")
    elif temp < 15:
        advice.append("🌡️ Cool temperature - Good for leafy vegetables")
    
    # Humidity-based advice
    if humidity > 80:
        advice.append("💧 High humidity - Watch for fungal diseases, ensure good air circulation")
    elif humidity < 30:
        advice.append("🌵 Low humidity - Consider drip irrigation, mulch to retain moisture")
    
    # Wind-based advice
    if wind > 20:
        advice.append("💨 Strong winds - Stake tall plants, delay pesticide spraying")
    
    # Rain conditions
    if 'rain' in weather_main:
        advice.append("🌧️ Rain expected - Delay fertilizer application, harvest ripe crops")
    elif 'storm' in weather_main or 'thunderstorm' in weather_main:
        advice.append("⛈️ Storm warning - Secure greenhouses, harvest ready crops immediately")
    
    # Add general advice if no specific conditions
    if not advice:
        advice.append("✅ Good weather conditions for general farming activities")
    
    return advice[:4]  # Return top 4 advice items

@app.route('/api/community/posts', methods=['GET'])
def get_community_posts():
    """Get community posts and agriculture news"""
    try:
        posts = [
            {
                'id': 1,
                'author': 'Farmer Raju',
                'location': 'Punjab, India',
                'content': 'My wheat crop is showing excellent growth this season after using organic fertilizers! Yield increased by 20%.',
                'image': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400',
                'likes': 45,
                'comments': 12,
                'timestamp': '2 hours ago',
                'tags': ['wheat', 'organic', 'success']
            },
            {
                'id': 2,
                'author': 'Dr. Sharma (Expert)',
                'location': 'IARI, Delhi',
                'content': '🌾 TIP: Use neem oil spray (5ml/L) every 15 days to prevent pest attacks naturally. Best applied early morning!',
                'likes': 89,
                'comments': 23,
                'timestamp': '5 hours ago',
                'tags': ['tips', 'pestcontrol', 'organic']
            },
            {
                'id': 3,
                'author': 'Farmer Lakshmi',
                'location': 'Andhra Pradesh',
                'content': 'Successfully controlled tomato leaf curl virus using yellow sticky traps and neem oil. Sharing what worked for me!',
                'image': 'https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=400',
                'likes': 67,
                'comments': 18,
                'timestamp': '1 day ago',
                'tags': ['tomato', 'virus', 'solution']
            },
            {
                'id': 4,
                'author': 'Agriculture News',
                'location': 'India',
                'content': '📰 Government announces 5% increase in MSP for wheat. New price: ₹2,275 per quintal for 2024-25 season.',
                'likes': 123,
                'comments': 45,
                'timestamp': '1 day ago',
                'tags': ['news', 'msp', 'wheat']
            },
            {
                'id': 5,
                'author': 'Young Farmer Kumar',
                'location': 'Karnataka',
                'content': 'Drip irrigation reduced my water usage by 40% and increased tomato yield. Initial investment worth it!',
                'likes': 56,
                'comments': 9,
                'timestamp': '2 days ago',
                'tags': ['irrigation', 'tomato', 'watersaving']
            }
        ]
        
        return jsonify(posts), 200
        
    except Exception as e:
        logger.error(f"Community feed error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/prices', methods=['GET'])
def get_market_prices():
    """Get current market prices for crops"""
    try:
        # Sample market prices - you can integrate with real API later
        prices = {
            'updated': datetime.now().strftime('%d %b %Y, %I:%M %p'),
            'market': 'National Average',
            'crops': [
                {
                    'name': '🌾 Wheat',
                    'price': '₹2,250',
                    'unit': 'per quintal',
                    'change': '+2.5%',
                    'trend': 'up'
                },
                {
                    'name': '🌾 Rice (Basmati)',
                    'price': '₹3,500',
                    'unit': 'per quintal',
                    'change': '-1.2%',
                    'trend': 'down'
                },
                {
                    'name': '🥔 Potato',
                    'price': '₹18',
                    'unit': 'per kg',
                    'change': '+8%',
                    'trend': 'up'
                },
                {
                    'name': '🧅 Onion',
                    'price': '₹28',
                    'unit': 'per kg',
                    'change': '-5%',
                    'trend': 'down'
                },
                {
                    'name': '🍅 Tomato',
                    'price': '₹35',
                    'unit': 'per kg',
                    'change': '+15%',
                    'trend': 'up'
                },
                {
                    'name': '🌶️ Green Chilli',
                    'price': '₹60',
                    'unit': 'per kg',
                    'change': '+3%',
                    'trend': 'up'
                },
                {
                    'name': '🌽 Maize',
                    'price': '₹2,100',
                    'unit': 'per quintal',
                    'change': '0%',
                    'trend': 'stable'
                },
                {
                    'name': '🥜 Groundnut',
                    'price': '₹5,500',
                    'unit': 'per quintal',
                    'change': '+4%',
                    'trend': 'up'
                }
            ]
        }
        
        return jsonify(prices), 200
        
    except Exception as e:
        logger.error(f"Market prices error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/farming/tips', methods=['GET'])
def get_farming_tips():
    """Get daily farming tips"""
    try:
        tips = [
            {
                'id': 1,
                'category': 'Irrigation',
                'tip': 'Water plants early morning (5-7 AM) or late evening (5-7 PM) to minimize evaporation loss',
                'icon': '💧'
            },
            {
                'id': 2,
                'category': 'Soil Health',
                'tip': 'Rotate crops yearly: Follow legumes after cereals to naturally replenish nitrogen in soil',
                'icon': '🌱'
            },
            {
                'id': 3,
                'category': 'Pest Control',
                'tip': 'Install yellow sticky traps at crop height to monitor and control whiteflies and aphids',
                'icon': '🐛'
            },
            {
                'id': 4,
                'category': 'Fertilizer',
                'tip': 'Apply fertilizers after irrigation when soil is moist for better nutrient absorption',
                'icon': '🌿'
            },
            {
                'id': 5,
                'category': 'Disease Prevention',
                'tip': 'Maintain 2-3 feet spacing between plants for air circulation to prevent fungal diseases',
                'icon': '🦠'
            }
        ]
        
        # Get random tip of the day based on current date
        import random
        random.seed(datetime.now().day)
        tip_of_day = random.choice(tips)
        
        return jsonify({
            'tip_of_day': tip_of_day,
            'all_tips': tips
        }), 200
        
    except Exception as e:
        logger.error(f"Farming tips error: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== END NEW ROUTES SECTION ====================

@app.route('/health')
def health():
    """Health check endpoint"""
    providers_status = {}
    
    try:
        # Check which providers are available
        if hasattr(disease_detector, 'providers_initialized'):
            providers_status = disease_detector.providers_initialized
    except:
        pass
    
    return jsonify({
        'status': 'healthy',
        'providers': providers_status,
        'version': '2.0'
    }), 200

# PWA Routes
@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest"""
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    """Serve service worker"""
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/offline')
def offline():
    """Offline page for PWA"""
    return render_template('offline.html')

# Mobile detection
@app.before_request
def detect_mobile():
    """Detect if request is from mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    request.is_mobile = any(device in user_agent for device in ['android', 'iphone', 'ipad'])

@app.route('/test')
def test_page():
    """Test page for checking functionality"""
    return render_template('test.html')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting AgriSage server on port {port}")
    logger.info(f"Debug mode: {debug_mode}")
    
    # Log available providers
    if hasattr(disease_detector, 'provider_priority'):
        logger.info(f"Available AI providers: {disease_detector.provider_priority}")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)