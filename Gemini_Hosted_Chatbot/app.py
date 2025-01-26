from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import os
import logging
import google.generativeai as genai
from datetime import datetime
from constants import constants
from apis.token_generation import get_x_api_token
from apis.list_storage_systems import get_list_storage_systems
from apis.storage_system_alerts import get_storage_system_alerts
from apis.storage_system_notifications import get_storage_system_notifications
from apis.tenant_alerts import get_tenant_alerts
from apis.metrics_storage_system import get_storage_system_metrics
from apis.volume_storage_system import get_storage_system_volumes
from apis.tenant_notifications import get_tenant_notifications
from apis.system_name_to_system_uuid_mapping import get_system_name_to_uuid_mapping
import urllib3
import psycopg2
import uuid
from flask_session import Session
# Set the logging level for the library to ERROR
logging.getLogger('langchain_google_genai').setLevel(logging.ERROR)
urllib3.disable_warnings()

token = None
# Global variable to hold the tenant connection details
tenant_id = ""
 
class StorageTools:

    def __init__(self):
        self.x_api_key = get_x_api_token()
    
    def get_system_name_to_system_uuid_mapping(self):
        """
        Get the system uuid corresponding to storage system name. This tool should be used as pre-requisite to convert storage system name to system_uuid.
        So whenever any tool requires system uuid and the user provides only the storage system name, then this tool should be used as a pre-requisite to first convert the storage system name to the corresponding system_uuid.

        Returns:
            str: A JSON object containing mappings of storage system names to it's corresponsing system uuids.
        """

        response = get_system_name_to_uuid_mapping(self.x_api_key)
        return str(response)


    def get_alert_details_for_tenant(self):
        """
        Get alert details on a tenant level.

        Returns:
            str: A JSON object containing alert details data of various resources on this tenant.
        """
        response = get_tenant_alerts(self.x_api_key)
        return str(response)

    def get_notifications_for_storage_system(self, storage_system_uuid: str):
        """
        Get notification details related to user specified storage system uuid.

        Args:
            storage_system_uuid (str): The storage system uuid for which user wants to get notification details.

        Returns:
            str: A JSON object containing notifications data for the storage system uuid specified by user.
        """
        response = get_storage_system_notifications(self.x_api_key, storage_system_uuid)
        return str(response)

    def get_alerts_for_storage_system(self, storage_system_uuid: str):
        """
        Get alerts details for user specified storage system uuid on this tenant.

        Args:
            storage_system_uuid (str): The storage system uuid for which user wants to get alert details.

        Returns:
            str: A JSON object containing the alert details data for user specified storage system uuid.
        """
        response = get_storage_system_alerts(self.x_api_key, storage_system_uuid)
        return str(response)

    def get_list_of_all_storage_systems(self):
        """
        To get list of details of all storage systems present on this tenant.

        Returns:
            str: A JSON object containing the details of all storage systems on this tenant.
        """
        response = get_list_storage_systems(self.x_api_key)
        return str(response)

    def get_volumes_of_storage_system(self, storage_system_uuid: str):
        """
        To get details of all volumes present in user specified storage system. First get system uuid from system name using get_system_name_to_system_uuid_mapping tool if user has only provided the system name.

        Args:
            storage_system_uuid (str): The storage system uuid for which user wants to get volumes details.

        Returns:
            str: A JSON object containing all volumes details in user specified storage system uuid.
        """
        response = get_storage_system_volumes(self.x_api_key, storage_system_uuid)
        return str(response)

    def get_metrics_of_storage_system(self, storage_system_uuid: str, duration_in_days: int = 30):
        """
        To get details of all metrics present in user specified storage system. For example, metrics like CPU utilization, capacity, and others alike.

        Args:
            storage_system_uuid (str): The storage system uuid for which user wants to get metrics details.
            duration_in_days (int, optional): The duration in days for which the metrics are to be fetched. Defaults to 30.

        Returns:
            str: A JSON object containing the metrics details for user specified storage system uuid.
        """
        response = get_storage_system_metrics(self.x_api_key, storage_system_uuid)
        return str(response)

    def get_notifications_for_tenant(self, severity_level: str = 'critical'):
        """
        Get notification details related to this tenant having all storage systems on it.

        Args:
            severity_level (str, optional): The severity level of the notifications to be fetched from tenant. Defaults to 'critical'.

        Returns:
            str: A JSON object containing notifications data on this tenant of all its storage systems.
        """
        response = get_tenant_notifications(self.x_api_key)
        return str(response)


GOOGLE_API_KEY = constants.GOOGLE_API_KEY
genai.configure(api_key=GOOGLE_API_KEY)
# Initialize the StorageTools instance
storage_tools = StorageTools()

# Define the generative model outside the class
generative_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config={'temperature': 0},
    tools=[
        storage_tools.get_system_name_to_system_uuid_mapping,
        storage_tools.get_alert_details_for_tenant,
        storage_tools.get_notifications_for_storage_system,
        storage_tools.get_alerts_for_storage_system,
        storage_tools.get_list_of_all_storage_systems,
        storage_tools.get_volumes_of_storage_system,
        storage_tools.get_metrics_of_storage_system,
        storage_tools.get_notifications_for_tenant
    ],
    system_instruction="""
        Use the tools provided to you to answer the questions asked by the user. Always ensure accurate response.
        If the user has provided insufficient information, ask the user to follow up with more details based on the tools requirement.
        Please summarize your responses by focusing only on the specific information the user has requested.
        Highlight key points that directly answer the user's questions and exclude any additional or unrelated information.
        Parse the json structure carefully to find what user is asking about and respond accordingly.
    """
)

def parse_and_call_function(response,storage_tools):

    responses_dict = {}
    for part in response.parts:
        if fn := part.function_call:
            args = ", ".join(f"{key}={val}" for key, val in fn.args.items())
            args_dict = {key: val for key, val in fn.args.items()}
            function_name = fn.name
            
            #Call the function dynamically
            func = getattr(storage_tools, function_name)
            result = func(**args_dict)
            responses_dict[function_name] = result
            
    try:
        response_parts = [
            genai.protos.Part(function_response=genai.protos.FunctionResponse(name=fn, response={"result": val}))
            for fn, val in responses_dict.items()
        ]
        return response_parts
    
    except Exception as e:
        response_parts = "Unfortunately, I am not sure about this"
        return response_parts



app = Flask(__name__)
secret_key = os.urandom(24)
# Convert the bytes to a string for Flask
app.secret_key = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Database connection setup
def get_db_connection():
    
    conn = psycopg2.connect(
        user=<USER_NAME>,
        password=<PASSWORD>,
        host=<HOST>,
        port=<PORT>,
        database=<DB_NAME>
    )
    return conn

# In-memory storage for simplicity; replace with a database for production
chat_histories = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        session['tenant_id'] = request.form['tenant_id']

        # Attempt to authenticate with provided details
        global token
        token = get_x_api_token()
        print("Token is = ")
        print(token)
        if token:
            return redirect(url_for('chat'))
        else:
            return render_template('start.html', error="Connection unsuccessful. Please try again.")
    return render_template('start.html')

@app.route('/chat', methods=['GET'])
def chat():
    if not token:
        return redirect(url_for('start'))
    
    return render_template('chat.html')

# Initialize the chat once globally
chatmodel = generative_model.start_chat(enable_automatic_function_calling=False, history=[])

@app.route('/chat_api', methods=['POST'])
def chat_api():
    global chatmodel  
    try:
        data = request.json
        message = data.get('message')
        conversation_id = data.get('conversation_id')

        if not conversation_id:
            conversation_id = str(uuid.uuid4())  # Generate a new UUID if not provided

        # Retrieve or initialize chat history
        tenant_id = session.get('tenant_id')
        history = chat_histories.get(tenant_id, [])

        conn = get_db_connection()
        cur = conn.cursor()

        # Save the user message to the database
        cur.execute("""
            INSERT INTO SCHEMA.table_name (conversation_id, sender, message)
            VALUES (%s, %s, %s)
        """, (conversation_id, 'User', message))

        # Process the message using the chat model
        response = chatmodel.send_message(message)
        
        # Handle function calling
        while True:
            function_call_needed = False
            new_response = None

            for part in response.parts:
                if fn := part.function_call:
                    response_parts = parse_and_call_function(response, storage_tools)
                    new_response = chatmodel.send_message(response_parts)
                    function_call_needed = True
                    break

            if function_call_needed:
                response = new_response
            else:
                break

        final_response = ""
        for part in response.parts:
            if fn := part.text:
                final_response = fn
        
        # Save the assistant's response to the database
        cur.execute("""
            INSERT INTO SCHEMA.table_name (conversation_id, sender, message)
            VALUES (%s, %s, %s)
        """, (conversation_id, 'Assistant', final_response))

        conn.commit()
        cur.close()
        conn.close()

        # Append to chat history
        history.append({"user": message, "assistant": final_response})
        chat_histories[tenant_id] = history

        return jsonify({'response': final_response, 'conversation_id': conversation_id})

    except Exception as e:
        print(f"Bot: Sorry, can you come again? {e}")
        return jsonify({'response': "Sorry, I don't understand. Can you come again?", 'conversation_id': conversation_id})


# Endpoint to fetch the chat history for a specific conversation
@app.route('/get_conversation/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sender, message FROM SCHEMA.table_name
        WHERE conversation_id = %s
        ORDER BY created_at ASC
    """, (conversation_id,))
    messages = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({'messages': messages})

# Endpoint to fetch all conversation IDs
@app.route('/get_conversations', methods=['GET'])
def get_conversations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT conversation_id FROM SCHEMA.table_name
    """)
    conversations = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify({'conversations': [convo[0] for convo in conversations]})

if __name__ == '__main__':
    app.run(debug=True)