# Execute these commands one by one in your terminal

# Set your environment variables
PROJECT_ID="gen-lang-client-0989634693"
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-lung-cancer-model"
MODEL_DISPLAY_NAME="lung-cancer-classifier-$(date +%Y%m%d%H%M%S)"

# Set the project in gcloud
gcloud config set project ${PROJECT_ID}

# Create a Cloud Storage bucket (if it doesn't exist)
gsutil mb -l ${REGION} gs://${BUCKET_NAME} || echo "Bucket already exists or couldn't be created"

# Upload the SavedModel to the bucket
gsutil cp -r saved_model gs://${BUCKET_NAME}/

# Create the model in Vertex AI
gcloud ai models upload \
  --region=${REGION} \
  --display-name=${MODEL_DISPLAY_NAME} \
  --container-image-uri="us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-8:latest" \
  --artifact-uri=gs://${BUCKET_NAME}/saved_model

# Wait a moment for the model to be created
echo "Waiting for model creation to complete..."
sleep 10

# Get the model ID
MODEL_ID=$(gcloud ai models list \
  --region=${REGION} \
  --filter="displayName=${MODEL_DISPLAY_NAME}" \
  --format="value(name)")
echo "Model ID: ${MODEL_ID}"

# Create a Vertex AI endpoint
ENDPOINT_DISPLAY_NAME="lung-cancer-endpoint-$(date +%Y%m%d%H%M%S)"
gcloud ai endpoints create \
  --region=${REGION} \
  --display-name=${ENDPOINT_DISPLAY_NAME}

# Wait a moment for the endpoint to be created
echo "Waiting for endpoint creation to complete..."
sleep 10

# Get the endpoint ID
ENDPOINT_ID=$(gcloud ai endpoints list \
  --region=${REGION} \
  --filter="displayName=${ENDPOINT_DISPLAY_NAME}" \
  --format="value(name)")
echo "Endpoint ID: ${ENDPOINT_ID}"

# Deploy the model to the endpoint
gcloud ai endpoints deploy-model ${ENDPOINT_ID} \
  --region=${REGION} \
  --model=${MODEL_ID} \
  --display-name=${MODEL_DISPLAY_NAME} \
  --machine-type=n1-standard-2 \
  --min-replica-count=1 \
  --max-replica-count=1 \
  --traffic-split=0=100

echo "===== DEPLOYMENT SUMMARY ====="
echo "Project ID: ${PROJECT_ID}"
echo "Model ID: ${MODEL_ID}"
echo "Endpoint ID: ${ENDPOINT_ID}"
echo "Model location: gs://${BUCKET_NAME}/saved_model"
echo "=============================="
