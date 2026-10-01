from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'catalogue.py'
s=source.read_text(encoding='utf-8')

# Set the Windows process DPI-awareness before Tk is created. This prevents
# Windows from simply bitmap-upscaling the entire window on HiDPI displays.
old="from decimal import Decimal, InvalidOperation\n"
new="""from decimal import Decimal, InvalidOperation

if sys.platform == 'win32':
    try:
        import ctypes
        # PER_MONITOR_AWARE_V2. Fall back gracefully on older Windows versions.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError, ValueError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError, ValueError):
            pass
"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Make high-DPI app logo thumbnails with suitable downsampling.
old="im=Image.open(ASSET).convert('RGBA');im.thumbnail((65,65));photo=ImageTk.PhotoImage(im);self._images.append(photo)"
new="im=Image.open(ASSET).convert('RGBA');im.thumbnail((82,82),Image.Resampling.LANCZOS);photo=ImageTk.PhotoImage(im);self._images.append(photo)"
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Adapt Tk text scaling to Windows' logical DPI, avoiding tiny/soft raster text.
old="        self.font=('Lucida Sans',10);self.small=('Lucida Sans',9);self.heading=('Lucida Sans',23,'bold')"
new="""        try:
            dpi=self.winfo_fpixels('1i')
            self.tk.call('tk','scaling',max(1.0,dpi/72.0))
        except (tk.TclError, ValueError):
            pass
        self.option_add('*Font',('Lucida Sans',10))
        self.font=('Lucida Sans',10);self.small=('Lucida Sans',9);self.heading=('Lucida Sans',23,'bold')"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Decorative, crisp thin rule accents in the sidebar and above summaries.
old="        tk.Frame(self.sidebar,bg=DARK).pack(fill='both',expand=True)"
new="""        footer_rule=tk.Frame(self.sidebar,bg=DARK,height=16)
        footer_rule.pack(side='bottom',fill='x',padx=22,pady=(5,8))
        tk.Frame(footer_rule,bg='#A84F58',height=1).place(relx=0,rely=0.5,relwidth=1)
        self.text(footer_rule,'◆',9,fg='#DEA9AA',bg=DARK).place(relx=.5,rely=.5,anchor='center')
        tk.Frame(self.sidebar,bg=DARK).pack(fill='both',expand=True)"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Attach top-edge burgundy accents to the statistic cards, keeping the cream background.
old="            x=self.panel(top);x.pack(side='left',fill='both',expand=True,padx=(0,8) if i<3 else 0)"
new="""            x=self.panel(top);x.pack(side='left',fill='both',expand=True,padx=(0,8) if i<3 else 0)
            tk.Frame(x,bg=[DARK,RED,ROSE,'#A93D47'][i],height=4).pack(side='top',fill='x')"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Understated section accent for the middle and bottom panels.
old="        self.text(inner,'Subscription Breakdown',13,True,fg=DARK).pack(anchor='w')"
new="""        tk.Frame(inner,bg='#C58186',height=2).pack(fill='x',pady=(0,11))
        self.text(inner,'Subscription Breakdown',13,True,fg=DARK).pack(anchor='w')"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

old="        self.text(il,'Next 7 Days',13,True,fg=DARK).pack(anchor='w')"
new="""        tk.Frame(il,bg='#C58186',height=2).pack(fill='x',pady=(0,11))
        self.text(il,'Next 7 Days',13,True,fg=DARK).pack(anchor='w')"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

old="        head=tk.Frame(ir,bg=PAPER);head.pack(fill='x');self.text(head,'Subscriptions',13,True,fg=DARK).pack(side='left')"
new="""        tk.Frame(ir,bg='#C58186',height=2).pack(fill='x',pady=(0,11))
        head=tk.Frame(ir,bg=PAPER);head.pack(fill='x');self.text(head,'Subscriptions',13,True,fg=DARK).pack(side='left')"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

# Reintroduce a fine editorial separator beneath the masthead.
old="        area=tk.Frame(self.content,bg=CREAM);area.pack(fill='both',expand=True)"
new="""        tk.Frame(self.content,bg=BORDER,height=1).pack(fill='x',padx=31,pady=(0,7))
        area=tk.Frame(self.content,bg=CREAM);area.pack(fill='both',expand=True)"""
assert s.count(old)==1,s.count(old)
s=s.replace(old,new,1)

source.write_text(s,encoding='utf-8')
print('Catalogue typography, scaling, and burgundy styling patch applied')
