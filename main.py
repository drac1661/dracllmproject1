from fastapi import FastAPI, HTTPException, Query
import os
import subprocess
import re
import json
from typing import Optional, List
from dotenv import load_dotenv
import requests
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

from tasks import (
    install_and_run_datagen,
    format_file,
    count_wednesdays,
    sort_contacts,
    recent_logs,
    create_index,
    extract_email,
    extract_credit_card,
    find_similar_comments,
    calculate_gold_sales,
    # Import additional Phase B task functions here
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['GET','POST'],
    allow_headers=['*']
)

DATA_DIR = "data"
api_key= os.getenv("AIPROXY_TOKEN")
host = os.getenv("host")  # Replace with actual LLM endpoint

# Task mapping
task_mapping = {
    "A1": install_and_run_datagen,
    "A2": format_file,
    "A3": count_wednesdays,
    "A4": sort_contacts,
    "A5": recent_logs,
    "A6": create_index,
    "A7": extract_email,
    "A8": extract_credit_card,
    "A9": find_similar_comments,
    "A10": calculate_gold_sales,
    # Add Phase B task mappings here
}


#validate input path
def validate_input_path(path: str):
    """Ensure the input path exists and is inside data."""
    abs_path = os.path.abspath(path)
    data_dir_abs = os.path.abspath(DATA_DIR)

    # Check if the path is outside the DATA_DIR
    if not abs_path.startswith(data_dir_abs):
        raise HTTPException(status_code=400, detail="Access to paths outside data is restricted")

    # Check if the path is a file deletion attempt
    if os.path.exists(abs_path) and os.path.basename(abs_path).lower() in ["rm", "delete"]:
        raise HTTPException(status_code=400, detail="File deletion is not allowed")

    # Check if the file exists
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=400, detail=f"Input file does not exist: {path}")

    # Check if the path is a directory and raise an error if it is
    if os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="Access to directories is restricted")



#validate output path
def validate_output_path(path: str):
    """Ensure the output path is inside data but does not need to exist."""
    abs_path = os.path.abspath(path)
 
    if os.path.exists(abs_path) and os.path.basename(abs_path).lower() in ["rm", "delete"]:
        raise HTTPException(status_code=400, detail="File deletion is not allowed")
    
    if not abs_path.startswith(os.path.abspath(DATA_DIR)):
        raise HTTPException(status_code=400, detail="Access to paths outside data is restricted")
    
    output_dir = os.path.dirname(abs_path)
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=400, detail=f"Output directory does not exist: {output_dir}")
    
    
    

# call the LLM
def call_llm(task_description: str) -> dict:
    """Call the LLM to parse the task description."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",  # Ensure this matches the supported model
        "messages": [
            {"role": "system", "content": """You are an automation agent that parses plain-English task descriptions and maps them to predefined tasks (A1 to A10). Given a task description, output a JSON object with a "tasks" key, which contains a list of tasks to execute. Each task should include a "name" corresponding to the task identifier (e.g., "A2") and a "params" object containing the required parameters. so Identify which predefined task (A1 to A10) matches this user input and respond with only the task code.Classify the following task into one of these categories:
                                A1: generate_data
                                A2: format_file
                                A3: count_dates
                                A4: sort_contact_json
                                A5: process_logs
                                A6: find_all_markdown
                                A7: extract_email
                                A8: credit_card_process_image
                                A9: find_similar_comments
                                A10: query_database
            return the required params  and in params when the name in A1 then give "email" key and 
            "output_file" key is "./data" and  when the name is A3 then give the "input_file" key and "output_file" key and "day" key and when the name is A10 then give the "input_file" key and "output_file" key and "ticket_type" otherwise give only "input_file" key and "output_file" key and add . as a prefix in "input_file" key and "output_file" for all names(that is from A2 to A10) ".
                                
                                """
                                },
            
            {"role": "user", "content": f"{task_description}"},
        ],
    }

    try:
        response = requests.post(host, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with LLM: {str(e)}")



# Post request 
@app.post("/run")
def run_task(task: str = Query(..., description="Plain English task description")):
    """Processes the task using an LLM and executes the corresponding action."""
    try:
        # Call the LLM to parse the task
        llm_response = call_llm(task)
        print("Raw LLM response:", llm_response)
        
        completion = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(completion)
        if not completion.strip():
            raise HTTPException(status_code=500, detail="Empty response from LLM")
        
        completion = re.sub(r"^```json\n|\n```$", "", completion.strip())
        
        try:
            instructions = json.loads(completion)
            print(instructions)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Invalid JSON: {str(e)}")

        
        results = []
        for instr in instructions.get("tasks", []):
            task_name = instr.get("name")
            params = instr.get("params", {})

            if task_name in task_mapping:
                func = task_mapping[task_name]
                
            if 'input_file' in params:
                validate_input_path(params["input_file"])   
            if 'output_file' in params:
                validate_input_path(params["output_file"])
                
            print(params)
            result = func(**params)
            
            results.append({task_name: result})
            print(result)
        
        return {"status": "success", "results": results}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON response from LLM")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#Get request
@app.get("/read")
def read_file(path: str = Query(..., description="File path")):
    """Reads and returns the content of the specified file."""
    # validate_path(path)
    path='.'+path
    if (path):
        validate_output_path(path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(path, "r") as f:
        return {"content": f.read()}