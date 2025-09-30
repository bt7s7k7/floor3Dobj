import configparser
import json
import os
import sys
from typing import Any, List, Union

import numpy as np
from FloorplanToBlenderLib import IO, execution, floorplan
from gltflib import (GLTF, Accessor, AccessorType, Asset, Attributes, Buffer,
                     BufferView, ComponentType, FileResource, GLTFModel, Mesh,
                     Node, Primitive, PrimitiveMode, Scene)

# --- Helper Functions for 3D ---

def calculate_polygon_normal(vertices_data: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Calculates the normal vector for the polygon's plane."""
    if len(indices) < 3:
        return np.array([0.0, 0.0, 0.0])

    # Get the first three unique vertices' coordinates
    v0 = vertices_data[indices[0]]
    v1 = vertices_data[indices[1]]
    v2 = vertices_data[indices[2]]

    # Calculate two edge vectors
    e1 = v1 - v0
    e2 = v2 - v0

    # The normal is the cross product of the two edges
    normal = np.cross(e1, e2)
    # Normalize the vector for consistency
    norm = np.linalg.norm(normal)
    return normal / norm if norm != 0 else np.array([0.0, 0.0, 0.0])

EPSILON = 1e-6
def orientation_sign_3d(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, normal: np.ndarray) -> float:
    """
    Calculates the orientation (scalar cross product equivalent) using 3D vectors
    and the polygon's normal.
    """
    # Edge vectors
    e1 = p2 - p1
    e2 = p3 - p2
    
    # 3D cross product: determines a vector perpendicular to the triangle (p1, p2, p3)
    cross = np.cross(e1, e2)

    # Dot product of the cross vector with the polygon's normal.
    # The sign indicates whether the turn (p1->p2->p3) is CCW or CW 
    # when viewed from the 'outside' of the normal vector.
    result = np.dot(cross, normal)
    if abs(result) < EPSILON:
        return 0.0
    
    return result


def is_point_in_triangle_3d(p: np.ndarray, t1: np.ndarray, t2: np.ndarray, t3: np.ndarray, normal: np.ndarray) -> bool:
    """
    Checks if point p is strictly inside the triangle (t1, t2, t3).
    This uses the barycentric/same-side technique adapted for 3D space 
    using the orientation function.
    """
    
    def same_side(p1, p2, a, b):
        # Checks if p1 and p2 are on the same side of the edge (a, b)
        # by looking at the orientation of (a, b, p1) vs (a, b, p2)
        cp1 = orientation_sign_3d(a, b, p1, normal)
        cp2 = orientation_sign_3d(a, b, p2, normal)
        
        # Check if they have the same sign (or one is zero)
        return cp1 * cp2 >= 0
    
    # Point is inside if it's on the same side of all three edges.
    return (same_side(p, t1, t2, t3) and 
            same_side(p, t2, t1, t3) and 
            same_side(p, t3, t1, t2))

# --- Ear-Clipping Main Function (with 3D adaptation) ---

def ngon_to_triangle_indices_3d_concave(
    vertices_data: np.ndarray,
    indices: Union[np.ndarray, List[int]]
) -> List[np.ndarray]:
    """
    Triangulates a planar polygon with 3D vertices using the Ear-Clipping algorithm.
    """
    v_indices = np.array(indices, dtype=np.int32)
    num_vertices = len(v_indices)

    if num_vertices < 3:
        return []

    # 1. Determine the Polygon's Normal Vector
    normal = calculate_polygon_normal(vertices_data, v_indices)
    if np.linalg.norm(normal) == 0:
         # Cannot determine a normal (e.g., collinear points).
        return [] 

    # 2. Determine Winding Order (CCW or CW)
    # The orientation function with a CCW winding will be positive.
    is_ccw = orientation_sign_3d(
        vertices_data[v_indices[0]], 
        vertices_data[v_indices[1]], 
        vertices_data[v_indices[2]], 
        normal
    ) > 0

    triangle_indices = []
    
    # 3. Main Ear-Clipping Loop
    while len(v_indices) > 3:
        found_ear = False
        
        for i_curr in range(len(v_indices)):
            # Indices in the current v_indices array
            i_prev = (i_curr - 1 + len(v_indices)) % len(v_indices)
            i_next = (i_curr + 1) % len(v_indices)
            
            # Original vertex indices
            idx_prev = v_indices[i_prev]
            idx_curr = v_indices[i_curr]
            idx_next = v_indices[i_next]

            # Corresponding 3D vertex coordinates
            v_prev = vertices_data[idx_prev]
            v_curr = vertices_data[idx_curr]
            v_next = vertices_data[idx_next]
            
            # --- EAR CHECK ---
            
            # A. Convexity Check
            orientation = orientation_sign_3d(v_prev, v_curr, v_next, normal)
            is_convex = (orientation > 0) if is_ccw else (orientation < 0)
            if not is_convex:
                continue # Concave angle, skip

            # B. Containment Check
            is_valid_ear = True
            for j in range(len(v_indices)):
                # Skip the three vertices forming the potential ear
                if j == i_prev or j == i_curr or j == i_next:
                    continue
                    
                p = vertices_data[v_indices[j]]
                
                # Check if any other vertex is inside the triangle
                if is_point_in_triangle_3d(p, v_prev, v_curr, v_next, normal):
                    is_valid_ear = False
                    break
            
            if is_valid_ear:
                # Ear found and valid! Clip it.
                triangle = np.array([idx_prev, idx_curr, idx_next], dtype=np.int32)
                triangle_indices.extend(triangle)
                
                # Remove the "eaten" vertex (v_curr) from the list
                v_indices = np.delete(v_indices, i_curr)
                
                found_ear = True
                break # Restart search

        if not found_ear and len(v_indices) > 3:
            print("Error: Failed to find an ear. Polygon may be non-simple, non-planar, or degenerate.")
            break
            
    # Add the last remaining triangle
    if len(v_indices) == 3:
        triangle_indices.extend(v_indices)
        
    return triangle_indices

def read_from_file(file_path) -> "Any":
    """Read JSON data from file"""
    print(f"    Reading {file_path}.txt")
    try:
        with open(file_path + ".txt", "r") as f:
            return json.loads(f.read())
    except:
        return None

class ProcessorConfigHandler:
    def __init__(self,
            default_config_path: str = "./Configs/default.ini",
            config_path: str = "./Configs/default.ini",
            clean_data_path = True
        ):
        self.default_config_path = default_config_path
        self.config_path = config_path
        self.clean_data_path = clean_data_path
        pass

    def create_config(self, image_path: str):
        # Read current config
        conf = configparser.ConfigParser()
        conf.read(self.default_config_path)
        
        # Update image path
        if 'IMAGE' not in conf:
            conf.add_section('IMAGE')
        conf.set('IMAGE', 'image_path', f'"{image_path}"')
        
        # Write back
        with open(self.config_path, 'w') as configfile:
            conf.write(configfile)


def create_glb(image_path: str, output_path, config: "ProcessorConfigHandler | None" = None):
    if config is None:
        config = ProcessorConfigHandler()
    
    print(f"Starting conversion {image_path} -> {output_path}")
    print()

    if image_path.endswith(".txt"):
        data_path = os.path.dirname(image_path)
    else:
    
        # Check if image exists
        if not os.path.exists(image_path):
            raise RuntimeError(f"Error: Image {image_path} not found!")
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print("Processing floorplan...")
        
        config.create_config(image_path)
        
        # Create floorplan object
        fp = floorplan.new_floorplan(config.config_path)
        
        # Generate data files
        print("Generating data files...")

        if config.clean_data_path:
            IO.clean_data_folder("Data")

        data_path = execution.simple_single(fp)
    
    # Create 3D model directly
    print("Creating 3D model...")

    # Read transform data
    transform_file = os.path.join(data_path, "transform.txt")
    if os.path.exists(transform_file):
        with open(transform_file, 'r') as f:
            transform = json.loads(f.read())
        origin_path = transform.get("origin_path", data_path)
        # If origin_path is relative, make it relative to current directory
        if not os.path.isabs(origin_path):
            origin_path = os.path.join(".", origin_path)
    else:
        origin_path = data_path

    print(f"Reading data from: {origin_path}")

    gltf_nodes: "list[Node]" = []
    gltf_buffers: "list[Buffer]" = []
    gltf_resources: "list[Any]" = []
    gltf_buffer_views: "list[BufferView]" = []
    gltf_accessors: "list[Accessor]" = []
    gltf_meshes: "list[Mesh]" = []

    def create(list: list, resource: "Any"):
        id = len(list)
        list.append(resource)
        return id

    def create_mesh(name: str, faces, vertices, invert_normals = False):
        # 1. Define the Mesh Data (Vertices and Indices)

        # Example: A simple square (two triangles)
        # Vertices (x, y, z) - float32 is common for positions
        # Note: glTF uses a right-handed coordinate system, typically Y-up.
        vertices = np.array(
            vertices,
            dtype=np.float32,
        )

        # Indices (to form two triangles: 0-1-2 and 1-3-2) - uint16 is common for indices
        if len(faces) > 1:
            print(f"Mesh {name} has more than one face: {faces}")

        indices = np.array(
            ngon_to_triangle_indices_3d_concave(vertices, faces[0]),
            dtype=np.uint16,
        )

        if invert_normals:
            indices = indices[::-1]

        # 2. Convert Data to Binary Buffers

        # Combine all data into a single binary buffer for efficiency
        # gltflib handles the packing into a single bytes object.
        binary_blob = vertices.tobytes() + indices.tobytes()

        resource_name = name + ".bin"
        resource = FileResource(resource_name, data=binary_blob)
        gltf_resources.append(resource)

        buffer = create(gltf_buffers, Buffer(byteLength=len(binary_blob), uri=resource_name))

        # 3. Define Buffer Views

        # A BufferView describes a segment of a Buffer.

        # For Vertices (Position data)
        vertex_byte_offset = 0
        vertex_byte_length = vertices.nbytes
        vertex_buffer_id = create(gltf_buffer_views,  BufferView(
            buffer=buffer,
            byteOffset=vertex_byte_offset,
            byteLength=vertex_byte_length,
            # target=34962,  # ARRAY_BUFFER (Optional, but good practice)
        ))

        # For Indices
        index_byte_offset = vertex_byte_length  # Starts after the vertices
        index_byte_length = indices.nbytes
        index_buffer_id = create(gltf_buffer_views, BufferView(
            buffer=buffer,
            byteOffset=index_byte_offset,
            byteLength=index_byte_length,
            # target=34963,  # ELEMENT_ARRAY_BUFFER (Optional, but good practice)
        ))

        # 4. Define Accessors

        # Accessors define how to interpret the data in a BufferView.

        # Accessor for Positions (Vertices)
        position_accessor = create(gltf_accessors, Accessor(
            bufferView=vertex_buffer_id,
            byteOffset=0,
            componentType=ComponentType.FLOAT,
            count=len(vertices),
            type=AccessorType.VEC3.value,
            max=vertices.max(axis=0).tolist(),
            min=vertices.min(axis=0).tolist(),
        ))

        # Accessor for Indices
        index_accessor = create(gltf_accessors, Accessor(
            bufferView=index_buffer_id,
            byteOffset=0,
            componentType=ComponentType.UNSIGNED_SHORT, # Corresponds to np.uint16
            count=len(indices),
            type=AccessorType.SCALAR.value, # Single value per index
        ))

        # 5. Build the Mesh Primitive

        # A Primitive is the actual drawing geometry (e.g., a set of triangles).
        primitive = Primitive(
            attributes=Attributes(POSITION=position_accessor), # POSITION uses the first accessor (index 0)
            indices=index_accessor, # Indices use the second accessor (index 1)
            mode=PrimitiveMode.TRIANGLES.value,
        )

        mesh = create(gltf_meshes, Mesh(primitives=[primitive], name="SquareMesh"))
        create(gltf_nodes, Node(mesh=mesh, name=name))

    # See: floorplan_to_3dObject_in_blender.py
    path_to_wall_vertical_faces_file = origin_path + "wall_vertical_faces"
    path_to_wall_vertical_verts_file = origin_path + "wall_vertical_verts"

    path_to_wall_horizontal_faces_file = origin_path + "wall_horizontal_faces"
    path_to_wall_horizontal_verts_file = origin_path + "wall_horizontal_verts"

    path_to_floor_faces_file = origin_path + "floor_faces"
    path_to_floor_verts_file = origin_path + "floor_verts"

    path_to_rooms_faces_file = origin_path + "room_faces"
    path_to_rooms_verts_file = origin_path + "room_verts"

    path_to_doors_vertical_faces_file = origin_path + "door_vertical_faces"
    path_to_doors_vertical_verts_file = origin_path + "door_vertical_verts"

    path_to_doors_horizontal_faces_file = origin_path + "door_horizontal_faces"
    path_to_doors_horizontal_verts_file = origin_path + "door_horizontal_verts"

    path_to_windows_vertical_faces_file = origin_path + "window_vertical_faces"
    path_to_windows_vertical_verts_file = origin_path + "window_vertical_verts"

    path_to_windows_horizontal_faces_file = origin_path + "window_horizontal_faces"
    path_to_windows_horizontal_verts_file = origin_path + "window_horizontal_verts"

    print("\n### Walls ###\n")

    print("\n-- get image wall data")
    verts = read_from_file(path_to_wall_vertical_verts_file)
    faces = read_from_file(path_to_wall_vertical_faces_file)

    i = 0
    if verts and faces:
        for walls in verts:
            j = 0
            for wall in walls:
                create_mesh(f"Wall_{i}_{j}", faces, wall)
                j += 1
            i += 1
    
    print("\n-- get image top wall data")
    verts = read_from_file(path_to_wall_horizontal_verts_file)
    faces = read_from_file(path_to_wall_horizontal_faces_file)

    if verts and faces:
        for i in range(0, len(verts)):
            create_mesh(f"WallTop_{i}", faces[i], verts[i])
    
    print("\n### Windows ###\n")
    
    print("\n-- get image wall data")
    verts = read_from_file(path_to_windows_vertical_verts_file)
    faces = read_from_file(path_to_windows_vertical_faces_file)

    i = 0
    if verts and faces:
        for walls in verts:
            j = 0
            for wall in walls:
                create_mesh(f"Window_{i}_{j}", faces, wall, invert_normals=True)
                j += 1
            i += 1

    print("\n-- get windows")
    verts = read_from_file(path_to_windows_horizontal_verts_file)
    faces = read_from_file(path_to_windows_horizontal_faces_file)

    if verts and faces:
        for i in range(0, len(verts)):
            create_mesh(f"Window_{i}", faces[i], verts[i], invert_normals=True)

    print("\n### Doors ###\n")
    
    print("\n-- get image wall data")
    verts = read_from_file(path_to_doors_vertical_verts_file)
    faces = read_from_file(path_to_doors_vertical_faces_file)

    i = 0
    if verts and faces:
        for walls in verts:
            j = 0
            for wall in walls:
                create_mesh(f"Door_{i}_{j}", faces, wall)
                j += 1
            i += 1

    print("\n-- get windows")
    verts = read_from_file(path_to_doors_horizontal_verts_file)
    faces = read_from_file(path_to_doors_horizontal_faces_file)

    if verts and faces:
        for i in range(0, len(verts)):
            create_mesh(f"Door_{i}", faces[i], verts[i])
    
    print("\n### Floor ###\n")
    print("\n-- get image wall data")
    verts = read_from_file(path_to_floor_verts_file)
    faces = read_from_file(path_to_floor_faces_file)

    i = 0
    if verts and faces:
        create_mesh(f"Floor_{i}", [faces], verts)
        i += 1

    print("\n### rooms ###\n")
    print("\n-- get image wall data")
    verts = read_from_file(path_to_rooms_verts_file)
    faces = read_from_file(path_to_rooms_faces_file)

    if verts and faces:
        for i in range(0, len(verts)):
            create_mesh(f"Room_{i}", faces[i], verts[i])
    
    model = GLTFModel(
        asset=Asset(version='2.0'),
        scenes=[Scene(nodes=list(range(len(gltf_nodes))))],
        nodes=gltf_nodes,
        meshes=gltf_meshes,
        buffers=gltf_buffers,
        bufferViews=gltf_buffer_views,
        accessors=gltf_accessors
    )

    gltf = GLTF(model=model, resources=gltf_resources)
    gltf.export(output_path)

    return data_path

if __name__ == "__main__":
   
    input = sys.argv[1] if len(sys.argv) > 1 else None
    if not input:
        print("Missing 'input' parameter, expected: <input> <output>")
        print("Example usage: python create_glb.py Images/Examples/example2.png Target/floorplan_direct.glb")
        sys.exit(1)

    output = sys.argv[2] if len(sys.argv) > 2 else None
    if not output:
        print("Missing 'output' parameter, expected: <input> <output>")
        print("Example usage: python create_glb.py Images/Examples/example2.png Target/floorplan_direct.glb")
        sys.exit(1)

    create_glb(input, output)
