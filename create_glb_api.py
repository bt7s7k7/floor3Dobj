from posixpath import join
from tempfile import TemporaryDirectory

from create_glb import ProcessorConfigHandler, create_glb
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MiB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
def parse_extension(filename: "str | None"):
    if filename is None:
        return None
    
    if not '.' in filename:
        return None
    
    extension = filename.rsplit('.', 1)[1].lower()
    if not extension in ALLOWED_EXTENSIONS:
        return None

    return extension

@app.route('/api/create_glb', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({"error": "No 'image' file part in the request"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    extension = parse_extension(file.filename)
    if extension is None:
        return jsonify({"error": "Illegal extension"}), 400
    
    with TemporaryDirectory() as tmpdir:
        image_path = join(tmpdir, "image." + extension)

        try:
            file.save(image_path)
        except IOError:
            app.logger.error(f"Failed to save file to {image_path}")
            return jsonify({"error": "Failed to save file on server"}), 500

        app.logger.info(f"Saving user image to: {image_path}")

        config = ProcessorConfigHandler(
            config_path=join(tmpdir, "config.ini"),
            clean_data_path=False
        )

        output_path = join(tmpdir, "output.glb")

        try:
            create_glb(image_path, output_path, config)
        except Exception as e:
            app.logger.error(f"GLB creation failed: {e}")
            return jsonify({"error": "Image processing failed"}), 500

        response = send_file(
            output_path, 
            mimetype='model/gltf-binary',
            as_attachment=True, 
            download_name="output.glb"
        )

        return response

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File size exceeds limit"}), 413

app.run(port=8081)
