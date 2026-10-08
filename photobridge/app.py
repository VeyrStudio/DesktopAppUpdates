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
TRANSFERS={'success':{},'failure':{},'active':{}}
def success_dir():
    p=DEST/'Success'
    p.mkdir(parents=True,exist_ok=True)
    return p
WEB="""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>PhotoBridge • Transfer</title><style>
:root{color-scheme:dark;--bg:#101014;--panel:#1b1a20;--border:#70542b;--gold:#dcb160;--cream:#f3e5d2;--purple:#83118f}
*{box-sizing:border-box}body{margin:0;background:repeating-linear-gradient(130deg,#101014,#101014 4px,#121116 5px);color:var(--cream);font-family:Georgia,serif;min-height:100vh}
header{background:var(--purple);height:33px}main{max-width:600px;margin:auto;padding:29px 18px 65px}.eyebrow{font:700 11px system-ui;letter-spacing:3px;color:var(--gold)}h1{font-size:43px;font-weight:normal;margin:8px 0 3px}p{line-height:1.5;color:#d4c4b8}.panel{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:22px;margin-top:20px}.step{display:flex;align-items:center;gap:14px;margin:12px 0;font:15px system-ui}.num{color:var(--gold);border:1px solid var(--border);width:29px;height:29px;display:grid;place-items:center;border-radius:50%;flex-shrink:0}.picker{display:block;border:1px dashed var(--gold);background:#251922;padding:22px;text-align:center;border-radius:12px;font:16px system-ui;color:var(--cream)}input{margin-top:13px;width:100%;font:14px system-ui}button{font:600 16px system-ui;background:#491b40;color:#fff0e0;border:1px solid var(--gold);border-radius:10px;padding:16px;width:100%;margin-top:18px}button:disabled{opacity:.6}progress{width:100%;height:20px;margin:15px 0;accent-color:var(--gold)}#status{font:14px system-ui;overflow-wrap:anywhere}#count{font:13px system-ui;color:var(--gold)}.note{font:13px system-ui;color:#d9c7a9;border-left:3px solid #815e37;padding-left:12px}
</style></head><body><header></header><main><div class="eyebrow">THE PRIVATE MEDIA ARCHIVE</div><h1>PhotoBridge</h1><p>Send your memories from iPhone to Windows, directly over your home Wi-Fi.</p><section class="panel"><div class="eyebrow">HOW IT WORKS</div><div class="step"><span class="num">1</span><span>Keep PhotoBridge open on your computer.</span></div><div class="step"><span class="num">2</span><span>Choose photos and videos below.</span></div><div class="step"><span class="num">3</span><span>Press Send and keep Safari open.</span></div></section><section class="panel"><div class="eyebrow">SELECT MEDIA</div><label class="picker">Choose photos, videos & GIFs<input id="files" type="file" multiple accept="image/*,video/*,.gif,.heic,.heif,.mov,.mp4"></label><p id="count">No files selected</p><button id="go">Send to computer →</button><progress id="bar" value="0" max="100"></progress><p id="status" role="status" aria-live="polite">Ready to transfer</p></section><p class="note">This is a copy-only transfer. Nothing gets deleted from your phone. Safari might not expose every original Live Photo component. Review your PC copies before deleting anything.</p></main><script>
const f=document.getElementById('files'),b=document.getElementById('go'),s=document.getElementById('status'),p=document.getElementById('bar'),count=document.getElementById('count');
f.onchange=()=>{count.textContent=f.files.length.toLocaleString()+' files selected';p.value=0};
b.onclick=async()=>{if(!f.files.length){alert('Select files first');return}b.disabled=true;let done=0,dupes=0;for(let i=0;i<f.files.length;i++){let x=f.files[i];s.textContent='Sending '+(i+1)+' of '+f.files.length+' — '+x.name;try{let r=await fetch('/upload?key=__KEY__&name='+encodeURIComponent(x.name),{method:'POST',body:x,headers:{'Content-Type':'application/octet-stream'}});if(!r.ok)throw Error(await r.text());if((await r.text()).includes('Duplicate'))dupes++;done++;p.value=Math.round(done*100/f.files.length)}catch(e){s.textContent='Stopped after '+done+' files. '+e.message+'. Keep your originals and try again.';b.disabled=false;return}}s.textContent='Complete: '+done+' files received ('+dupes+' duplicates skipped). Verify them on your computer.';b.disabled=false};
</script></body></html>"""
class Receiver(BaseHTTPRequestHandler):
    def reply(self,code,data,ctype="text/plain"):
        raw=data.encode()
        self.send_response(code);self.send_header("Content-Type",ctype);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def permitted(self):return parse_qs(urlparse(self.path).query).get("key",[""])[0]==KEY
    def do_GET(self):
        if not self.permitted():return self.reply(403,"Denied")
        if urlparse(self.path).path=='/status':
            with LOCK: state={k:dict(v) for k,v in TRANSFERS.items()}
            return self.reply(200,json.dumps(state),'application/json')
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
    GREEN="#201b24"
    DEEP="#101014"
    PANEL="#392036"
    CREAM="#f0e2ce"
    GOLD="#d5aa58"
    MUTED="#bca9b2"
    def __init__(self,root):
        self.root=root
        self.server=None
        self.page="Dashboard"
        self.checked=tk.StringVar(value="No transfer verification performed yet")
        self.link=tk.StringVar(value="Receiver is offline")
        self.folder=tk.StringVar(value=str(DEST))
        self.state=tk.StringVar(value="OFFLINE")
        self.count=tk.StringVar(value="0 saved files")
        self.update_state=tk.StringVar(value="Updates checked automatically")
        root.title("PhotoBridge  |  Media Transfer")
        root.geometry("1040x700")
        root.minsize(840,580)
        root.configure(bg=self.DEEP)
        self.root.option_add("*Font","Segoe UI 10")
        self.sidebar=tk.Frame(root,bg="#161318",width=235)
        self.sidebar.pack(side="left",fill="y")
        self.sidebar.pack_propagate(False)
        tk.Frame(self.sidebar,bg="#83118f",height=13).pack(fill="x")
        tk.Label(self.sidebar,text="PHOTO",bg="#161318",fg=self.CREAM,font=("Georgia",23,"bold"),anchor="w").pack(fill="x",padx=26,pady=(31,0))
        tk.Label(self.sidebar,text="B R I D G E",bg="#161318",fg=self.GOLD,font=("Georgia",13,"bold"),anchor="w").pack(fill="x",padx=27,pady=(0,33))
        for page,mark in [("Dashboard","⌂"),("Transfers","⇄"),("Library","▤"),("Settings","⚙")]:
            tk.Button(self.sidebar,text="  "+mark+"    "+page,anchor="w",bg="#161318",fg=self.CREAM,activebackground="#421c38",activeforeground=self.GOLD,borderwidth=0,highlightthickness=0,padx=19,pady=14,font=("Segoe UI",11),command=lambda p=page:self.show(p)).pack(fill="x",padx=10,pady=2)
        tk.Label(self.sidebar,text="LOCAL TRANSFER  •  v"+VERSION,bg="#161318",fg=self.MUTED,font=("Segoe UI",8)).pack(side="bottom",pady=23)
        self.main=tk.Frame(root,bg="#101014")
        self.main.pack(side="left",fill="both",expand=True)
        self.purple_strip=tk.Frame(self.main,bg="#83118f",height=13)
        self.purple_strip.pack(fill="x")
        self.purple_strip.pack_propagate(False)
        self.header=tk.Frame(self.main,bg="#101014")
        self.header.pack(fill="x",padx=38,pady=(27,15))
        self.heading=tk.Label(self.header,text="Dashboard",bg="#101014",fg=self.CREAM,font=("Georgia",28))
        self.heading.pack(side="left")
        self.chip=tk.Label(self.header,textvariable=self.state,bg="#381a38",fg=self.GOLD,font=("Segoe UI",9,"bold"),padx=12,pady=8)
        self.chip.pack(side="right")
        self.body=tk.Frame(self.main,bg="#101014")
        self.body.pack(fill="both",expand=True,padx=38,pady=(0,22))
        self.show("Dashboard")
        self.root.after(3000,lambda:self.update(False))
        self.root.after(2000,self.refresh)
        root.protocol("WM_DELETE_WINDOW",self.close)
    def panel(self,parent):
        card=tk.Frame(parent,bg="#1a191e",highlightbackground="#624a29",highlightthickness=1,padx=23,pady=21)
        card.pack(fill="x",pady=(0,16))
        return card
    def label(self,parent,text,size=11,fg=None,bold=False):
        w=tk.Label(parent,text=text,bg=parent.cget("bg"),fg=fg or self.CREAM,font=("Georgia" if size>=16 else "Segoe UI",size,"bold" if bold else "normal"),anchor="w",justify="left",wraplength=680)
        w.pack(fill="x",pady=(0,9))
        return w
    def button(self,parent,title,command,primary=True):
        w=tk.Button(parent,text=title,command=command,bg=self.GREEN if primary else "#e8ddc8",fg=self.CREAM if primary else self.GOLD,activebackground=self.PANEL if primary else "#d8cba9",activeforeground=self.CREAM if primary else self.GREEN,relief="flat",borderwidth=0,padx=18,pady=12,font=("Segoe UI",10,"bold"),cursor="hand2")
        w.pack(side="left",padx=(0,9),pady=4)
        return w
    def show(self,page):
        self.page=page
        self.heading.config(text=page)
        for child in self.body.winfo_children():child.destroy()
        if page=="Dashboard":
            self.label(self.body,"Your photos. Your computer. Your control.",20)
            self.label(self.body,"Transfer your iPhone media over your own Wi-Fi, only when you choose.",10,fg="#bba9a9")
            card=self.panel(self.body)
            self.label(card,"RECEIVER CONNECTION",12,bold=True)
            tk.Label(card,textvariable=self.link,bg=card.cget("bg"),fg=self.GREEN,font=("Consolas",10),wraplength=620).pack(anchor="w",pady=8)
            bar=tk.Frame(card,bg=card.cget("bg"));bar.pack(anchor="w",fill="x")
            self.button(bar,"Start / Stop Receiver",self.toggle)
            self.button(bar,"Copy iPhone Link",self.copy,False)
            card=self.panel(self.body)
            self.label(card,"TRANSFER STATUS",12,bold=True)
            tk.Label(card,textvariable=self.count,bg=card.cget("bg"),fg=self.GREEN,font=("Georgia",22,"bold")).pack(anchor="w")
            tk.Label(card,textvariable=self.checked,bg=card.cget("bg"),fg="#bba9a9",wraplength=580).pack(anchor="w",pady=10)
            bar=tk.Frame(card,bg=card.cget("bg"));bar.pack(anchor="w")
            self.button(bar,"View Library",lambda:self.show("Library"))
            self.button(bar,"Verify Saved Files",self.verify,False)
        elif page=="Transfers":
            card=self.panel(self.body)
            self.label(card,"TRANSFER FROM iPHONE",16,bold=True)
            self.label(card,"1. Open PhotoBridge on your computer and start the receiver.\n2. On your iPhone, open the address shown below in Safari.\n3. Select pictures, videos or GIFs, then tap Send to computer.\n4. Leave Safari open until it confirms the transfer.",11)
            tk.Label(card,textvariable=self.link,bg=card.cget("bg"),fg=self.GREEN,font=("Consolas",10),wraplength=620).pack(anchor="w",pady=9)
            row=tk.Frame(card,bg=card.cget("bg"));row.pack(anchor="w")
            self.button(row,"Start / Stop Receiver",self.toggle)
            self.button(row,"Copy iPhone Link",self.copy,False)
            card=self.panel(self.body)
            self.label(card,"IMPORTANT",12,bold=True)
            self.label(card,"Photos remain on your iPhone. Safari only uploads the media you select. Verify the files on this computer, including videos and Live Photos, before deleting originals.",10)
        elif page=="Library":
            card=self.panel(self.body)
            self.label(card,"SAVED MEDIA",16,bold=True)
            self.label(card,"All received files are stored in your chosen Windows folder.")
            row=tk.Frame(card,bg=card.cget("bg"));row.pack(anchor="w")
            self.button(row,"Open Saved Folder",lambda:os.startfile(DEST))
            self.button(row,"Verify Library",self.verify,False)
            self.listbox=tk.Listbox(card,bg="#25232a",fg=self.CREAM,selectbackground="#642c60",relief="flat",height=13,font=("Segoe UI",10),activestyle="none")
            self.listbox.pack(fill="both",expand=True,pady=10)
            self.refresh_list()
            tk.Label(card,textvariable=self.checked,bg=card.cget("bg"),fg="#bba9a9",wraplength=620).pack(anchor="w")
        else:
            card=self.panel(self.body)
            self.label(card,"FILE STORAGE",16,bold=True)
            tk.Label(card,textvariable=self.folder,bg=card.cget("bg"),fg=self.GREEN,wraplength=610).pack(anchor="w",pady=9)
            row=tk.Frame(card,bg=card.cget("bg"));row.pack(anchor="w")
            self.button(row,"Change Storage Folder",self.choose)
            self.button(row,"Open Folder",lambda:os.startfile(DEST),False)
            card=self.panel(self.body)
            self.label(card,"GITHUB UPDATES",16,bold=True)
            self.label(card,"PhotoBridge uses its own update channel in DesktopAppUpdates. New installers are checked and verified before installation.",10)
            tk.Label(card,textvariable=self.update_state,bg=card.cget("bg"),fg="#bba9a9").pack(anchor="w")
            row=tk.Frame(card,bg=card.cget("bg"));row.pack(anchor="w")
            self.button(row,"Check for Updates",lambda:self.update(True))
    def refresh_list(self):
        if not hasattr(self,"listbox") or not self.listbox.winfo_exists():return
        self.listbox.delete(0,"end")
        files=sorted((p for p in DEST.iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix!=".part"),key=lambda p:p.stat().st_mtime,reverse=True)
        for p in files[:2500]:self.listbox.insert("end",p.name+"    ·    "+str(round(p.stat().st_size/1024/1024,1))+" MB")
        if not files:self.listbox.insert("end","No files transferred yet.")
    def refresh(self):
        try:
            files=[p for p in DEST.iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix!=".part"]
            self.count.set(str(len(files))+" saved files")
            if self.page=="Library":self.refresh_list()
        except Exception:pass
        self.root.after(2500,self.refresh)
    def toggle(self):
        if self.server:
            old=self.server;self.server=None
            threading.Thread(target=lambda:(old.shutdown(),old.server_close()),daemon=True).start()
            self.link.set("Receiver is offline");self.state.set("OFFLINE");return
        try:self.server=ThreadingHTTPServer(("0.0.0.0",8765),Receiver)
        except OSError as e:messagebox.showerror("Receiver error",str(e));return
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.link.set("http://"+local_ip()+":8765/?key="+KEY)
        self.state.set("CONNECTED")
    def copy(self):
        if not self.server:return messagebox.showinfo("PhotoBridge","Start the receiver first.")
        self.root.clipboard_clear();self.root.clipboard_append(self.link.get())
        messagebox.showinfo("Link copied","Paste this address into Safari on your iPhone.")
    def choose(self):
        global DEST
        if self.server:return messagebox.showinfo("PhotoBridge","Stop the receiver before changing folders.")
        p=filedialog.askdirectory()
        if p:
            DEST=Path(p);DEST.mkdir(parents=True,exist_ok=True)
            CONFIG.write_text(json.dumps({"folder":str(DEST)}));self.folder.set(p)
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
        result=str(len(idx)-len(bad))+" indexed files verified; "+str(len(bad))+" missing or changed."
        self.checked.set(result)
        messagebox.showinfo("Verification",result+"\n\nVerify that all intended photos and videos were selected and sent before deleting anything from your phone.")
    def update(self,manual):
        self.update_state.set("Checking GitHub...")
        def run():
            try:
                with urllib.request.urlopen(urllib.request.Request(MANIFEST,headers={"User-Agent":"PhotoBridge"}),timeout=12) as response:m=json.load(response)
                ver=lambda x:tuple(int(k) for k in x.split("."))
                if ver(m["version"])<=ver(VERSION):
                    self.root.after(0,lambda:self.update_state.set("PhotoBridge is up to date."))
                    if manual:self.root.after(0,lambda:messagebox.showinfo("Updates","PhotoBridge is up to date."))
                    return
                self.root.after(0,lambda:self.offer(m))
            except Exception as e:
                self.root.after(0,lambda:self.update_state.set("Update check unavailable."))
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
