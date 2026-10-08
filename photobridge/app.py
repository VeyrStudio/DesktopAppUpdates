import hashlib,json,os,socket,secrets,threading,tempfile,urllib.request,subprocess
from pathlib import Path
from uuid import uuid4
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlparse
import tkinter as tk
from tkinter import filedialog,messagebox

VERSION="0.1.0"
MANIFEST="https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/photobridge/latest.json"
CONFIG=Path(os.environ.get("LOCALAPPDATA",str(Path.home())))/"PhotoBridge"/"config.json"
CONFIG.parent.mkdir(parents=True,exist_ok=True)
try: DEST=Path(json.loads(CONFIG.read_text())["folder"])
except Exception: DEST=Path.home()/"Pictures"/"PhotoBridge"
DEST.mkdir(parents=True,exist_ok=True)
KEY=secrets.token_urlsafe(28)
LOCK=threading.Lock()
WEB="""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PhotoBridge</title><style>body{font:16px system-ui;background:#20152b;color:#f8eeff;margin:30px auto;max-width:650px;padding:20px}button{background:#8e4cc2;color:white;padding:15px;border:0;border-radius:9px;width:100%;margin:18px 0}progress{width:100%}</style></head><body><h1>PhotoBridge</h1><p>Select photos and videos, then tap Send to computer. Keep Safari open.</p><input type="file" multiple accept="image/*,video/*,.gif,.heic,.mov" id="files"><button id="go">Send to computer</button><progress id="bar" value="0" max="100"></progress><p id="status">Ready</p><p>Original files stay on your iPhone. Verify before deleting manually.</p><script>let f=document.getElementById('files'),b=document.getElementById('go'),s=document.getElementById('status'),p=document.getElementById('bar');b.onclick=async()=>{if(!f.files.length)return alert('Choose files first');b.disabled=true;let done=0;for(let i=0;i<f.files.length;i++){let x=f.files[i];s.textContent='Sending '+(i+1)+'/'+f.files.length+' — '+x.name;try{let r=await fetch('/upload?key=__KEY__&name='+encodeURIComponent(x.name),{method:'POST',body:x,headers:{'Content-Type':'application/octet-stream'}});if(!r.ok)throw Error(await r.text());done++;p.value=Math.round(done*100/f.files.length)}catch(e){s.textContent='Stopped after '+done+': '+e.message;b.disabled=false;return}}s.textContent='Transferred '+done+' files. Check them on your PC.';b.disabled=false}</script></body></html>"""
class Receiver(BaseHTTPRequestHandler):
    def reply(self,code,data,ctype="text/plain"):
        raw=data.encode()
        self.send_response(code);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def permitted(self):return parse_qs(urlparse(self.path).query).get("key",[""])[0]==KEY
    def do_GET(self):
        if not self.permitted():return self.reply(403,"Denied")
        self.reply(200,WEB.replace("__KEY__",KEY),"text/html; charset=utf-8")
    def do_POST(self):
        if not self.permitted():return self.reply(403,"Denied")
        if urlparse(self.path).path!="/upload":return self.reply(404,"Not found")
        name=Path(parse_qs(urlparse(self.path).query).get("name",["file"])[0].replace("\\","/")).name
        if not name or name in (".",".."):return self.reply(400,"Invalid name")
        try:size=int(self.headers.get("Content-Length","0"))
        except ValueError:return self.reply(400,"Invalid length")
        if not 0<size<=20*1024**3:return self.reply(413,"Invalid size")
        staging=DEST/("."+uuid4().hex+".part")
        try:
            digest=hashlib.sha256()
            with staging.open("xb") as f:
                while size:
                    data=self.rfile.read(min(size,1024*1024))
                    if not data:raise IOError("Interrupted")
                    f.write(data);digest.update(data);size-=len(data)
                f.flush();os.fsync(f.fileno())
            with LOCK:
                idxfile=DEST/".photobridge-index.json"
                try: idx=json.loads(idxfile.read_text())
                except Exception:idx={}
                sha=digest.hexdigest()
                if sha in idx and (DEST/idx[sha]).exists():
                    staging.unlink();return self.reply(200,"Duplicate")
                out=DEST/name
                n=2
                while out.exists():
                    p=Path(name);out=DEST/(p.stem+" ("+str(n)+")"+p.suffix);n+=1
                os.replace(staging,out);idx[sha]=out.name
                temp=idxfile.with_suffix(".tmp")
                temp.write_text(json.dumps(idx,indent=2));os.replace(temp,idxfile)
            self.reply(200,"Saved")
        except Exception as e:
            staging.unlink(missing_ok=True);self.reply(500,str(e))
    def log_message(self,*args):pass
def local_ip():
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1",80));return s.getsockname()[0]
    except Exception:return socket.gethostbyname(socket.gethostname())
class App:
    def __init__(self,root):
        self.root=root;self.server=None
        root.title("PhotoBridge");root.geometry("680x480");root.configure(bg="#20152b")
        frame=tk.Frame(root,bg="#20152b",padx=25,pady=24);frame.pack(fill="both",expand=True)
        def txt(t,size=11):
            w=tk.Label(frame,text=t,font=("Segoe UI",size),fg="#f7ecff",bg="#20152b",wraplength=620);w.pack(pady=7);return w
        txt("PhotoBridge",27)
        txt("Send photos, videos and GIFs from Safari directly to this PC.")
        tk.Button(frame,text="Start / Stop Receiver",command=self.toggle,bg="#8e4cc2",fg="white",font=("Segoe UI",12)).pack(fill="x",pady=12)
        self.link=tk.StringVar(value="Receiver is off")
        tk.Label(frame,textvariable=self.link,fg="#dfadff",bg="#20152b",wraplength=620).pack(pady=8)
        tk.Button(frame,text="Copy iPhone link",command=self.copy).pack(pady=5)
        self.folder=tk.StringVar(value=str(DEST))
        tk.Label(frame,textvariable=self.folder,fg="white",bg="#20152b",wraplength=620).pack(pady=8)
        row=tk.Frame(frame,bg="#20152b");row.pack()
        for name,fn in [("Change Folder",self.choose),("Open Folder",lambda:os.startfile(DEST)),("Verify Files",self.verify),("Check Updates",lambda:self.update(True))]:
            tk.Button(row,text=name,command=fn).pack(side="left",padx=4)
        txt("Transfers only happen when you press Send on your iPhone. Originals are never deleted.",10)
        root.protocol("WM_DELETE_WINDOW",self.close)
        root.after(2000,lambda:self.update(False))
    def toggle(self):
        if self.server:
            old=self.server;self.server=None
            threading.Thread(target=lambda:(old.shutdown(),old.server_close()),daemon=True).start()
            self.link.set("Receiver is off");return
        try:self.server=ThreadingHTTPServer(("0.0.0.0",8765),Receiver)
        except OSError as e:messagebox.showerror("Receiver error",str(e));return
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.link.set("http://"+local_ip()+":8765/?key="+KEY)
    def copy(self):
        self.root.clipboard_clear();self.root.clipboard_append(self.link.get())
    def choose(self):
        global DEST
        if self.server:return messagebox.showinfo("PhotoBridge","Stop receiver before changing folders.")
        p=filedialog.askdirectory()
        if p:
            DEST=Path(p);CONFIG.write_text(json.dumps({"folder":str(DEST)}));self.folder.set(p)
    def verify(self):
        try:idx=json.loads((DEST/".photobridge-index.json").read_text())
        except Exception:idx={}
        bad=[]
        for digest,name in idx.items():
            p=DEST/name
            if not p.exists():bad.append(name);continue
            h=hashlib.sha256()
            with p.open("rb") as f:
                for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
            if h.hexdigest()!=digest:bad.append(name)
        messagebox.showinfo("Verification",str(len(idx)-len(bad))+" verified; "+str(len(bad))+" missing or damaged.\nAlso confirm all intended phone photos were selected and transferred before deleting originals.")
    def update(self,manual):
        def run():
            try:
                with urllib.request.urlopen(urllib.request.Request(MANIFEST,headers={"User-Agent":"PhotoBridge"}),timeout=12) as response:m=json.load(response)
                ver=lambda x:tuple(int(k) for k in x.split("."))
                if ver(m["version"])<=ver(VERSION):
                    if manual:self.root.after(0,lambda:messagebox.showinfo("Updates","Up to date."))
                    return
                self.root.after(0,lambda:self.offer(m))
            except Exception as e:
                if manual:self.root.after(0,lambda:messagebox.showerror("Updates",str(e)))
        threading.Thread(target=run,daemon=True).start()
    def offer(self,m):
        if not messagebox.askyesno("PhotoBridge update","Version "+m["version"]+" is available. Download it?"):return
        def run():
            try:
                dest=Path(tempfile.gettempdir())/("PhotoBridge-Setup-"+m["version"]+".exe")
                sha=hashlib.sha256()
                with urllib.request.urlopen(urllib.request.Request(m["url"],headers={"User-Agent":"PhotoBridge"}),timeout=60) as r,dest.open("wb") as f:
                    for data in iter(lambda:r.read(1024*1024),b""):f.write(data);sha.update(data)
                if sha.hexdigest().lower()!=m["sha256"].lower():raise ValueError("Installer SHA256 mismatch")
                self.root.after(0,lambda:self.install(dest))
            except Exception as e:self.root.after(0,lambda:messagebox.showerror("Update failed",str(e)))
        threading.Thread(target=run,daemon=True).start()
    def install(self,dest):
        if messagebox.askyesno("Install update","Installer verified. Close PhotoBridge and run it?"):
            subprocess.Popen([str(dest)]);self.close()
    def close(self):
        if self.server:
            self.server.shutdown();self.server.server_close()
        self.root.destroy()
if __name__=="__main__":
    window=tk.Tk();App(window);window.mainloop()
