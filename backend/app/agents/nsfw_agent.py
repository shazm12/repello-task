from google.cloud import vision
from PIL import Image
import io
from typing import Dict, List
from dotenv import load_dotenv
import os
import logging
# Load environment variables from .env file
load_dotenv()

# Recommended: Service Acccounts
#os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


class NSFWAgent:
    def __init__(self):
        self.client = vision.ImageAnnotatorClient(
                    client_options={"api_key": GOOGLE_API_KEY}
                )

        self.categories = {
            'adult': {
                'threshold': 3,
                'description': 'Nudity or sexual content'
            },
            'violence': {
                'threshold': 3,
                'description': 'Violent or graphic content'
            },
            'racy': {
                'threshold': 3,
                'description': 'Suggestive content'
            },
            'medical': {
                'threshold': 3,
                'description': 'Medical conditions/injuries'
            },
            'spoof': {
                'threshold': 3,
                'description': 'Edited/doctored media'
            }
        }

    def detect(self, image: Image.Image) -> Dict:
        try:
            # Convert image if needed
            if image.mode == 'RGBA':
                image = image.convert('RGB')

            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            content = img_byte_arr.getvalue()

            # Call APIs
            safe_response = self.client.safe_search_detection(
                image=vision.Image(content=content))
            object_response = self.client.object_localization(
                image=vision.Image(content=content))

            if safe_response.error.message:
                return {"error": safe_response.error.message}

            # Process results
            safe = safe_response.safe_search_annotation
            likelihood_name = ['UNKNOWN', 'VERY_UNLIKELY', 'UNLIKELY',
                               'POSSIBLE', 'LIKELY', 'VERY_LIKELY']
            likelihood_score = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9]

            flagged = []
            for cat, config in self.categories.items():
                level = getattr(safe, cat)
                if level >= config['threshold']:
                    flagged.append(cat)

            visual_cues = []
            for obj in object_response.localized_object_annotations:
                if obj.score > 0.7:
                    visual_cues.append(obj.name)

            overall_confidence = 1.0  # Default for safe images
            if flagged:
                # Get max confidence from flagged categories
                max_conf = 0.0
                for cat in flagged:
                    level = getattr(safe, cat)
                    max_conf = max(max_conf, likelihood_score[level])
                overall_confidence = max_conf

            return {
                "is_toxic": bool(flagged),
                "confidence": overall_confidence,
                "flagged_categories": flagged,  # Just category names
                "visual_cues": visual_cues,    # Just visual cue names
                "details": {
                    cat: {
                        'level': likelihood_name[getattr(safe, cat)],
                        'confidence': likelihood_score[getattr(safe, cat)]
                    } for cat in self.categories
                }
            }

        except Exception as e:
            logging.error(e, exc_info=True)
            return {"error": str(e)}
