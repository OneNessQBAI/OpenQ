from flask import Flask, request, jsonify, send_from_directory, Response
import threading, time, models, os, sys
from ansio import application_keypad, mouse_input, raw_input
from ansio.input import InputEvent, get_input_event
from OpenQuantumAI import OpenQuantumAI, OpenQuantumAIConfig
from python.helpers.print_style import PrintStyle
from python.helpers.files import read_file
from python.helpers import files
import python.helpers.timed_input as timed_input
from logger import log_messages  # Import log_messages from logger.py
import cirq
from cirq.circuits.circuit import Circuit
from cirq.ops.common_gates import H
from cirq.devices.line_qubit import LineQubit
from cirq.ops.measure_util import measure
from cirq.sim.sparse_simulator import Simulator
import numpy as np
import sympy
from flask import Flask, request, jsonify
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import sqlite3
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet
# Import quantum_sha256 related functions
from quantum_sha256 import quantum_sha256
import stripe
from datetime import datetime, timedelta
from typing import Tuple, List, Union

app = Flask(__name__)

# Stripe configuration
stripe.api_key = "YOUR_STRIPE_SECRET_KEY"

# Redirect stdout and stderr in main.py as well if needed
# This ensures all prints go to logger.py's log_messages
class StreamToList:
    def write(self, message):
        if message.strip():
            from logger import add_log
            add_log(message)

    def flush(self):
        pass

sys.stdout = StreamToList()
sys.stderr = StreamToList()

# Initialize OpenQuantumAI instance
openai_api_key = None
open_quantum_ai_instance = None  # Renamed the instance to avoid conflict

input_lock = threading.Lock()
os.chdir(files.get_abs_path("./work_dir"))  # Change CWD to work_dir

# Initialize Database (Ensure this is placed where other initializations are done)
def init_db():
    conn = sqlite3.connect('quantum_sha256.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS signatures (
            id INTEGER PRIMARY KEY,
            tag TEXT NOT NULL UNIQUE,
            hash BLOB NOT NULL,
            qubits BLOB NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            user_email TEXT NOT NULL UNIQUE,
            subscription_id TEXT NOT NULL,
            end_date DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Encrypt data using Fernet symmetric encryption
def encrypt_data(data):
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(data.encode('utf-8'))
    return key, cipher_text

# Decrypt data using Fernet symmetric encryption
def decrypt_data(key, cipher_text):
    cipher_suite = Fernet(key)
    plain_text = cipher_suite.decrypt(cipher_text).decode('utf-8')
    return plain_text

# Route to store SHA256 signature
@app.route('/quantum-sha256-store', methods=['POST'])
def store_signature():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    content = data.get('content', '')
    tag = data.get('tag', '')

    if not tag:
        return jsonify({'error': 'Tag is required.'}), 400

    sha256_hash, qubits_output = quantum_sha256(content)
    key_hash, encrypted_hash = encrypt_data(sha256_hash)
    key_qubits, encrypted_qubits = encrypt_data(qubits_output)
    
    conn = sqlite3.connect('quantum_sha256.db')
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO signatures (tag, hash, qubits) VALUES (?, ?, ?)
        ''', (tag, b64encode(key_hash + b'||' + encrypted_hash), b64encode(key_qubits + b'||' + encrypted_qubits)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Tag already exists.'}), 400
    finally:
        conn.close()

    return jsonify({
        'message': 'Signature stored successfully.',
        'quantum_signature': qubits_output
    })

# Route to verify SHA256 signature
@app.route('/quantum-sha256-verify', methods=['POST'])
def verify_signature():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    content = data.get('content', '')
    tag = data.get('tag', '')

    sha256_hash, qubits_output = quantum_sha256(content)

    conn = sqlite3.connect('quantum_sha256.db')
    c = conn.cursor()
    c.execute('SELECT hash, qubits FROM signatures WHERE tag = ?', (tag,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Tag not found.'}), 400

    key_hash, encrypted_hash = b64decode(row[0]).split(b'||')
    key_qubits, encrypted_qubits = b64decode(row[1]).split(b'||')
    stored_hash = decrypt_data(key_hash, encrypted_hash)
    stored_qubits = decrypt_data(key_qubits, encrypted_qubits)

    if stored_hash == sha256_hash:
        return jsonify({
            'match': True,
            'message': 'Signatures match!',
            'quantum_signature': qubits_output
        })
    else:
        return jsonify({
            'match': False,
            'message': 'Signatures do not match.',
            'quantum_signature': qubits_output
        })

# New route to search for SHA256 signature by tag
@app.route('/quantum-sha256-search', methods=['POST'])
def search_signature():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    tag = data.get('tag', '')

    if not tag:
        return jsonify({'error': 'Tag is required.'}), 400

    conn = sqlite3.connect('quantum_sha256.db')
    c = conn.cursor()
    c.execute('SELECT hash, qubits FROM signatures WHERE tag = ?', (tag,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Tag not found.'}), 404

    key_hash, encrypted_hash = b64decode(row[0]).split(b'||')
    key_qubits, encrypted_qubits = b64decode(row[1]).split(b'||')
    stored_hash = decrypt_data(key_hash, encrypted_hash)
    stored_qubits = decrypt_data(key_qubits, encrypted_qubits)

    return jsonify({
        'hash': stored_hash,
        'quantum_signature': stored_qubits
    })

# Initialize the database when starting the app
init_db()

# Initialize OpenQuantumAI instance
def initialize_models():
    global open_quantum_ai_instance  # Ensure we're aware of this variable globally

    # Main chat model used by agents (smarter, more accurate)
    chat_llm = models.get_openai_chat(model_name="gpt-4o-mini", temperature=0, api_key=openai_api_key)
    print("Chat model initialized.")  # Debugging line

    # Utility model used for helper functions (cheaper, faster)
    utility_llm = chat_llm

    # Embedding model used for memory
    embedding_llm = models.get_openai_embedding(model_name="text-embedding-3-small", api_key=openai_api_key)
    print("Embedding model initialized.")  # Debugging line

    # Configuration
    config = OpenQuantumAIConfig(
        chat_model=chat_llm,
        utility_model=utility_llm,
        embeddings_model=embedding_llm,
        auto_memory_count=0,
        code_exec_docker_enabled=True,
        code_exec_ssh_enabled=True,
    )
    
    # Create the first agent
    open_quantum_ai_instance = OpenQuantumAI(number=0, config=config)  # Provide the required argument for the 'number' parameter
    print(f"OpenQuantumAI initialized: {open_quantum_ai_instance is not None}")  # Additional Debugging line

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/styles.css')
def serve_css():
    return send_from_directory('frontend', 'styles.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('frontend', 'script.js')

# New routes for serving images and videos
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

@app.route('/video/<path:filename>')
def serve_video(filename):
    return send_from_directory('video', filename)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    user_input = data.get('message')
    console_output = ""
    if user_input:
        if open_quantum_ai_instance is None:
            return jsonify({'error': 'OpenQuantumAI instance not initialized.'}), 400
        assistant_response = open_quantum_ai_instance.message_loop(msg=user_input)
        console_output = f"User Input: {user_input}\nAssistant Response: {assistant_response}\n"
        print(console_output)  # Print to terminal for visibility
        return jsonify({
            'response': assistant_response,
            'console': console_output
        })
    return jsonify({'error': 'No message provided'}), 400

@app.route('/connect', methods=['POST'])
def connect():
    global openai_api_key, open_quantum_ai_instance
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    api_key = data.get('apiKey')
    print(f"Received API Key: {api_key}")  # Debugging line
    if api_key:
        openai_api_key = api_key
        initialize_models()  # Properly initializes models and sets open_quantum_ai_instance
        print(f"OpenQuantumAI initialized: {open_quantum_ai_instance is not None}")  # Debugging line
        return jsonify({'status': 'connected', 'apiKey': api_key})
    return jsonify({'error': 'No API key provided'}), 400

@app.route('/login', methods=['POST'])
def login_route():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    if username and password:
        # Implement login logic
        print(f"User logged in: {username}")  # Debugging line
        return jsonify({'status': 'logged in', 'username': username})
    return jsonify({'error': 'Invalid credentials'}), 400

@app.route('/logout', methods=['POST'])
def logout_route():
    # Implement logout logic
    print("User logged out.")  # Debugging line
    return jsonify({'status': 'logged out'})

@app.route('/fetch-ai-data', methods=['POST'])
def fetch_ai_data():
    global open_quantum_ai_instance
    
    if open_quantum_ai_instance is None:
        error_message = "OpenQuantumAI instance not initialized. Please connect your API key first."
        print(error_message)  # Log to server console
        return jsonify({
            'error': error_message,
            'console': f"Error: {error_message}"
        }), 400
    
    try:
        data = request.get_json(silent=True)
        if not data:
            raise ValueError("Invalid JSON data in request")
        
        message = data.get('message', '')
        if not message:
            raise ValueError("No message provided in the request")
        
        # Use the message_loop method to process the request
        ai_response = open_quantum_ai_instance.message_loop(msg=message)
        console_output = f"AI Data Fetch: {ai_response}"
        print(console_output)  # Log to server console
        return jsonify({
            'response': ai_response,
            'console': console_output
        })
    except ValueError as ve:
        error_message = str(ve)
        print(f"ValueError: {error_message}")  # Log to server console
        return jsonify({
            'error': error_message,
            'console': f"Error: {error_message}"
        }), 400
    except Exception as e:
        error_message = f"Error during AI data fetch: {str(e)}"
        print(error_message)  # Log to server console
        return jsonify({
            'error': error_message,
            'console': f"Error: {error_message}"
        }), 500

# Route to update system prompt with user instructions
@app.route('/update-instructions', methods=['POST'])
def update_instructions_route():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    instruction = data.get('instruction', '')
    if open_quantum_ai_instance:
        # Update the system prompt dynamically using the new method
        open_quantum_ai_instance.update_system_prompt(instruction)
        return jsonify({'status': 'updated'})
    return jsonify({'status': 'failed', 'error': 'OpenQuantumAI instance not initialized.'}), 400

# Route to clear conversation
@app.route('/clear-conversation', methods=['POST'])
def clear_conversation_route():
    if open_quantum_ai_instance:
        open_quantum_ai_instance.history = []
        print("Conversation history cleared by user.")
        return jsonify({'status': 'cleared'})
    return jsonify({'status': 'failed', 'error': 'OpenQuantumAI instance not initialized.'}), 400

# SSE route to stream logs
@app.route('/stream-logs')
def stream_logs():
    def event_stream():
        last_index = 0
        while True:
            if last_index < len(log_messages):
                msg = log_messages[last_index]
                last_index += 1
                yield f'data: {msg}\n\n'
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

def initialize():
    global open_quantum_ai_instance, openai_api_key
    if not openai_api_key:
        print("OpenAI API key not set. Please use the /connect endpoint to set the API key.")
        return

    # Main chat model used by OpenQuantumAIs (smarter, more accurate)
    chat_llm = models.get_openai_chat(model_name="gpt-4o-mini", temperature=0, api_key=openai_api_key)
    
    # Utility model used for helper functions (cheaper, faster)
    utility_llm = chat_llm
    
    # Embedding model used for memory
    embedding_llm = models.get_openai_embedding(model_name="text-embedding-3-small", api_key=openai_api_key)

    # OpenQuantumAI configuration
    config = OpenQuantumAIConfig(
        chat_model=chat_llm,
        utility_model=utility_llm,
        embeddings_model=embedding_llm,
        code_exec_docker_enabled=True,
        code_exec_ssh_enabled=True,
    )

    open_quantum_ai_instance = OpenQuantumAI(number=0, config=config)


# Twilio credentials
account_sid = 'AC3e40112d57aba95d84cbef2d1a9add11'
auth_token = '675f5691c210562b8edeef8729bb47d4'
client = Client(account_sid, auth_token)

def quantum_random(min_value: float, max_value: float) -> float:
    """Generate a quantum random number using Cirq."""
    qubits = [LineQubit(i) for i in range(8)]
    circuit = Circuit(
        H.on_each(qubits),
        measure(*qubits, key='result')
    )
    result = Simulator().run(circuit, repetitions=1).measurements['result'][0]
    value = int(''.join(map(str, result)), 2)
    return min_value + (value / 255) * (max_value - min_value)

def generate_prime(min_value: int, max_value: int) -> int:
    """Generate a prime number using quantum randomness."""
    while True:
        num = int(quantum_random(min_value, max_value))
        if sympy.isprime(num):
            return num

def generate_keypair(p: int, q: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Generate RSA keypair."""
    n = p * q
    phi = (p - 1) * (q - 1)
    e = sympy.randprime(1, phi)
    d = pow(e, -1, phi)
    return ((e, n), (d, n))

def quantum_encrypt(public_key: Tuple[int, int], message: str) -> List[int]:
    """Encrypt a message using quantum circuits."""
    e, n = public_key
    encrypted = [pow(ord(char), e, n) for char in message]
    return encrypted

def quantum_decrypt(private_key: Tuple[int, int], ciphertext: List[int]) -> str:
    """Decrypt a message using quantum circuits."""
    d, n = private_key
    decrypted = ''.join([chr(pow(char, d, n)) for char in ciphertext])
    return decrypted

@app.route('/quantum-rsa-generate', methods=['POST'])
def generate_rsa_keypair():
    p = generate_prime(100, 1000)
    q = generate_prime(100, 1000)
    public_key, private_key = generate_keypair(p, q)
    return jsonify({
        'publicKey': f"{public_key[0]},{public_key[1]}",
        'privateKey': f"{private_key[0]},{private_key[1]}"
    })

@app.route('/quantum-rsa-encrypt', methods=['POST'])
def encrypt_message():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    public_key = tuple(map(int, data['publicKey'].split(',')))
    message = data['message']
    encrypted = quantum_encrypt(public_key, message)
    return jsonify({'encryptedMessage': ','.join(map(str, encrypted))})

@app.route('/quantum-rsa-decrypt', methods=['POST'])
def decrypt_message():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    private_key = tuple(map(int, data['privateKey'].split(',')))
    encrypted_message = list(map(int, data['message'].split(',')))
    decrypted = quantum_decrypt(private_key, encrypted_message)
    return jsonify({'decryptedMessage': decrypted})

# New route to create a subscription
@app.route('/create-subscription', methods=['POST'])
def create_subscription():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    email = data.get('email')
    payment_method = data.get('payment_method')

    try:
        # Create a customer
        customer = stripe.Customer.create(
            email=email,
            payment_method=payment_method,
            invoice_settings={
                'default_payment_method': payment_method
            }
        )

        # Create a subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': 'YOUR_STRIPE_PRICE_ID'}],  # Replace with your actual price ID
            expand=['latest_invoice.payment_intent']
        )

        # Store subscription info in the database
        conn = sqlite3.connect('quantum_sha256.db')
        c = conn.cursor()
        end_date = datetime.now() + timedelta(days=30)
        c.execute('''
            INSERT OR REPLACE INTO subscriptions (user_email, subscription_id, end_date)
            VALUES (?, ?, ?)
        ''', (email, subscription.id, end_date))
        conn.commit()
        conn.close()

        client_secret = None
        if hasattr(subscription, 'latest_invoice') and \
           hasattr(subscription.latest_invoice, 'payment_intent') and \
           hasattr(subscription.latest_invoice.payment_intent, 'client_secret'):
            client_secret = subscription.latest_invoice.payment_intent.client_secret

        return jsonify({
            'status': subscription.status,
            'subscription_id': subscription.id,
            'client_secret': client_secret
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

# New route to check subscription status
@app.route('/check-subscription', methods=['POST'])
def check_subscription():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
    
    email = data.get('email')

    conn = sqlite3.connect('quantum_sha256.db')
    c = conn.cursor()
    c.execute('SELECT subscription_id, end_date FROM subscriptions WHERE user_email = ?', (email,))
    row = c.fetchone()
    conn.close()

    if row:
        subscription_id, end_date = row
        end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S.%f')
        is_active = end_date > datetime.now()
        return jsonify({
            'is_subscribed': True,
            'is_active': is_active,
            'end_date': end_date.isoformat()
        })
    else:
        return jsonify({
            'is_subscribed': False
        })

if __name__ == "__main__":
    print("Initializing framework...")
    initialize()
    app.run(host='0.0.0.0', port=4000, threaded=True)
