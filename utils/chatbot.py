import os
import json
import logging
from datetime import datetime
import google.generativeai as genai
from typing import List, Dict, Any
import base64
from PIL import Image
import io
import requests

logger = logging.getLogger(__name__)

class AgriSageChatbot:
    def __init__(self, redis_handler=None):
        self.redis_handler = redis_handler
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.hf_token = os.getenv('HF_TOKEN')
        self.setup_gemini()
        self.conversation_history = {}
        self.setup_knowledge_base()
        
    def setup_gemini(self):
        """Initialize Gemini with correct model names"""
        try:
            if self.gemini_api_key:
                genai.configure(api_key=self.gemini_api_key)
                
                # Use the correct Gemini model names
                self.model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
                self.vision_model = genai.GenerativeModel('gemini-1.5-flash')  # This model supports both text and vision
                
                logger.info("Gemini models initialized successfully")
            else:
                self.model = None
                self.vision_model = None
                logger.warning("Gemini API key not found - using fallback mode")
        except Exception as e:
            logger.error(f"Error setting up Gemini: {e}")
            self.model = None
            self.vision_model = None
    
    def setup_knowledge_base(self):
        """Setup comprehensive farming knowledge base"""
        self.farming_knowledge = {
            'diseases': {
                'early_blight': {
                    'symptoms': 'Dark spots with concentric rings on leaves, yellowing, leaf drop',
                    'treatment': 'Apply copper fungicide or neem oil, remove affected leaves, improve air circulation',
                    'prevention': 'Crop rotation, resistant varieties, proper spacing, avoid overhead watering'
                },
                'late_blight': {
                    'symptoms': 'Water-soaked spots, white fungal growth, rapid plant death',
                    'treatment': 'Apply metalaxyl or chlorothalonil, destroy infected plants',
                    'prevention': 'Plant resistant varieties, good drainage, fungicide sprays'
                },
                'powdery_mildew': {
                    'symptoms': 'White powdery coating on leaves, stunted growth',
                    'treatment': 'Sulfur spray, baking soda solution, neem oil',
                    'prevention': 'Good air circulation, avoid excess nitrogen, resistant varieties'
                },
                'bacterial_spot': {
                    'symptoms': 'Dark spots with yellow halos, leaf edges brown',
                    'treatment': 'Copper-based bactericides, remove infected parts',
                    'prevention': 'Use disease-free seeds, avoid working with wet plants'
                },
                'leaf_curl': {
                    'symptoms': 'Leaves curl upward, become thick and leathery',
                    'treatment': 'Remove affected parts, apply systemic insecticides for vectors',
                    'prevention': 'Control whiteflies, use resistant varieties'
                }
            },
            'fertilizers': {
                'npk': {
                    'usage': 'Primary nutrients for plant growth',
                    'application': '10-26-26 for flowering/fruiting, 20-20-20 for balanced growth',
                    'timing': 'Apply during planting and before flowering'
                },
                'organic': {
                    'types': 'Compost, vermicompost, cow manure, green manure',
                    'benefits': 'Improves soil structure, slow-release nutrients, eco-friendly',
                    'application': '2-3 tons per acre, mix with soil before planting'
                },
                'micronutrients': {
                    'types': 'Zinc, Iron, Boron, Manganese',
                    'symptoms': 'Yellowing between veins, stunted growth, poor fruit set',
                    'application': 'Foliar spray 0.5% solution'
                }
            },
            'pests': {
                'aphids': {
                    'damage': 'Suck plant sap, transmit viruses, honeydew secretion',
                    'control': 'Neem oil, soap spray, ladybugs, yellow sticky traps',
                    'prevention': 'Remove weeds, reflective mulches'
                },
                'whiteflies': {
                    'damage': 'Sap sucking, virus transmission, sooty mold',
                    'control': 'Yellow sticky traps, neem oil, systemic insecticides',
                    'prevention': 'Remove host plants, use reflective mulches'
                },
                'caterpillars': {
                    'damage': 'Eat leaves, bore into fruits',
                    'control': 'Bt spray, manual removal, bird perches',
                    'prevention': 'Pheromone traps, crop rotation'
                }
            },
            'irrigation': {
                'methods': {
                    'drip': 'Most efficient, 90% water efficiency, reduces disease',
                    'sprinkler': '75% efficiency, good for large areas',
                    'flood': 'Traditional, 50% efficiency, cheap but wasteful'
                },
                'scheduling': 'Check soil moisture, irrigate at 50% depletion, early morning best',
                'conservation': 'Mulching, rainwater harvesting, soil moisture sensors'
            },
            'crops': {
                'tomato': {
                    'season': 'Kharif (June-July), Rabi (Oct-Nov)',
                    'spacing': '45x30 cm',
                    'harvest': '60-90 days after transplanting',
                    'yield': '25-35 tons/acre'
                },
                'potato': {
                    'season': 'October-November',
                    'spacing': '60x20 cm',
                    'harvest': '75-90 days',
                    'yield': '10-12 tons/acre'
                },
                'onion': {
                    'season': 'Kharif (June-July), Rabi (Oct-Dec)',
                    'spacing': '15x10 cm',
                    'harvest': '120-150 days',
                    'yield': '12-15 tons/acre'
                }
            }
        }
    
    def get_system_prompt(self):
        """Enhanced system prompt for comprehensive farming assistance"""
        return """You are AgriSage, an expert AI farming assistant with deep knowledge in:
        
        1. **Crop Diseases**: Identification, symptoms, treatment (organic & chemical), prevention
        2. **Fertilizers**: NPK ratios, organic options, micronutrients, application timing
        3. **Pest Management**: Identification, IPM strategies, biological control
        4. **Irrigation**: Methods, scheduling, water conservation
        5. **Crop Management**: Planting, spacing, pruning, harvesting
        6. **Soil Health**: Testing, amendments, pH management
        7. **Weather & Climate**: Seasonal planning, climate adaptation
        8. **Market Information**: Crop selection, timing, storage
        
        Guidelines:
        - Provide specific, actionable advice with measurements and timings
        - Always suggest both organic and chemical options
        - Include cost-effective solutions for small farmers
        - Mention safety precautions for chemical use
        - Consider local/traditional methods
        - Be encouraging and supportive
        
        Format responses with:
        - Clear problem identification
        - Step-by-step solutions
        - Prevention tips
        - Expected outcomes/timeline"""
    
    def analyze_image_with_hf(self, image_data: str) -> Dict[str, Any]:
        """Analyze image using HuggingFace model for disease detection"""
        try:
            if not self.hf_token:
                return {'error': 'HuggingFace token not configured'}
            
            # Decode base64 image
            if ',' in image_data:
                image_bytes = base64.b64decode(image_data.split(',')[1])
            else:
                image_bytes = base64.b64decode(image_data)
            
            # Prepare for HF API
            API_URL = "https://api-inference.huggingface.co/models/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            
            # Make request
            response = requests.post(API_URL, headers=headers, data=image_bytes)
            
            if response.status_code == 200:
                results = response.json()
                if results and len(results) > 0:
                    top_result = results[0]
                    disease_name = self.format_disease_name(top_result['label'])
                    confidence = round(top_result['score'] * 100, 2)
                    
                    return {
                        'disease': disease_name,
                        'confidence': confidence,
                        'top_3': results[:3] if len(results) >= 3 else results
                    }
            
            return {'error': 'Could not analyze image'}
            
        except Exception as e:
            logger.error(f"HF image analysis error: {e}")
            return {'error': str(e)}
    
    def format_disease_name(self, label):
        """Format disease label"""
        if '___' in label:
            parts = label.split('___')
            plant = parts[0].replace('_', ' ').title()
            disease = parts[1].replace('_', ' ').title()
            return f"{plant} - {disease}"
        return label.replace('_', ' ').title()
    
    def process_message(self, session_id: str, message: str, 
                       image_data: str = None, language: str = 'en') -> Dict[str, Any]:
        """Process chat message with enhanced capabilities"""
        try:
            # Initialize session history
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []
            
            # Add user message to history
            user_msg = {
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            }
            
            if image_data:
                user_msg['has_image'] = True
                
            self.conversation_history[session_id].append(user_msg)
            
            # Process based on input type
            if image_data:
                response = self.process_with_image(message, image_data, language)
            else:
                response = self.process_text_only(session_id, message, language)
            
            # Add response to history
            assistant_msg = {
                'role': 'assistant',
                'content': response['response'],
                'timestamp': datetime.now().isoformat()
            }
            self.conversation_history[session_id].append(assistant_msg)
            
            # Maintain history limit
            if len(self.conversation_history[session_id]) > 10:
                self.conversation_history[session_id] = self.conversation_history[session_id][-10:]
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self.get_fallback_response(message)
    
    def process_text_only(self, session_id: str, message: str, language: str) -> Dict[str, Any]:
        """Process text message with Gemini or fallback"""
        try:
            # First, check if we can answer from knowledge base
            kb_response = self.search_knowledge_base(message)
            
            if self.model:
                # Use Gemini for comprehensive response
                context = self.get_system_prompt() + "\n\n"
                
                # Add conversation history
                recent_history = self.conversation_history.get(session_id, [])[-4:]
                for msg in recent_history:
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"
                
                # Add current message
                context += f"User: {message}\n"
                
                # Add knowledge base context if available
                if kb_response:
                    context += f"\nRelevant Information: {json.dumps(kb_response, indent=2)}\n"
                
                # Language instruction
                if language == 'te':
                    context += "\nRespond in Telugu language."
                
                context += "\nProvide a detailed, practical response with specific steps and measurements.\nAssistant: "
                
                # Generate response
                response = self.model.generate_content(context)
                
                return {
                    'response': response.text,
                    'suggestions': self.get_smart_suggestions(message, response.text)
                }
            else:
                # Use knowledge base fallback
                return self.get_enhanced_fallback(message, kb_response)
                
        except Exception as e:
            logger.error(f"Error in text processing: {e}")
            return self.get_enhanced_fallback(message, kb_response if 'kb_response' in locals() else None)
    
    def process_with_image(self, message: str, image_data: str, language: str) -> Dict[str, Any]:
        """Process message with image using multiple approaches"""
        try:
            # First try HuggingFace for disease detection
            hf_result = self.analyze_image_with_hf(image_data)
            
            if self.vision_model and not hf_result.get('error'):
                # Decode image for Gemini
                if ',' in image_data:
                    image_bytes = base64.b64decode(image_data.split(',')[1])
                else:
                    image_bytes = base64.b64decode(image_data)
                
                image = Image.open(io.BytesIO(image_bytes))
                
                # Create comprehensive prompt
                prompt = f"""{self.get_system_prompt()}
                
                User has uploaded a crop/plant image and asks: {message}
                
                HuggingFace Disease Detection Results:
                - Primary Detection: {hf_result.get('disease', 'Unknown')}
                - Confidence: {hf_result.get('confidence', 0)}%
                
                Please provide:
                1. **Visual Analysis**: Describe what you see in the image
                2. **Disease Assessment**: Confirm or refine the detection
                3. **Severity Level**: Rate the severity (Low/Moderate/High)
                4. **Immediate Actions**: 3-5 urgent steps to take
                5. **Treatment Plan**:
                   - Organic options with exact measurements
                   - Chemical options with safety notes
                6. **Prevention**: Future prevention strategies
                7. **Expected Recovery**: Timeline with proper treatment
                
                Be specific with dosages, timings, and application methods."""
                
                if language == 'te':
                    prompt += "\nRespond in Telugu."
                
                # Generate comprehensive response
                response = self.vision_model.generate_content([prompt, image])
                
                return {
                    'response': response.text,
                    'disease_detection': hf_result,
                    'has_image_analysis': True,
                    'suggestions': [
                        "Show me organic treatment details",
                        "What's the application schedule?",
                        "How to prevent spread to other plants?"
                    ]
                }
            else:
                # Fallback to HF results only
                if not hf_result.get('error'):
                    disease_info = self.get_disease_treatment(hf_result.get('disease', 'Unknown'))
                    
                    response_text = f"""Based on image analysis:
                    
**Disease Detected**: {hf_result.get('disease', 'Unknown')}
**Confidence**: {hf_result.get('confidence', 0)}%

**Recommended Treatment**:
{disease_info}

Upload another image or ask specific questions about this disease."""
                    
                    return {
                        'response': response_text,
                        'disease_detection': hf_result,
                        'suggestions': [
                            "Tell me more about this disease",
                            "What organic treatments work?",
                            "How long until recovery?"
                        ]
                    }
                else:
                    return {
                        'response': "I'm having trouble analyzing the image. Please ensure it's a clear photo of the affected plant parts. You can also describe what you see, and I'll help based on your description.",
                        'suggestions': [
                            "Describe the symptoms you see",
                            "What crop is affected?",
                            "When did symptoms appear?"
                        ]
                    }
                    
        except Exception as e:
            logger.error(f"Error in image processing: {e}")
            return {
                'response': "I encountered an error analyzing your image. Please try again or describe the symptoms you're seeing, and I'll provide guidance based on your description.",
                'error': str(e),
                'suggestions': self.get_suggestions(message)
            }
    
    def search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Search local knowledge base for relevant information"""
        query_lower = query.lower()
        results = {}
        
        # Search for disease information
        for disease, info in self.farming_knowledge['diseases'].items():
            if disease.replace('_', ' ') in query_lower or any(word in query_lower for word in disease.split('_')):
                results['disease_info'] = {disease: info}
                break
        
        # Search for fertilizer information
        if any(word in query_lower for word in ['fertilizer', 'npk', 'nutrient', 'organic']):
            results['fertilizer_info'] = self.farming_knowledge['fertilizers']
        
        # Search for pest information
        for pest, info in self.farming_knowledge['pests'].items():
            if pest in query_lower:
                results['pest_info'] = {pest: info}
                break
        
        # Search for irrigation information
        if any(word in query_lower for word in ['water', 'irrigation', 'drip']):
            results['irrigation_info'] = self.farming_knowledge['irrigation']
        
        # Search for crop information
        for crop, info in self.farming_knowledge['crops'].items():
            if crop in query_lower:
                results['crop_info'] = {crop: info}
                break
        
        return results
    
    def get_disease_treatment(self, disease_name: str) -> str:
        """Get specific treatment for detected disease"""
        treatments = {
            'Early Blight': """
**Organic Treatment**:
- Neem oil spray: 5ml/liter, every 3 days
- Remove infected leaves immediately
- Apply copper fungicide: 2g/liter

**Chemical Treatment**:
- Chlorothalonil: 2ml/liter, weekly
- Mancozeb: 2.5g/liter, every 7-10 days

**Prevention**:
- Maintain 45cm plant spacing
- Water at soil level only
- Apply mulch to prevent splash""",
            
            'Late Blight': """
**Organic Treatment**:
- Bordeaux mixture: 1% solution
- Remove and burn infected plants
- Copper oxychloride: 3g/liter

**Chemical Treatment**:
- Metalaxyl: 2g/liter, immediately
- Cymoxanil + Mancozeb: 3g/liter

**Prevention**:
- Plant resistant varieties
- Ensure good drainage
- Avoid overhead irrigation""",
            
            'default': """
**General Treatment**:
- Remove affected parts
- Improve air circulation
- Apply appropriate fungicide
- Monitor daily for spread

Consult local agriculture officer for specific recommendations."""
        }
        
        for key in treatments:
            if key.lower() in disease_name.lower():
                return treatments[key]
        
        return treatments['default']
    
    def get_enhanced_fallback(self, message: str, kb_data: Dict = None) -> Dict[str, Any]:
        """Enhanced fallback responses using knowledge base"""
        message_lower = message.lower()
        
        # Build response from knowledge base
        response_parts = []
        
        if kb_data:
            if 'disease_info' in kb_data:
                for disease, info in kb_data['disease_info'].items():
                    response_parts.append(f"**{disease.replace('_', ' ').title()}**")
                    response_parts.append(f"Symptoms: {info['symptoms']}")
                    response_parts.append(f"Treatment: {info['treatment']}")
                    response_parts.append(f"Prevention: {info['prevention']}")
            
            if 'fertilizer_info' in kb_data:
                response_parts.append("\n**Fertilizer Information**")
                for fert_type, info in kb_data['fertilizer_info'].items():
                    if isinstance(info, dict):
                        response_parts.append(f"\n{fert_type.upper()}:")
                        for key, value in info.items():
                            response_parts.append(f"- {key}: {value}")
            
            if 'pest_info' in kb_data:
                for pest, info in kb_data['pest_info'].items():
                    response_parts.append(f"\n**{pest.title()} Control**")
                    response_parts.append(f"Damage: {info['damage']}")
                    response_parts.append(f"Control: {info['control']}")
                    response_parts.append(f"Prevention: {info['prevention']}")
        
        if response_parts:
            response = "\n".join(response_parts)
        else:
            # Generic helpful responses
            if 'disease' in message_lower or 'problem' in message_lower:
                response = """For disease identification:
1. Upload a clear photo of affected parts
2. Look for: spots, discoloration, wilting, mold
3. Common diseases: Early blight, Late blight, Powdery mildew
4. Immediate action: Remove affected parts, improve air circulation

Need specific help? Describe the symptoms you see."""
            
            elif 'fertilizer' in message_lower:
                response = """Fertilizer recommendations:
                
**NPK Basics**:
- Vegetative growth: 20-10-10
- Flowering/Fruiting: 10-26-26
- Balanced: 19-19-19

**Application**:
- Base dose: During land preparation
- Top dressing: 30 & 45 days after planting
- Rate: 100-120 kg/acre

**Organic Options**:
- Vermicompost: 2-3 tons/acre
- FYM: 5-10 tons/acre
- Green manure: Grow and incorporate"""
            
            elif 'pest' in message_lower or 'insect' in message_lower:
                response = """Pest Management:

**Common Pests**:
1. Aphids: Use neem oil (5ml/L) or yellow sticky traps
2. Whiteflies: Spray soap solution, use reflective mulch
3. Caterpillars: Apply Bt spray, manual picking

**IPM Approach**:
- Monitor regularly
- Use pheromone traps
- Encourage natural predators
- Chemical spray as last resort"""
            
            elif 'water' in message_lower or 'irrigation' in message_lower:
                response = """Irrigation Management:

**Water Requirements**:
- Most vegetables: 1-2 inches/week
- Critical stages: Flowering & fruit development
- Check soil moisture at 2-inch depth

**Methods**:
- Drip: Most efficient (90% efficiency)
- Sprinkler: Good for large areas
- Furrow: Traditional but less efficient

**Tips**:
- Water early morning or evening
- Mulch to reduce evaporation
- Avoid overwatering (causes root rot)"""
            
            else:
                response = """I'm AgriSage, your farming assistant! I can help with:

🌱 **Crop Diseases**: Upload photos for identification
🌿 **Fertilizers**: NPK ratios, organic options
🐛 **Pest Control**: IPM strategies, organic methods
💧 **Irrigation**: Scheduling, conservation methods
🌾 **Crop Management**: Planting to harvesting

Ask me anything about farming, or upload a photo for analysis!"""
        
        return {
            'response': response,
            'suggestions': self.get_suggestions(message)
        }
    
    def get_suggestions(self, message: str) -> List[str]:
        """Get contextual suggestions"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['disease', 'sick', 'spot', 'blight']):
            return [
                "Upload photo for disease identification",
                "How to prevent disease spread?",
                "Organic disease control methods"
            ]
        elif any(word in message_lower for word in ['fertilizer', 'nutrient', 'npk']):
            return [
                "Best fertilizer for my crop?",
                "Organic vs chemical fertilizers",
                "Fertilizer application schedule"
            ]
        elif any(word in message_lower for word in ['pest', 'insect', 'worm']):
            return [
                "Natural pest control methods",
                "Identify pest from photo",
                "IPM strategies for vegetables"
            ]
        elif any(word in message_lower for word in ['water', 'irrigation']):
            return [
                "Drip irrigation setup guide",
                "Water conservation methods",
                "Irrigation scheduling"
            ]
        elif any(word in message_lower for word in ['plant', 'seed', 'grow']):
            return [
                "Best planting season?",
                "Seed treatment methods",
                "Crop spacing guidelines"
            ]
        else:
            return [
                "Disease identification from photo",
                "Fertilizer recommendations",
                "Pest control strategies"
            ]
    
    def get_smart_suggestions(self, query: str, response: str) -> List[str]:
        """Generate smart follow-up suggestions based on context"""
        suggestions = []
        
        # Analyze response content
        response_lower = response.lower()
        
        if 'organic' in response_lower:
            suggestions.append("Compare with chemical alternatives")
        if 'spray' in response_lower or 'application' in response_lower:
            suggestions.append("What's the best time to spray?")
        if 'disease' in response_lower:
            suggestions.append("How to prevent recurrence?")
        if any(word in response_lower for word in ['harvest', 'yield']):
            suggestions.append("Post-harvest storage tips")
        
        # Add default helpful suggestions if needed
        if len(suggestions) < 3:
            suggestions.extend([
                "Show treatment schedule",
                "Cost-benefit analysis",
                "Success stories from farmers"
            ])
        
        return suggestions[:3]
    
    def clear_session(self, session_id: str):
        """Clear conversation history"""
        if session_id in self.conversation_history:
            del self.conversation_history[session_id]