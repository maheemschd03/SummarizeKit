from flask import Flask, render_template, request, jsonify
import sounddevice as sd
from scipy.io.wavfile import write
from supabase import create_client, Client
import google.generativeai as genai
import threading
import os

# Flask app setup
app = Flask(__name__)

#Supabase client setup
url = "https://gyenrnbndwaoganpvlfv.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd5ZW5ybmJuZHdhb2dhbnB2bGZ2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNzA0ODE2MywiZXhwIjoyMDUyNjI0MTYzfQ.zQXN3Cc4YsCMA4NG6bfIMS6BJQ_jOylrRpZ4kABZ8M4"
supabase: Client = create_client(url, key)

# Google Generative AI setup
genai.configure(api_key="AIzaSyBjDFhGbbAp948PqeaZFZ1YxR5hR4uxpSk")

# Variables to control recording
is_recording = False
audio_data = None
file_name = "recorded_audio.wav"
subject = ""
type_of_class = ""

# Flask route for the main page
@app.route('/')
def index():
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
        duration = 3600  # Duration of the recording in seconds
        sample_rate = 44100  # Sample rate in Hz

        # Start the recording in a separate thread
        def record_audio():
            global audio_data, file_name
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()  # Wait until the recording is finished
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

    if not os.path.exists(file_name):
        return jsonify({"message": "No audio file found."})

    # Upload file to Google Generative AI
    myfile = genai.upload_file(file_name)
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

    # Save summary, attendance report, subject, and type to Supabase
    response = (
        supabase.table("Main")
        .insert({"summary": summary, "attendance_report": attendance_report, "subject": subject, "type": type_of_class})
        .execute()
    )

    return jsonify({"summary": summary, "attendance_report": attendance_report})

if __name__ == '__main__':
    app.run(debug=True)
