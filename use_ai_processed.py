import json
import numpy as np
import os
from FloorplanToBlenderLib import (
    IO,
    config,
    const,
    execution,
    dialog,
    floorplan,
)

"""
Use AI-Processed Images for 3D Generation
This script uses the already AI-processed images to generate 3D models.
"""

class OBJGenerator:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []
        self.vertex_count = 1
        
    def add_vertices(self, verts):
        start_index = self.vertex_count
        for vert in verts:
            self.vertices.append(f"v {vert[0]:.6f} {vert[1]:.6f} {vert[2]:.6f}")
            self.vertex_count += 1
        return start_index
    
    def add_face(self, face_indices, material_name="default"):
        face_str = "f " + " ".join([str(i) for i in face_indices])
        self.faces.append(f"usemtl {material_name}")
        self.faces.append(face_str)
    
    def add_material(self, name, color=(0.8, 0.8, 0.8)):
        if name not in [m['name'] for m in self.materials]:
            self.materials.append({'name': name, 'color': color})
    
    def create_mesh_from_data(self, verts, faces, material_name="default", color=(0.8, 0.8, 0.8), offset_z=0.0):
        if not verts or not faces:
            return
            
        self.add_material(material_name, color)
        
        if offset_z != 0.0:
            verts = [[v[0], v[1], v[2] + offset_z] for v in verts]
        
        start_index = self.add_vertices(verts)
        
        for face in faces:
            if isinstance(face, list) and len(face) >= 3:
                face_indices = [i + start_index for i in face]
                self.add_face(face_indices, material_name)
    
    def save_obj(self, obj_path):
        with open(obj_path, 'w') as f:
            f.write("# Generated from AI-Processed Floorplan\n")
            f.write(f"mtllib {os.path.basename(obj_path).replace('.obj', '.mtl')}\n\n")
            
            for vertex in self.vertices:
                f.write(vertex + "\n")
            f.write("\n")
            
            for face in self.faces:
                f.write(face + "\n")
    
    def save_mtl(self, mtl_path):
        with open(mtl_path, 'w') as f:
            f.write("# Generated from AI-Processed Floorplan\n\n")
            
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
    try:
        with open(file_path + ".txt", "r") as f:
            return json.loads(f.read())
    except:
        return None

def create_3d_from_ai_processed(ai_image_path, output_path):
    """Create 3D model from AI-processed image"""
    
    obj_gen = OBJGenerator()
    
    print(f"📁 Using AI-processed image: {ai_image_path}")
    
    # Update config to use AI-processed image
    config_path = "./Configs/default.ini"
    if os.path.exists(config_path):
        import configparser
        conf = configparser.ConfigParser()
        conf.read(config_path)
        
        if 'IMAGE' not in conf:
            conf.add_section('IMAGE')
        conf.set('IMAGE', 'image_path', f'"{ai_image_path}"')
        
        with open(config_path, 'w') as configfile:
            conf.write(configfile)
    
    # Generate data files using AI-processed image
    print("🔄 Generating data files from AI-processed image...")
    fp = floorplan.new_floorplan(config_path)
    IO.clean_data_folder("Data")
    data_path = execution.simple_single(fp)
    
    # Read transform data
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
    
    # Create Floor
    floor_verts = read_from_file(os.path.join(origin_path, "floor_verts"))
    floor_faces = read_from_file(os.path.join(origin_path, "floor_faces"))
    
    if floor_verts and floor_faces:
        print(f"🏠 Adding floor with {len(floor_verts)} vertices")
        obj_gen.create_mesh_from_data(
            floor_verts, [floor_faces], 
            "floor", (0.7, 0.7, 0.7), 
            offset_z=-0.01
        )
    
    # Create Rooms
    room_verts = read_from_file(os.path.join(origin_path, "room_verts"))
    room_faces = read_from_file(os.path.join(origin_path, "room_faces"))
    
    if room_verts and room_faces:
        print(f"🏠 Adding {len(room_verts)} rooms")
        for i, (rverts, rfaces) in enumerate(zip(room_verts, room_faces)):
            obj_gen.create_mesh_from_data(
                rverts, rfaces, 
                f"room_{i}", (0.9, 0.9, 0.8), 
                offset_z=0.005
            )
    
    # Create Walls
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
    
    # Save files
    obj_path = output_path
    mtl_path = output_path.replace('.obj', '.mtl')
    
    obj_gen.save_obj(obj_path)
    obj_gen.save_mtl(mtl_path)
    
    print(f"✅ 3D Model from AI-processed image created: {obj_path}")
    print(f"✅ Materials created: {mtl_path}")
    print(f"📊 Total vertices: {obj_gen.vertex_count - 1}")
    print(f"📊 Total materials: {len(obj_gen.materials)}")
    
    return obj_path

def main():
    """Use existing AI-processed images"""
    dialog.figlet()
    
    print("🤖 ----- USE AI-PROCESSED IMAGES FOR 3D GENERATION -----")
    print("This script uses already AI-processed floorplan images!")
    print()
    
    # List available AI-processed images
    processed_dir = "Images/Processed"
    if os.path.exists(processed_dir):
        processed_images = [f for f in os.listdir(processed_dir) if f.endswith('.png')]
        
        if processed_images:
            print("📁 Available AI-processed images:")
            for i, img in enumerate(processed_images, 1):
                print(f"  {i}. {img}")
            print()
            
            choice = input(f"Select image (1-{len(processed_images)}) [default = 1]: ")
            if not choice:
                choice = "1"
            
            try:
                selected_idx = int(choice) - 1
                if 0 <= selected_idx < len(processed_images):
                    ai_image_path = os.path.join(processed_dir, processed_images[selected_idx])
                else:
                    ai_image_path = os.path.join(processed_dir, processed_images[0])
            except:
                ai_image_path = os.path.join(processed_dir, processed_images[0])
        else:
            print("❌ No AI-processed images found!")
            return
    else:
        print("❌ No AI-processed images directory found!")
        return
    
    # Get output path
    base_name = os.path.basename(ai_image_path).replace('.png', '').replace('ai_processed_', '')
    default_output = f"Target/{base_name}_from_ai.obj"
    
    output_path = input(f"Enter output path [default = {default_output}]: ")
    if not output_path:
        output_path = default_output
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"\n🚀 Processing AI-enhanced image: {ai_image_path}")
    
    try:
        result_path = create_3d_from_ai_processed(ai_image_path, output_path)
        
        print(f"\n🎉 Success! 3D model from AI-processed image created!")
        print(f"📁 Location: {result_path}")
        print(f"🌐 View at: http://localhost:8080/simple_viewer.html")
        print("\n✨ Floor3D - From AI-Processed Images")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
