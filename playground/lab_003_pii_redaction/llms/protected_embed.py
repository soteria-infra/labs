import os
import json
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from llms.get_vector_db import get_vector_db
import soteria_sdk
from dotenv import load_dotenv

from llms.cleaner import clean_dirty_json

load_dotenv()

# Configure Soteria SDK
soteria_api_key = os.getenv("SOTERIA_API_KEY")
print(f"DEBUG: Soteria API Key present: {bool(soteria_api_key)}")

if soteria_api_key:
    soteria_sdk.configure(api_key=soteria_api_key, api_base="https://api.soteriainfra.com")
    print("DEBUG: Soteria SDK configured")
else:
    print("WARNING: No Soteria API Key found!")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'json'}

def save_file(file):
    """Save the uploaded file to the temporary folder (for Flask uploads)"""
    ct = datetime.now()
    ts = ct.timestamp()
    filename = str(ts) + "_" + secure_filename(file.filename)
    file_path = os.path.join(TEMP_FOLDER, filename)
    file.save(file_path)
    return file_path

@soteria_sdk.guard_pii_redactor
def scan_pii_with_soteria(prompt: str) -> str:
    """
    Scan content for pii using Soteria SDK.
    This function MUST have a 'prompt' parameter for Soteria to work.
    """
    return prompt

def load_and_process_json(file_path):
    """Load JSON file, scan for pii, and convert to documents"""
    try:
       
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
    
        try:
            if soteria_api_key:
                scanned_content = scan_pii_with_soteria(prompt=raw_content)
            else:
                scanned_content = raw_content
               
        except soteria_sdk.SoteriaValidationError as e:
            raise ValueError(f"PII detected in file content, and redaction/policy failed: {e}")
        except Exception as e:
            scanned_content = raw_content

        cleaned_json = clean_dirty_json(scanned_content)
        try:
            json_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            import re 
            cleaned_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned_json) 
            try: 
                json_data = json.loads(cleaned_content) 
            except json.JSONDecodeError as e2:
                print(f"DEBUG: Still cannot parse after cleaning: {e2}")
                return None

       
        # Convert to documents
        documents = []
       
        if isinstance(json_data, dict):
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            documents.append(Document(
                page_content=content,
                metadata={"source": file_path, "type": "json_object"}
            ))

           
        elif isinstance(json_data, list):
            for i, item in enumerate(json_data):
                if isinstance(item, (dict, list)):
                    content = json.dumps(item, indent=2, ensure_ascii=False)
                else:
                    content = str(item)
                documents.append(Document(
                    page_content=content,
                    metadata={"source": file_path, "item_index": i, "type": "json_array_item"}
                ))
           
        else:
            content = str(json_data)
            documents.append(Document(
                page_content=content,
                metadata={"source": file_path, "type": "json_primitive"}
            ))
            logger.info(f"Created 1 document from JSON primitive")
            print(f"DEBUG: Created 1 document from JSON primitive")
       

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=7500, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)
       
       
        return chunks
       
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        print(f"DEBUG: JSON parse error: {e}")
        return None
    except ValueError as e: 
        logger.error(f"Critical PII redaction issue for {file_path}: {e}")
        print(f"DEBUG: Critical PII redaction issue: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        print(f"DEBUG: Processing error: {e}")
        return None


def embed_file_object(file):
    """Handle embedding for file objects (Flask uploads)"""
    print(f"DEBUG: embed_file_object called with file: {file.filename if hasattr(file, 'filename') else 'unknown'}")
    
    if file.filename != '' and file and allowed_file(file.filename):
        try:
            file_path = save_file(file)
            print(f"DEBUG: File saved to: {file_path}")
            
            chunks = load_and_process_json(file_path)
            
            if chunks is None:
                return {"success": False, "error": "Failed to load and process data"}
            
            print(f"DEBUG: Embedding {len(chunks)} chunks to vector DB...")
            db = get_vector_db()
            db.add_documents(chunks)
            
            # Remove persist() call if it's causing warnings
            try:
                db.persist()
            except:
                pass  # Ignore persistence warnings
                
            os.remove(file_path)
            print(f"DEBUG: File embedded successfully and temp file removed")
            
            return {"success": True, "message": "File embedded successfully"}
        except Exception as e:
            print(f"DEBUG: embed_file_object error: {e}")
            logger.error(f"Error in embed_file_object: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "Invalid file or file type not allowed"}

def embed_file_path(file_path):
    """Handle embedding for file paths (strings)"""
    print(f"DEBUG: embed_file_path called with: {file_path}")
    
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    
    filename = os.path.basename(file_path)
    if not allowed_file(filename):
        return {"success": False, "error": f"File type not allowed. Only JSON files are supported."}
    
    try:
        chunks = load_and_process_json(file_path)
        
        if chunks is None:
            return {"success": False, "error": "Failed to load and process data"}
        
        print(f"DEBUG: Embedding {len(chunks)} chunks to vector DB...")
        db = get_vector_db()
        db.add_documents(chunks)
        
        # Remove persist() call if it's causing warnings
        try:
            db.persist()
        except:
            pass  # Ignore persistence warnings
        
        print(f"DEBUG: File embedded successfully")
        return {"success": True, "message": f"File '{filename}' embedded successfully"}
        
    except Exception as e:
        print(f"DEBUG: embed_file_path error: {e}")
        logger.error(f"Error in embed_file_path: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

def embed(file_or_path):
    """
    Universal embed function that handles both file objects and file paths
    """
    print(f"DEBUG: embed() called with type: {type(file_or_path)}")
    
    if hasattr(file_or_path, 'filename'):
        # It's a file object (like from Flask upload)
        print("DEBUG: Detected file object, calling embed_file_object")
        return embed_file_object(file_or_path)
    elif isinstance(file_or_path, str):
        # It's a file path string
        print("DEBUG: Detected file path string, calling embed_file_path")
        return embed_file_path(file_or_path)
    else:
        error_msg = f"Invalid input type: {type(file_or_path)}, expected file object or file path string"
        print(f"DEBUG: {error_msg}")
        return {"success": False, "error": error_msg}

