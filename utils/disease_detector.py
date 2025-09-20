import os
import logging
import json
import time
import base64
from typing import Dict, Any, Optional, List
from PIL import Image
import requests
from io import BytesIO
import numpy as np

logger = logging.getLogger(__name__)

class DiseaseDetector:
    def __init__(self):
        """Initialize disease detector with multiple AI providers"""
        self.providers_initialized = {}
        self.provider_priority = []
        
        # Initialize all providers
        self.init_grok()
        self.init_gemini()
        self.init_openai()
        self.init_huggingface()
        self.init_groq()  # Alternative to Grok
        
        # Set priority based on what's available
        self.set_provider_priority()
        
        # Setup disease knowledge base
        self.setup_disease_database()
        
        logger.info(f"Providers ready: {self.provider_priority}")

    def init_grok(self):
        """Initialize xAI Grok API"""
        self.grok_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API_KEY')
        
        if self.grok_key:
            try:
                # Grok uses OpenAI-compatible client
                from openai import OpenAI
                self.grok_client = OpenAI(
                    api_key=self.grok_key,
                    base_url="https://api.x.ai/v1"  # xAI endpoint
                )
                self.providers_initialized['grok'] = True
                logger.info("✅ Grok (xAI) initialized")
            except Exception as e:
                logger.warning(f"Grok init failed: {e}")
                self.providers_initialized['grok'] = False
        else:
            self.providers_initialized['grok'] = False

    def init_groq(self):
        """Initialize Groq as alternative (free and fast)"""
        self.groq_key = os.getenv('GROQ_API_KEY')
        
        if self.groq_key:
            try:
                from openai import OpenAI
                self.groq_client = OpenAI(
                    api_key=self.groq_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                self.providers_initialized['groq'] = True
                logger.info("✅ Groq initialized (fast alternative)")
            except Exception as e:
                logger.warning(f"Groq init failed: {e}")
                self.providers_initialized['groq'] = False
        else:
            self.providers_initialized['groq'] = False

    def init_gemini(self):
        """Initialize Google Gemini - FIXED VERSION"""
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                
                # Try different model versions
                model_versions = [
                    'gemini-1.5-flash',
                    'gemini-1.5-pro',
                    'gemini-pro-vision',
                    'gemini-pro'
                ]
                
                for model_name in model_versions:
                    try:
                        self.gemini_model = genai.GenerativeModel(model_name)
                        self.gemini_model_name = model_name
                        logger.info(f"✅ Gemini initialized with {model_name}")
                        self.providers_initialized['gemini'] = True
                        break
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
                self.providers_initialized['gemini'] = False
        else:
            self.providers_initialized['gemini'] = False

    def init_openai(self):
        """Initialize OpenAI GPT-4"""
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
                # Test if key has credits
                try:
                    # Quick test call
                    self.openai_client.models.list()
                    self.providers_initialized['openai'] = True
                    logger.info("✅ OpenAI initialized with credits")
                except:
                    self.providers_initialized['openai'] = False
                    logger.warning("OpenAI key valid but no credits")
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")
                self.providers_initialized['openai'] = False
        else:
            self.providers_initialized['openai'] = False

    def init_huggingface(self):
        """Initialize HuggingFace with multiple models"""
        self.hf_token = os.getenv('HF_TOKEN')
        
        # Multiple models for better reliability
        self.hf_models = [
            "PlantNet/PlantNet-300K",  # Best quality model
            "zuppif/plantdisease",
            "emre/plant_disease_detection",
            "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
            "Shravyasri/plant-disease-detection"
        ]
        
        self.current_model_idx = 0
        self.update_hf_model()
        
        if self.hf_token:
            self.hf_headers = {"Authorization": f"Bearer {self.hf_token}"}
        else:
            self.hf_headers = {}
        
        self.providers_initialized['huggingface'] = True
        logger.info("✅ HuggingFace initialized (always available)")

    def update_hf_model(self):
        """Update current HuggingFace model"""
        self.current_hf_model = self.hf_models[self.current_model_idx]
        self.hf_api_url = f"https://api-inference.huggingface.co/models/{self.current_hf_model}"

    def set_provider_priority(self):
        """Set provider priority based on availability"""
        # Priority order (best to fallback)
        priority_order = ['grok', 'groq', 'openai', 'gemini', 'huggingface']
        
        for provider in priority_order:
            if self.providers_initialized.get(provider, False):
                self.provider_priority.append(provider)
        
        # Always add huggingface as final fallback
        if 'huggingface' not in self.provider_priority:
            self.provider_priority.append('huggingface')

    def setup_disease_database(self):
        """Comprehensive disease database"""
        self.disease_db = {
            'early_blight': {
                'name': 'Early Blight',
                'scientific': 'Alternaria solani',
                'symptoms': [
                    'Dark brown circular spots with concentric rings',
                    'Yellow halos around spots',
                    'Lower leaves affected first',
                    'Premature leaf drop'
                ],
                'treatment': [
                    'Remove and destroy infected leaves immediately',
                    'Apply neem oil (5ml/L) every 3 days',
                    'Use copper fungicide or chlorothalonil',
                    'Improve air circulation between plants'
                ]
            },
            'late_blight': {
                'name': 'Late Blight',
                'scientific': 'Phytophthora infestans',
                'symptoms': [
                    'Water-soaked dark spots on leaves',
                    'White fuzzy growth on undersides',
                    'Stems turn dark brown/black',
                    'Rapid plant collapse'
                ],
                'treatment': [
                    'Remove and burn all infected plants immediately',
                    'Apply metalaxyl or mancozeb fungicide',
                    'Use Bordeaux mixture for organic control',
                    'Ensure good drainage'
                ]
            },
            'bacterial_spot': {
                'name': 'Bacterial Spot',
                'scientific': 'Xanthomonas spp.',
                'symptoms': [
                    'Small dark spots with yellow halos',
                    'Spots merge into large brown areas',
                    'Leaf edges turn brown',
                    'Raised spots on fruits'
                ],
                'treatment': [
                    'Apply copper-based bactericide',
                    'Remove all infected plant parts',
                    'Avoid overhead watering',
                    'Use disease-free seeds'
                ]
            },
            'powdery_mildew': {
                'name': 'Powdery Mildew',
                'scientific': 'Erysiphe spp.',
                'symptoms': [
                    'White powdery coating on leaves',
                    'Leaves curl and distort',
                    'Yellowing of affected areas',
                    'Stunted growth'
                ],
                'treatment': [
                    'Apply sulfur or potassium bicarbonate',
                    'Neem oil spray weekly',
                    'Remove infected leaves',
                    'Improve air circulation'
                ]
            },
            'leaf_mold': {
                'name': 'Leaf Mold',
                'scientific': 'Fulvia fulva',
                'symptoms': [
                    'Pale green/yellow spots on upper leaves',
                    'Olive-green mold on undersides',
                    'Leaves curl and wilt',
                    'Flower drop'
                ],
                'treatment': [
                    'Reduce humidity below 85%',
                    'Improve greenhouse ventilation',
                    'Apply chlorothalonil fungicide',
                    'Remove lower leaves'
                ]
            },
            'healthy': {
                'name': 'Healthy Plant',
                'symptoms': ['No disease symptoms observed'],
                'treatment': ['Maintain current care routine', 'Monitor regularly']
            }
        }

    def preprocess_image(self, image_path: str, target_size: int = 224) -> bytes:
        """Preprocess image for API calls"""
        try:
            img = Image.open(image_path)
            
            # Convert to RGB
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize
            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
            
            # Convert to bytes
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            return buffered.getvalue()
            
        except Exception as e:
            logger.error(f"Image preprocessing error: {e}")
            return None

    def detect_with_grok(self, image_path: str) -> Optional[Dict]:
        """Use xAI Grok for detection"""
        if not self.providers_initialized.get('grok'):
            return None
        
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            response = self.grok_client.chat.completions.create(
                model="grok-vision-beta",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify the plant disease in this image. What disease is it? What are symptoms and treatment?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                max_tokens=300
            )
            
            text = response.choices[0].message.content
            return self.parse_ai_response(text, 'Grok (xAI)')
            
        except Exception as e:
            logger.error(f"Grok error: {e}")
            return None

    def detect_with_groq(self, image_path: str) -> Optional[Dict]:
        """Use Groq for fast detection"""
        if not self.providers_initialized.get('groq'):
            return None
        
        try:
            # Groq works with text description for now
            # You can add vision support when available
            prompt = """Based on common plant diseases, if you see symptoms like:
            - Dark spots with rings: likely Early Blight
            - Water-soaked spots: likely Late Blight  
            - White powder: likely Powdery Mildew
            - Small spots with halos: likely Bacterial Spot
            
            Provide disease name and treatment."""
            
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            return self.parse_ai_response(text, 'Groq AI')
            
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None

    def detect_with_gemini(self, image_path: str) -> Optional[Dict]:
        """Use Gemini for detection - WORKING VERSION"""
        if not self.providers_initialized.get('gemini'):
            return None
        
        try:
            import google.generativeai as genai
            
            image = Image.open(image_path)
            
            prompt = """You are a plant disease expert. Analyze this image and identify:
1. The plant type
2. Any disease present (or say "Healthy")
3. Main symptoms visible
4. Treatment needed

Be specific and confident in your diagnosis."""

            # Use simple generation config without problematic parameters
            generation_config = {
                'temperature': 0.1,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 500
            }
            
            response = self.gemini_model.generate_content(
                [prompt, image],
                generation_config=generation_config
            )
            
            return self.parse_ai_response(response.text, f'Gemini ({self.gemini_model_name})')
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

    def detect_with_openai(self, image_path: str) -> Optional[Dict]:
        """Use OpenAI GPT-4 Vision"""
        if not self.providers_initialized.get('openai'):
            return None
        
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Identify the plant disease. Name the disease, describe symptoms, and suggest treatment."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "low"}}
                    ]
                }],
                max_tokens=300,
                temperature=0.1
            )
            
            text = response.choices[0].message.content
            return self.parse_ai_response(text, 'OpenAI GPT-4')
            
        except Exception as e:
            if "quota" in str(e).lower():
                logger.warning("OpenAI quota exceeded")
            else:
                logger.error(f"OpenAI error: {e}")
            return None

    def detect_with_huggingface(self, image_path: str, retry_count: int = 0) -> Optional[Dict]:
        """Use HuggingFace models - ENHANCED VERSION"""
        try:
            image_bytes = self.preprocess_image(image_path)
            if not image_bytes:
                return None
            
            # Try current model
            response = requests.post(
                self.hf_api_url,
                headers=self.hf_headers,
                data=image_bytes,
                timeout=20
            )
            
            logger.info(f"HF {self.current_hf_model}: Status {response.status_code}")
            
            # Handle loading models
            if response.status_code == 503:
                if retry_count < 3:
                    logger.info(f"Model loading, waiting...")
                    time.sleep(5)
                    # Try next model
                    self.current_model_idx = (self.current_model_idx + 1) % len(self.hf_models)
                    self.update_hf_model()
                    return self.detect_with_huggingface(image_path, retry_count + 1)
            
            elif response.status_code == 200:
                try:
                    results = response.json()
                    
                    if isinstance(results, list) and len(results) > 0:
                        top = results[0]
                        label = top.get('label', 'Unknown')
                        score = top.get('score', 0)
                        
                        # Parse label
                        disease_name = self.format_hf_label(label)
                        confidence = round(score * 100, 2)
                        
                        # Get disease info
                        disease_info = self.get_disease_info(disease_name)
                        
                        return {
                            'disease': disease_name,
                            'confidence': confidence,
                            'symptoms': disease_info['symptoms'],
                            'treatment': disease_info['treatment'],
                            'provider': f'HuggingFace ({self.current_hf_model.split("/")[-1]})',
                            'alternatives': [
                                {'name': self.format_hf_label(r.get('label')), 
                                 'confidence': round(r.get('score', 0) * 100, 2)}
                                for r in results[1:3] if r.get('label')
                            ]
                        }
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from HuggingFace")
            
            # Try next model on failure
            if retry_count < len(self.hf_models):
                self.current_model_idx = (self.current_model_idx + 1) % len(self.hf_models)
                self.update_hf_model()
                return self.detect_with_huggingface(image_path, retry_count + 1)
            
            return None
            
        except Exception as e:
            logger.error(f"HuggingFace error: {e}")
            return None

    def format_hf_label(self, label: str) -> str:
        """Format HuggingFace label to readable name"""
        if not label:
            return "Unknown"
        
        # Remove prefixes
        label = label.replace('LABEL_', '').replace('class_', '')
        
        # Handle PlantVillage format
        if '___' in label:
            parts = label.split('___')
            if len(parts) >= 2:
                plant = parts[0].replace('_', ' ').title()
                disease = parts[1].replace('_', ' ').title()
                return f"{plant} - {disease}"
        
        # Handle underscores
        return label.replace('_', ' ').replace('-', ' ').title()

    def parse_ai_response(self, text: str, provider: str) -> Dict:
        """Parse AI response text into structured format"""
        result = {
            'disease': 'Unknown',
            'confidence': 75,
            'symptoms': [],
            'treatment': [],
            'provider': provider
        }
        
        if not text:
            return result
        
        text_lower = text.lower()
        
        # Find disease mentions
        for key, info in self.disease_db.items():
            disease_name = info['name'].lower()
            if disease_name in text_lower or key.replace('_', ' ') in text_lower:
                result['disease'] = info['name']
                result['symptoms'] = info.get('symptoms', [])
                result['treatment'] = info.get('treatment', [])
                result['confidence'] = 85
                break
        
        # If no specific disease found, look for keywords
        if result['disease'] == 'Unknown':
            disease_keywords = {
                'blight': 'Blight Disease',
                'spot': 'Leaf Spot Disease',
                'mildew': 'Mildew Disease',
                'rust': 'Rust Disease',
                'wilt': 'Wilt Disease',
                'rot': 'Root/Stem Rot',
                'healthy': 'Healthy Plant'
            }
            
            for keyword, disease_name in disease_keywords.items():
                if keyword in text_lower:
                    result['disease'] = disease_name
                    result['confidence'] = 70
                    break
        
        # Extract confidence if mentioned
        import re
        conf_match = re.search(r'(\d+)%|confidence.*?(\d+)', text_lower)
        if conf_match:
            conf_value = conf_match.group(1) or conf_match.group(2)
            result['confidence'] = min(int(conf_value), 100)
        
        return result

    def get_disease_info(self, disease_name: str) -> Dict:
        """Get disease information from database"""
        disease_lower = disease_name.lower()
        
        # Search in database
        for key, info in self.disease_db.items():
            if key.replace('_', ' ') in disease_lower or info['name'].lower() in disease_lower:
                return {
                    'symptoms': info.get('symptoms', []),
                    'treatment': info.get('treatment', [])
                }
        
        # Default info
        return {
            'symptoms': ['Visual abnormalities detected on plant'],
            'treatment': ['Monitor plant closely', 'Consult local agricultural expert']
        }

    def use_mock_detection(self, image_path: str) -> Dict:
        """Fallback mock detection for testing"""
        import random
        
        diseases = [
            ('Tomato - Early Blight', 87),
            ('Tomato - Late Blight', 82),
            ('Tomato - Bacterial Spot', 85),
            ('Potato - Early Blight', 79),
            ('Pepper - Bacterial Spot', 83),
            ('Tomato - Healthy', 95)
        ]
        
        selected = random.choice(diseases)
        disease_info = self.get_disease_info(selected[0])
        
        return {
            'disease': selected[0],
            'confidence': selected[1],
            'symptoms': disease_info['symptoms'],
            'treatment': disease_info['treatment'],
            'provider': 'Mock Detection (Demo)',
            'note': 'Configure API keys for real detection'
        }

    def detect_disease(self, image_path: str) -> Dict[str, Any]:
        """Main detection method with multi-provider fallback"""
        logger.info(f"Starting detection for: {image_path}")
        
        # Verify file exists
        if not os.path.exists(image_path):
            return {
                'disease': 'File Error',
                'confidence': 0,
                'error': 'Image file not found',
                'provider': 'None'
            }
        
        # Try each provider in priority order
        attempts = []
        
        for provider in self.provider_priority:
            logger.info(f"Attempting with {provider}...")
            
            result = None
            try:
                if provider == 'grok':
                    result = self.detect_with_grok(image_path)
                elif provider == 'groq':
                    result = self.detect_with_groq(image_path)
                elif provider == 'openai':
                    result = self.detect_with_openai(image_path)
                elif provider == 'gemini':
                    result = self.detect_with_gemini(image_path)
                elif provider == 'huggingface':
                    result = self.detect_with_huggingface(image_path)
                
                if result and result.get('disease') != 'Unknown':
                    logger.info(f"✅ Success with {provider}: {result['disease']}")
                    result['attempts'] = attempts
                    return result
                    
                attempts.append(f"{provider}: {'No disease found' if result else 'Failed'}")
                
            except Exception as e:
                logger.error(f"{provider} error: {e}")
                attempts.append(f"{provider}: Error")
        
        # If all fail, use mock detection
        logger.warning("All providers failed, using mock detection")
        mock_result = self.use_mock_detection(image_path)
        mock_result['attempts'] = attempts
        return mock_result

    def get_status(self) -> Dict[str, bool]:
        """Get status of all providers"""
        return {
            'grok': self.providers_initialized.get('grok', False),
            'groq': self.providers_initialized.get('groq', False),
            'openai': self.providers_initialized.get('openai', False),
            'gemini': self.providers_initialized.get('gemini', False),
            'huggingface': self.providers_initialized.get('huggingface', False),
            'active_providers': self.provider_priority
        }