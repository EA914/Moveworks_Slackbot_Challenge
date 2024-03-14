import os
import json
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier
from dotenv import load_dotenv

load_dotenv()

signing_secret = os.getenv('SLACK_SIGNING_SECRET')
if not signing_secret:
	exit(1)

client = WebClient(token=os.getenv('SLACK_API_TOKEN'))

verifier = SignatureVerifier(signing_secret)

app = Flask(__name__)

with open('employee_info_db.json', 'r') as file:
	users_data = json.load(file)

@app.route('/slack/events', methods=['POST'])
def slack_commands():
	global users_data
	data = request.json

	if data.get('type') == 'url_verification':
		return jsonify({'challenge': data.get('challenge')}), 200

	if not verifier.is_valid_request(request.get_data(), request.headers):
		return '', 400

	event = data.get('event', {})
	if 'bot_id' in event:
		return '', 200

	text = event.get('text', '').strip()
	parts = text.split() if text else []

	if not parts:
		return jsonify({'response_type': 'ephemeral', 'text': 'Invalid command'})

	if parts[0] == 'list':
		user_list = [f"{user} - {users_data[user]['department']}" for user in users_data]
		response_text = f"All Users:\n{'\n'.join(user_list)}"
		client.chat_postMessage(channel=event['channel'], text=response_text)
		return '', 200

	elif parts[0] == 'query':
		if len(parts) < 2:
			return jsonify({'response_type': 'ephemeral', 'text': 'Invalid query command'})
		user_id = parts[1].lower()
		user_data = users_data.get(user_id, None)
		if not user_data:
			return jsonify({'response_type': 'in_channel', 'text': f"User {user_id} not found"})

		attributes = parts[2:]
		if not attributes:
			response_text = f"User: {user_id}\nData: {json.dumps(user_data, indent=4)}"
		else:
			filtered_data = {attr: user_data[attr] for attr in attributes if attr in user_data}
			response_text = f"User: {user_id}\n"
			response_text += '\n'.join([f"{attr.capitalize()}: {value}" for attr, value in filtered_data.items()])

		client.chat_postMessage(channel=event['channel'], text=response_text)
		return '', 200

	return jsonify({'response_type': 'ephemeral', 'text': 'Invalid command'})

if __name__ == '__main__':
	app.run(port=5000)
