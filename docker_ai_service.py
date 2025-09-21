#!/usr/bin/env python3
import os
import json
import base64
import tempfile
import zipfile
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv
from subprocess import check_output, CalledProcessError
import uuid
import shutil

# Import našich knižníc
from FloorplanToBlenderLib import (
    IO,
    config,
    execution,
    floorplan,
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Konfigurácia
UPLOAD_FOLDER = '/tmp/uploads'
OUTPUT_FOLDER = '/tmp/outputs'
BLENDER_PATH = os.getenv('BLENDER_PATH', '/Applications/Blender.app/Contents/MacOS/Blender')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Vytvorenie priečinkov
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class AIFloorplanProcessor:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment variables!")
        
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
    def preprocess_image_with_ai(self, image_path, output_path):
        """Use OpenAI to preprocess the floorplan image"""
        print(f"🤖 Preprocessing image with AI: {image_path}")
        
        try:
            print("📡 Sending request to OpenAI...")
            
            # Use gpt-image-1 with images/edits endpoint
            edit_prompt = """Remove all furniture, leave only walls and doors. Make walls thick black lines on white background. Remove all text, labels, and decorative elements. Fill windows to show continuous walls."""

            response = self.openai_client.images.edit(
                model="gpt-image-1",
                image=open(image_path, "rb"),
                prompt=edit_prompt,
            )
            
            # Get the processed image
            processed_image_b64 = response.data[0].b64_json
            processed_image_bytes = base64.b64decode(processed_image_b64)
            
            # Save the processed image
            with open(output_path, "wb") as f:
                f.write(processed_image_bytes)
            
            print(f"✅ AI preprocessing completed! Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ AI preprocessing failed: {e}")
            print("🔄 Using original image instead...")
            return image_path

    def create_blender_project_from_ai(self, ai_processed_image, output_blend_path, data_folder):
        """Create Blender project from AI-processed image using working approach"""
        
        print("🔄 Generating data files from AI-processed image...")
        
        # Use the working approach from ai_blender_workflow.py
        import configparser
        conf = configparser.ConfigParser()
        conf.read("./Configs/default.ini")
        
        if 'IMAGE' not in conf:
            conf.add_section('IMAGE')
        conf.set('IMAGE', 'image_path', f'"{ai_processed_image}"')
        
        with open("./Configs/default.ini", 'w') as configfile:
            conf.write(configfile)
        
        # Generate data files using AI-processed image
        fp = floorplan.new_floorplan("./Configs/default.ini")
        IO.clean_data_folder("Data")
        data_path = execution.simple_single(fp)
        
        # Set up Blender paths using the working approach
        blender_install_path = BLENDER_PATH
        blender_script_path = "Blender/floorplan_to_3dObject_in_blender.py"
        program_path = os.getcwd() + "/"
        
        # Create target directory
        target_folder = os.path.dirname(output_blend_path)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
        
        print(f"🎨 Creating Blender project with data from: {data_path}")
        print(f"📁 Output will be: {output_blend_path}")
        
        # Run Blender using the exact working approach from ai_blender_workflow.py
        try:
            check_output([
                blender_install_path,
                "-noaudio",  # macOS fix
                "--background",
                "--python",
                blender_script_path,
                program_path,  # Send this as parameter to script
                output_blend_path,
                data_path
            ])
            
            print(f"✅ Blender project created at: {program_path + output_blend_path}")
            return program_path + output_blend_path
            
        except CalledProcessError as e:
            print(f"❌ Blender execution failed: {e}")
            return None

    def export_blend_to_gltf(self, blend_path, gltf_path):
        """Export Blender file to glTF format"""
        
        blender_export_script = "Blender/blender_export_any.py"
        
        try:
            print(f"🔄 Exporting {blend_path} to glTF...")
            
            check_output([
                BLENDER_PATH,
                "--background",
                "--python",
                blender_export_script,
                "--",
                blend_path,
                ".gltf",
                gltf_path
            ])
            
            print(f"✅ glTF export completed: {gltf_path}")
            return gltf_path
            
        except CalledProcessError as e:
            print(f"❌ glTF export failed: {e}")
            return None

    def export_blend_to_glb(self, blend_path, glb_path):
        """Export Blender file to GLB format (binary glTF)"""
        
        blender_export_script = "Blender/blender_export_any.py"
        
        try:
            print(f"🔄 Exporting {blend_path} to GLB...")
            
            check_output([
                BLENDER_PATH,
                "--background",
                "--python",
                blender_export_script,
                "--",
                blend_path,
                ".glb",
                glb_path
            ])
            
            print(f"✅ GLB export completed: {glb_path}")
            return glb_path
            
        except CalledProcessError as e:
            print(f"❌ GLB export failed: {e}")
            return None

# Initialize processor
try:
    processor = AIFloorplanProcessor()
    print("🤖 OpenAI configured: True")
except Exception as e:
    processor = None
    print(f"❌ OpenAI configuration failed: {e}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'blender_path': BLENDER_PATH,
        'openai_configured': processor is not None
    })

@app.route('/process-floorplan', methods=['POST'])
def process_floorplan():
    """
    Main endpoint: Upload image → AI processing → glTF generation
    """
    
    if not processor:
        return jsonify({'error': 'OpenAI not configured'}), 500
    
    # Check if file is present
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({'error': 'Only PNG, JPG, JPEG files allowed'}), 400
    
    try:
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create working directory
        work_dir = os.path.join(OUTPUT_FOLDER, f"{timestamp}_{request_id}")
        os.makedirs(work_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        original_path = os.path.join(work_dir, f"original_{filename}")
        file.save(original_path)
        
        print(f"📁 Processing request {request_id}")
        print(f"📷 Original image: {original_path}")
        
        # Step 1: AI preprocessing
        ai_processed_path = os.path.join(work_dir, f"ai_processed_{filename}")
        final_image_path = processor.preprocess_image_with_ai(original_path, ai_processed_path)
        
        # Step 2: Create Blender project
        data_folder = os.path.join(work_dir, "data")
        os.makedirs(data_folder, exist_ok=True)
        
        blend_path = os.path.join(work_dir, f"model_{request_id}.blend")
        blend_result = processor.create_blender_project_from_ai(final_image_path, blend_path, data_folder)
        
        if not blend_result:
            return jsonify({'error': 'Blender project creation failed'}), 500
        
        # Step 3: Export to glTF
        gltf_path = os.path.join(work_dir, f"model_{request_id}.gltf")
        gltf_result = processor.export_blend_to_gltf(blend_path, gltf_path)
        
        if not gltf_result:
            return jsonify({'error': 'glTF export failed'}), 500
        
        # Step 4: Create ZIP package with results
        zip_path = os.path.join(work_dir, f"floorplan_3d_{request_id}.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add glTF files
            if os.path.exists(gltf_path):
                zipf.write(gltf_path, f"model_{request_id}.gltf")
            
            bin_path = gltf_path.replace('.gltf', '.bin')
            if os.path.exists(bin_path):
                zipf.write(bin_path, f"model_{request_id}.bin")
            
            # Add AI processed image
            if os.path.exists(ai_processed_path):
                zipf.write(ai_processed_path, f"ai_processed_{filename}")
            
            # Add original image
            zipf.write(original_path, f"original_{filename}")
        
        print(f"✅ Processing completed for request {request_id}")
        
        # Return the ZIP file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"floorplan_3d_{timestamp}.zip",
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/test-glb-export', methods=['GET'])
def test_glb_export():
    """Test endpoint to verify GLB export works with existing .blend file"""
    
    # Use existing .blend file
    existing_blend = "Target/example5_ai_blender.blend"
    
    if not os.path.exists(existing_blend):
        return jsonify({
            'success': False,
            'error': 'Test .blend file not found'
        }), 404
    
    try:
        # Create test output
        test_glb = f"/tmp/test_export_glb_{int(time.time())}.glb"
        
        # Export to GLB
        result = processor.export_blend_to_glb(existing_blend, test_glb)
        
        if result and os.path.exists(test_glb):
            # Read GLB and encode to Base64
            with open(test_glb, 'rb') as f:
                glb_data = f.read()
            
            glb_base64 = base64.b64encode(glb_data).decode('utf-8')
            
            return jsonify({
                'success': True,
                'model': glb_base64,
                'format': 'glb',
                'metadata': {
                    'test_file': 'example5_ai_blender.blend',
                    'file_size_bytes': len(glb_data),
                    'base64_size_chars': len(glb_base64),
                    'timestamp': datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'GLB export failed'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test GLB export failed: {str(e)}'
        }), 500

@app.route('/test-gltf-export', methods=['GET'])
def test_gltf_export():
    """Test endpoint to verify glTF export works with existing .blend file"""
    
    # Use existing .blend file
    existing_blend = "Target/example4_ai_blender.blend"
    
    if not os.path.exists(existing_blend):
        return jsonify({'error': 'Test .blend file not found'}), 404
    
    try:
        # Create test output
        test_gltf = f"/tmp/test_export_{int(time.time())}.gltf"
        
        # Export to glTF
        result = processor.export_blend_to_gltf(existing_blend, test_gltf)
        
        if result and os.path.exists(test_gltf):
            return send_file(
                test_gltf,
                as_attachment=True,
                download_name="test_export.gltf",
                mimetype='model/gltf+json'
            )
        else:
            return jsonify({'error': 'glTF export failed'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Test export failed: {str(e)}'}), 500

@app.route('/process-glb', methods=['POST'])
def process_glb():
    """
    Main GLB endpoint: Upload image → AI processing → GLB generation → Base64 response
    Returns GLB as Base64 encoded string with metadata
    """
    
    if not processor:
        return jsonify({
            'success': False,
            'error': 'OpenAI not configured'
        }), 500
    
    # Check if file is present
    if 'image' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No image file provided'
        }), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({
            'success': False,
            'error': 'Only PNG, JPG, JPEG files allowed'
        }), 400
    
    try:
        # Generate unique ID for this request
        request_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create working directory in Target folder (where Blender works)
        work_dir = os.path.join("Target", f"glb_{timestamp}_{request_id}")
        os.makedirs(work_dir, exist_ok=True)
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        original_path = os.path.join(work_dir, f"original_{filename}")
        file.save(original_path)
        
        print(f"📁 Processing GLB request {request_id}")
        print(f"📷 Original image: {original_path}")
        
        # Step 1: AI preprocessing
        ai_processed_path = os.path.join(work_dir, f"ai_processed_{filename}")
        final_image_path = processor.preprocess_image_with_ai(original_path, ai_processed_path)
        
        # Step 2: Create Blender project
        data_folder = os.path.join(work_dir, "data")
        os.makedirs(data_folder, exist_ok=True)
        
        blend_path = os.path.join(work_dir, f"model_{request_id}.blend")
        blend_result = processor.create_blender_project_from_ai(final_image_path, blend_path, data_folder)
        
        if not blend_result:
            return jsonify({
                'success': False,
                'error': 'Blender project creation failed'
            }), 500
        
        # Step 3: Export to GLB
        glb_path = os.path.join(work_dir, f"model_{request_id}.glb")
        glb_result = processor.export_blend_to_glb(blend_path, glb_path)
        
        if not glb_result or not os.path.exists(glb_path):
            return jsonify({
                'success': False,
                'error': 'GLB export failed'
            }), 500
        
        # Step 4: Read GLB file and encode to Base64
        with open(glb_path, 'rb') as f:
            glb_data = f.read()
        
        glb_base64 = base64.b64encode(glb_data).decode('utf-8')
        
        # Step 5: Extract metadata from data files
        metadata = {
            'rooms': 0,
            'walls': 0,
            'area': 0,
            'dimensions': {'width': 0, 'height': 0, 'depth': 2.5}
        }
        
        # Try to read metadata from generated files
        try:
            room_verts_file = os.path.join("Data", "0", "room_verts.txt")
            if os.path.exists(room_verts_file):
                with open(room_verts_file, 'r') as f:
                    room_data = json.loads(f.read())
                    metadata['rooms'] = len(room_data) if isinstance(room_data, list) else 0
            
            wall_verts_file = os.path.join("Data", "0", "wall_vertical_verts.txt")
            if os.path.exists(wall_verts_file):
                with open(wall_verts_file, 'r') as f:
                    wall_data = json.loads(f.read())
                    metadata['walls'] = len(wall_data) if isinstance(wall_data, list) else 0
                    
        except Exception as e:
            print(f"⚠️ Metadata extraction failed: {e}")
        
        print(f"✅ GLB processing completed for request {request_id}")
        print(f"📊 GLB size: {len(glb_data)} bytes")
        print(f"📊 Base64 size: {len(glb_base64)} characters")
        
        # Return GLB as Base64 with metadata
        return jsonify({
            'success': True,
            'model': glb_base64,
            'format': 'glb',
            'metadata': {
                'request_id': request_id,
                'timestamp': timestamp,
                'original_filename': filename,
                'file_size_bytes': len(glb_data),
                'base64_size_chars': len(glb_base64),
                'rooms': metadata['rooms'],
                'walls': metadata['walls'],
                'area': metadata['area'],
                'dimensions': metadata['dimensions']
            }
        })
        
    except Exception as e:
        print(f"❌ GLB processing error: {e}")
        return jsonify({
            'success': False,
            'error': f'Processing failed: {str(e)}'
        }), 500

@app.route('/process-simple', methods=['POST'])
def process_simple():
    """
    Simplified endpoint: Returns only glTF file
    """
    
    if not processor:
        return jsonify({'error': 'OpenAI not configured'}), 500
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        request_id = str(uuid.uuid4())[:8]
        work_dir = os.path.join(OUTPUT_FOLDER, f"simple_{request_id}")
        os.makedirs(work_dir, exist_ok=True)
        
        # Save and process
        filename = secure_filename(file.filename)
        original_path = os.path.join(work_dir, filename)
        file.save(original_path)
        
        # AI processing
        ai_processed_path = os.path.join(work_dir, f"ai_{filename}")
        final_image_path = processor.preprocess_image_with_ai(original_path, ai_processed_path)
        
        # Blender processing
        data_folder = os.path.join(work_dir, "data")
        os.makedirs(data_folder, exist_ok=True)
        
        blend_path = os.path.join(work_dir, "model.blend")
        blend_result = processor.create_blender_project_from_ai(final_image_path, blend_path, data_folder)
        
        if not blend_result:
            return jsonify({'error': 'Blender processing failed'}), 500
        
        # glTF export
        gltf_path = os.path.join(work_dir, "model.gltf")
        gltf_result = processor.export_blend_to_gltf(blend_path, gltf_path)
        
        if not gltf_result:
            return jsonify({'error': 'glTF export failed'}), 500
        
        # Return just the glTF file
        return send_file(
            gltf_path,
            as_attachment=True,
            download_name=f"floorplan_{request_id}.gltf",
            mimetype='model/gltf+json'
        )
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting AI-Enhanced Floorplan to 3D Service...")
    print(f"🔧 Blender executable: {BLENDER_PATH}")
    print(f"🤖 OpenAI configured: {processor is not None}")
    
    # Try different ports if 5000 is occupied
    port = int(os.getenv('PORT', 5000))
    for attempt_port in range(port, port + 10):
        try:
            app.run(host='0.0.0.0', port=attempt_port, debug=False)
            break
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"Port {attempt_port} is in use, trying {attempt_port + 1}...")
                continue
            else:
                raise
