import json
import numpy as np
import os
import base64
from openai import OpenAI
from dotenv import load_dotenv
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
AI-Enhanced OBJ Generator
This script uses OpenAI to preprocess floorplan images before generating 3D models.
"""

class AIEnhancedOBJGenerator:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []
        self.vertex_count = 1  # OBJ files start vertex indices at 1
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables!")
        
        self.openai_client = OpenAI(api_key=api_key)
        
    def preprocess_image_with_ai(self, image_path, output_path):
        """
        Use OpenAI to preprocess the floorplan image:
        - Remove furniture and windows
        - Keep only walls as black lines
        """
        print(f"🤖 Preprocessing image with AI: {image_path}")
        
        # Create the prompt for vision model
        prompt = """Please analyze this floorplan image and create a cleaned version with these specifications:
- Remove all furniture, decorations, text, and labels
- Remove windows and doors - fill these openings to show continuous walls
- Keep only the structural walls as clean black lines
- Use white background
- Make walls thick and clearly visible in black color
- Ensure all wall connections are continuous without gaps"""
        
        try:
            print("📡 Sending request to OpenAI...")
            
            # Read image as base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Use gpt-image-1 with images/edits endpoint as recommended
            edit_prompt = """Remove all furniture, leave only walls and doors. Make walls thick black lines on white background. Remove all text, labels, and decorative elements. Fill windows to show continuous walls."""

            # Use the correct gpt-image-1 model with image edit
            response = self.openai_client.images.edit(
                model="gpt-image-1",
                image=open(image_path, "rb"),
                prompt=edit_prompt,
            )
            
            # Get the processed image
            processed_image_b64 = response.data[0].b64_json
            processed_image_bytes = base64.b64decode(processed_image_b64)
            print(f"✨ AI successfully edited the image with gpt-image-1!")
            
            # Save the processed image
            with open(output_path, "wb") as f:
                f.write(processed_image_bytes)
            
            print(f"✅ AI preprocessing completed! Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ AI preprocessing failed: {e}")
            print("🔄 Using original image instead...")
            return image_path
    
    def add_vertices(self, verts):
        """Add vertices to the OBJ and return starting index"""
        start_index = self.vertex_count
        for vert in verts:
            self.vertices.append(f"v {vert[0]:.6f} {vert[1]:.6f} {vert[2]:.6f}")
            self.vertex_count += 1
        return start_index
    
    def add_face(self, face_indices, material_name="default"):
        """Add a face to the OBJ"""
        face_str = "f " + " ".join([str(i) for i in face_indices])
        self.faces.append(f"usemtl {material_name}")
        self.faces.append(face_str)
    
    def add_material(self, name, color=(0.8, 0.8, 0.8)):
        """Add a material definition"""
        if name not in [m['name'] for m in self.materials]:
            self.materials.append({
                'name': name,
                'color': color
            })
    
    def create_mesh_from_data(self, verts, faces, material_name="default", color=(0.8, 0.8, 0.8), offset_z=0.0):
        """Create mesh from vertex and face data"""
        if not verts or not faces:
            return
            
        # Add material
        self.add_material(material_name, color)
        
        # Offset vertices in Z if needed
        if offset_z != 0.0:
            verts = [[v[0], v[1], v[2] + offset_z] for v in verts]
        
        # Add vertices and get starting index
        start_index = self.add_vertices(verts)
        
        # Add faces
        for face in faces:
            if isinstance(face, list) and len(face) >= 3:
                # Convert to 1-based indices and add to start_index
                face_indices = [i + start_index for i in face]
                self.add_face(face_indices, material_name)
    
    def save_obj(self, obj_path):
        """Save OBJ file"""
        with open(obj_path, 'w') as f:
            f.write("# Generated by Floor3D - AI-Enhanced Direct OBJ Export\n")
            f.write(f"mtllib {os.path.basename(obj_path).replace('.obj', '.mtl')}\n\n")
            
            # Write vertices
            for vertex in self.vertices:
                f.write(vertex + "\n")
            f.write("\n")
            
            # Write faces
            for face in self.faces:
                f.write(face + "\n")
    
    def save_mtl(self, mtl_path):
        """Save MTL material file"""
        with open(mtl_path, 'w') as f:
            f.write("# Generated by Floor3D - AI-Enhanced Direct OBJ Export\n\n")
            
            for material in self.materials:
                f.write(f"newmtl {material['name']}\n")
                f.write("Ns 225.000000\n")
                f.write("Ka 1.000000 1.000000 1.000000\n")
                color = material['color']
                f.write(f"Kd {color[0]:.6f} {color[1]:.6f} {color[2]:.6f}\n")
                f.write(f"Ks 0.500000 0.500000 0.500000\n")
                f.write("Ke 0.000000 0.000000 0.000000\n")
                f.write("Ni 1.450000\n")
                f.write("d 1.000000\n")
                f.write("illum 2\n\n")

def read_from_file(file_path):
    """Read JSON data from file"""
    try:
        with open(file_path + ".txt", "r") as f:
            return json.loads(f.read())
    except:
        return None

def create_3d_model_with_ai(original_image_path, output_path):
    """Create 3D model with AI preprocessing"""
    
    obj_gen = AIEnhancedOBJGenerator()
    
    # Step 1: Preprocess image with AI
    processed_image_dir = "Images/Processed"
    os.makedirs(processed_image_dir, exist_ok=True)
    
    image_name = os.path.basename(original_image_path)
    processed_image_path = os.path.join(processed_image_dir, f"ai_processed_{image_name}")
    
    final_image_path = obj_gen.preprocess_image_with_ai(original_image_path, processed_image_path)
    
    # Step 2: Update config to use processed image
    config_path = "./Configs/default.ini"
    if os.path.exists(config_path):
        import configparser
        conf = configparser.ConfigParser()
        conf.read(config_path)
        
        if 'IMAGE' not in conf:
            conf.add_section('IMAGE')
        conf.set('IMAGE', 'image_path', f'"{final_image_path}"')
        
        with open(config_path, 'w') as configfile:
            conf.write(configfile)
    
    # Step 3: Generate data files using processed image
    print("🔄 Generating data files from processed image...")
    fp = floorplan.new_floorplan(config_path)
    IO.clean_data_folder("Data")
    data_path = execution.simple_single(fp)
    
    # Step 4: Read transform data
    transform_file = os.path.join(data_path, "transform.txt")
    if os.path.exists(transform_file):
        with open(transform_file, 'r') as f:
            transform = json.loads(f.read())
        origin_path = transform.get("origin_path", data_path)
        if not os.path.isabs(origin_path):
            origin_path = os.path.join(".", origin_path)
    else:
        origin_path = data_path
    
    print(f"📁 Reading data from: {origin_path}")
    
    # Step 5: Create Floor (lowest level)
    floor_verts = read_from_file(os.path.join(origin_path, "floor_verts"))
    floor_faces = read_from_file(os.path.join(origin_path, "floor_faces"))
    
    if floor_verts and floor_faces:
        print(f"🏠 Adding floor with {len(floor_verts)} vertices")
        obj_gen.create_mesh_from_data(
            floor_verts, [floor_faces], 
            "floor", (0.7, 0.7, 0.7), 
            offset_z=-0.01  # Floor slightly down
        )
    
    # Step 6: Create Rooms (slightly above floor)
    room_verts = read_from_file(os.path.join(origin_path, "room_verts"))
    room_faces = read_from_file(os.path.join(origin_path, "room_faces"))
    
    if room_verts and room_faces:
        print(f"🏠 Adding {len(room_verts)} rooms")
        for i, (rverts, rfaces) in enumerate(zip(room_verts, room_faces)):
            obj_gen.create_mesh_from_data(
                rverts, rfaces, 
                f"room_{i}", (0.9, 0.9, 0.8), 
                offset_z=0.005  # Rooms slightly up from floor
            )
    
    # Step 7: Create Walls
    # Vertical walls
    wall_v_verts = read_from_file(os.path.join(origin_path, "wall_vertical_verts"))
    wall_v_faces = read_from_file(os.path.join(origin_path, "wall_vertical_faces"))
    
    if wall_v_verts and wall_v_faces:
        print(f"🧱 Adding {len(wall_v_verts)} vertical wall groups")
        for i, walls in enumerate(wall_v_verts):
            for j, wall in enumerate(walls):
                obj_gen.create_mesh_from_data(
                    wall, wall_v_faces, 
                    "wall", (0.9, 0.9, 0.9)
                )
    
    # Horizontal walls
    wall_h_verts = read_from_file(os.path.join(origin_path, "wall_horizontal_verts"))
    wall_h_faces = read_from_file(os.path.join(origin_path, "wall_horizontal_faces"))
    
    if wall_h_verts and wall_h_faces:
        print(f"🧱 Adding {len(wall_h_verts)} horizontal walls")
        for i, (wverts, wfaces) in enumerate(zip(wall_h_verts, wall_h_faces)):
            obj_gen.create_mesh_from_data(
                wverts, wfaces, 
                "wall", (0.9, 0.9, 0.9)
            )
    
    print("⏭️  Skipping windows and doors for cleaner model")
    
    # Step 8: Save files
    obj_path = output_path
    mtl_path = output_path.replace('.obj', '.mtl')
    
    obj_gen.save_obj(obj_path)
    obj_gen.save_mtl(mtl_path)
    
    print(f"✅ AI-Enhanced 3D Model created at: {obj_path}")
    print(f"✅ Materials created at: {mtl_path}")
    print(f"📊 Total vertices: {obj_gen.vertex_count - 1}")
    print(f"📊 Total materials: {len(obj_gen.materials)}")
    
    return obj_path

def main():
    """Main function - AI-enhanced 3D model generation"""
    dialog.figlet()
    
    print("🤖 ----- AI-ENHANCED 3D MODEL GENERATOR -----")
    print("This version uses OpenAI to preprocess floorplan images!")
    print("✨ Features:")
    print("  • Removes furniture automatically")
    print("  • Cleans up windows and doors")
    print("  • Enhances wall detection")
    print("  • No Blender required!")
    print()
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not found in .env file!")
        print("Please add your OpenAI API key to the .env file:")
        print("OPENAI_API_KEY=your_api_key_here")
        return
    
    # Get image path
    image_path = input(f"Enter path to floorplan image [default = Images/Examples/podorys1221.png]: ")
    if not image_path:
        image_path = "Images/Examples/podorys1221.png"
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Error: Image {image_path} not found!")
        return
    
    # Get output path
    output_path = input("Enter output path for OBJ file [default = Target/ai_enhanced.obj]: ")
    if not output_path:
        output_path = "Target/ai_enhanced.obj"
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("\n🚀 Starting AI-enhanced processing...")
    
    try:
        # Create 3D model with AI preprocessing
        result_path = create_3d_model_with_ai(image_path, output_path)
        
        print(f"\n🎉 Success! AI-Enhanced 3D model created!")
        print(f"📁 Location: {result_path}")
        print(f"🌐 View at: http://localhost:8080/simple_viewer.html")
        print("\n✨ Floor3D - AI-Enhanced (No Blender Required)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your OpenAI API key and internet connection.")

if __name__ == "__main__":
    main()
