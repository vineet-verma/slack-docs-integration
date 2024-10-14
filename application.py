import json
import os
import slack
from dotenv import load_dotenv
from pathlib import Path
from flask import Flask
import requests
from slackeventsapi import SlackEventAdapter
import base64

app = Flask(__name__)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events', app)
client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

# Confluence credentials and URL
CONFLUENCE_URL = os.environ["CONFLUENCE_URL"]
CONFLUENCE_USERNAME = os.environ["CONFLUENCE_USERNAME"]
CONFLUENCE_API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
CONFLUENCE_PAGE_ID = os.environ["CONFLUENCE_PAGE_ID"]  # Page to update


BOT_ID = client.api_call("auth.test")['user_id']

@slack_events_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    # Here you could add logic to filter which messages to post
    if text.startswith("docs:"):  # Example command
        content = text[len("docs:"):].strip()
        print('update_confluence_page content : ' + content)
        get_confluence_page(content)

    if BOT_ID != user_id:
        client.chat_postMessage(channel=channel_id,text="Page updated.")


def update_confluence_page(content, page_id, version):
    credentials = f"{CONFLUENCE_USERNAME}:{CONFLUENCE_API_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    print(encoded_credentials)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_credentials}'
    }

    # Prepare the payload to update the page
    payload = {
        "version": {
            "number": version  # Increment this number to update the page
        },
        "title": "CCP Page",  # The title of the page
        "type": "page",
        "space": {
          "key":"amex"
        },
        "body": {
            "storage": {
                "value": f"{content}",
                "representation": "storage"
            }
        }
    }
    url = f"{CONFLUENCE_URL}/rest/api/content/"+page_id
    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("Page updated successfully!")
    else:
        print(f"Failed to update page: {response.content}")

def get_confluence_page(content):
    credentials = f"{CONFLUENCE_USERNAME}:{CONFLUENCE_API_TOKEN}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {encoded_credentials}'
    }
    url = f"{CONFLUENCE_URL}/rest/api/content?expand=body.storage,version.number"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("All content fetched")

        # Load the JSON data
        parsed_data = json.loads(response.content)

        # Extract the required fields
        for result in parsed_data['results']:
            page_type = result.get('type')
            page_title = result.get('title')
            body_value = result.get('body', {}).get('storage', {}).get('value')
            version = result.get('version', {}).get('number', {})
            if page_type == 'page' and page_title == 'CCP Page':
                page_id = result.get('id')
                print("Type:", page_type)
                print("Title:", page_title)
                print("Body Storage Value:", body_value)
                update_confluence_page(body_value+"<p>"+content+"</p>", page_id,version+1)
    else:
        print(f"Failed to update page: {response.content}")
if __name__ == "__main__":
    app.run(debug=True)