#!/usr/bin/env python3
import re
import zipfile
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import argparse

parser = argparse.ArgumentParser(description="Host zip file as DocumentRoot of http server.")
parser.add_argument("zipfile", metavar="<file.zip>")
parser.add_argument("-p", "--port", dest="port", type=int, default=8082)
args = parser.parse_args()

zf = zipfile.ZipFile(args.zipfile)
zfp = zipfile.Path(zf)

RANGE_BYTES_REGEX = re.compile(r"^bytes=([0-9]+)-([0-9]+)?$")

class ZHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = zfp / self.path[1:]
        if p.is_dir():
            if not self.path.endswith("/"):
                self.send_response(302)
                self.send_header("Location", self.path+"/")
                self.end_headers()
                return
            out = f"""<h1>Index of {self.path}</h1><ul>"""
            for dir in p.iterdir():
                if dir.is_dir():
                    out += f'<li><a href="{dir.name}/">{dir.name}/</a></li>'
                else:
                    out += f'<li><a href="{dir.name}">{dir.name}</a></li>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(out.encode("UTF-8"))
            return
        elif p.is_file():
            pi = zf.getinfo(self.path[1:])
            with p.open("rb") as pf:
                start_pos = None
                read_length = None
                h_range = self.headers.get("range")
                if h_range is not None:
                    hrm = RANGE_BYTES_REGEX.match(h_range)
                    if hrm is not None:
                        start_pos = int(hrm.group(1))
                        if hrm.group(2) is not None:
                            read_length = int(hrm.group(2)) - start_pos + 1
                        else:
                            read_length = pi.file_size
                mimetype, encoding = mimetypes.guess_type(p.name)
                if mimetype is None:
                    mimetype = "text/plain"
                if start_pos is not None:
                    self.send_response(206)
                    d = pf.read(start_pos + min(read_length, 1024 * 1024))
                    self.send_header("Content-Range", f"bytes {0}-{len(d)-1}/{pi.file_size}")
                    self.send_header("Content-Type", mimetype)
                    self.end_headers()
                    self.wfile.write(d)
                    return
                self.send_response(200)
                self.send_header("Content-Type", mimetype)
                self.end_headers()
                while True:
                    readed = pf.read(1024)
                    if readed is None or len(readed) == 0:
                        break
                    self.wfile.write(readed)

ThreadingHTTPServer(('', args.port), RequestHandlerClass=ZHTTPRequestHandler).serve_forever()
