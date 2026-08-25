from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.32'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.31': raise SystemExit(f"Expected 0.2.31 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode()); files={f['path']:f for f in p['files']}
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')

# Replace page renderer with an asymmetric bound-book silhouette and stronger gutter depth.
page_pat=re.compile(r'(?s)public class BookPagePanel : Panel \{.*?\n\}\n\npublic class BookTabButton : Button \{')
page_new=r'''public class BookPagePanel : Panel {
    public bool IsLeftPage { get; set; }
    public BookPagePanel() {
        DoubleBuffered = true; AutoScroll = false;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
        Resize += delegate { UpdateRegion(); };
    }
    GraphicsPath PagePath(Rectangle r) {
        GraphicsPath p=new GraphicsPath();
        int outer=18, inner=7;
        if(IsLeftPage){
            p.AddBezier(r.Left+outer,r.Top, r.Left+8,r.Top+2, r.Left+3,r.Top+14, r.Left+3,r.Top+30);
            p.AddLine(r.Left+3,r.Bottom-28);
            p.AddBezier(r.Left+3,r.Bottom-12,r.Left+9,r.Bottom-2,r.Left+outer,r.Bottom);
            p.AddLine(r.Right-inner,r.Bottom-4);
            p.AddBezier(r.Right-2,r.Bottom-18,r.Right-1,r.Top+18,r.Right-inner,r.Top+4);
            p.CloseFigure();
        } else {
            p.AddBezier(r.Left+inner,r.Top+4,r.Left+1,r.Top+18,r.Left+2,r.Bottom-18,r.Left+inner,r.Bottom-4);
            p.AddLine(r.Right-outer,r.Bottom);
            p.AddBezier(r.Right-9,r.Bottom-2,r.Right-3,r.Bottom-12,r.Right-3,r.Bottom-28);
            p.AddLine(r.Right-3,r.Top+30);
            p.AddBezier(r.Right-3,r.Top+14,r.Right-8,r.Top+2,r.Right-outer,r.Top);
            p.CloseFigure();
        }
        return p;
    }
    void UpdateRegion(){if(Width<20||Height<20)return;using(GraphicsPath p=PagePath(new Rectangle(0,0,Width-1,Height-1)))Region=new Region(p);}
    protected override void OnPaintBackground(PaintEventArgs e) {
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        Rectangle r=new Rectangle(0,0,Math.Max(1,Width-1),Math.Max(1,Height-1));
        using(GraphicsPath path=PagePath(r)){
            Color a=IsLeftPage?Color.FromArgb(244,226,188):Color.FromArgb(239,218,178);
            Color b=IsLeftPage?Color.FromArgb(220,188,140):Color.FromArgb(225,194,147);
            using(LinearGradientBrush paper=new LinearGradientBrush(r,a,b,IsLeftPage?5f:175f))e.Graphics.FillPath(paper,path);
            using(Pen edge=new Pen(Color.FromArgb(180,104,72,40),1.25f))e.Graphics.DrawPath(edge,path);
        }
        for(int i=0;i<70;i++){
            int x=13+Math.Abs((i*83+Width*7)%Math.Max(14,Width-26));int y=10+Math.Abs((i*47+Height*5)%Math.Max(12,Height-20));
            using(Brush dot=new SolidBrush(Color.FromArgb(8+(i%4)*3,92,61,34)))e.Graphics.FillEllipse(dot,x,y,(i%3)+1,(i%2)+1);
        }
        using(Pen ornament=new Pen(Color.FromArgb(105,118,78,42),1f)){
            int m=25,l=17;e.Graphics.DrawLine(ornament,m,m,m+l,m);e.Graphics.DrawLine(ornament,m,m,m,m+l);
            e.Graphics.DrawLine(ornament,Width-m,m,Width-m-l,m);e.Graphics.DrawLine(ornament,Width-m,m,Width-m,m+l);
            e.Graphics.DrawLine(ornament,m,Height-m,m+l,Height-m);e.Graphics.DrawLine(ornament,m,Height-m,m,Height-m-l);
            e.Graphics.DrawLine(ornament,Width-m,Height-m,Width-m-l,Height-m);e.Graphics.DrawLine(ornament,Width-m,Height-m,Width-m,Height-m-l);
        }
        Rectangle sh=IsLeftPage?new Rectangle(Math.Max(0,Width-44),0,44,Height):new Rectangle(0,0,44,Height);
        Color dark=Color.FromArgb(118,55,34,20),clear=Color.FromArgb(0,55,34,20);
        using(LinearGradientBrush shadow=IsLeftPage?new LinearGradientBrush(sh,clear,dark,0f):new LinearGradientBrush(sh,dark,clear,0f))e.Graphics.FillRectangle(shadow,sh);
        int sx=IsLeftPage?Width-8:7;
        using(Pen seam=new Pen(Color.FromArgb(120,77,48,28),1f))e.Graphics.DrawLine(seam,sx,14,sx,Height-14);
    }
}

public class BookTabButton : Button {'''
core,n=page_pat.subn(page_new,core,count=1)
if n!=1: raise SystemExit('BookPagePanel block not found')

# Replace tab renderer with outward-pointing leather bookmarks.
tab_pat=re.compile(r'(?s)public class BookTabButton : Button \{.*?\n\}\n\npublic class BookStatusTabButton : Button \{')
tab_new=r'''public class BookTabButton : Button {
    public Color Tone { get; set; }
    public bool ActiveTab { get; set; }
    public bool Mirror { get; set; }
    public BookTabButton(){Tone=Color.FromArgb(91,71,52);FlatStyle=Flat;FlatAppearance.BorderSize=0;Cursor=Cursors.Hand;SetStyle(ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.UserPaint,true);}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;Color t=ActiveTab?ControlPaint.Light(Tone,.22f):Tone;
        int notch=16;
        Point[] pts;
        if(!Mirror)pts=new Point[]{new Point(2,4),new Point(Width-notch,4),new Point(Width-3,Height/2),new Point(Width-notch,Height-4),new Point(2,Height-4)};
        else pts=new Point[]{new Point(Width-3,4),new Point(notch,4),new Point(3,Height/2),new Point(notch,Height-4),new Point(Width-3,Height-4)};
        using(LinearGradientBrush b=new LinearGradientBrush(ClientRectangle,ControlPaint.Light(t,.10f),ControlPaint.Dark(t,.18f),90f))e.Graphics.FillPolygon(b,pts);
        using(Pen edge=new Pen(Color.FromArgb(215,176,126,58),ActiveTab?2.2f:1.2f))e.Graphics.DrawPolygon(edge,pts);
        Rectangle stitch=!Mirror?new Rectangle(8,10,Math.Max(8,Width-notch-15),Math.Max(8,Height-21)):new Rectangle(notch+7,10,Math.Max(8,Width-notch-15),Math.Max(8,Height-21));
        using(Pen st=new Pen(Color.FromArgb(125,235,208,161),1f)){st.DashStyle=DashStyle.Dot;e.Graphics.DrawRectangle(st,stitch);}
        Rectangle tr=!Mirror?new Rectangle(8,2,Width-notch-12,Height-4):new Rectangle(notch+5,2,Width-notch-12,Height-4);
        TextRenderer.DrawText(e.Graphics,Text,Font,tr,Color.FromArgb(248,225,181),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);
    }
}

public class BookStatusTabButton : Button {'''
core,n=tab_pat.subn(tab_new,core,count=1)
if n!=1: raise SystemExit('BookTabButton block not found')

# Add a dedicated leather navigation button control before OrnateButton.
nav_class=r'''
public class LeatherNavButton : Button {
    public bool CurrentCell { get; set; }
    public LeatherNavButton(){FlatStyle=Flat;FlatAppearance.BorderSize=0;Cursor=Cursors.Hand;SetStyle(ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.UserPaint,true);}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;Rectangle r=new Rectangle(1,1,Math.Max(1,Width-3),Math.Max(1,Height-3));
        Color a=CurrentCell?Color.FromArgb(48,31,21):Color.FromArgb(36,23,17);Color b=CurrentCell?Color.FromArgb(27,18,14):Color.FromArgb(20,14,11);
        using(LinearGradientBrush br=new LinearGradientBrush(r,a,b,90f))e.Graphics.FillRectangle(br,r);
        using(Pen p=new Pen(Color.FromArgb(180,157,108,48),1.2f))e.Graphics.DrawRectangle(p,r);
        Rectangle inner=Rectangle.Inflate(r,-5,-5);using(Pen p2=new Pen(Color.FromArgb(72,213,177,101),1f))e.Graphics.DrawRectangle(p2,inner);
        TextRenderer.DrawText(e.Graphics,Text,Font,new Rectangle(8,4,Width-16,Height-8),Color.FromArgb(232,201,145),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.WordBreak|TextFormatFlags.EndEllipsis);
    }
}
'''
if 'public class LeatherNavButton' not in core:
    core=core.replace('\npublic class OrnateButton : Button {',nav_class+'\npublic class OrnateButton : Button {',1)

# Mirror right-side section tabs and prepend restrained glyphs to all section labels.
core=core.replace("$b.Text=$nm; $b.Tag=$nm; $b.Width=138;", "$b.Text=(Get-SectionTabText $nm); $b.Tag=$nm; $b.Width=150;", 2)
# Insert section-tab text helper once.
helper="""function Get-SectionTabText([string]$Name){
    $icons=@{Overview='✥';Appearance='♙';Personality='◌';Background='✦';Family='♣';Relationships='♢';Powers='⚔';Story='☰';Timeline='⌛';Notes='✎'}
    if($icons.ContainsKey($Name)){return ($icons[$Name]+'  '+$Name)}
    return $Name
}
"""
if 'function Get-SectionTabText' not in core:
    idx=core.find("$script:SectionButtons=@{}")
    if idx<0: raise SystemExit('section button construction not found')
    core=core[:idx]+helper+core[idx:]
# Set Mirror on right loop by matching loop header area.
core=core.replace("foreach($nm in $rightNames){\n    try{$b=New-Object BookTabButton; $b.Tone=$tabColors[$i % $tabColors.Count]}","foreach($nm in $rightNames){\n    try{$b=New-Object BookTabButton; $b.Tone=$tabColors[$i % $tabColors.Count]; $b.Mirror=$true}",1)

# Compact Notes layout: remove the large hard-coded vertical deserts.
old_notes="function Render-NotesSection($c,$leftContainer,$rightContainer){\n    $y=10;$y=Render-NotesListEditor $leftContainer 'Aliases' 'ALIASES' $y 160;$y+=10;$y=Render-NotesListEditor $leftContainer 'Tags' 'TAGS' $y 180;$y+=10;Render-ImportantObjectsEditor $leftContainer $y\n    $r=10;$r=Render-MoodBoardEditor $rightContainer $r 330;$r+=10;$r=Render-NotesListEditor $rightContainer 'AestheticTags' 'AESTHETIC TAGS' $r 155;$r+=10;[void](Render-ColorPaletteEditor $rightContainer $r 170)\n}"
new_notes="function Render-NotesSection($c,$leftContainer,$rightContainer){\n    $y=8;$y=Render-NotesListEditor $leftContainer 'Aliases' 'ALIASES' $y 105;$y+=8;$y=Render-NotesListEditor $leftContainer 'Tags' 'TAGS' $y 115;$y+=8;Render-ImportantObjectsEditor $leftContainer $y\n    $r=8;$r=Render-MoodBoardEditor $rightContainer $r 220;$r+=8;$r=Render-NotesListEditor $rightContainer 'AestheticTags' 'AESTHETIC TAGS' $r 105;$r+=8;[void](Render-ColorPaletteEditor $rightContainer $r 120)\n}"
if old_notes not in core: raise SystemExit('Render-NotesSection exact block not found')
core=core.replace(old_notes,new_notes,1)

# Convert bottom nav controls to the dedicated leather cells if their creation uses ordinary Buttons.
for var in ('prevBtn','currentNav','nextBtn'):
    core,n=re.subn(rf'\${var}=New-Object System\.Windows\.Forms\.Button',rf'${var}=New-Object LeatherNavButton',core,count=1)
    if n!=1: raise SystemExit(f'{var} creation not found')
# Current cell receives subtly different fill.
core=core.replace("$currentNav=New-Object LeatherNavButton;", "$currentNav=New-Object LeatherNavButton; $currentNav.CurrentCell=$true;",1)
# Widen/strengthen nav font if exact assignments exist.
core=core.replace("$prevBtn.Font=$script:FontSmall", "$prevBtn.Font=$script:FontSerif")
core=core.replace("$currentNav.Font=$script:FontSmall", "$currentNav.Font=$script:FontSerif")
core=core.replace("$nextBtn.Font=$script:FontSmall", "$nextBtn.Font=$script:FontSerif")

# Make the central gutter visually deeper regardless of panel painting.
core=core.replace("$gutter.BackColor=[System.Drawing.Color]::FromArgb(58,38,25)","$gutter.BackColor=[System.Drawing.Color]::FromArgb(31,18,12)",1)

# Ensure page-turn calls remain inert: visual reference explicitly excludes page turning.
anim=re.search(r'(?ms)^function Animate-BookPages\([^\n]*\) \{.*?^\}',core)
if anim:
    core=core[:anim.start()]+"function Animate-BookPages([int]$Direction,[int]$Count,[bool]$Whole=$false) { return }"+core[anim.end():]

raw=core.encode('utf-8-sig')
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode();files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'));app['version']=VERSION;files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode()).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']);f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION;p['files']=list(files.values());out=json.dumps(p,separators=(',',':')).encode();name='payload-0.2.32-visual-geometry-part-001.txt';(TF/name).write_bytes(out);sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    data=base64.b64decode(f['contentBase64']);assert hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
assert gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))==raw
checks={'asymmetricBookPages':'GraphicsPath PagePath' in core,'deepGutter':"FromArgb(31,18,12)" in core,'shapedLeatherTabs':'public bool Mirror' in core,'rightTabsMirrored':'$b.Mirror=$true' in core,'sectionTabIcons':'function Get-SectionTabText' in core,'leatherBottomNav':'public class LeatherNavButton' in core,'compactNotes':"Render-MoodBoardEditor $rightContainer $r 220" in core,'pageTurnDisabled':"function Animate-BookPages([int]$Direction,[int]$Count,[bool]$Whole=$false) { return }" in core,'bookMasterSkinPreserved':'function Apply-BookMasterSkin' in core,'notesPreserved':'function Render-NotesSection' in core,'timelinePreserved':'function Render-TimelineSection' in core,'storyPreserved':"'Story' = @(" in core,'powersPreserved':'function Render-PowersSection' in core,'userDataSeparate':"TheFiles\\Data" in core,'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True}
if not all(checks.values()): raise SystemExit('checks failed '+str(checks))
val={'version':VERSION,'baseVersion':'0.2.31','payload':name,'payloadSha256':sha,'requirements':checks}
(TF/'visual-geometry-0.2.32-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.visual-v0232-validation';vd.mkdir(exist_ok=True);(vd/'TheFilesCore.ps1').write_bytes(raw);(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
print(json.dumps(val,indent=2))
