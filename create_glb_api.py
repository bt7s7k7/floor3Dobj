import sys
from logging import INFO
from os import system
from posixpath import join
from tempfile import TemporaryDirectory, mkdtemp

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MiB
app.logger.setLevel(INFO)

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
    
    def process_image(tmpdir: str):
        image_path = join(tmpdir, "image." + extension)

        try:
            file.save(image_path)
        except IOError:
            app.logger.error(f"Failed to save file to {image_path}")
            return jsonify({"error": "Failed to save file on server"}), 500

        app.logger.info(f"Saving user image to: {image_path}")

        output_path = join(tmpdir, "output.glb")
        config_path=join(tmpdir, "config.ini")

        command = f"{sys.executable} create_glb.py {image_path} {output_path} --clean-intermediate-data --no-clean-data-path --config-path={config_path}"
        app.logger.info(f"$$ Executing: {command}")
        if system(command) != 0:
            app.logger.error(f"GLB creation failed")
            return jsonify({"error": "Image processing failed"}), 500

        response = send_file(
            output_path, 
            mimetype='model/gltf-binary',
            as_attachment=True, 
            download_name="output.glb"
        )

        return response
    
    debug = False

    if debug:
        # If debug is enabled, do not use context so the temporary directory is not deleted and we
        # can inspect the files
        path = mkdtemp()
        return process_image(path)

    with TemporaryDirectory() as tmpdir:
        return process_image(tmpdir)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File size exceeds limit"}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
