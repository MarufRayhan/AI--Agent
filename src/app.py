from flask import Flask, render_template, request, Response, jsonify
import json
import sys
import os
import tempfile
from datetime import datetime
import io
import re
import threading
import queue
import time
import traceback
import signal

# Import your existing modules
import config
import readinput

# Function to strip ANSI color codes
def strip_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Set OpenAI API key from environment variable
# Try to get it from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()  # take environment variables from .env
except ImportError:
    # dotenv not installed, continue without it
    pass

# Set the OpenAI API key for your application
openai_api_key = os.environ.get('OPENAI_API_KEY')
if openai_api_key:
    # Set the API key for the OpenAI module
    import openai
    openai.api_key = openai_api_key
    # For older versions of the OpenAI library
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
    except ImportError:
        pass

app = Flask(__name__)

# Global queue for output messages
output_queue = queue.Queue()
# Global variable to store the complete output
complete_output = ""
# Flag to indicate if processing is complete
processing_complete = threading.Event()
# Flag to indicate if processing should stop
stop_processing = threading.Event()
# Current processing thread
current_thread = None

@app.route('/', methods=['GET'])
def home():
    # Check if API key is set
    if not openai_api_key:
        api_warning = "Warning: OpenAI API key not set. Please set the OPENAI_API_KEY environment variable."
    else:
        api_warning = None

    # Get available config files
    config_files = []
    config_dir = os.path.join(os.path.dirname(__file__), '../config')
    if os.path.exists(config_dir):
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    
    # Reset global variables
    global complete_output, processing_complete, stop_processing, current_thread
    complete_output = ""
    processing_complete.clear()
    stop_processing.clear()
    current_thread = None
    while not output_queue.empty():
        output_queue.get()
    
    return render_template('index.html', 
                          config_files=config_files,
                          api_warning=api_warning)

@app.route('/process', methods=['POST'])
def process():
    """Start the processing in a background thread and return immediately"""
    try:
        global current_thread, stop_processing
        
        # Clear the stop flag
        stop_processing.clear()
        
        # Check API key
        if not openai_api_key:
            return jsonify({'error': "OpenAI API key not set. Please set the OPENAI_API_KEY environment variable."}), 400

        # Get form data
        config_file = request.form.get('config_file')
        user_story = request.form.get('user_story')
        mvp_text = request.form.get('mvp_text')
        
        # Handle encoding issues - normalize text to plain ASCII/Unicode
        user_story = normalize_text(user_story)
        mvp_text = normalize_text(mvp_text)
        
        # Save user story and MVP to temporary files using UTF-8 encoding
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, suffix='.txt') as user_story_file:
            user_story_file.write(user_story)
            user_story_path = user_story_file.name
        
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, suffix='.txt') as mvp_file:
            mvp_file.write(mvp_text)
            mvp_path = mvp_file.name
        
        # Set up config path
        config_path = os.path.join(os.path.dirname(__file__), '../config', config_file)
        
        # Start processing in a background thread
        current_thread = threading.Thread(
            target=run_pipeline_thread, 
            args=(config_path, user_story_path, mvp_path),
            daemon=True
        )
        current_thread.start()
        
        return jsonify({'success': True})
    
    except Exception as e:
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        custom_print(error_msg)
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/stop', methods=['POST'])
def stop():
    """Stop the processing"""
    global stop_processing, current_thread, processing_complete
    
    try:
        # Set the stop flag
        stop_processing.set()
        
        # Wait a bit for the thread to notice the flag
        time.sleep(0.5)
        
        # If thread is still running, try to force it to complete
        if current_thread and current_thread.is_alive():
            # Signal that processing is complete (even though it was stopped)
            processing_complete.set()
            custom_print("\n*** Processing stopped by user ***\n")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def normalize_text(text):
    """Normalize text to avoid encoding issues"""
    # Replace common problematic characters
    replacements = {
        '\u2013': '-',  # en dash
        '\u2014': '-',  # em dash
        '\u2018': "'",  # left single quote
        '\u2019': "'",  # right single quote
        '\u201c': '"',  # left double quote
        '\u201d': '"',  # right double quote
        '\u2026': '...',  # ellipsis
        '\u00a0': ' ',  # non-breaking space
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Further normalize by ensuring it's valid UTF-8
    text = text.encode('utf-8', errors='replace').decode('utf-8')
    
    return text

@app.route('/stream')
def stream():
    """Stream the output as it's generated"""
    def event_stream():
        while True:
            # Check if there are messages in the queue
            try:
                message = output_queue.get(timeout=0.1)
                yield f"data: {json.dumps({'message': message})}\n\n"
            except queue.Empty:
                # If processing is complete and queue is empty, send completion message
                if processing_complete.is_set():
                    yield f"data: {json.dumps({'complete': True, 'full_output': complete_output})}\n\n"
                    break
                # Otherwise just continue checking
                pass
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    """Set the OpenAI API key from a POST request"""
    try:
        data = request.get_json()
        if not data or 'api_key' not in data:
            return jsonify({'success': False, 'error': 'No API key provided'}), 400
        
        api_key = data['api_key']
        if not api_key.startswith('sk-'):
            return jsonify({'success': False, 'error': 'Invalid API key format'}), 400
        
        # Set the API key in the global variable
        global openai_api_key
        openai_api_key = api_key
        
        # Set the API key for the OpenAI module
        import openai
        openai.api_key = api_key
        # For newer versions of the OpenAI library
        try:
            from openai import OpenAI
            global client
            client = OpenAI(api_key=api_key)
        except ImportError:
            pass
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def custom_print(text):
    """Custom print function that puts output in the queue and adds to complete output"""
    global complete_output
    # Strip ANSI codes
    clean_text = strip_ansi_codes(text)
    # Add to queue for streaming
    output_queue.put(clean_text)
    # Add to complete output
    complete_output += clean_text + "\n"

def run_pipeline_thread(config_path, input_path, mvp_path):
    """Run the pipeline in a thread and capture output for streaming"""
    try:
        # Redirect standard output to our custom print function
        original_print = print
        
        def thread_print(*args, **kwargs):
            # Convert args to string like the print function would
            message = " ".join(str(arg) for arg in args)
            if "end" in kwargs:
                message += kwargs["end"]
            else:
                message += "\n"
            # Use our custom print function
            custom_print(message)
        
        # Replace the global print function with our thread_print
        import builtins
        builtins.print = thread_print
        
        try:
            # Run the pipeline
            run_pipeline(config_path, input_path, mvp_path)
        except Exception as e:
            print(f"Error in run_pipeline: {str(e)}")
            print(traceback.format_exc())
        finally:
            # Restore the original print function
            builtins.print = original_print
            
            # Clean up temp files
            try:
                os.unlink(input_path)
                os.unlink(mvp_path)
            except Exception as e:
                print(f"Error cleaning up temp files: {str(e)}")
            
            # Signal that processing is complete
            processing_complete.set()
            
    except Exception as e:
        # If an error occurs, add it to the queue
        error_message = f"Error in thread: {str(e)}"
        custom_print(error_message)
        custom_print(traceback.format_exc())
        # Signal that processing is complete
        processing_complete.set()

def run_pipeline(config_path, input_path, mvp_path):
    """Run the pipeline directly, similar to main() in main.py"""
    # Load configuration file and create agents
    config_file = config.read_json(config_path)
    config.validate(config_file)
    print("Successfully read configuration file")
    
    agents = config.create_coloragents(config_file)
    agent_order = config_file["agent_order"]
    iterations = config_file.get("iterations", 1)

    # Fetch the initial user story
    user_story = fetch_task(input_path, mvp_path)

    # Iterate over each step for each agent
    for iteration in range(iterations):
        # Check if should stop
        if stop_processing.is_set():
            print("Processing stopped by user request.")
            return

        print(f"--- Phase {iteration + 1} ---")

        for agent_name in agent_order:
            # Check if should stop
            if stop_processing.is_set():
                print("Processing stopped by user request.")
                return
                
            # Find the agent configuration in the list
            agent_config = next((agent for agent in config_file["agents"] if agent["name"] == agent_name), None)
            if not agent_config:   
                continue

            task_info = agent_config["tasks"].get(str(iteration + 1))

            if task_info:
                if iteration == 0:
                    task = f"The user story is the following:\n{task_info}\n\nUser Story:\n{user_story}"
                else:
                    task = f"The user story is the following:\n{task_info}{user_story}"
                print("-------------------------------")
                print(f"Assigning task to {agent_name}: {task_info}")
                
                # Check if should stop
                if stop_processing.is_set():
                    print("Processing stopped by user request.")
                    return
                    
                agent = agents[agent_name]
                agent.append_message("user", task, False)
                
                # For streaming the response, we'll print each token as it comes
                print(f"Response from {agent_name}:")
                response = agent.get_full_response()
                print(response)
                
                user_story = response

def fetch_task(input_path: str, mvp_path: str) -> str:
    """Load a task from a given file path and MVP file"""
    print("Reading input file...")
    task = config.read_file(input_path)
    print("Successfully read input file")
    
    print("Reading MVP file...")
    mvp = config.read_file(mvp_path)
    print("Successfully read MVP file")
    
    return task + "\n\nMVP:\n" + mvp

if __name__ == '__main__':
    app.run(debug=True, threaded=True)