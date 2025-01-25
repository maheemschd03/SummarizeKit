from flask import Flask, render_template, request, jsonify
import sounddevice as sd
from scipy.io.wavfile import write
from supabase import create_client, Client
from cryptography.fernet import Fernet
import google.generativeai as genai
import threading
import os
import time
import base64

supa_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZW5ybmJuZHdhb2dhbnB2bGZ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNzA0ODE2MywiZXhwIjoyMDUyNjI0MTYzfQ.zQXN3Cc4YsCMA4NG6bfIMS6BJQ_jOylrRpZ4kABZ8M4"
url = "https://gyenrnbndwaoganpvlfv.supabase.co"



# Generate and store a key securely
key = Fernet.generate_key()
cipher = Fernet(key)


# connecting to the supabase and creating a client
print("Connecting")
url = url
key = key
supabase: Client = create_client(url, supa_key)
print("Connected to the Supabase")

# Google Generative AI setup
genai.configure(api_key="AIzaSyBjDFhGbbAp948PqeaZFZ1YxR5hR4uxpSk")

# Variables to control recording
is_recording = False
audio_data = None
file_name = "recorded_audio.wav"
subject = ""
type_of_class = ""




def getUniqueSubs(data):
    unique = set()

    for entry in data:
        data_str = entry['subject']
        unique.add(data_str)

    # Convert the set back to a list if you need a list of unique dates
    unique = list(unique)
    return (unique)







# Routes
app = Flask(__name__)



#User authentication
from flask import Flask, render_template, request, redirect, url_for, flash
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app and Supabase client
app.secret_key = 'your_secret_key'  # Set a secret key for flash messages


# Routes for registration and login
@app.route('/')
def welcome():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if email already exists in the database
        user = supabase.table('users').select('*').eq('email', email).execute()
        if user.data:
            flash('Email is already registered.', 'danger')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        # Insert user data into Supabase table
        supabase.table('users').insert({
            'email': email,
            'password': hashed_password
        }).execute()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch user data from Supabase
        user = supabase.table('users').select('*').eq('email', email).execute()

        if user.data:
            # Check if the password is correct
            if check_password_hash(user.data[0]['password'], password):
                global user_ID
                response = supabase.table('users').select('id').eq('email', email).execute()
                user_ID = response.data[0]['id']
                print(f"Current User = {user_ID}")
                flash('Login successful!', 'success')
                return redirect(url_for('home'))  # Redirect to a protected page
            else:
                flash('Incorrect password.', 'danger')
        else:
            flash('Email not found.', 'danger')

        return redirect(url_for('login'))

    return render_template('login.html')



@app.route("/home",methods=['GET', 'POST'])
def home():
    #here I am fetching the subjects from the database
    response = supabase.table("Main").select("subject").eq('user_id', user_ID).execute()
    subjects = getUniqueSubs(response.data)

    return render_template('home.html', subjects=subjects)




@app.route('/process_subject', methods=['GET', 'POST'])
def index():
    selected_subject = request.form['selected_subject']  # Get the selected date from the form

    # Fetching the subjects from the database
    response = supabase.table("Main").select("subject").eq('user_id', user_ID).execute()
    subjects = getUniqueSubs(response.data)


    if selected_subject in subjects:
        # making the list for the values
        response = supabase.table("Main").select("created_at").eq("subject", selected_subject).eq('user_id', user_ID).execute()
        dates = []

        for entry in response.data:
            dates.append(entry['created_at'])

        return render_template('home.html', subjects=dates)

    else :
        response = supabase.table("Main").select("*").eq("created_at", selected_subject).execute()
        return render_template('display.html', data=response.data[0])

@app.route('/delete', methods=['POST'])
def submit():
    # Catch the button value from the form
    button_value = request.form.get('timestamp')
    response = supabase.table('Main').delete().eq('created_at', button_value).execute()
    return redirect(url_for('home'))
    return jsonify({"message": f' This record was deleted : {button_value}'})

# Flask route for the main page
@app.route('/start', methods=['GET', 'POST'])
def start():
    return render_template('Record.html')


# Flask route to start recording
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global is_recording, audio_data, file_name, subject, type_of_class

    # Get subject and type from request
    data = request.get_json()
    subject = data.get('subject')
    type_of_class = data.get('type')

    if not is_recording:
        is_recording = True
        duration = 30  # Duration of the recording in seconds
        sample_rate = 44100  # Sample rate in Hz

        # Start the recording in a separate thread
        def record_audio():
            global audio_data, file_name
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            while(is_recording):
                time.sleep(1)
            sd.stop()
            write(file_name, sample_rate, audio_data)

        threading.Thread(target=record_audio).start()
        return jsonify({"message": "Recording started."})
    else:
        return jsonify({"message": "Recording is already in progress."})

# Flask route to stop recording
@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global is_recording

    if is_recording:
        is_recording = False
        return jsonify({"message": "Recording stopped. Processing file."})
    else:
        return jsonify({"message": "No recording in progress."})

# Flask route to process the recorded audio
@app.route('/process_audio', methods=['POST'])
def process_audio():
    global file_name, subject, type_of_class

    time.sleep(10)
    if not os.path.exists(file_name):
        return jsonify({"message": "No audio file found."})

    # Upload file to Google Generative AI
    myfile = genai.upload_file(file_name)
    print("File was Uploaded")
    prompt = '''
        This is my class recording. I missed the class. Summarize the class for me. Make detailed notes for me. 
        Also, give me the overall picture of what happened in the class. Provide the output in HTML styling code.
    '''

    model = genai.GenerativeModel("gemini-1.5-flash")
    result = model.generate_content([myfile, prompt])
    summary = result.text


    # Attendance report
    attendance_prompt = "Tell me the roll number of present and absent students. Style it as HTML code."
    attendance_result = model.generate_content([myfile, attendance_prompt])
    attendance_report = attendance_result.text

    #now encrpting the data for security purpose
    # Encrypt data
    encrypted_summary = cipher.encrypt(summary.encode())
    encrypted_attendance_report = cipher.encrypt(attendance_report.encode())

    # Encode encrypted data to Base64 strings
    encrypted_summary_base64 = base64.b64encode(encrypted_summary).decode('utf-8')
    encrypted_attendance_report_base64 = base64.b64encode(encrypted_attendance_report).decode('utf-8')

    print("The processing was done successfully")

    # Save summary, attendance report, subject, and type to Supabase
    response = (
        supabase.table("Main")
        .insert({
            "summary": summary,
            "attendance_report": attendance_report,
            "subject": subject,
            "type": type_of_class,
            "user_id": user_ID,
        })
        .execute()
    )

    #deleting the audio file after processing
    if os.path.exists(file_name):
        os.remove(file_name)  # Delete the file
        print(f"{file_name} has been deleted successfully.")
    else:
        print(f"{file_name} does not exist.")

    return jsonify({"summary": summary, "attendance_report": attendance_report})



if __name__ == "__main__":
    app.run(debug=True)
