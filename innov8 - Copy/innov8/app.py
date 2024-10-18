from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
import sqlite3
import random
import string
import google.generativeai as genai
import logging

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'sdf656sd5fsd45sdfjsuifhsidfbhsdufhnsfjwerfhailhcfaf'
DATABASE = 'users.db'

# Setup logging for better debugging
logging.basicConfig(level=logging.DEBUG)

# Initialize the database
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            token TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Configure Google Generative AI
genai.configure(api_key="AIzaSyAKeXpmwXpIHfKtfqDCpctNqjtkhcLEs_Y")  # Replace with your real API key

# Define the model configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

# Create the model
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-8b-exp-0827",
    generation_config=generation_config,
    system_instruction=(
        "You are a teacher responsible for grading students' answers. You will receive a question, "
        "answer, total mark, question type (short question or long question), and class level. Your task is "
        "to evaluate the student's answer for correctness, grammar, spelling, formatting, length (for long "
        "questions), and alignment with the difficulty level of the class. If the answer is incorrect, give 0 marks. "
        "If the answer is correct but contains errors, deduct 0.22 marks for each spelling mistake and 0.34 marks for "
        "each grammar mistake. Be strict and deduct marks for basic errors. Provide your assessment in this JSON format: "
        "{'answer': 'right' or 'wrong', 'Improve': 'tips to improve if any, else null', 'Mark': 'mark out of total', "
        "'Mistake': 'mistake if any, else null'}. Output only the JSON response."
    )
)

# Function to generate a random token for users
def generate_token(length=16):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['Name']
        contact = request.form['Contact']
        email = request.form['Email']
        password = request.form['Password']
        confirm_password = request.form['CPassword']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        token = generate_token()

        try:
            c.execute("INSERT INTO users (name, contact, email, password, token) VALUES (?, ?, ?, ?, ?)",
                      (name, contact, email, password, token))
            conn.commit()
            flash('Registration successful! Your token is: ' + token, 'success')
            return redirect(url_for('signin'))
        except sqlite3.IntegrityError:
            flash('Email already registered!', 'danger')
        finally:
            conn.close()
        
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['Email']
        password = request.form['Password']
        
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            token = user[5]
            flash('Login successful!', 'success')
            response = make_response(redirect(url_for('home')))
            response.set_cookie('token', token)
            return response
        else:
            flash('Invalid credentials!', 'danger')
        
    return render_template('signin.html')

@app.route('/')
def home():
    token = request.cookies.get('token')
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if token:
        c.execute("SELECT * FROM users WHERE token = ?", (token,))
        user = c.fetchone()
    else:
        user = None
    
    conn.close()

    if user:
        return render_template('withlogin/index2.html', user=user)
    else:
        return render_template('withoutlog/index.html')

@app.route('/ai', methods=['GET'])
def ai():
    token = request.cookies.get('token')

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if token:
        c.execute("SELECT * FROM users WHERE token = ?", (token,))
        user = c.fetchone()
    else:
        user = None
    
    conn.close()
    
    if user:
        return render_template('withlogin/ai.html', user=user)
    else:
        return redirect(url_for('signin'))

@app.route('/check_answer', methods=['POST'])
def check_answer():
    try:
        # Get data from form
        question = request.form['question']
        answer = request.form['answer']
        total_mark = request.form['total_mark']
        question_type = request.form['question_type']
        class_level = request.form['class_level']

        # Format the input for the AI model
        user_input = f"{question}, {answer}, {total_mark}, {question_type}, {class_level}"
        logging.info(f"Sending user input to AI: {user_input}")

        # Start a chat session and send the input to the AI
        chat_session = model.start_chat()
        response = chat_session.send_message(user_input)

        # Ensure we have a valid response from the AI
        if 'candidates' in response:
            result = response['candidates'][0]['output']
            logging.info(f"Received AI response: {result}")
            return jsonify({'result': result})
        else:
            logging.error(f"Invalid response from AI: {response}")
            return jsonify({'error': 'Invalid response from AI'})

    except Exception as e:
        # Log the error and provide feedback
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({'error': 'An error occurred, please try again'})

if __name__ == '__main__':
    app.run(debug=True)
