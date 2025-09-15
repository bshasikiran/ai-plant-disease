import redis
import json
import os
import logging

logger = logging.getLogger(__name__)

class RedisHandler:
    def __init__(self):
        self.redis_client = None
        self.connect()
        self.initialize_data()
    
    def connect(self):
        """Connect to Redis (Upstash)"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            # Use in-memory fallback
            self.redis_client = None
    
    def initialize_data(self):
        """Initialize treatment data in Redis"""
        treatments = {
            "Apple Scab": {
                "organic": "Apply neem oil spray, remove infected leaves, ensure good air circulation",
                "chemical": "Use fungicides containing captan or myclobutanil",
                "prevention": "Plant resistant varieties, prune for air circulation, clean fallen leaves"
            },
            "Tomato Early Blight": {
                "organic": "Apply copper-based organic fungicide, mulch to prevent soil splash",
                "chemical": "Use chlorothalonil or mancozeb fungicides",
                "prevention": "Rotate crops, water at soil level, remove infected plants"
            },
            "Potato Late Blight": {
                "organic": "Use copper sulfate spray, remove infected plants immediately",
                "chemical": "Apply metalaxyl or chlorothalonil fungicides",
                "prevention": "Plant certified disease-free seeds, ensure good drainage"
            },
            "Corn Common Rust": {
                "organic": "Apply sulfur dust, remove infected leaves",
                "chemical": "Use propiconazole or azoxystrobin fungicides",
                "prevention": "Plant resistant hybrids, avoid overhead irrigation"
            },
            "Grape Black Rot": {
                "organic": "Prune infected parts, apply Bordeaux mixture",
                "chemical": "Use myclobutanil or tebuconazole fungicides",
                "prevention": "Remove mummified fruits, ensure good air flow"
            }
        }
        
        try:
            if self.redis_client:
                for disease, treatment in treatments.items():
                    self.redis_client.set(
                        f"treatment:{disease.lower().replace(' ', '_')}",
                        json.dumps(treatment)
                    )
                logger.info("Treatment data initialized in Redis")
        except Exception as e:
            logger.error(f"Error initializing Redis data: {str(e)}")
    
    def get_treatment(self, disease_name):
        """Get treatment for a disease"""
        try:
            # Fallback data if Redis is not available
            fallback_treatment = {
                "organic": "Apply organic fungicides like neem oil or copper-based solutions. Remove infected parts.",
                "chemical": "Consult local agricultural expert for appropriate chemical treatment.",
                "prevention": "Ensure proper spacing, good air circulation, and regular monitoring."
            }
            
            if not self.redis_client:
                return fallback_treatment
            
            key = f"treatment:{disease_name.lower().replace(' ', '_')}"
            treatment_data = self.redis_client.get(key)
            
            if treatment_data:
                return json.loads(treatment_data)
            else:
                # Return generic treatment if specific not found
                return fallback_treatment
                
        except Exception as e:
            logger.error(f"Error getting treatment: {str(e)}")
            return {
                "organic": "Apply organic fungicides",
                "chemical": "Consult local expert",
                "prevention": "Monitor regularly"
            }