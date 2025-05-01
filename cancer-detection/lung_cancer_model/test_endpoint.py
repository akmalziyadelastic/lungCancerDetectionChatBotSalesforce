#!/usr/bin/env python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import numpy as np
from PIL import Image
import os
import sys
import json
import requests
import traceback
from typing import Dict, List, Union
import base64
import google.auth
import google.auth.transport.requests

def debug_print(step, message):
    """Print debug information with step name."""
    print(f"[DEBUG - {step}] {message}")

def get_access_token():
    """Get Google Cloud access token for authentication."""
    debug_print("auth", "Getting access token")
    try:
        credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return credentials.token
    except Exception as e:
        debug_print("auth", f"Error getting access token: {str(e)}")
        raise

def preprocess_image(image_path, target_size=(224, 224)):
    """
    Preprocess an image for prediction
    
    Args:
        image_path: Path to the image file
        target_size: Size to resize the image to
        
    Returns:
        Dictionary with processed image data
    """
    debug_print("preprocess_image", f"Starting image preprocessing: {image_path}")
    
    try:
        # Check if file exists
        if not os.path.isfile(image_path):
            debug_print("preprocess_image", f"ERROR: Image file not found: {image_path}")
            return None
            
        # Resize the image
        debug_print("preprocess_image", f"Opening and resizing image to {target_size}")
        img = Image.open(image_path).resize(target_size)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            debug_print("preprocess_image", f"Converting image from {img.mode} to RGB")
            img = img.convert('RGB')
        
        # Convert to numpy array
        debug_print("preprocess_image", "Converting image to numpy array")
        img_array = np.array(img)
        
        # Normalize pixel values to [0, 1]
        debug_print("preprocess_image", "Normalizing pixel values")
        img_array = img_array.astype(np.float32) / 255.0
        
        # Format the array different ways for flexibility
        return {
            "flat_array": img_array.reshape(-1).tolist(),
            "shaped_array": img_array.tolist(),
            "raw_array": img_array.astype(np.float32).tolist(),
            "shape": img_array.shape
        }
        
    except Exception as e:
        debug_print("preprocess_image", f"ERROR: Exception during preprocessing: {str(e)}")
        traceback.print_exc()
        return None

def predict_endpoint(
    project: str,
    endpoint_id: str,
    image_path: str,
    location: str = "us-central1"
):
    """
    Send prediction request to Vertex AI endpoint with image data using direct REST API
    
    Args:
        project: Google Cloud project ID
        endpoint_id: Vertex AI endpoint ID
        image_path: Path to the image file
        location: Google Cloud region
        
    Returns:
        Prediction response
    """
    debug_print("predict", f"Starting prediction. Project: {project}, Endpoint: {endpoint_id}")
    
    try:
        # Get access token for authentication
        access_token = get_access_token()
        debug_print("predict", "Access token obtained")
        
        # Preprocess the image
        debug_print("predict", "Preprocessing image")
        image_data = preprocess_image(image_path)
        
        if image_data is None:
            debug_print("predict", "Failed to preprocess image. Aborting prediction.")
            return None
        
        # Construct the endpoint URL according to the specification
        endpoint_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/endpoints/{endpoint_id}:predict"
        debug_print("predict", f"Endpoint URL: {endpoint_url}")
        
        # Set up headers with authentication
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Try different request formats
        formats = [
            # Format 1: Flat array (most common)
            {
                "instances": [image_data["flat_array"]]
            },
            # Format 2: Shaped array preserving dimensions
            {
                "instances": [image_data["shaped_array"]]
            },
            # Format 3: With named fields
            {
                "instances": [{"input": image_data["flat_array"]}]
            },
            # Format 4: With different named field
            {
                "instances": [{"inputs": image_data["flat_array"]}]
            },
            # Format 5: With tensor name field
            {
                "instances": [{"input_tensor": image_data["flat_array"]}]
            },
            # Format 6: With a different tensor name field
            {
                "instances": [{"image_tensor": image_data["flat_array"]}]
            },
            # Format 7: With pixels field
            {
                "instances": [{"pixels": image_data["flat_array"]}]
            },
            # Format 8: With "instances" as key
            {
                "instances": [{"instances": image_data["flat_array"]}]
            },
            # Format 9: With "features" as key
            {
                "instances": [{"features": image_data["flat_array"]}]
            },
            # Format 10: Raw unprocessed array
            {
                "instances": [image_data["raw_array"]]
            }
        ]
        
        # Try each format until one works
        for i, request_body in enumerate(formats):
            format_name = f"Format {i+1}"
            debug_print("predict", f"Trying {format_name}")
            
            try:
                debug_print("predict", f"Request body size: {len(json.dumps(request_body))} bytes")
                
                # Make the prediction request
                response = requests.post(endpoint_url, headers=headers, json=request_body)
                
                # Check if request was successful
                if response.status_code == 200:
                    debug_print("predict", f"{format_name} successful with status code 200")
                    return {
                        "status_code": response.status_code,
                        "content": response.json(),
                        "format_used": format_name
                    }
                else:
                    debug_print("predict", f"{format_name} failed with status code {response.status_code}")
                    debug_print("predict", f"Response: {response.text}")
            except Exception as e:
                debug_print("predict", f"{format_name} failed with exception: {str(e)}")
        
        # If we get here, all formats failed
        debug_print("predict", "All formats failed")
        return {
            "status_code": 400,
            "content": "All request formats failed. Check your model's expected input format.",
            "format_used": None
        }
        
    except Exception as e:
        debug_print("predict", f"ERROR: Exception during prediction: {str(e)}")
        traceback.print_exc()
        return None

def check_environment():
    """Check environment setup for debugging."""
    debug_print("environment", f"Python version: {sys.version}")
    
    # Check Google Cloud authentication
    debug_print("environment", "Checking Google Cloud credentials")
    try:
        import google.auth
        credentials, project = google.auth.default()
        if credentials:
            debug_print("environment", f"Google Cloud credentials found. Default project: {project}")
        else:
            debug_print("environment", "No Google Cloud credentials found")
    except Exception as e:
        debug_print("environment", f"Error checking Google Cloud credentials: {str(e)}")
    
    # Check required packages
    for package in ["google.auth", "PIL", "numpy", "requests"]:
        try:
            __import__(package.split(".")[0])
            debug_print("environment", f"Package {package.split('.')[0]} is available")
        except ImportError:
            debug_print("environment", f"Package {package.split('.')[0]} is NOT available")

def display_predictions(response):
    """
    Display prediction results in a readable format
    
    Args:
        response: Response from prediction endpoint
    """
    try:
        if response["status_code"] != 200:
            print(f"\nError: Prediction failed with status code {response['status_code']}")
            print(f"Response: {response['content']}")
            return
            
        print(f"\nSuccessful prediction using {response['format_used']}!")
        
        # Extract content from response
        content = response["content"]
        
        # Print the full response first for reference
        print("\nFull response:")
        print(json.dumps(content, indent=2))
        
        # Check if predictions exist in the response
        if "predictions" in content:
            predictions = content["predictions"]
            
            print("\nPredictions:")
            if isinstance(predictions, list) and len(predictions) > 0:
                # Handle first prediction (usually just one)
                prediction = predictions[0]
                
                # Different formats of predictions
                if isinstance(prediction, list):
                    # List format - likely class probabilities
                    class_id = np.argmax(prediction)
                    confidence = prediction[class_id]
                    print(f"  Class ID with highest probability: {class_id}")
                    print(f"  Confidence: {confidence:.4f}")
                    
                    print("  All class probabilities:")
                    for i, prob in enumerate(prediction):
                        print(f"    Class {i}: {prob:.4f}")
                        
                elif isinstance(prediction, dict):
                    # Dictionary format - extract relevant fields
                    print("  Prediction details:")
                    for key, value in prediction.items():
                        print(f"    {key}: {value}")
                    
                    # Try to find classification results
                    if "scores" in prediction and ("classes" in prediction or "classNames" in prediction or "labels" in prediction):
                        # Get class names (could be under different keys)
                        class_names = prediction.get("classes", prediction.get("classNames", prediction.get("labels", [])))
                        scores = prediction["scores"]
                        
                        # Get highest score
                        if isinstance(scores, list) and len(scores) > 0:
                            best_idx = np.argmax(scores)
                            best_class = class_names[best_idx] if len(class_names) > best_idx else f"Class {best_idx}"
                            print(f"\n  Top class: {best_class}")
                            print(f"  Confidence: {scores[best_idx]:.4f}")
                else:
                    # Other format
                    print(f"  {prediction}")
            else:
                print("  No predictions data or empty predictions.")
        
        # Print model info if available
        if "deployedModelId" in content:
            print(f"\nDeployed Model ID: {content['deployedModelId']}")
        
        if "modelDisplayName" in content:
            print(f"Model Display Name: {content['modelDisplayName']}")
            
    except Exception as e:
        print(f"Error displaying predictions: {e}")
        print("Raw response:")
        print(response)

def main():
    parser = argparse.ArgumentParser(description="Test Vertex AI endpoint with an image")
    parser.add_argument("--project", required=True, help="Google Cloud project ID")
    parser.add_argument("--endpoint", required=True, help="Vertex AI endpoint ID")
    parser.add_argument("--image", required=True, help="Path to the image file")
    parser.add_argument("--region", default="us-central1", help="Google Cloud region")
    
    try:
        args = parser.parse_args()
        debug_print("main", f"Arguments parsed: {args}")
    except Exception as e:
        debug_print("main", f"ERROR: Failed to parse arguments: {str(e)}")
        return
    
    # Check environment setup
    check_environment()
    
    # Verify the image exists
    if not os.path.exists(args.image):
        debug_print("main", f"ERROR: Image file {args.image} doesn't exist")
        print(f"Error: Image file {args.image} doesn't exist")
        return
    else:
        debug_print("main", f"Image confirmed to exist at {args.image}")
        try:
            img = Image.open(args.image)
            debug_print("main", f"Image opened successfully. Format: {img.format}, Size: {img.size}, Mode: {img.mode}")
        except Exception as e:
            debug_print("main", f"WARNING: Image exists but couldn't be opened: {str(e)}")
    
    print(f"Sending prediction request to Vertex AI endpoint...")
    
    try:
        # Call the prediction function
        debug_print("main", "Calling predict_endpoint function")
        response = predict_endpoint(
            project=args.project,
            endpoint_id=args.endpoint,
            image_path=args.image,
            location=args.region
        )
        
        if response is None:
            debug_print("main", "No response received from predict function")
            print("Error: Failed to get prediction response. Check debug output above for details.")
            return
        
        # Display the prediction results
        display_predictions(response)
        
    except Exception as e:
        debug_print("main", f"ERROR: Exception in main: {str(e)}")
        print(f"Error making prediction: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Vertex AI prediction script")
    main()
    print("Script execution completed")