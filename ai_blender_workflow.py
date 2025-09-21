#!/usr/bin/env python3
import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv
from subprocess import check_output
from FloorplanToBlenderLib import (
    IO,
    config,
    const,
    execution,
    dialog,
    floorplan,
)

# Load environment variables
load_dotenv()

"""
AI + Blender Workflow
1. Take original PNG image
2. Process with AI to clean it
3. Use Blender to create .blend file from AI-processed image
"""

def preprocess_image_with_ai(image_path, output_path):
    """Use OpenAI to preprocess the floorplan image"""
    print(f"🤖 Preprocessing image with AI: {image_path}")
    
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found!")
        return image_path
    
    openai_client = OpenAI(api_key=api_key)
    
    try:
        print("📡 Sending request to OpenAI...")
        
        # Use gpt-image-1 with images/edits endpoint
        edit_prompt = """Remove all furniture, leave only walls and doors. Make walls thick black lines on white background. Remove all text, labels, and decorative elements. Fill windows to show continuous walls."""

        response = openai_client.images.edit(
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

def create_blender_project_from_ai(ai_processed_image, output_blend_path):
    """Create Blender project from AI-processed image"""
    
    # Update config to use AI-processed image
    config_path = "./Configs/default.ini"
    if os.path.exists(config_path):
        import configparser
        conf = configparser.ConfigParser()
        conf.read(config_path)
        
        if 'IMAGE' not in conf:
            conf.add_section('IMAGE')
        conf.set('IMAGE', 'image_path', f'"{ai_processed_image}"')
        
        with open(config_path, 'w') as configfile:
            conf.write(configfile)
    
    # Generate data files using AI-processed image
    print("🔄 Generating data files from AI-processed image...")
    fp = floorplan.new_floorplan(config_path)
    IO.clean_data_folder("Data")
    data_path = execution.simple_single(fp)
    
    # Set up Blender paths
    blender_install_path = "/Applications/Blender.app/Contents/MacOS/Blender"
    blender_script_path = "Blender/floorplan_to_3dObject_in_blender.py"
    program_path = os.getcwd() + "/"
    
    # Create target directory
    target_folder = "/Target/"
    if not os.path.exists("." + target_folder):
        os.makedirs("." + target_folder)
    
    print(f"🎨 Creating Blender project with data from: {data_path}")
    print(f"📁 Output will be: {output_blend_path}")
    
    # Run Blender to create .blend file
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
        
    except Exception as e:
        print(f"❌ Blender execution failed: {e}")
        return None

def main():
    """Main AI + Blender workflow"""
    dialog.figlet()
    
    print("🤖🎨 ----- AI + BLENDER WORKFLOW -----")
    print("This combines AI preprocessing with original Blender functionality!")
    print("✨ Process:")
    print("  1. Take PNG image")
    print("  2. AI cleans and processes image")
    print("  3. Blender creates .blend file")
    print()
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not found in .env file!")
        return
    
    # Use the specified image
    original_image = "Images/Examples/example5.png"
    
    # Check if image exists
    if not os.path.exists(original_image):
        print(f"❌ Error: Image {original_image} not found!")
        return
    
    print(f"📷 Using image: {original_image}")
    
    # Step 1: AI preprocessing
    processed_image_dir = "Images/Processed"
    os.makedirs(processed_image_dir, exist_ok=True)
    
    image_name = os.path.basename(original_image)
    processed_image_path = os.path.join(processed_image_dir, f"ai_processed_{image_name}")
    
    final_image_path = preprocess_image_with_ai(original_image, processed_image_path)
    
    # Step 2: Create Blender project
    output_blend = "Target/example5_ai_blender.blend"
    
    result_path = create_blender_project_from_ai(final_image_path, output_blend)
    
    if result_path:
        print(f"\n🎉 Success! AI + Blender workflow completed!")
        print(f"📁 Blender project: {result_path}")
        print("\n✨ FloorplanToBlender3d - AI + Blender Workflow")
    else:
        print(f"\n❌ Workflow failed!")

if __name__ == "__main__":
    main()
