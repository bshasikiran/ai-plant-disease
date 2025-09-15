import cv2
import numpy as np
from PIL import Image
import tensorflow as tf
import logging
import requests
from io import BytesIO

logger = logging.getLogger(__name__)

class DiseaseDetector:
    def __init__(self):
        self.model = None
        self.classes = [
            'Apple_scab', 'Apple_black_rot', 'Apple_cedar_rust', 'Apple_healthy',
            'Blueberry_healthy', 'Cherry_healthy', 'Cherry_powdery_mildew',
            'Corn_gray_leaf_spot', 'Corn_common_rust', 'Corn_northern_leaf_blight', 'Corn_healthy',
            'Grape_black_rot', 'Grape_esca', 'Grape_leaf_blight', 'Grape_healthy',
            'Orange_haunglongbing', 'Peach_bacterial_spot', 'Peach_healthy',
            'Pepper_bacterial_spot', 'Pepper_healthy', 'Potato_early_blight',
            'Potato_late_blight', 'Potato_healthy', 'Raspberry_healthy',
            'Soybean_healthy', 'Squash_powdery_mildew', 'Strawberry_leaf_scorch',
            'Strawberry_healthy', 'Tomato_bacterial_spot', 'Tomato_early_blight',
            'Tomato_late_blight', 'Tomato_leaf_mold', 'Tomato_septoria_leaf_spot',
            'Tomato_spider_mites', 'Tomato_target_spot', 'Tomato_yellow_leaf_curl_virus',
            'Tomato_mosaic_virus', 'Tomato_healthy'
        ]
        self.load_model()
    
    def load_model(self):
        """Load a simple CNN model or use a pre-trained one"""
        try:
            # For simplicity, we'll create a mock model
            # In production, load an actual trained model
            self.model = self.create_simple_model()
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model = None
    
    def create_simple_model(self):
        """Create a simple CNN model for demonstration"""
        model = tf.keras.Sequential([
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Conv2D(128, (3, 3), activation='relu'),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.Dense(len(self.classes), activation='softmax')
        ])
        return model
    
    def preprocess_image(self, image_path):
        """Preprocess image for model input"""
        try:
            # Load and resize image
            img = Image.open(image_path)
            img = img.convert('RGB')
            img = img.resize((224, 224))
            
            # Convert to array and normalize
            img_array = np.array(img)
            img_array = img_array / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            return img_array
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return None
    
    def detect_disease(self, image_path):
        """Detect disease from image"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            if processed_img is None:
                return {'disease': 'Unknown', 'confidence': 0}
            
            # For demonstration, return a mock result
            # In production, use: predictions = self.model.predict(processed_img)
            
            # Mock prediction
            import random
            disease_idx = random.randint(0, len(self.classes) - 1)
            confidence = random.uniform(0.7, 0.99)
            
            disease_name = self.classes[disease_idx].replace('_', ' ').title()
            
            return {
                'disease': disease_name,
                'confidence': round(confidence * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error detecting disease: {str(e)}")
            return {'disease': 'Unknown', 'confidence': 0}