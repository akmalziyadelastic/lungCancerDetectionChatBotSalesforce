#!/bin/bash
# Google Cloud Vertex AI Deployment Script for Lung Cancer Classification Model

# Set your project ID
PROJECT_ID="gen-lang-client-0989634693"
REGION="us-central1"  # You can change this to your preferred region
BUCKET_NAME="${PROJECT_ID}-lung-cancer-model"
MODEL_DIR="lung_cancer_model"  # Local directory containing your .pb file
MODEL_FILENAME="lung_cancer_model.pb"
MODEL_DISPLAY_NAME="lung-cancer-classifier-$(date +%Y%m%d%H%M%S)"
ENDPOINT_DISPLAY_NAME="lung-cancer-endpoint-$(date +%Y%m%d%H%M%S)"

# Step 1: Set the current project
echo "Setting project to: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Step 2: List and clean up existing resources (optional - be careful!)
echo "Listing existing Vertex AI models..."
gcloud ai models list --region=${REGION}

echo "Listing existing Vertex AI endpoints..."
gcloud ai endpoints list --region=${REGION}

echo "Listing existing Cloud Storage buckets..."
gsutil ls

# Uncomment the following lines if you want to delete existing resources
# WARNING: This will delete ALL models and endpoints in the specified region
# echo "Deleting all existing Vertex AI models in ${REGION}..."
# gcloud ai models list --region=${REGION} --format="value(name)" | xargs -I {} gcloud ai models delete {} --region=${REGION} --quiet

# echo "Deleting all existing Vertex AI endpoints in ${REGION}..."
# gcloud ai endpoints list --region=${REGION} --format="value(name)" | xargs -I {} gcloud ai endpoints delete {} --region=${REGION} --quiet

# echo "Deleting the existing bucket if it exists..."
# gsutil rm -r gs://${BUCKET_NAME} || true

# Step 3: Create a new Cloud Storage bucket
echo "Creating a new Cloud Storage bucket: ${BUCKET_NAME}"
gsutil mb -l ${REGION} gs://${BUCKET_NAME}

# Step 4: Upload the model to the bucket
echo "Uploading model to Cloud Storage..."
gsutil cp ${MODEL_DIR}/${MODEL_FILENAME} gs://${BUCKET_NAME}/

# Optional: Create model.json for TensorFlow model metadata
cat > model.json << EOF
{
  "format": "tf-saved-model",
  "signatureDefKey": "serving_default",
  "inputTensors": [
    {
      "name": "input",
      "dataType": "float32",
      "shape": [-1, 224, 224, 3]
    }
  ],
  "outputTensors": [
    {
      "name": "output",
      "dataType": "float32"
    }
  ]
}
EOF

# Upload model.json to the bucket
gsutil cp model.json gs://${BUCKET_NAME}/

# Step 5: Create a Vertex AI model
echo "Creating Vertex AI model..."
gcloud ai models upload \
  --region=${REGION} \
  --display-name=${MODEL_DISPLAY_NAME} \
  --container-image-uri="us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-8:latest" \
  --artifact-uri=gs://${BUCKET_NAME}/ \
  --model-id=${MODEL_DISPLAY_NAME}

# Step 6: Create a Vertex AI endpoint
echo "Creating Vertex AI endpoint..."
gcloud ai endpoints create \
  --region=${REGION} \
  --display-name=${ENDPOINT_DISPLAY_NAME}

# Step 7: Get the endpoint ID
ENDPOINT_ID=$(gcloud ai endpoints list \
  --region=${REGION} \
  --filter="displayName=${ENDPOINT_DISPLAY_NAME}" \
  --format="value(name)")

echo "Endpoint ID: ${ENDPOINT_ID}"

# Step 8: Deploy the model to the endpoint
echo "Deploying model to endpoint..."
MODEL_ID=$(gcloud ai models list \
  --region=${REGION} \
  --filter="displayName=${MODEL_DISPLAY_NAME}" \
  --format="value(name)")

echo "Model ID: ${MODEL_ID}"

gcloud ai endpoints deploy-model ${ENDPOINT_ID} \
  --region=${REGION} \
  --model=${MODEL_ID} \
  --display-name=${MODEL_DISPLAY_NAME} \
  --machine-type=n1-standard-2 \
  --min-replica-count=1 \
  --max-replica-count=1 \
  --traffic-split=0=100

# Step 9: Create a Python script for testing the endpoint
cat > test_endpoint.py << EOF
import base64
import json
import requests
import argparse
import sys
from PIL import Image
import numpy as np
import io
import os
from google.cloud import aiplatform
from google.oauth2 import service_account

def preprocess_image(image_path):
    """Preprocess an image for prediction."""
    img = Image.open(image_path).resize((224, 224))
    img_array = np.array(img) / 255.0
    
    # Check if image is grayscale and convert to RGB if needed
    if len(img_array.shape) == 2:
        img_array = np.stack((img_array,) * 3, axis=-1)
    elif img_array.shape[2] == 1:
        img_array = np.repeat(img_array, 3, axis=2)
    elif img_array.shape[2] == 4:  # RGBA images
        img_array = img_array[:, :, :3]
    
    return img_array.tolist()

def predict_image(project_id, endpoint_id, image_path, region="us-central1"):
    """Send a prediction request to a deployed model on Vertex AI."""
    
    # Initialize the Vertex AI SDK
    aiplatform.init(project=project_id, location=region)
    
    # Get the endpoint
    endpoint = aiplatform.Endpoint(endpoint_id)
    
    # Preprocess the image
    instances = [{"input": preprocess_image(image_path)}]
    
    # Get the prediction
    prediction = endpoint.predict(instances=instances)
    
    # Process and return the prediction results
    return prediction

def main():
    parser = argparse.ArgumentParser(description='Test Vertex AI lung cancer model endpoint')
    parser.add_argument('--project', required=True, help='Google Cloud project ID')
    parser.add_argument('--endpoint', required=True, help='Vertex AI endpoint ID')
    parser.add_argument('--image', required=True, help='Path to image file for prediction')
    parser.add_argument('--region', default='us-central1', help='Google Cloud region')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image):
        print(f"Error: Image file {args.image} does not exist")
        sys.exit(1)
    
    try:
        prediction = predict_image(
            args.project, 
            args.endpoint, 
            args.image,
            args.region
        )
        
        print("Prediction result:")
        print(prediction)
        
        # If the output is an array of probabilities, show the highest probability class
        if hasattr(prediction, 'predictions') and len(prediction.predictions) > 0:
            probs = prediction.predictions[0]
            if isinstance(probs, list):
                class_id = np.argmax(probs)
                confidence = probs[class_id]
                print(f"Predicted class: {class_id} with confidence: {confidence:.4f}")
        
    except Exception as e:
        print(f"Error making prediction: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

echo "=== Deployment Complete ==="
echo "Project ID: ${PROJECT_ID}"
echo "Model ID: ${MODEL_ID}"
echo "Endpoint ID: ${ENDPOINT_ID}"
echo ""
echo "To test your endpoint with the provided Python script:"
echo "python test_endpoint.py --project=${PROJECT_ID} --endpoint=${ENDPOINT_ID} --image=path/to/your/test/image.png"
echo ""
echo "Note: You may need to install the Google Cloud AI Platform SDK:"
echo "pip install google-cloud-aiplatform"