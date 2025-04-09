import json
import boto3
import os
from flask import Flask, request, jsonify
from lip_sync import generate_lip_sync_data
import logging
import time

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bedrock = boto3.client('bedrock-runtime', region_name='ap-south-1')
polly = boto3.client('polly', region_name='ap-south-1')
s3 = boto3.client('s3', region_name='ap-south-1')
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
appsync = boto3.client('appsync', region_name='ap-south-1')

BUCKET_NAME = 'visual-chatbot-audio'
TABLE_NAME = 'ChatHistory'
APPSYNC_API_ID_RAW = os.environ.get("APPSYNC_API_ID", "MISSING_API_ID")

if "arn:aws:appsync" in APPSYNC_API_ID_RAW:
    APPSYNC_API_ID = APPSYNC_API_ID_RAW.split('/')[-1]
else:
    APPSYNC_API_ID = APPSYNC_API_ID_RAW
logger.info(f"Raw APPSYNC_API_ID from env: {APPSYNC_API_ID_RAW}")
logger.info(f"Parsed APPSYNC_API_ID: {APPSYNC_API_ID}")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message')
        if not user_input:
            raise ValueError("No message provided in request body")
        logger.info(f"Received user input: {user_input}")

        response = bedrock.invoke_model(
            modelId='anthropic.claude-v2',
            body=json.dumps({
                'prompt': f'Human: {user_input} Assistant: ',
                'max_tokens_to_sample': 300,
                'temperature': 0.7
            }),
            contentType='application/json'
        )
        response_text = json.loads(response['body'].read())['completion'].strip()
        logger.info(f"Generated response: {response_text}")

        polly_response = polly.synthesize_speech(
            Text=response_text,
            OutputFormat='mp3',
            VoiceId='Joanna'
        )
        audio_path = '/tmp/response.mp3'
        with open(audio_path, 'wb') as f:
            f.write(polly_response['AudioStream'].read())
        logger.info("Converted text to speech")

        lip_sync_data = generate_lip_sync_data(audio_path)
        logger.info(f"Generated lip sync data with {len(lip_sync_data)} frames")

        audio_key = f'response_{int(time.time())}.mp3'  # Unique key without context
        s3.upload_file(audio_path, BUCKET_NAME, audio_key, ExtraArgs={'ContentType': 'audio/mpeg'})
        audio_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{audio_key}'
        logger.info(f"Uploaded audio to S3: {audio_url}")

        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={
            'request_id': str(int(time.time())),
            'user_input': user_input,
            'response': response_text,
            'audio_key': audio_key,
            'timestamp': int(time.time())
        })
        logger.info("Stored conversation in DynamoDB")

        mutation_query = '''
            mutation PublishResponse($response: String!, $audioUrl: String!, $lipSync: AWSJSON!) {
                publishResponse(response: $response, audioUrl: $audioUrl, lipSync: $lipSync) {
                    response
                    audioUrl
                    lipSync
                }
            }
        '''
        variables = {
            'response': response_text,
            'audioUrl': audio_url,
            'lipSync': json.dumps(lip_sync_data)
        }
        logger.info(f"Executing AppSync mutation with API ID: {APPSYNC_API_ID}")
        appsync_response = appsync.graphql(
            apiId=APPSYNC_API_ID,
            query=mutation_query,
            variables=variables
        )
        logger.info(f"AppSync response: {json.dumps(appsync_response)}")

        os.remove(audio_path)
        return jsonify({'message': 'Processing complete'}), 200

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
