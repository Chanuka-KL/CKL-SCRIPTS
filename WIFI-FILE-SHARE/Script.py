from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import shutil
from urllib.parse import unquote, urlparse
from io import BytesIO

PORT = 8080

class FileManagerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path[1:])
        if os.path.isdir(path) or self.path == "/":
            self.list_directory(path or ".")
        elif self.path == "/upload":
            self.upload_form()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/upload":
            self.upload_file()
        elif self.path.startswith("/delete/"):
            self.delete_file_or_dir()
        elif self.path.startswith("/rename/"):
            self.rename_file()
        elif self.path.startswith("/move/"):
            self.move_file_or_dir()
        elif self.path.startswith("/copy/"):
            self.copy_file_or_dir()
        elif self.path.startswith("/create/"):
            self.create_file_or_dir()
        else:
            super().do_POST()

    def list_directory(self, path):
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "Directory not found")
            return None

        # Generate styled HTML for file-explorer with server details
        output = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>C-RAT - File Manager</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #3b0d0c;
                    color: white;
                }}
                .toolbar {{
                    background-color: #a51212;
                    padding: 10px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .toolbar h1 {{
                    margin: 0;
                }}
                .content {{
                    padding: 20px;
                }}
                .entry {{
                    margin: 10px 0;
                    padding: 10px;
                    background-color: #5c1d1d;
                    border-radius: 5px;
                    cursor: pointer;
                }}
                .entry:hover {{
                    background-color: #a51212;
                }}
                .folder {{
                    color: #ffd700;
                }}
                .file {{
                    color: #add8e6;
                }}
                a {{
                    color: #ffffff;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="toolbar">
                <h1>CKL WIFI FILE SHARE</h1>
                <div>Server: Python HTTP Server | Port: {PORT}</div>
                <a href="/upload">Upload File</a>
            </div>
            <div class="content">
        """
        for entry in entries:
            entry_path = os.path.join(path, entry)
            if os.path.isdir(entry_path):
                output += f'<div class="entry folder"><a href="/{entry_path}">📁 {entry}</a></div>'
            else:
                output += f'<div class="entry file"><a href="/{entry_path}" download>📄 {entry}</a></div>'
            # Add delete, rename, move, and copy actions
            output += f'''
            <div>
                <a href="/delete/{entry}">Delete</a> |
                <a href="/rename/{entry}">Rename</a> |
                <a href="/move/{entry}">Move</a> |
                <a href="/copy/{entry}">Copy</a>
            </div>
            '''
        output += """
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(output.encode("utf-8"))

    def upload_form(self):
        # Display the upload form
        output = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Upload File</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #3b0d0c;
                    color: white;
                }}
                .upload-form {{
                    background-color: #5c1d1d;
                    padding: 20px;
                    border-radius: 5px;
                    margin-top: 50px;
                }}
                input[type="file"] {{
                    color: #ffd700;
                }}
                button {{
                    background-color: #a51212;
                    padding: 10px 20px;
                    border: none;
                    cursor: pointer;
                }}
                button:hover {{
                    background-color: #7d0e0d;
                }}
            </style>
        </head>
        <body>
            <div class="upload-form">
                <h2>Upload a File</h2>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" required>
                    <button type="submit">Upload</button>
                </form>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(output.encode("utf-8"))

    def upload_file(self):
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)
        boundary = self.headers['Content-Type'].split('=')[1].encode()

        # Extract the file from the form data
        parts = data.split(boundary)[1:-1]
        for part in parts:
            if b'filename' in part:
                filename = part.split(b'filename="')[1].split(b'"')[0].decode()
                file_data = part.split(b'\r\n\r\n')[1].split(b'\r\n')[0]
                file_path = os.path.join(".", filename)
                with open(file_path, 'wb') as f:
                    f.write(file_data)
                break
        
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

    def delete_file_or_dir(self):
        target = unquote(self.path[len('/delete/'):])
        if os.path.exists(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404, "File or Directory not found")

    def rename_file(self):
        target = unquote(self.path[len('/rename/'):])
        new_name = self.headers.get('X-New-Name')
        if os.path.exists(target) and new_name:
            os.rename(target, new_name)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404, "File not found or invalid new name")

    def move_file_or_dir(self):
        target = unquote(self.path[len('/move/'):])
        new_location = self.headers.get('X-New-Location')
        if os.path.exists(target) and new_location:
            shutil.move(target, new_location)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404, "File or Directory not found or invalid location")

    def copy_file_or_dir(self):
        target = unquote(self.path[len('/copy/'):])
        new_location = self.headers.get('X-New-Location')
        if os.path.exists(target) and new_location:
            if os.path.isdir(target):
                shutil.copytree(target, new_location)
            else:
                shutil.copy(target, new_location)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404, "File or Directory not found or invalid location")

    def create_file_or_dir(self):
        target = unquote(self.path[len('/create/'):])
        if target.endswith('/'):
            os.makedirs(target, exist_ok=True)
        else:
            with open(target, 'w') as f:
                f.write('')
        self.send_response(303)
        self.send_header('Location', '/')
        self.end_headers()

server = HTTPServer(("", PORT), FileManagerHandler)
print(f"Serving on port {PORT}")
server.serve_forever()
