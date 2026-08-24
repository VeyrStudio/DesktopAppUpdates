# The Files Desktop — v0.2.6
# Offline-first character book / character-sheet manager.
# User data lives in %LOCALAPPDATA%\TheFiles\Data and is never stored beside app code.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()


# Rich painted controls keep the book visual detailed without shipping a heavy image skin.
try {
    Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;

public class BookDeskPanel : Panel {
    public BookDeskPanel() {
        DoubleBuffered = true;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
    }
    protected override void OnPaintBackground(PaintEventArgs e) {
        using (LinearGradientBrush b = new LinearGradientBrush(ClientRectangle, Color.FromArgb(20,16,13), Color.FromArgb(49,31,20), 16f))
            e.Graphics.FillRectangle(b, ClientRectangle);
        using (Pen grain = new Pen(Color.FromArgb(26,190,145,92), 1f)) {
            int step = 31;
            for (int y = 10; y < Height; y += step) {
                int wobble = (y * 17) % 13;
                e.Graphics.DrawBezier(grain, -20, y, Width/3, y-2-wobble/4, Width*2/3, y+3+wobble/5, Width+20, y-1);
            }
        }
        using (Pen edge = new Pen(Color.FromArgb(110,8,6,5), 2f)) e.Graphics.DrawRectangle(edge, 1,1,Math.Max(1,Width-3),Math.Max(1,Height-3));
    }
}

public class BookContentPanel : Panel {
    public BookContentPanel() {
        DoubleBuffered=true; AutoScroll=true;
        SetStyle(ControlStyles.SupportsTransparentBackColor | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        BackColor=Color.Transparent;
    }
}

public class BookFramePanel : Panel {
    public BookFramePanel() {
        DoubleBuffered = true;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
        BackColor = Color.FromArgb(62,40,27);
    }
    GraphicsPath RR(Rectangle r, int rad) {
        GraphicsPath p = new GraphicsPath(); int d = rad*2;
        p.AddArc(r.X,r.Y,d,d,180,90); p.AddArc(r.Right-d,r.Y,d,d,270,90);
        p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90); p.AddArc(r.X,r.Bottom-d,d,d,90,90); p.CloseFigure(); return p;
    }
    protected override void OnPaintBackground(PaintEventArgs e) {
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        Rectangle r = new Rectangle(2,2,Math.Max(1,Width-5),Math.Max(1,Height-5));
        using (GraphicsPath p = RR(r,22))
        using (LinearGradientBrush b = new LinearGradientBrush(r, Color.FromArgb(92,53,29), Color.FromArgb(42,27,20), 90f)) {
            e.Graphics.FillPath(b,p);
            using (Pen border = new Pen(Color.FromArgb(150,118,73,37),3f)) e.Graphics.DrawPath(border,p);
            Rectangle r2 = Rectangle.Inflate(r,-10,-10);
            using (GraphicsPath p2=RR(r2,16)) using(Pen gold=new Pen(Color.FromArgb(130,190,146,73),1f)) e.Graphics.DrawPath(gold,p2);
        }
        // Layered page-block edges visible beneath the current spread.
        using (Pen pg1 = new Pen(Color.FromArgb(90,216,191,145),1f))
        using (Pen pg2 = new Pen(Color.FromArgb(70,117,87,55),1f)) {
            for(int i=0;i<9;i++) {
                int yy = Height-20-i*2;
                e.Graphics.DrawLine((i%2==0)?pg1:pg2, 35, yy, Math.Max(36,Width-35), yy);
            }
            for(int i=0;i<7;i++) {
                e.Graphics.DrawLine((i%2==0)?pg1:pg2, 18+i*2, 35, 18+i*2, Math.Max(36,Height-32));
                e.Graphics.DrawLine((i%2==0)?pg1:pg2, Width-19-i*2, 35, Width-19-i*2, Math.Max(36,Height-32));
            }
        }
    }
}

public class BookPagePanel : Panel {
    public bool IsLeftPage { get; set; }
    public BookPagePanel() {
        DoubleBuffered = true; AutoScroll = false;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
        Resize += delegate { UpdateRegion(); };
    }
    GraphicsPath RR(Rectangle r, int rad) {
        GraphicsPath p = new GraphicsPath(); int d = rad*2;
        p.AddArc(r.X,r.Y,d,d,180,90); p.AddArc(r.Right-d,r.Y,d,d,270,90);
        p.AddArc(r.Right-d,r.Bottom-d,d,d,0,90); p.AddArc(r.X,r.Bottom-d,d,d,90,90); p.CloseFigure(); return p;
    }
    void UpdateRegion() { if(Width<10||Height<10)return; using(GraphicsPath p=RR(new Rectangle(0,0,Width,Height),12)) Region=new Region(p); }
    protected override void OnPaintBackground(PaintEventArgs e) {
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        Rectangle r = ClientRectangle;
        Color a = IsLeftPage ? Color.FromArgb(244,226,188) : Color.FromArgb(239,218,178);
        Color b = IsLeftPage ? Color.FromArgb(228,201,157) : Color.FromArgb(232,207,164);
        using (LinearGradientBrush paper = new LinearGradientBrush(r,a,b,IsLeftPage?7f:173f)) e.Graphics.FillRectangle(paper,r);
        // Subtle paper fibres/speckling. Deterministic, so it never flickers during repaint.
        for(int i=0;i<55;i++) {
            int x = 10 + Math.Abs((i*83 + Width*7) % Math.Max(11,Width-20));
            int y = 8 + Math.Abs((i*47 + Height*5) % Math.Max(9,Height-16));
            int alpha = 10 + (i%4)*3;
            using(Brush dot=new SolidBrush(Color.FromArgb(alpha,95,66,38))) e.Graphics.FillEllipse(dot,x,y,(i%3)+1,(i%2)+1);
        }
        // Very faint old stains.
        using(Brush stain=new SolidBrush(Color.FromArgb(10,126,77,39))) {
            e.Graphics.FillEllipse(stain, Width/7, Height/5, Math.Max(24,Width/4), Math.Max(18,Height/7));
            e.Graphics.FillEllipse(stain, Width*3/5, Height*3/4, Math.Max(18,Width/5), Math.Max(16,Height/8));
        }
        using(Pen outer=new Pen(Color.FromArgb(145,111,79,49),1f)) e.Graphics.DrawRectangle(outer,8,8,Math.Max(1,Width-17),Math.Max(1,Height-17));
        using(Pen inner=new Pen(Color.FromArgb(85,154,116,69),1f)) e.Graphics.DrawRectangle(inner,13,13,Math.Max(1,Width-27),Math.Max(1,Height-27));
        // Small archival corner ornaments.
        using(Pen ornament=new Pen(Color.FromArgb(100,116,80,44),1f)) {
            int m=22, l=18;
            e.Graphics.DrawLine(ornament,m,m,m+l,m); e.Graphics.DrawLine(ornament,m,m,m,m+l);
            e.Graphics.DrawLine(ornament,Width-m,m,Width-m-l,m); e.Graphics.DrawLine(ornament,Width-m,m,Width-m,m+l);
            e.Graphics.DrawLine(ornament,m,Height-m,m+l,Height-m); e.Graphics.DrawLine(ornament,m,Height-m,m,Height-m-l);
            e.Graphics.DrawLine(ornament,Width-m,Height-m,Width-m-l,Height-m); e.Graphics.DrawLine(ornament,Width-m,Height-m,Width-m,Height-m-l);
        }
        // Gutter shadow gives the flat spread physical depth without an animated turning page.
        Rectangle sh = IsLeftPage ? new Rectangle(Math.Max(0,Width-28),0,28,Height) : new Rectangle(0,0,28,Height);
        Color sc1 = Color.FromArgb(70,54,35,21), sc2 = Color.FromArgb(0,54,35,21);
        using(LinearGradientBrush shadow = IsLeftPage ? new LinearGradientBrush(sh,sc2,sc1,0f) : new LinearGradientBrush(sh,sc1,sc2,0f)) e.Graphics.FillRectangle(shadow,sh);
    }
}

public class BookTabButton : Button {
    public Color Tone { get; set; }
    public bool ActiveTab { get; set; }
    public BookTabButton() {
        Tone = Color.FromArgb(91,71,52); FlatStyle=Flat; FlatAppearance.BorderSize=0; Cursor=Cursors.Hand;
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint, true);
    }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        Rectangle r=new Rectangle(2,2,Math.Max(1,Width-5),Math.Max(1,Height-5));
        Color t=ActiveTab?ControlPaint.Light(Tone,.25f):Tone;
        using(LinearGradientBrush b=new LinearGradientBrush(r,ControlPaint.Light(t,.10f),ControlPaint.Dark(t,.10f),90f)) e.Graphics.FillRectangle(b,r);
        using(Pen edge=new Pen(Color.FromArgb(185,184,139,69),ActiveTab?2f:1f)) e.Graphics.DrawRectangle(edge,r);
        using(Pen stitch=new Pen(Color.FromArgb(120,236,211,168),1f)){stitch.DashStyle=DashStyle.Dot;e.Graphics.DrawRectangle(stitch,7,7,Math.Max(1,Width-15),Math.Max(1,Height-15));}
        TextRenderer.DrawText(e.Graphics,Text,Font,r,Color.FromArgb(246,226,191),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);
    }
}

public class BookStatusTabButton : Button {
    public bool ActiveTab { get; set; }
    public BookStatusTabButton(){FlatStyle=Flat;FlatAppearance.BorderSize=0;Cursor=Cursors.Hand;SetStyle(ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.UserPaint,true);}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        Point[] pts=new Point[]{new Point(8,Height-2),new Point(8,12),new Point(22,3),new Point(Width-22,3),new Point(Width-8,12),new Point(Width-8,Height-2)};
        Color c=ActiveTab?Color.FromArgb(236,210,163):Color.FromArgb(191,150,94);
        using(Brush b=new SolidBrush(c))e.Graphics.FillPolygon(b,pts);
        using(Pen p=new Pen(Color.FromArgb(164,108,68,36),1.5f))e.Graphics.DrawPolygon(p,pts);
        TextRenderer.DrawText(e.Graphics,Text,Font,new Rectangle(7,8,Width-14,Height-10),Color.FromArgb(62,43,28),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);
    }
}

public class OrnateButton : Button {
    public OrnateButton(){FlatStyle=Flat;FlatAppearance.BorderSize=0;Cursor=Cursors.Hand;SetStyle(ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.UserPaint,true);}
    protected override void OnPaint(PaintEventArgs e){
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        Rectangle r=new Rectangle(1,1,Math.Max(1,Width-3),Math.Max(1,Height-3));
        using(LinearGradientBrush b=new LinearGradientBrush(r,Color.FromArgb(235,211,168),Color.FromArgb(203,171,117),90f))e.Graphics.FillRectangle(b,r);
        using(Pen p=new Pen(Color.FromArgb(150,105,70,39),1f))e.Graphics.DrawRectangle(p,r);
        TextRenderer.DrawText(e.Graphics,Text,Font,r,Color.FromArgb(58,40,27),TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);
    }
}
"@ -ErrorAction Stop
} catch {}


$script:AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:DataRoot = Join-Path $env:LOCALAPPDATA 'TheFiles\Data'
$script:MediaRoot = Join-Path $script:DataRoot 'Media'
$script:CharactersPath = Join-Path $script:DataRoot 'characters.json'
$script:SettingsPath = Join-Path $script:DataRoot 'settings.json'
$script:VersionPath = Join-Path $script:AppRoot 'AppVersion.json'
$script:UpdateHostPath = Join-Path $script:AppRoot 'RemoteUpdateHost.ps1'
$script:UpdateAppDir = $script:AppRoot
$script:UpdateDataDir = $script:DataRoot
$script:UpdateLauncherPath = Join-Path $script:AppRoot 'Launch The Files.vbs'
$script:UpdateExpectedMain = 'TheFiles.ps1'
$script:UpdateWorkRoot = Join-Path $script:DataRoot 'Updates'
$script:UpdateAppId = 'the-files'
$script:UpdateAppName = 'The Files'
$script:CurrentAppVersion = '0.2.15'
$script:UpdateManifestUrl = 'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'

New-Item -ItemType Directory -Force -Path $script:DataRoot | Out-Null
New-Item -ItemType Directory -Force -Path $script:MediaRoot | Out-Null

function Show-Info([string]$Message) {
    [System.Windows.Forms.MessageBox]::Show($Message,'The Files',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
}
function Show-Error([string]$Message) {
    [System.Windows.Forms.MessageBox]::Show($Message,'The Files',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
}
function Show-Confirm([string]$Message) {
    return [System.Windows.Forms.MessageBox]::Show($Message,'The Files',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Question)
}

try {
    if (Test-Path -LiteralPath $script:VersionPath) {
        $vc = Get-Content -LiteralPath $script:VersionPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$vc.appId -eq $script:UpdateAppId) {
            if (-not [string]::IsNullOrWhiteSpace([string]$vc.version)) { $script:CurrentAppVersion = [string]$vc.version }
            if (-not [string]::IsNullOrWhiteSpace([string]$vc.manifestUrl)) { $script:UpdateManifestUrl = [string]$vc.manifestUrl }
        }
    }
} catch {}

$script:Parchment = [System.Drawing.Color]::FromArgb(239,221,183)
$script:Parchment2 = [System.Drawing.Color]::FromArgb(232,211,169)
$script:Ink = [System.Drawing.Color]::FromArgb(55,39,28)
$script:Dark = [System.Drawing.Color]::FromArgb(25,22,19)
$script:Dark2 = [System.Drawing.Color]::FromArgb(38,31,25)
$script:Gold = [System.Drawing.Color]::FromArgb(188,148,78)
$script:Leather = [System.Drawing.Color]::FromArgb(74,48,31)
$script:Muted = [System.Drawing.Color]::FromArgb(112,90,66)
$script:SelectedTab = [System.Drawing.Color]::FromArgb(126,86,50)
$script:FontSerif = New-Object System.Drawing.Font('Georgia',10)
$script:FontSmall = New-Object System.Drawing.Font('Georgia',9)
$script:FontHeading = New-Object System.Drawing.Font('Georgia',16,[System.Drawing.FontStyle]::Bold)
$script:FontTitle = New-Object System.Drawing.Font('Georgia',26,[System.Drawing.FontStyle]::Bold)
$script:FontTab = New-Object System.Drawing.Font('Georgia',10,[System.Drawing.FontStyle]::Bold)

$script:FieldDefs = [ordered]@{
    'Overview' = @(
        @{Key='FullName';Label='Full Name';Type='Text'},
        @{Key='Nicknames';Label='Nickname';Type='Text'},
        @{Key='StoryTitle';Label='Story Title';Type='Text'},
        @{Key='Partner';Label='Love Interest';Type='Text'},
        @{Key='CharacterRole';Label='Character Role';Type='Choice';Options=@('Main Character','Secondary Main','Supporting Character','Love Interest','Antagonist','Villain','Rival','Mentor','Sidekick','Minor Character','Background Character','Other')},
        @{Key='LifeStatus';Label='Status';Type='Choice';Options=@('Alive','Dead','Missing','Unknown','Undead','Other')},
        @{Key='Pronouns';Label='Pronouns';Type='Text'},
        @{Key='Gender';Label='Gender';Type='Text'},
        @{Key='Age';Label='Age';Type='Text'},
        @{Key='Birthday';Label='Birthday';Type='Text'},
        @{Key='Species';Label='Species';Type='Text'},
        @{Key='Residence';Label='Residence';Type='Text'},
        @{Key='FreedomStatus';Label='Freedom Status';Type='Choice';Options=@('Free','Restricted','Confined','Detained','Imprisoned','Captive','Under Guard','House Arrest','Institutionalized','Missing / Unknown','Other')},
        @{Key='Occupation';Label='Occupation';Type='Text'},
        @{Key='SocialStatus';Label='Social Status';Type='Choice';Options=@('Lower Class','Working Class','Middle Class','Upper Class','Wealthy','Elite','Aristocracy / Nobility','Royalty','Outcast','Social Pariah','Unknown','Other')}
    )
    'Appearance' = @(
        @{Key='HairColor';Label='Hair Color';Type='Swatch';Options=@('Black','Dark Brown','Brown','Light Brown','Auburn','Red','Strawberry Blonde','Blonde','Platinum Blonde','Gray','White','Dyed / Fantasy','Multicolored','Custom','Unknown')},
        @{Key='EyeColor';Label='Eye Color';Type='Swatch';Options=@('Brown','Dark Brown','Hazel','Amber','Green','Blue','Gray','Blue-Gray','Green-Gray','Heterochromia','Custom','Unknown')},
        @{Key='SkinTone';Label='Skin Tone';Type='Swatch';Options=@('Very Fair','Fair','Light','Light-Medium','Medium','Medium-Tan','Tan','Medium-Brown','Brown','Deep Brown','Very Deep','Albinism','Custom','Unknown')},
        @{Key='Scars';Label='Scars';Type='Multi'},
        @{Key='HealthNotes';Label='Health Notes';Type='Multi'},
        @{Key='PhysicalDescription';Label='Full Physical Description';Type='Large'}
    )
    'Personality' = @(
        @{Key='CorePersonality';Label='Core Personality';Type='MultiChoice';Options=@('Reserved','Outgoing','Introverted','Extroverted','Calm','Intense','Gentle','Assertive','Cautious','Impulsive','Optimistic','Pessimistic','Pragmatic','Idealistic','Logical','Emotional','Empathetic','Detached','Trusting','Suspicious','Independent','Dependent','Adaptable','Stubborn','Patient','Impatient','Serious','Playful','Confident','Insecure','Easygoing','High-Strung','Rebellious','Dutiful','Competitive','Cooperative','Private','Open','Protective','Nurturing','Dominant','Submissive','Curious','Cynical','Other / Custom')},
        @{Key='PositiveTraits';Label='Positive Traits';Type='MultiChoice';Options=@('Adaptable','Brave','Calm','Compassionate','Confident','Cooperative','Creative','Curious','Dependable','Determined','Diplomatic','Disciplined','Empathetic','Forgiving','Generous','Honest','Humble','Independent','Kind','Loyal','Observant','Open-Minded','Optimistic','Patient','Protective','Reliable','Resilient','Resourceful','Responsible','Selfless','Thoughtful','Trustworthy','Other / Custom')},
        @{Key='NegativeTraits';Label='Negative Traits';Type='MultiChoice';Options=@('Arrogant','Avoidant','Controlling','Cruel','Cynical','Defensive','Detached','Dishonest','Hot-Tempered','Impatient','Impulsive','Insecure','Jealous','Judgmental','Manipulative','Naive','Obsessive','Overprotective','Passive-Aggressive','Pessimistic','Possessive','Prideful','Reckless','Secretive','Self-Destructive','Selfish','Stubborn','Suspicious','Unreliable','Vindictive','Other / Custom')},
        @{Key='Strengths';Label='Strengths';Type='MultiChoice';Options=@('Adaptability','Bravery','Communication','Creativity','Discipline','Emotional Resilience','Empathy','Endurance','Focus','Improvisation','Independence','Leadership','Loyalty','Negotiation','Observation','Patience','Problem-Solving','Protectiveness','Quick Thinking','Resourcefulness','Self-Control','Strategic Thinking','Teamwork','Other / Custom')},
        @{Key='Weaknesses';Label='Weaknesses';Type='MultiChoice';Options=@('Avoids Conflict','Confrontational','Difficulty Asking for Help','Fear of Vulnerability','Holds Grudges','Impulsive','Indecisive','Jealousy','Need for Control','Overconfidence','Overly Self-Sacrificing','Poor Boundaries','Poor Communication','Poor Impulse Control','Pride','Recklessness','Secretive','Self-Doubt','Stubbornness','Trust Issues','Other / Custom')},
        @{Key='Likes';Label='Likes';Type='MultiChoice';Options=@('Animals','Art','Books','Cities','Cold Weather','Competition','Cooking','Crowds','Dancing','Food','Forests','Games','Gardening','History','Learning','Music','Nature','Nighttime','Parties','Rain','Routine','Silence','Solitude','Sports','Storms','Sunlight','Technology','Travel','Warm Weather','Water / Ocean','Other / Custom')},
        @{Key='Dislikes';Label='Dislikes';Type='MultiChoice';Options=@('Animals','Authority','Chaos','Cold Weather','Conflict','Crowds','Dishonesty','Heat','Hospitals','Loud Noise','Mess','Nature','Physical Contact','Routine','Rules','Silence','Small Talk','Social Events','Spicy Food','Technology','Travel','Violence','Waiting','Water / Ocean','Other / Custom')},
        @{Key='Fears';Label='Fears';Type='MultiChoice';Options=@('Abandonment','Being Forgotten','Being Trapped','Change','Crowds','Darkness','Death','Failure','Heights','Illness','Intimacy','Isolation','Losing Control','Losing Loved Ones','Pain','Powerlessness','Public Humiliation','Rejection','The Unknown','Water / Drowning','Becoming Like Someone They Hate','Other / Custom')},
        @{Key='PetPeeves';Label='Pet Peeves';Type='MultiChoice';Options=@('Arrogance','Being Ignored','Being Interrupted','Being Lied To','Being Touched Without Permission','Disorganization','Dishonesty','Incompetence','Interruptions','Invading Personal Space','Lateness','Loud Chewing','Messiness','People Touching Their Things','Poor Manners','Repetition','Small Talk','Unnecessary Noise','Wasted Food','Other / Custom')}
    )
    'Background' = @(
        @{Key='Childhood';Label='Childhood';Type='MultiChoice';Options=@('Stable','Loving','Happy','Privileged','Sheltered','Strict','Religious','Rural','Urban','Nomadic','Poor','Unstable','Chaotic','Neglectful','Abusive','Isolated','Lonely','Orphaned','Foster Care','Institutionalized','Raised by Relatives','Single-Parent Household','Large Family','Only Child','Parentified','Military Family','Frequently Relocated','Homeless / Housing Insecure','War / Conflict','Persecution','Criminal Environment','Traumatic','Other / Custom','Unknown')},
        @{Key='Education';Label='Education';Type='EditChoice';Options=@('No Formal Education','Primary / Elementary Education','Some Secondary / High School','High School Diploma / GED','Trade / Vocational School','Apprenticeship','Some College / University','Associate Degree / Equivalent','Bachelor Degree / Equivalent','Graduate Degree','Doctorate / Professional Degree','Military Training','Religious Education','Private Tutoring','Homeschooled','Self-Taught','Other / Custom','Unknown')},
        @{Key='PastOccupations';Label='Past Occupation';Type='EditChoice';Options=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')},
        @{Key='MajorLifeEvents';Label='Major Life Events';Type='LifeEvents';Options=@('Loss / Death','Birth / New Family Member','Marriage / Partnership','Breakup / Divorce','Friendship Change','Betrayal','Abandonment','Abuse','Neglect','Poverty / Financial Hardship','Homelessness / Displacement','Illness / Diagnosis','Serious Injury','Disability / Health Change','Accident','Disaster','War / Armed Conflict','Persecution / Discrimination','Crime / Violence','Arrest / Legal Trouble','Imprisonment / Captivity','Escape / Rescue','Major Move / Relocation','Immigration / Exile','Education Milestone','Career Change','Major Achievement / Award','Skill Mastery','Leadership / Promotion','Failure / Defeat','Missed Opportunity','Broken Promise','Hurt Someone','Failed to Act','Crime They Committed','Secret Revealed','Major Discovery','Joined / Left a Group','Religious / Belief Change','Identity / Self-Discovery','Supernatural Event','Near-Death Experience','Other Hardship / Trauma','Regret / Past Mistake','Other / Custom')},
        @{Key='Secrets';Label='Secrets';Type='Large'}
    )
    'Family' = @(
        @{Key='Parent1Name';Label='Parent One — Name';Type='Text'},
        @{Key='Parent1Gender';Label='Parent One — Gender';Type='Choice';Options=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')},
        @{Key='Parent1Type';Label='Parent One — Parent Type';Type='Choice';Options=@('Mother','Father','Parent','Biological Parent','Adoptive Parent','Step-Parent','Foster Parent','Guardian','Spouse','Other')},
        @{Key='Parent1Spouse';Label='Parent One — Spouse / Partner';Type='Text'},
        @{Key='Parent1Status';Label='Parent One — Status';Type='Choice';Options=@('Alive','Dead','Missing','Estranged','Unknown','Other')},
        @{Key='Parent1Occupation';Label='Parent One — Occupation';Type='EditChoice';Options=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')},
        @{Key='Parent1Relationship';Label='Parent One — Relationship Dynamic';Type='MultiChoice';Options=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')},
        @{Key='Parent1Notes';Label='Parent One — Notes';Type='Multi'},
        @{Key='Parent2Name';Label='Parent Two — Name';Type='Text'},
        @{Key='Parent2Gender';Label='Parent Two — Gender';Type='Choice';Options=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')},
        @{Key='Parent2Type';Label='Parent Two — Parent Type';Type='Choice';Options=@('Mother','Father','Parent','Biological Parent','Adoptive Parent','Step-Parent','Foster Parent','Guardian','Spouse','Other')},
        @{Key='Parent2Spouse';Label='Parent Two — Spouse / Partner';Type='Text'},
        @{Key='Parent2Status';Label='Parent Two — Status';Type='Choice';Options=@('Alive','Dead','Missing','Estranged','Unknown','Other')},
        @{Key='Parent2Occupation';Label='Parent Two — Occupation';Type='EditChoice';Options=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')},
        @{Key='Parent2Relationship';Label='Parent Two — Relationship Dynamic';Type='MultiChoice';Options=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')},
        @{Key='Parent2Notes';Label='Parent Two — Notes';Type='Multi'},
        @{Key='Siblings';Label='Siblings';Type='FamilyJson'},
        @{Key='Children';Label='Children';Type='FamilyJson'},
        @{Key='OtherFamily';Label='Other Family';Type='FamilyJson'},
        @{Key='FamilyHistory';Label='Important Family History';Type='FamilyHistory'},
        @{Key='FamilyTree';Label='Family Tree / Family Structure';Type='Hidden'}
    )
    'Relationships' = @(
        @{Key='Partner';Label='Partner / Love Interest';Type='Text'},
        @{Key='RelationshipStatus';Label='Relationship Status';Type='Choice';Options=@('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','Complicated / Unclear','Unknown','Other / Custom')},
        @{Key='Sexuality';Label='Sexuality';Type='Choice';Options=@('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown','Other / Custom')},
        @{Key='Friends';Label='Friends';Type='RelationshipJson'},
        @{Key='Enemies';Label='Enemies';Type='RelationshipJson'},
        @{Key='Mentors';Label='Mentors';Type='RelationshipJson'}
    )
    'Skills' = @(
        @{Key='NaturalTalents';Label='Natural Talents';Type='Multi'},
        @{Key='LearnedSkills';Label='Learned Skills';Type='Large'},
        @{Key='CombatSkills';Label='Combat Skills';Type='Large'},
        @{Key='ProfessionalSkills';Label='Professional Skills';Type='Large'},
        @{Key='Languages';Label='Languages';Type='Multi'},
        @{Key='Powers';Label='Powers / Supernatural Abilities';Type='Large'},
        @{Key='PowerLimits';Label='Power Limitations';Type='Large'},
        @{Key='SupernaturalWeaknesses';Label='Supernatural Weaknesses';Type='Large'},
        @{Key='Equipment';Label='Equipment';Type='Large'},
        @{Key='Weapons';Label='Weapons';Type='Large'}
    )
    'Psychology' = @(
        @{Key='SelfImage';Label='Self-Image';Type='Large'},
        @{Key='Worldview';Label='Worldview';Type='Large'},
        @{Key='MoralBeliefs';Label='Moral Beliefs';Type='Large'},
        @{Key='MoralLeaning';Label='Moral Leaning / Alignment';Type='Multi'},
        @{Key='Boundaries';Label='Boundaries';Type='Large'},
        @{Key='Coping';Label='Coping Mechanisms';Type='Large'},
        @{Key='DefenseMechanisms';Label='Defense Mechanisms';Type='Large'},
        @{Key='Insecurities';Label='Insecurities';Type='Large'},
        @{Key='Triggers';Label='Emotional Triggers';Type='Large'},
        @{Key='Refuses';Label='Things They Refuse to Do';Type='Large'},
        @{Key='RuleBreakingTrigger';Label='What Could Make Them Break Those Rules';Type='Large'},
        @{Key='GreatestDesire';Label='Greatest Desire';Type='Large'},
        @{Key='GreatestFear';Label='Greatest Fear';Type='Large'},
        @{Key='BreakingPoint';Label='Breaking Point';Type='Large'},
        @{Key='CoreBelief';Label='Core Belief';Type='Large'},
        @{Key='FalseBelief';Label='False Belief';Type='Large'}
    )
    'Story' = @(
        @{Key='StoryTitle';Label='Story Title';Type='Text'},
        @{Key='CharacterTier';Label='Character Tier';Type='Choice';Options=@('Primary','Secondary','Tertiary','Minor','Background')},
        @{Key='StoryRole';Label='Story Role';Type='Choice';Options=@('Protagonist','Love Interest','Antagonist','Deuteragonist','Supporting','Mentor','Rival','Confidant','Comic Relief','Other')},
        @{Key='POVStatus';Label='POV Status';Type='Choice';Options=@('Main POV','Occasional POV','Never POV','Unknown')},
        @{Key='FirstAppearance';Label='First Appearance';Type='Text'},
        @{Key='LastAppearance';Label='Last Appearance';Type='Text'},
        @{Key='MainGoal';Label='Main Goal';Type='Large'},
        @{Key='ShortGoal';Label='Short-Term Goal';Type='Large'},
        @{Key='LongGoal';Label='Long-Term Goal';Type='Large'},
        @{Key='Motivation';Label='Motivation';Type='Large'},
        @{Key='ThinkTheyWant';Label='What They Think They Want';Type='Large'},
        @{Key='ActuallyNeed';Label='What They Actually Need';Type='Large'},
        @{Key='AbandonGoal';Label='What Would Make Them Abandon Their Goal';Type='Large'},
        @{Key='InternalConflict';Label='Internal Conflict';Type='Large'},
        @{Key='ExternalConflict';Label='External Conflict';Type='Large'},
        @{Key='RelationshipConflict';Label='Relationship Conflict';Type='Large'},
        @{Key='FatalFlaw';Label='Fatal Flaw / Major Weakness';Type='Large'},
        @{Key='ArcType';Label='Arc Type';Type='Choice';Options=@('Positive Change','Negative Change','Flat','Redemption','Corruption','Tragic','Disillusionment','Other')},
        @{Key='StartingState';Label='Beginning State';Type='Large'},
        @{Key='MiddleState';Label='Middle State';Type='Large'},
        @{Key='TurningPoints';Label='Major Turning Points';Type='Large'},
        @{Key='EndingState';Label='Ending State';Type='Large'},
        @{Key='ImportantScenes';Label='Important Scenes';Type='Large'},
        @{Key='PlotRelevance';Label='Plot Relevance';Type='Large'}
    )
    'Timeline' = @(
        @{Key='Timeline';Label='Life / Story Timeline';Type='Large'}
    )
    'Notes' = @(
        @{Key='Aliases';Label='Aliases / Former Names / Titles';Type='Multi'},
        @{Key='Tags';Label='Tags';Type='Multi'},
        @{Key='Quotes';Label='Quotes';Type='Large'},
        @{Key='Playlist';Label='Playlist / Theme Songs';Type='Large'},
        @{Key='Aesthetic';Label='Aesthetic / Moodboard Notes';Type='Large'},
        @{Key='ColorPalette';Label='Color Palette';Type='Multi'},
        @{Key='Inspirations';Label='Inspirations';Type='Large'},
        @{Key='VoiceReference';Label='Voice Reference';Type='Text'},
        @{Key='ImportantObjects';Label='Important Objects';Type='Large'},
        @{Key='Knowledge';Label='What This Character Knows';Type='Large'},
        @{Key='ReaderKnowledge';Label='What the Reader Knows';Type='Large'},
        @{Key='StorySpecificNotes';Label='Story-Specific Notes';Type='Large'},
        @{Key='UniverseNotes';Label='Universe-Wide Notes';Type='Large'},
        @{Key='Trivia';Label='Trivia';Type='Large'},
        @{Key='CustomFields';Label='Custom Fields / Anything Else';Type='Large'},
        @{Key='AuthorNotes';Label='Private / Author Notes';Type='Large'}
    )
}

function Get-FieldDefinition([string]$Key) {
    foreach($sectionName in $script:FieldDefs.Keys) {
        foreach($d in $script:FieldDefs[$sectionName]) {
            if([string]$d.Key -eq $Key){ return $d }
        }
    }
    return $null
}

function Split-MultiChoiceValue([string]$Value) {
    if([string]::IsNullOrWhiteSpace($Value)){ return @() }
    $out=New-Object System.Collections.Generic.List[string]
    foreach($part in @($Value -split '\s*;\s*')){
        $v=[string]$part
        if(-not [string]::IsNullOrWhiteSpace($v) -and -not $out.Contains($v.Trim())){[void]$out.Add($v.Trim())}
    }
    return @($out)
}

function Join-MultiChoiceValue($Values) {
    return (@($Values | Where-Object {-not [string]::IsNullOrWhiteSpace([string]$_)}) -join '; ')
}

function Get-MultiChoiceSummary([string]$Value) {
    $items=@(Split-MultiChoiceValue $Value)
    if($items.Count -eq 0){return 'Select one or more...  ▼'}
    if($items.Count -le 2){return (($items -join '; ') + '  ▼')}
    return (('{0}; {1}  +{2}  ▼' -f $items[0],$items[1],($items.Count-2)))
}

function ConvertFrom-LifeEvents([string]$Value) {
    $map=[ordered]@{}
    if([string]::IsNullOrWhiteSpace($Value)){return $map}
    try {
        $parsed=$Value | ConvertFrom-Json
        foreach($item in @($parsed)){
            $category=[string]$item.Category
            if(-not [string]::IsNullOrWhiteSpace($category)){$map[$category]=[string]$item.Notes}
        }
        if($map.Count -gt 0){return $map}
    } catch {}
    $map['Other / Custom']=$Value
    return $map
}

function ConvertTo-LifeEvents($Map) {
    $rows=New-Object System.Collections.Generic.List[object]
    if($null -ne $Map){
        foreach($category in @($Map.Keys)){
            [void]$rows.Add([pscustomobject][ordered]@{Category=[string]$category;Notes=[string]$Map[$category]})
        }
    }
    if($rows.Count -eq 0){return ''}
    return (ConvertTo-Json -InputObject @($rows) -Compress -Depth 4)
}

function Mark-CharacterChanged([string]$Value) {
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $c.Modified=(Get-Date).ToString('o');$moved=$false
    if($c.FileStatus -eq 'Blank' -and -not [string]::IsNullOrWhiteSpace($Value)){$c.FileStatus='In Progress';$script:ActiveStatus='In Progress';$moved=$true}
    Schedule-Save
    if($moved){Refresh-Navigation -KeepId $c.Id -NoRender}
    Update-NavLabels
}

function Set-MultiChoiceSelection([string]$Key,[string]$Option,[bool]$Selected) {
    if($script:Rendering){return}
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $items=New-Object System.Collections.Generic.List[string]
    foreach($v in @(Split-MultiChoiceValue ([string]$c.Fields[$Key]))){[void]$items.Add([string]$v)}
    if($Selected){if(-not $items.Contains($Option)){[void]$items.Add($Option)}}else{[void]$items.Remove($Option)}
    $value=Join-MultiChoiceValue $items
    $c.Fields[$Key]=$value
    if($script:FieldControls.ContainsKey($Key)){try{$script:FieldControls[$Key].Text=Get-MultiChoiceSummary $value}catch{}}
    Mark-CharacterChanged $value
}

function Queue-RenderCurrentCharacter {
    try {
        if($null -ne $script:MainForm -and -not $script:MainForm.IsDisposed){
            [void]$script:MainForm.BeginInvoke([System.Windows.Forms.MethodInvoker]{Render-CurrentCharacter})
        } else {Render-CurrentCharacter}
    } catch {try{Render-CurrentCharacter}catch{}}
}

function Set-LifeEventSelection([string]$Key,[string]$Category,[bool]$Selected) {
    if($script:Rendering){return}
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $map=ConvertFrom-LifeEvents ([string]$c.Fields[$Key])
    if($Selected){if(-not $map.Contains($Category)){$map[$Category]=''}}else{if($map.Contains($Category)){$map.Remove($Category)}}
    $value=ConvertTo-LifeEvents $map;$c.Fields[$Key]=$value
    Mark-CharacterChanged $value
    Queue-RenderCurrentCharacter
}

function Set-LifeEventNote([string]$Key,[string]$Category,[string]$Notes) {
    if($script:Rendering){return}
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $map=ConvertFrom-LifeEvents ([string]$c.Fields[$Key])
    if(-not $map.Contains($Category)){$map[$Category]=''}
    $map[$Category]=$Notes
    $value=ConvertTo-LifeEvents $map;$c.Fields[$Key]=$value
    Mark-CharacterChanged $value
}

# Labeled color swatches used by the Appearance pickers.
$script:SwatchColors = @{
    HairColor = @{
        'Black'='#1D1B1A'; 'Dark Brown'='#3B281E'; 'Brown'='#65452F'; 'Light Brown'='#9B704F';
        'Auburn'='#7B3626'; 'Red'='#A94B34'; 'Strawberry Blonde'='#C98968'; 'Blonde'='#D9BF7D';
        'Platinum Blonde'='#E8DFC8'; 'Gray'='#9A9994'; 'White'='#EFEDE6'; 'Dyed / Fantasy'='#8B5CA5';
        'Multicolored'='#B58A73'; 'Custom'='#B89BC7'; 'Unknown'='#B5ADA0'
    }
    EyeColor = @{
        'Brown'='#6B4A2F'; 'Dark Brown'='#3E2A20'; 'Hazel'='#8A7442'; 'Amber'='#C0832E';
        'Green'='#62805E'; 'Blue'='#5F84A9'; 'Gray'='#8A9297'; 'Blue-Gray'='#71899B';
        'Green-Gray'='#74877A'; 'Heterochromia'='#8B6F78'; 'Custom'='#B89BC7'; 'Unknown'='#B5ADA0'
    }
    SkinTone = @{
        'Very Fair'='#F4D9C7'; 'Fair'='#EBC9B2'; 'Light'='#DFB89C'; 'Light-Medium'='#D2A17F';
        'Medium'='#BF8968'; 'Medium-Tan'='#AD7655'; 'Tan'='#996447'; 'Medium-Brown'='#81513B';
        'Brown'='#694130'; 'Deep Brown'='#513124'; 'Very Deep'='#39231C'; 'Albinism'='#F2DDD5';
        'Custom'='#B89BC7'; 'Unknown'='#B5ADA0'
    }
}

function Convert-HexToColor([string]$Hex) {
    try {
        $h = $Hex.Trim().TrimStart('#')
        if ($h.Length -ne 6) { return [System.Drawing.Color]::Gray }
        return [System.Drawing.Color]::FromArgb(
            [Convert]::ToInt32($h.Substring(0,2),16),
            [Convert]::ToInt32($h.Substring(2,2),16),
            [Convert]::ToInt32($h.Substring(4,2),16)
        )
    } catch { return [System.Drawing.Color]::Gray }
}

$script:AllFieldKeys = @()
foreach ($sectionName in $script:FieldDefs.Keys) {
    foreach ($d in $script:FieldDefs[$sectionName]) {
        if ($script:AllFieldKeys -notcontains $d.Key) { $script:AllFieldKeys += $d.Key }
    }
}

$script:RandomPools = @{
    FullName = @('Adrian Vale','Elias Warren','Theo Mercer','Callum Reed','Julian Hart','Rowan Keane','Kieran Doyle','Dorian Cross','Sorin Marin','Adam Hale','Max Rowan','Cassian Ward','Levi Bowen','Grant Sinclair','Jamie Ward','Silas Voss','Tobias Kovac','Kiran Rao','Victor Hale','Beck Mercer')
    Nicknames = @('Ace','Ash','Cal','Dori','Eli','Ian','Jay','Kit','Ren','Ro','Sam','Theo','Toby','Vic','Wren')
    StoryTitle = @('Where the Pines Remember','The Last Light','Black River','A House Without Shadows','The Wild Road','Beneath Hollow Stars','The Quiet Between','No Road Home','The Long Winter','Ash & Briar')
    Partner = @('Elias Warren','Caelan','Max Rowan','Levi Bowen','Dorian Cross','Jamie Ward','Theo Mercer','Kiran Rao','Sorin Marin','Cassian Ward')
    CharacterTier = @('Primary','Secondary','Tertiary','Minor','Background')
    StoryRole = @('Protagonist','Love Interest','Antagonist','Deuteragonist','Supporting','Mentor','Rival','Confidant')
    CharacterRole = @('Main Character','Secondary Main','Supporting Character','Love Interest','Antagonist','Villain','Rival','Mentor','Sidekick','Minor Character','Background Character')
    LifeStatus = @('Alive','Alive','Alive','Missing','Unknown','Undead')
    Pronouns = @('He / Him','He / Him','They / Them','He / They','She / Her')
    Species = @('Human','Fae','Vampire','Werewolf','Demon','Spirit','Witch','Changeling','Siren','Unknown Supernatural Being')
    Occupation = @('Archivist','Ranger','Paramedic','Mechanic','Teacher','Bartender','Researcher','Soldier','Lawyer','Conservationist','Librarian','Carpenter','Detective','Artist','Doctor','Farmer','Student','Historian')
    FreedomStatus = @('Free','Restricted','Confined','Detained','Imprisoned','Captive','Under Guard','House Arrest','Institutionalized','Missing / Unknown')
    SocialStatus = @('Lower Class','Working Class','Middle Class','Upper Class','Wealthy','Elite','Aristocracy / Nobility','Royalty','Outcast','Social Pariah','Unknown')
    HairColor = @('Black','Dark Brown','Brown','Light Brown','Auburn','Red','Strawberry Blonde','Blonde','Platinum Blonde','Gray','White')
    EyeColor = @('Brown','Dark Brown','Hazel','Amber','Green','Blue','Gray','Blue-Gray','Green-Gray')
    SkinTone = @('Very Fair','Fair','Light','Light-Medium','Medium','Medium-Tan','Tan','Medium-Brown','Brown','Deep Brown','Very Deep')
    Scars = @('No notable scars','Old surgical scar','Several faded scars','Scar across the palm','Burn scar on one forearm','Small scar through one eyebrow')
    CorePersonality = @('Protective, stubborn, observant, quietly funny','Reserved, loyal, skeptical, deeply compassionate','Charismatic, reckless, affectionate, defensive','Patient, perceptive, anxious, determined','Dry-witted, private, principled, intense')
    PositiveTraits = @('Loyal, patient, brave','Compassionate, observant, resourceful','Funny, generous, resilient','Protective, curious, determined')
    NegativeTraits = @('Stubborn, secretive, jealous','Reckless, avoidant, defensive','Controlling, pessimistic, impatient','Prideful, suspicious, self-sacrificing')
    Strengths = @('Keeps calm in a crisis','Reads people well','Persistent under pressure','Protective of others','Learns quickly','Good at improvising')
    Weaknesses = @('Refuses to ask for help','Takes responsibility for everyone','Acts before thinking','Holds grudges','Avoids vulnerability','Trusts too slowly')
    Habits = @('Taps his thumb against his fingers when thinking. Checks exits without noticing he is doing it.','Pushes his hair back when frustrated. Makes tea when he cannot sleep.','Carries a notebook everywhere and writes down things he is afraid he will forget.')
    Likes = @('Rain, coffee, old books','Forests, dogs, quiet mornings','Late-night drives, music, spicy food','Cooking, thunderstorms, small towns')
    Dislikes = @('Crowds, dishonesty, fluorescent lights','Being watched, wasted food, arrogance','Hospitals, small talk, people touching his things')
    Fears = @('Failing someone who depends on him','Being trapped with no way out','Becoming like the person he hates most','Losing the person he loves','Being known completely and rejected anyway')
    StressBehavior = @('Gets very quiet and hyper-focused. Stops sleeping before he admits anything is wrong.','Becomes sarcastic and restless, then disappears to deal with the problem alone.','Tries to control every detail around him when he feels powerless.')
    Birthplace = @('Melbourne, Victoria','A small town in upstate New York','Dublin, Ireland','Cardiff, Wales','Glasgow, Scotland','Bucharest, Romania','A coastal town in Maine','A rural village outside the capital')
    Residence = @('A rented apartment above a shop','A cabin at the edge of the woods','A small house inherited from family','University housing','A converted loft','A weathered farmhouse')
    NationalityCulture = @('Irish','Welsh','Scottish','Romanian','Australian','American','Indian','French','Italian','Polish','Mexican','Palestinian','Greek','Norwegian')
    Education = @('University degree','Trade school','Some college','Self-taught','Military training','Graduate degree','High school diploma','Apprenticeship')
    PastOccupations = @('Retail worker, bartender','Soldier','Research assistant','Farm hand','Mechanic apprentice','Tutor','EMT','None')
    Achievements = @('Graduated at the top of his class','Saved someone during a crisis','Built a life from nothing','Won a local competition','Protected a community nobody else cared about')
    Parent1Status = @('Alive','Dead','Missing','Unknown')
    Parent2Status = @('Alive','Dead','Missing','Unknown')
    POVStatus = @('Main POV','Occasional POV','Never POV')
    ArcType = @('Positive Change','Redemption','Flat','Disillusionment','Negative Change','Tragic')
    Languages = @('English','English, Irish','English, Romanian','English, French','English, Spanish','English, Arabic','English, Hindi','English, Welsh')
    NaturalTalents = @('Pattern recognition','Reading people','Mechanical intuition','Spatial awareness','Music','Animal handling','Memory','Negotiation')
    VoiceReference = @('Low and soft-spoken','Warm baritone','Quick, clipped delivery','Measured and precise','Rough voice with a quiet laugh')
    VisualReference = @('Dark, romantic, weathered','Soft-featured and bookish','Rugged outdoorsman','Elegant and severe','Ordinary at first glance')
    Gender = @('Man','Woman','Nonbinary','Genderfluid','Agender')
    Birthday = @('January 8','February 19','March 14','April 27','May 3','June 21','July 11','August 30','September 17','October 6','November 24','December 12')
    Tags = @('Primary, Romance, Human','Secondary, Family','Supernatural, Love Interest','Antagonist, Morally Gray','Found Family, Survivor')
}

function Get-SmartNickname {
    $c=Get-CurrentCharacter
    $name=''; if($null -ne $c){$name=[string]$c.Fields.FullName}
    if([string]::IsNullOrWhiteSpace($name)){ $pick=[string](Get-Random -InputObject @($script:RandomPools.Nicknames)); if([string]::IsNullOrWhiteSpace($pick)){$pick='Ace'}; return $pick }
    $first=($name.Trim() -split '\s+')[0]
    $known=@{
        'Adrian'=@('Adri','Ian');'Alexander'=@('Alex','Xan');'Benjamin'=@('Ben','Benny');'Callum'=@('Cal');
        'Cassian'=@('Cass','Cas');'Christopher'=@('Chris','Kit');'Daniel'=@('Dan','Danny');'Dorian'=@('Dori','Ian');
        'Edward'=@('Ed','Eddie');'Elias'=@('Eli');'Gabriel'=@('Gabe');'James'=@('Jamie','Jay');
        'Jonathan'=@('Jon','Johnny');'Julian'=@('Jules');'Kieran'=@('Kier');'Maxwell'=@('Max');
        'Nicholas'=@('Nick','Nico');'Rowan'=@('Ro');'Samuel'=@('Sam');'Sebastian'=@('Seb','Bash');
        'Silas'=@('Si');'Sorin'=@('Sor');'Theodore'=@('Theo','Teddy');'Thomas'=@('Tom','Tommy');
        'Tobias'=@('Toby');'Victor'=@('Vic')
    }
    if($known.ContainsKey($first)){ return [string](Get-Random -InputObject $known[$first]) }
    if($first.Length -ge 5){
        $cut=[math]::Min(4,$first.Length-1)
        return $first.Substring(0,$cut)
    }
        $pick=[string](Get-Random -InputObject @($script:RandomPools.Nicknames)); if([string]::IsNullOrWhiteSpace($pick)){$pick='Ace'}; return $pick
}

function Get-RandomText([string]$Key) {
    $def=Get-FieldDefinition $Key
    if($null -ne $def -and [string]$def.Type -eq 'MultiChoice'){
        $opts=@($def.Options | Where-Object {$_ -ne 'Other / Custom' -and $_ -ne 'Unknown'})
        if($opts.Count -gt 0){
            $maxCount=[math]::Min(4,$opts.Count);$count=Get-Random -Minimum 1 -Maximum ($maxCount+1)
            return ((Get-Random -InputObject $opts -Count $count) -join '; ')
        }
    }
    if($null -ne $def -and [string]$def.Type -eq 'LifeEvents'){
        $opts=@($def.Options | Where-Object {$_ -ne 'Other / Custom'})
        if($opts.Count -gt 0){$m=[ordered]@{};$m[[string](Get-Random -InputObject $opts)]='';return (ConvertTo-LifeEvents $m)}
    }
    if($Key -eq 'Education' -or $Key -eq 'PastOccupations'){
        if($null -ne $def -and @($def.Options).Count -gt 0){return [string](Get-Random -InputObject @($def.Options))}
    }
    if ($Key -eq 'Nicknames') { return Get-SmartNickname }
    if ($Key -eq 'Age') { return [string](Get-Random -Minimum 18 -Maximum 71) }
    if ($Key -eq 'Height') {
        $feet = Get-Random -Minimum 5 -Maximum 7
        $inch = Get-Random -Minimum 0 -Maximum 12
        return ("{0}'{1}`"" -f $feet,$inch)
    }
    if ($Key -match 'Parent[12]Name') { return [string](Get-Random -InputObject $script:RandomPools.FullName) }
    if ($Key -match '^Parent[12]Spouse$') { return [string](Get-Random -InputObject $script:RandomPools.FullName) }
    if ($Key -match '^Parent[12]Occupation$') { return [string](Get-Random -InputObject $script:FamilyOccupationOptions) }
    if ($Key -match '^Parent[12]Notes$') { return [string](Get-Random -InputObject @('Their history with the character is complicated.','A major influence on the character''s early life.','They remain an important part of the family dynamic.','The relationship changed significantly after a major family event.')) }
    if ($Key -eq 'Siblings' -or $Key -eq 'Children' -or $Key -eq 'OtherFamily' -or $Key -eq 'FamilyHistory') { return Get-RandomFamilyStructuredValue $Key }
    if ($Key -eq 'Parent1Relationship' -or $Key -eq 'Parent2Relationship') { return [string](Get-Random -InputObject @('Close','Complicated','Estranged','Protective','Distant','Loving but tense','Unknown')) }
    if ($Key -eq 'RelationshipStatus') { return [string](Get-Random -InputObject @('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','Complicated / Unclear','Unknown')) }
    if ($Key -eq 'Sexuality') { return [string](Get-Random -InputObject @('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown')) }
    if ($Key -eq 'Partner') { if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)} }
    if ($Key -eq 'Friends' -or $Key -eq 'Enemies' -or $Key -eq 'Mentors') { return Get-RandomRelationshipStructuredValue $Key }
    if ($Key -eq 'MainGoal') { return [string](Get-Random -InputObject @('Protect the person he loves, even if it costs him the life he planned.','Find the truth behind the event that destroyed his family.','Build a quiet life somewhere nobody knows his past.','Keep his community safe while refusing to become the thing they fear.')) }
    if ($Key -eq 'InternalConflict') { return [string](Get-Random -InputObject @('He wants intimacy but treats vulnerability as a threat.','He believes his value comes from being useful to everyone else.','He cannot decide whether survival justifies becoming someone he hates.')) }
    if ($Key -eq 'ExternalConflict') { return [string](Get-Random -InputObject @('Someone powerful is actively trying to force him out of the life he built.','A dangerous secret from his past has followed him home.','The place he is trying to protect is becoming increasingly unsafe.')) }
    if ($Key -eq 'RelationshipConflict') { return [string](Get-Random -InputObject @('They want each other, but neither trusts the other enough to surrender control.','Their loyalties put them on opposite sides of the same problem.','One is ready to build a life together; the other still expects everything good to disappear.')) }
    if ($Key -eq 'Timeline') { return "AGE 8 — A formative family event.`r`nAGE 16 — First major break from home.`r`nAGE 21 — Meets someone who changes the direction of his life.`r`nPRESENT — The story begins." }
    if ($Key -eq 'AuthorNotes') { return 'Add anything here that does not belong cleanly in another section.' }
    if ($Key -match 'Description|History|Secrets|MajorLifeEvents|Relationship|Romantic|Attraction|LoveLanguage|Affection|Jealousy|Conflict|Intimacy|Skills|Powers|Limits|Weaknesses|Equipment|Weapons|SelfImage|Worldview|Moral|Boundaries|Coping|Defense|Insecurities|Triggers|Refuses|RuleBreaking|Desire|Fear|BreakingPoint|CoreBelief|FalseBelief|Goal|Motivation|Want|Need|Abandon|FatalFlaw|State|TurningPoints|Scenes|Relevance|Aliases|Quotes|Playlist|Aesthetic|Inspirations|Objects|Knowledge|Notes|Trivia|CustomFields|Siblings|Children|OtherFamily|Guardians|StepParents|Friends|Enemies|Rivals|Mentors|Dependents|ImportantRelationships|Mannerisms|PetPeeves|SenseHumor|Temper|SocialBehavior|ComfortableBehavior|Health|Disabilities|Injuries|HealthNotes|Scars') {
        return [string](Get-Random -InputObject @('None decided yet.','Complicated; expand later.','This is important to the character arc and should be revisited.','Kept deliberately private from most people.','A major source of tension throughout the story.'))
    }
    if ($script:RandomPools.ContainsKey($Key)) { return [string](Get-Random -InputObject $script:RandomPools[$Key]) }
    return ''
}

function New-CharacterRecord {
    $fields = [ordered]@{}
    foreach ($key in $script:AllFieldKeys) { $fields[$key] = '' }
    $fields['CharacterTier'] = 'Primary'
    $fields['StoryRole'] = 'Protagonist'
    $fields['CharacterRole'] = 'Main Character'
    $fields['FreedomStatus'] = 'Free'
    $fields['SocialStatus'] = 'Unknown'
    $fields['HairColor'] = 'Unknown'
    $fields['EyeColor'] = 'Unknown'
    $fields['SkinTone'] = 'Unknown'
    $fields['LifeStatus'] = 'Alive'
    $fields['Pronouns'] = 'He / Him'
    $fields['POVStatus'] = 'Main POV'
    $fields['ArcType'] = 'Positive Change'
    $maxNo = 0
    foreach ($c in $script:Characters) { if ([int]$c.FileNumber -gt $maxNo) { $maxNo = [int]$c.FileNumber } }
    return [ordered]@{
        Id = [guid]::NewGuid().ToString('N')
        FileNumber = $maxNo + 1
        FileStatus = 'Blank'
        Created = (Get-Date).ToString('o')
        Modified = (Get-Date).ToString('o')
        PortraitPath = ''
        Locks = @()
        Fields = $fields
    }
}

function Convert-ToCharacterRecord($raw) {
    $fields = [ordered]@{}
    foreach ($key in $script:AllFieldKeys) {
        $v = ''
        try { if ($null -ne $raw.Fields.PSObject.Properties[$key]) { $v = [string]$raw.Fields.$key } } catch {}
        $fields[$key] = $v
    }
    # Overview migration for v0.2.11: combine tier/role for the Overview page and replace location with freedom status.
    if ([string]::IsNullOrWhiteSpace([string]$fields['CharacterRole'])) {
        $oldRole='';$oldTier=''
        try { if ($null -ne $raw.Fields.PSObject.Properties['StoryRole']) { $oldRole=[string]$raw.Fields.StoryRole } } catch {}
        try { if ($null -ne $raw.Fields.PSObject.Properties['CharacterTier']) { $oldTier=[string]$raw.Fields.CharacterTier } } catch {}
        switch ($oldRole) {
            'Protagonist' { $fields['CharacterRole']='Main Character' }
            'Love Interest' { $fields['CharacterRole']='Love Interest' }
            'Antagonist' { $fields['CharacterRole']='Antagonist' }
            'Deuteragonist' { $fields['CharacterRole']='Secondary Main' }
            'Supporting' { $fields['CharacterRole']='Supporting Character' }
            'Mentor' { $fields['CharacterRole']='Mentor' }
            'Rival' { $fields['CharacterRole']='Rival' }
            'Confidant' { $fields['CharacterRole']='Supporting Character' }
            'Comic Relief' { $fields['CharacterRole']='Supporting Character' }
        }
        if ([string]::IsNullOrWhiteSpace([string]$fields['CharacterRole'])) {
            switch ($oldTier) {
                'Primary' { $fields['CharacterRole']='Main Character' }
                'Secondary' { $fields['CharacterRole']='Secondary Main' }
                'Tertiary' { $fields['CharacterRole']='Supporting Character' }
                'Minor' { $fields['CharacterRole']='Minor Character' }
                'Background' { $fields['CharacterRole']='Background Character' }
                default { $fields['CharacterRole']='Main Character' }
            }
        }
    }
    if ([string]::IsNullOrWhiteSpace([string]$fields['FreedomStatus'])) { $fields['FreedomStatus']='Free' }
    # Normalize older free-text Social Status values into the new dropdown without throwing away existing meaning.
    $oldSocial=[string]$fields['SocialStatus']
    if (-not [string]::IsNullOrWhiteSpace($oldSocial)) {
        switch -Regex ($oldSocial.Trim()) {
            '^(lower class|poor)$' { $fields['SocialStatus']='Lower Class'; break }
            '^working class$' { $fields['SocialStatus']='Working Class'; break }
            '^middle class$' { $fields['SocialStatus']='Middle Class'; break }
            '^(upper middle class|upper class)$' { $fields['SocialStatus']='Upper Class'; break }
            '^wealthy$' { $fields['SocialStatus']='Wealthy'; break }
            '^elite$' { $fields['SocialStatus']='Elite'; break }
            '^(aristocratic|aristocracy|nobility)$' { $fields['SocialStatus']='Aristocracy / Nobility'; break }
            '^royalty$' { $fields['SocialStatus']='Royalty'; break }
            '^(outsider|outcast)$' { $fields['SocialStatus']='Outcast'; break }
            '^(social pariah|pariah)$' { $fields['SocialStatus']='Social Pariah'; break }
            '^unknown$' { $fields['SocialStatus']='Unknown'; break }
            default { if (@('Lower Class','Working Class','Middle Class','Upper Class','Wealthy','Elite','Aristocracy / Nobility','Royalty','Outcast','Social Pariah','Unknown','Other') -notcontains $oldSocial) { $fields['SocialStatus']='Other' } }
        }
    } else { $fields['SocialStatus']='Unknown' }

    # Appearance migration for v0.2.12.
    # Convert older free-text Hair / Eyes values to the closest swatch while preserving direct matches.
    if ([string]::IsNullOrWhiteSpace([string]$fields['HairColor'])) {
        $oldHair=''
        try { if ($null -ne $raw.Fields.PSObject.Properties['Hair']) { $oldHair=[string]$raw.Fields.Hair } } catch {}
        switch -Regex ($oldHair.Trim()) {
            '(?i)platinum' { $fields['HairColor']='Platinum Blonde'; break }
            '(?i)strawberry' { $fields['HairColor']='Strawberry Blonde'; break }
            '(?i)auburn' { $fields['HairColor']='Auburn'; break }
            '(?i)\bred\b|ginger' { $fields['HairColor']='Red'; break }
            '(?i)blond' { $fields['HairColor']='Blonde'; break }
            '(?i)light brown' { $fields['HairColor']='Light Brown'; break }
            '(?i)dark brown' { $fields['HairColor']='Dark Brown'; break }
            '(?i)\bbrown\b' { $fields['HairColor']='Brown'; break }
            '(?i)\bblack\b|near-black' { $fields['HairColor']='Black'; break }
            '(?i)\bgray\b|\bgrey\b' { $fields['HairColor']='Gray'; break }
            '(?i)\bwhite\b' { $fields['HairColor']='White'; break }
            '^$' { $fields['HairColor']='Unknown'; break }
            default { $fields['HairColor']='Custom' }
        }
    }

    if ([string]::IsNullOrWhiteSpace([string]$fields['EyeColor'])) {
        $oldEyes=''
        try { if ($null -ne $raw.Fields.PSObject.Properties['Eyes']) { $oldEyes=[string]$raw.Fields.Eyes } } catch {}
        switch -Regex ($oldEyes.Trim()) {
            '(?i)heterochrom' { $fields['EyeColor']='Heterochromia'; break }
            '(?i)blue[- ]?gray|blue[- ]?grey' { $fields['EyeColor']='Blue-Gray'; break }
            '(?i)green[- ]?gray|green[- ]?grey' { $fields['EyeColor']='Green-Gray'; break }
            '(?i)dark brown|near-black' { $fields['EyeColor']='Dark Brown'; break }
            '(?i)\bbrown\b' { $fields['EyeColor']='Brown'; break }
            '(?i)hazel' { $fields['EyeColor']='Hazel'; break }
            '(?i)amber' { $fields['EyeColor']='Amber'; break }
            '(?i)green' { $fields['EyeColor']='Green'; break }
            '(?i)blue' { $fields['EyeColor']='Blue'; break }
            '(?i)\bgray\b|\bgrey\b' { $fields['EyeColor']='Gray'; break }
            '^$' { $fields['EyeColor']='Unknown'; break }
            default { $fields['EyeColor']='Custom' }
        }
    }

    $oldSkin=[string]$fields['SkinTone']
    if (-not [string]::IsNullOrWhiteSpace($oldSkin)) {
        if (@('Very Fair','Fair','Light','Light-Medium','Medium','Medium-Tan','Tan','Medium-Brown','Brown','Deep Brown','Very Deep','Albinism','Custom','Unknown') -notcontains $oldSkin) {
            switch -Regex ($oldSkin.Trim()) {
                '(?i)^pale$|very fair' { $fields['SkinTone']='Very Fair'; break }
                '(?i)^fair$' { $fields['SkinTone']='Fair'; break }
                '(?i)^light$' { $fields['SkinTone']='Light'; break }
                '(?i)light olive|light.medium' { $fields['SkinTone']='Light-Medium'; break }
                '(?i)^medium$' { $fields['SkinTone']='Medium'; break }
                '(?i)medium.tan' { $fields['SkinTone']='Medium-Tan'; break }
                '(?i)^tan$' { $fields['SkinTone']='Tan'; break }
                '(?i)medium brown|warm brown' { $fields['SkinTone']='Medium-Brown'; break }
                '(?i)^brown$|golden.brown' { $fields['SkinTone']='Brown'; break }
                '(?i)deep brown' { $fields['SkinTone']='Deep Brown'; break }
                '(?i)very deep' { $fields['SkinTone']='Very Deep'; break }
                '(?i)albin' { $fields['SkinTone']='Albinism'; break }
                default { $fields['SkinTone']='Custom' }
            }
        }
    } else { $fields['SkinTone']='Unknown' }

    if ([string]::IsNullOrWhiteSpace([string]$fields['Scars'])) {
        try { if ($null -ne $raw.Fields.PSObject.Properties['ScarsTattoos']) { $fields['Scars']=[string]$raw.Fields.ScarsTattoos } } catch {}
    }

    if ([string]::IsNullOrWhiteSpace([string]$fields['HealthNotes'])) {
        $healthParts = New-Object System.Collections.Generic.List[string]
        foreach ($pair in @(@('Health','Health'),@('Disabilities','Disabilities'),@('Injuries','Injuries'))) {
            try {
                if ($null -ne $raw.Fields.PSObject.Properties[$pair[0]]) {
                    $legacy=[string]$raw.Fields.($pair[0])
                    if (-not [string]::IsNullOrWhiteSpace($legacy)) { [void]$healthParts.Add(($pair[1] + ': ' + $legacy.Trim())) }
                }
            } catch {}
        }
        if ($healthParts.Count -gt 0) { $fields['HealthNotes']=($healthParts -join "`r`n") }
    }

    # Personality + Background migration for v0.2.13.
    # Multi-choice fields keep any older free-text value as one preserved custom selection.
    # The four previous background-history fields are folded into Major Life Events with attached notes.
    if ([string]::IsNullOrWhiteSpace([string]$fields['MajorLifeEvents'])) {
        $legacyEvents=[ordered]@{}
        foreach($legacy in @(
            @('PastEvents','Other / Custom','Important Past Events'),
            @('Trauma','Other Hardship / Trauma','Trauma / Hardship'),
            @('Achievements','Major Achievement / Award','Achievements'),
            @('Regrets','Regret / Past Mistake','Regrets')
        )){
            try {
                if($null -ne $raw.Fields.PSObject.Properties[$legacy[0]]){
                    $text=[string]$raw.Fields.($legacy[0])
                    if(-not [string]::IsNullOrWhiteSpace($text)){
                        $cat=[string]$legacy[1]
                        $note=([string]$legacy[2] + ': ' + $text.Trim())
                        if($legacyEvents.Contains($cat) -and -not [string]::IsNullOrWhiteSpace([string]$legacyEvents[$cat])){$legacyEvents[$cat]=([string]$legacyEvents[$cat] + "`r`n" + $note)}else{$legacyEvents[$cat]=$note}
                    }
                }
            } catch {}
        }
        if($legacyEvents.Count -gt 0){$fields['MajorLifeEvents']=ConvertTo-LifeEvents $legacyEvents}
    }

    $id = [guid]::NewGuid().ToString('N'); if ($raw.Id) { $id = [string]$raw.Id }
    $fileNumber = 1; if ($raw.FileNumber) { $fileNumber = [int]$raw.FileNumber }
    $fileStatus = 'In Progress'; if ($raw.FileStatus) { $fileStatus = [string]$raw.FileStatus }
    $created = (Get-Date).ToString('o'); if ($raw.Created) { $created = [string]$raw.Created }
    $modified = (Get-Date).ToString('o'); if ($raw.Modified) { $modified = [string]$raw.Modified }
    $portrait = ''; if ($raw.PortraitPath) { $portrait = [string]$raw.PortraitPath }
    return [ordered]@{
        Id = $id
        FileNumber = $fileNumber
        FileStatus = $fileStatus
        Created = $created
        Modified = $modified
        PortraitPath = $portrait
        Locks = @($raw.Locks | ForEach-Object { [string]$_ })
        Fields = $fields
    }
}

$script:Characters = @()
try {
    if (Test-Path -LiteralPath $script:CharactersPath) {
        $rawList = @(Get-Content -LiteralPath $script:CharactersPath -Raw -Encoding UTF8 | ConvertFrom-Json)
        foreach ($raw in $rawList) { $script:Characters += ,(Convert-ToCharacterRecord $raw) }
    }
} catch {
    try { Copy-Item -LiteralPath $script:CharactersPath -Destination ($script:CharactersPath + '.broken-' + (Get-Date -Format 'yyyyMMdd-HHmmss')) -Force } catch {}
    $script:Characters = @()
}

$script:Settings = [ordered]@{ AutoUpdateCheck = $true; LastUpdateCheck = ''; LastCharacterId=''; LastSection='Overview'; LastStatus='Existing'; ScrollLeft=0; ScrollRight=0 }
try {
    if (Test-Path -LiteralPath $script:SettingsPath) {
        $s = Get-Content -LiteralPath $script:SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -ne $s.AutoUpdateCheck) { $script:Settings.AutoUpdateCheck = [bool]$s.AutoUpdateCheck }
        if ($s.LastUpdateCheck) { $script:Settings.LastUpdateCheck = [string]$s.LastUpdateCheck }
        if ($s.LastCharacterId) { $script:Settings.LastCharacterId = [string]$s.LastCharacterId }
        if ($s.LastSection) { $script:Settings.LastSection = [string]$s.LastSection }
        if ($s.LastStatus) { $script:Settings.LastStatus = [string]$s.LastStatus }
        if ($null -ne $s.ScrollLeft) { $script:Settings.ScrollLeft = [int]$s.ScrollLeft }
        if ($null -ne $s.ScrollRight) { $script:Settings.ScrollRight = [int]$s.ScrollRight }
    }
} catch {}

function Save-AllData {
    try {
        $tmp = $script:CharactersPath + '.tmp'
        ConvertTo-Json -InputObject @($script:Characters) -Depth 8 | Set-Content -LiteralPath $tmp -Encoding UTF8
        Move-Item -LiteralPath $tmp -Destination $script:CharactersPath -Force
        $script:Settings | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $script:SettingsPath -Encoding UTF8
        if ($null -ne $script:SaveStateLabel) { $script:SaveStateLabel.Text = 'AUTO-SAVED  ' + (Get-Date -Format 'h:mm tt') }
    } catch {
        if ($null -ne $script:SaveStateLabel) { $script:SaveStateLabel.Text = 'SAVE ERROR' }
    }
}

$script:SaveTimer = New-Object System.Windows.Forms.Timer
$script:SaveTimer.Interval = 700
$script:SaveTimer.Add_Tick({ $script:SaveTimer.Stop(); Save-AllData })
function Schedule-Save { $script:SaveTimer.Stop(); $script:SaveTimer.Start() }

function Get-RemoteUpdateManifest {
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $r = Invoke-WebRequest -Uri $script:UpdateManifestUrl -UseBasicParsing -TimeoutSec 8 -Headers @{'Cache-Control'='no-cache'}
        if ($null -eq $r -or [string]::IsNullOrWhiteSpace([string]$r.Content)) { return $null }
        return ($r.Content | ConvertFrom-Json)
    } catch { return $null }
}
function Test-RemoteVersionNewer([string]$RemoteVersion,[string]$LocalVersion) {
    try { return ([version]$RemoteVersion -gt [version]$LocalVersion) } catch { return ($RemoteVersion -ne $LocalVersion) }
}
function Start-RemoteAppUpdate($Manifest,[bool]$Automatic=$false) {
    try {
        if ($null -eq $Manifest) { throw 'The update manifest is missing.' }
        if ([string]$Manifest.appId -ne $script:UpdateAppId) { throw 'The update feed returned the wrong app.' }
        if ($null -eq $Manifest.payloadParts -or @($Manifest.payloadParts).Count -lt 1) { throw 'The update payload list is missing.' }
        if ([string]::IsNullOrWhiteSpace([string]$Manifest.payloadSha256)) { throw 'The update payload checksum is missing.' }
        if (-not (Test-Path -LiteralPath $script:UpdateHostPath)) { throw 'The local update helper is missing.' }

        # Save current edits before an automatic restart.
        Save-AllData

        New-Item -ItemType Directory -Force -Path $script:UpdateWorkRoot | Out-Null
        $job = Join-Path $script:UpdateWorkRoot ('job_' + [guid]::NewGuid().ToString('N'))
        $payload = Join-Path $job 'payload'
        $payloadJsonPath = Join-Path $job 'payload.json'
        New-Item -ItemType Directory -Force -Path $payload | Out-Null
        $stream = [System.IO.File]::Open($payloadJsonPath,[System.IO.FileMode]::Create,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
        try {
            $n = 0
            foreach ($part in @($Manifest.payloadParts)) {
                $n++
                $partPath = Join-Path $job ('part_' + $n.ToString('000') + '.txt')
                Invoke-WebRequest -Uri ([string]$part.url) -UseBasicParsing -TimeoutSec 120 -OutFile $partPath
                $actual = (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash.ToLowerInvariant()
                $expected = ([string]$part.sha256).Trim().ToLowerInvariant()
                if ($actual -ne $expected) { throw "Update part $n failed its SHA-256 safety check." }
                $bytes = [System.IO.File]::ReadAllBytes($partPath)
                $stream.Write($bytes,0,$bytes.Length)
            }
        } finally { if ($null -ne $stream) { $stream.Dispose() } }
        $actualPayload = (Get-FileHash -LiteralPath $payloadJsonPath -Algorithm SHA256).Hash.ToLowerInvariant()
        $expectedPayload = ([string]$Manifest.payloadSha256).Trim().ToLowerInvariant()
        if ($actualPayload -ne $expectedPayload) { throw 'The reconstructed update failed its SHA-256 safety check.' }
        $doc = Get-Content -LiteralPath $payloadJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$doc.appId -ne $script:UpdateAppId) { throw 'The downloaded payload belongs to a different app.' }
        if ([string]$doc.version -ne [string]$Manifest.version) { throw 'The update payload version does not match the manifest.' }
        $payloadRoot = [System.IO.Path]::GetFullPath($payload).TrimEnd('\')
        foreach ($entry in @($doc.files)) {
            $rel = ([string]$entry.path).Replace('/','\').Trim()
            $dest = [System.IO.Path]::GetFullPath((Join-Path $payload $rel))
            if (-not $dest.StartsWith($payloadRoot + '\',[System.StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe file path: $rel" }
            $parent = Split-Path -Parent $dest
            if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
            $bytes = [Convert]::FromBase64String([string]$entry.contentBase64)
            [System.IO.File]::WriteAllBytes($dest,$bytes)
            if ($entry.sha256) {
                $fh = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($fh -ne ([string]$entry.sha256).Trim().ToLowerInvariant()) { throw "File verification failed for $rel." }
            }
        }
        if ($null -ne $doc.delete -and @($doc.delete).Count -gt 0) {
            @($doc.delete) | Set-Content -LiteralPath (Join-Path $payload '_delete.txt') -Encoding UTF8
        }
        if (-not (Test-Path -LiteralPath (Join-Path $payload $script:UpdateExpectedMain))) { throw 'The update payload is incomplete.' }
        $tempHost = Join-Path $env:TEMP ('TheFiles_Update_' + [guid]::NewGuid().ToString('N') + '.ps1')
        Copy-Item -LiteralPath $script:UpdateHostPath -Destination $tempHost -Force
        $args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$tempHost`" -WaitPid $PID -PayloadDir `"$payload`" -AppDir `"$script:UpdateAppDir`" -DataDir `"$script:UpdateDataDir`" -Launcher `"$script:UpdateLauncherPath`" -AppName `"$script:UpdateAppName`" -ExpectedMain `"$script:UpdateExpectedMain`""
        Start-Process powershell.exe -ArgumentList $args -WindowStyle Hidden

        # Automatic updates are intentionally interaction-free.
        if (-not $Automatic) {
            Show-Info "The Files update was downloaded and verified.`r`n`r`nThe app will close, update its application files, and reopen."
        }
        $form.Close()
    } catch {
        # Failed automatic updates do not interrupt normal app use; manual checks still explain the failure.
        try {
            New-Item -ItemType Directory -Force -Path $script:UpdateDataDir | Out-Null
            ((Get-Date).ToString('yyyy-MM-dd HH:mm:ss') + "`r`n`r`n" + $_.Exception.Message) |
                Set-Content -LiteralPath (Join-Path $script:UpdateDataDir 'update-error.txt') -Encoding UTF8
        } catch {}
        if (-not $Automatic) { Show-Error ("The update could not be installed.`r`n`r`n" + $_.Exception.Message) }
    }
}
function Check-ForRemoteUpdate([bool]$Silent=$false) {
    $manifest = Get-RemoteUpdateManifest
    $script:Settings.LastUpdateCheck = (Get-Date).ToString('o')
    Schedule-Save
    if ($null -eq $manifest) { if (-not $Silent) { Show-Info "The update feed could not be reached.`r`n`r`nInstalled version: $script:CurrentAppVersion" }; return }
    if ([string]$manifest.appId -ne $script:UpdateAppId) { if (-not $Silent) { Show-Error 'The update feed returned the wrong app channel.' }; return }
    $rv = [string]$manifest.version
    if (-not (Test-RemoteVersionNewer $rv $script:CurrentAppVersion)) { if (-not $Silent) { Show-Info "The Files is up to date.`r`n`r`nInstalled version: $script:CurrentAppVersion" }; return }

    if ($Silent) {
        # Startup checks install immediately with no confirmation dialog.
        Start-RemoteAppUpdate $manifest $true
        return
    }

    $msg = "A new The Files update is available.`r`n`r`nInstalled: $script:CurrentAppVersion`r`nAvailable: $rv"
    if ($manifest.notes) { $msg += "`r`n`r`n" + [string]$manifest.notes }
    $msg += "`r`n`r`nInstall it now?"
    if ((Show-Confirm $msg) -eq [System.Windows.Forms.DialogResult]::Yes) { Start-RemoteAppUpdate $manifest $false }
}
function Should-AutoCheck {
    # Automatic updates are checked once on every app launch.
    return [bool]$script:Settings.AutoUpdateCheck
}

$form = New-Object System.Windows.Forms.Form
$script:MainForm = $form
$form.Text = 'The Files'
$form.Size = New-Object System.Drawing.Size(1280,720)
$form.MinimumSize = New-Object System.Drawing.Size(560,560)
$form.FormBorderStyle = 'Sizable'
$form.MaximizeBox = $true
$form.MinimizeBox = $true
$form.StartPosition = 'CenterScreen'
$form.BackColor = $script:Dark
$form.ForeColor = $script:Parchment
try { $form.Icon = New-Object System.Drawing.Icon((Join-Path $script:AppRoot 'TheFiles.ico')) } catch {}

$header = New-Object System.Windows.Forms.Panel
$header.Dock='Top'; $header.Height=52; $header.BackColor=[System.Drawing.Color]::FromArgb(20,19,17)
$form.Controls.Add($header)
$title = New-Object System.Windows.Forms.Label
$title.Text='THE FILES'; $title.Font=New-Object System.Drawing.Font('Georgia',18,[System.Drawing.FontStyle]::Bold); $title.ForeColor=$script:Gold; $title.AutoSize=$true
$header.Controls.Add($title)
$titleFlourishL=New-Object System.Windows.Forms.Label; $titleFlourishL.Text='— ✦ —'; $titleFlourishL.Font=$script:FontSmall; $titleFlourishL.ForeColor=[System.Drawing.Color]::FromArgb(128,99,55); $titleFlourishL.AutoSize=$true; $header.Controls.Add($titleFlourishL)
$titleFlourishR=New-Object System.Windows.Forms.Label; $titleFlourishR.Text='— ✦ —'; $titleFlourishR.Font=$script:FontSmall; $titleFlourishR.ForeColor=[System.Drawing.Color]::FromArgb(128,99,55); $titleFlourishR.AutoSize=$true; $header.Controls.Add($titleFlourishR)

$searchBox=New-Object System.Windows.Forms.TextBox; $searchBox.Font=$script:FontSmall; $searchBox.Width=205; $searchBox.Height=28; $searchBox.BackColor=[System.Drawing.Color]::FromArgb(31,28,24); $searchBox.ForeColor=[System.Drawing.Color]::FromArgb(238,219,183); $searchBox.BorderStyle='FixedSingle'; $header.Controls.Add($searchBox)
$searchHint=New-Object System.Windows.Forms.Label; $searchHint.Text='Search characters…'; $searchHint.Font=$script:FontSmall; $searchHint.ForeColor=[System.Drawing.Color]::FromArgb(132,111,83); $searchHint.AutoSize=$true; $searchHint.Add_Click({$searchBox.Focus()}); $header.Controls.Add($searchHint)
$storyFilter=New-Object System.Windows.Forms.ComboBox; $storyFilter.DropDownStyle='DropDownList'; $storyFilter.Width=170; $storyFilter.Font=$script:FontSmall; $storyFilter.BackColor=[System.Drawing.Color]::FromArgb(236,216,179); $header.Controls.Add($storyFilter)
$jumpCombo=New-Object System.Windows.Forms.ComboBox; $jumpCombo.DropDownStyle='DropDownList'; $jumpCombo.Width=205; $jumpCombo.Font=$script:FontSmall; $jumpCombo.BackColor=[System.Drawing.Color]::FromArgb(236,216,179); $header.Controls.Add($jumpCombo)
$updateBtn=New-Object System.Windows.Forms.Button; $updateBtn.Text='CHECK UPDATES'; $updateBtn.Width=105; $updateBtn.Height=28; $updateBtn.FlatStyle='Flat'; $updateBtn.FlatAppearance.BorderColor=$script:Gold; $updateBtn.ForeColor=$script:Gold; $updateBtn.BackColor=[System.Drawing.Color]::FromArgb(20,19,17); $updateBtn.Font=$script:FontSmall; $updateBtn.Add_Click({Check-ForRemoteUpdate $false}); $header.Controls.Add($updateBtn)

try { $main=New-Object BookDeskPanel } catch { $main=New-Object System.Windows.Forms.Panel; $main.BackColor=[System.Drawing.Color]::FromArgb(31,23,18) }
$main.Dock='Fill'; $form.Controls.Add($main); $header.BringToFront()

try { $book=New-Object BookFramePanel } catch { $book=New-Object System.Windows.Forms.Panel; $book.BackColor=$script:Leather }
$book.Anchor='None'; $main.Controls.Add($book)
try { $leftPage=New-Object BookPagePanel; $leftPage.IsLeftPage=$true } catch { $leftPage=New-Object System.Windows.Forms.Panel; $leftPage.BackColor=$script:Parchment }
try { $rightPage=New-Object BookPagePanel; $rightPage.IsLeftPage=$false } catch { $rightPage=New-Object System.Windows.Forms.Panel; $rightPage.BackColor=$script:Parchment2 }
$leftPage.Anchor='None'; $rightPage.Anchor='None'; $book.Controls.Add($leftPage); $book.Controls.Add($rightPage)
$gutter=New-Object System.Windows.Forms.Panel; $gutter.BackColor=[System.Drawing.Color]::FromArgb(58,38,25); $gutter.Anchor='None'; $book.Controls.Add($gutter)

$script:StatusButtons=@{}
foreach($st in @('Existing','In Progress','Blank')) {
    try { $b=New-Object BookStatusTabButton } catch { $b=New-Object System.Windows.Forms.Button; $b.FlatStyle='Flat' }
    $b.Text=$st.ToUpper(); $b.Tag=$st; $b.Width=132; $b.Height=42; $b.Font=$script:FontTab; $b.Add_Click({Save-BrowseState;$script:ActiveStatus=[string]$this.Tag;$script:Settings.LastStatus=$script:ActiveStatus;Animate-BookPages 1 2 $false;Refresh-Navigation;Schedule-Save}); $main.Controls.Add($b); $script:StatusButtons[$st]=$b
}

$script:SectionButtons=@{}
$leftNames=@('Overview','Appearance','Personality','Background','Family')
$rightNames=@('Relationships','Skills','Psychology','Story','Timeline','Notes')
$script:SectionOrder=@('Overview','Appearance','Personality','Background','Family','Relationships','Skills','Psychology','Story','Timeline','Notes')
$tabColors=@([System.Drawing.Color]::FromArgb(166,135,88),[System.Drawing.Color]::FromArgb(81,92,63),[System.Drawing.Color]::FromArgb(52,62,79),[System.Drawing.Color]::FromArgb(105,62,41),[System.Drawing.Color]::FromArgb(70,55,88),[System.Drawing.Color]::FromArgb(105,49,37),[System.Drawing.Color]::FromArgb(46,72,70))
$i=0
foreach($nm in $leftNames){
    try{$b=New-Object BookTabButton; $b.Tone=$tabColors[$i % $tabColors.Count]}catch{$b=New-Object System.Windows.Forms.Button; $b.BackColor=$tabColors[$i % $tabColors.Count];$b.ForeColor=[System.Drawing.Color]::FromArgb(246,226,191);$b.FlatStyle='Flat'}
    $b.Text=$nm; $b.Tag=$nm; $b.Width=138; $b.Height=52; $b.Font=$script:FontTab; $b.Add_Click({Go-ToSection ([string]$this.Tag)}); $main.Controls.Add($b);$script:SectionButtons[$nm]=$b;$i++
}
$i=0
foreach($nm in $rightNames){
    try{$b=New-Object BookTabButton; $b.Tone=$tabColors[($i+2) % $tabColors.Count]}catch{$b=New-Object System.Windows.Forms.Button;$b.BackColor=$tabColors[($i+2) % $tabColors.Count];$b.ForeColor=[System.Drawing.Color]::FromArgb(246,226,191);$b.FlatStyle='Flat'}
    $b.Text=$nm; $b.Tag=$nm; $b.Width=138; $b.Height=52; $b.Font=$script:FontTab; $b.Add_Click({Go-ToSection ([string]$this.Tag)});$main.Controls.Add($b);$script:SectionButtons[$nm]=$b;$i++
}

$bottom=New-Object System.Windows.Forms.Panel; $bottom.Dock='Bottom'; $bottom.Height=70; $bottom.BackColor=[System.Drawing.Color]::FromArgb(22,20,17); $main.Controls.Add($bottom); $bottom.BringToFront()
$prevBtn=New-Object System.Windows.Forms.Button; $prevBtn.Text='‹  PREVIOUS'; $prevBtn.Width=205; $prevBtn.Height=45; $prevBtn.FlatStyle='Flat';$prevBtn.FlatAppearance.BorderColor=$script:Gold;$prevBtn.BackColor=[System.Drawing.Color]::FromArgb(28,25,21);$prevBtn.ForeColor=[System.Drawing.Color]::FromArgb(222,186,116);$prevBtn.Font=$script:FontTab;$bottom.Controls.Add($prevBtn)
$nextBtn=New-Object System.Windows.Forms.Button;$nextBtn.Text='NEXT  ›';$nextBtn.Width=205;$nextBtn.Height=45;$nextBtn.FlatStyle='Flat';$nextBtn.FlatAppearance.BorderColor=$script:Gold;$nextBtn.BackColor=[System.Drawing.Color]::FromArgb(28,25,21);$nextBtn.ForeColor=[System.Drawing.Color]::FromArgb(222,186,116);$nextBtn.Font=$script:FontTab;$bottom.Controls.Add($nextBtn)
$currentNav=New-Object System.Windows.Forms.Label;$currentNav.Text='CURRENT';$currentNav.TextAlign='MiddleCenter';$currentNav.Width=260;$currentNav.Height=45;$currentNav.ForeColor=[System.Drawing.Color]::FromArgb(239,220,183);$currentNav.Font=$script:FontTab;$bottom.Controls.Add($currentNav)
$newBtn=New-Object System.Windows.Forms.Button;$newBtn.Text='+ NEW BLANK FILE';$newBtn.Width=158;$newBtn.Height=38;$newBtn.FlatStyle='Flat';$newBtn.FlatAppearance.BorderColor=$script:Gold;$newBtn.ForeColor=$script:Gold;$newBtn.BackColor=[System.Drawing.Color]::FromArgb(28,25,21);$newBtn.Font=$script:FontSmall;$bottom.Controls.Add($newBtn)
$deleteBtn=New-Object System.Windows.Forms.Button;$deleteBtn.Text='DELETE';$deleteBtn.Width=72;$deleteBtn.Height=38;$deleteBtn.FlatStyle='Flat';$deleteBtn.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,65,45);$deleteBtn.ForeColor=[System.Drawing.Color]::FromArgb(218,126,92);$deleteBtn.BackColor=[System.Drawing.Color]::FromArgb(28,25,21);$bottom.Controls.Add($deleteBtn)
$script:SaveStateLabel=New-Object System.Windows.Forms.Label;$script:SaveStateLabel.Text='AUTO-SAVE READY';$script:SaveStateLabel.AutoSize=$true;$script:SaveStateLabel.ForeColor=[System.Drawing.Color]::FromArgb(137,177,120);$script:SaveStateLabel.Font=$script:FontSmall;$bottom.Controls.Add($script:SaveStateLabel)

function Write-LayoutError([string]$Stage,$ErrorRecord) {
    try {
        $msg = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') [$Stage] " + [string]$ErrorRecord.Exception.Message
        Add-Content -LiteralPath (Join-Path $script:DataRoot 'layout-error.txt') -Value $msg -Encoding UTF8
    } catch {}
}
function Layout-Book {
    if($null -eq $main -or $null -eq $book){return}

    # The normal open-book spread is used when there is enough width. When Windows
    # snaps The Files beside another app, switch to a compact book layout instead of
    # forcing a desktop-sized minimum width. Compact mode keeps full-width readable
    # pages and lets the book itself scroll horizontally between the left and right page.
    $isCompact=([int]$form.ClientSize.Width -lt 1050)
    $desiredHeader=if($isCompact){88}else{52}
    $desiredBottom=if($isCompact){94}else{70}
    if($header.Height -ne $desiredHeader){$header.Height=$desiredHeader;return}
    if($bottom.Height -ne $desiredBottom){$bottom.Height=$desiredBottom;return}

    $w=[int]$main.ClientSize.Width; $h=[int]$main.ClientSize.Height
    if($w -lt 500 -or $h -lt 400){return}

    if($isCompact){
        # ---------- SPLIT-SCREEN / SNAP MODE ----------
        $bookLeft=6; $bookTop=104
        $bookWidth=[math]::Max(500,$w-12)
        $bookHeight=[math]::Max(280,$h-$bottom.Height-$bookTop-8)
        $margin=20; $gut=14
        # One page is almost the whole snapped window width. The second page sits to
        # the right and is reached with the book's horizontal scrollbar.
        $pageW=[math]::Max(440,$bookWidth-44)
        $pageH=[math]::Max(250,$bookHeight-44)

        try {
            $book.Anchor='None'; $leftPage.Anchor='None'; $rightPage.Anchor='None'; $gutter.Anchor='None'
            $book.AutoScroll=$true
            $book.SetBounds($bookLeft,$bookTop,$bookWidth,$bookHeight)
            $leftPage.SetBounds($margin,20,$pageW,$pageH)
            $gutter.SetBounds(($margin+$pageW),25,$gut,[math]::Max(20,$pageH-10))
            $rightPage.SetBounds(($margin+$pageW+$gut),20,$pageW,$pageH)
            $book.AutoScrollMinSize=New-Object System.Drawing.Size(($margin+$pageW+$gut+$pageW+$margin),($pageH+40))
            $book.HorizontalScroll.SmallChange=70
            $book.HorizontalScroll.LargeChange=[math]::Max(180,[int]($bookWidth*0.75))
            $book.Invalidate()
        } catch { Write-LayoutError 'compact-book/pages' $_ }

        # Header becomes two tidy rows when snapped: title/update on top and the
        # search/story/character controls below it.
        try {
            $hw=[int]$header.ClientSize.Width
            $title.Location=New-Object System.Drawing.Point(12,8)
            $titleFlourishL.Visible=$false; $titleFlourishR.Visible=$false
            $updateBtn.Width=105; $updateBtn.Height=28
            $updateBtn.Location=New-Object System.Drawing.Point([math]::Max(430,$hw-117),8)

            $searchW=[math]::Max(145,[math]::Min(190,[int]($hw*0.28)))
            $storyW=[math]::Max(125,[math]::Min(165,[int]($hw*0.24)))
            $searchBox.Width=$searchW; $storyFilter.Width=$storyW
            $searchBox.Location=New-Object System.Drawing.Point(12,49)
            $searchHint.Location=New-Object System.Drawing.Point(20,55)
            $storyFilter.Location=New-Object System.Drawing.Point((20+$searchW),48)
            $jumpX=28+$searchW+$storyW
            $jumpCombo.Width=[math]::Max(145,$hw-$jumpX-12)
            $jumpCombo.Location=New-Object System.Drawing.Point($jumpX,48)
            if($searchBox.Focused -or $searchBox.Text.Length -gt 0){$searchHint.Visible=$false}else{$searchHint.Visible=$true}
        } catch { Write-LayoutError 'compact-header' $_ }

        # The side bookmarks become two horizontal bookmark rows. Nothing is hidden;
        # every section stays one click away even at half-screen width.
        try {
            $gap=4; $leftPad=7
            $row1=@('Overview','Appearance','Personality','Background','Family','Relationships')
            $row2=@('Skills','Psychology','Story','Timeline','Notes')
            $bw1=[math]::Max(72,[int](($w-($leftPad*2)-($gap*5))/$row1.Count))
            $bw2=[math]::Max(82,[int](($w-($leftPad*2)-($gap*4))/$row2.Count))
            for($i=0;$i -lt $row1.Count;$i++){
                $b=$script:SectionButtons[$row1[$i]]
                if($null -ne $b){$b.Width=$bw1;$b.Height=28;$b.Font=$script:FontSmall;$b.Location=New-Object System.Drawing.Point(($leftPad+$i*($bw1+$gap)),4);$b.Visible=$true;$b.BringToFront()}
            }
            for($i=0;$i -lt $row2.Count;$i++){
                $b=$script:SectionButtons[$row2[$i]]
                if($null -ne $b){$b.Width=$bw2;$b.Height=28;$b.Font=$script:FontSmall;$b.Location=New-Object System.Drawing.Point(($leftPad+$i*($bw2+$gap)),36);$b.Visible=$true;$b.BringToFront()}
            }
        } catch { Write-LayoutError 'compact-section-tabs' $_ }

        try {
            $statusW=[math]::Min(132,[int](($w-34)/3)); $statusGap=5
            $statusTotal=($statusW*3)+($statusGap*2); $statusStart=[int](($w-$statusTotal)/2)
            $i=0
            foreach($st in @('Existing','In Progress','Blank')){
                $b=$script:StatusButtons[$st]
                if($null -ne $b){$b.Width=$statusW;$b.Height=30;$b.Font=$script:FontSmall;$b.Location=New-Object System.Drawing.Point(($statusStart+$i*($statusW+$statusGap)),69);$b.Visible=$true;$b.BringToFront()}
                $i++
            }
        } catch { Write-LayoutError 'compact-status-tabs' $_ }

        try {
            $navGap=4; $navSide=[math]::Max(112,[math]::Min(145,[int]($w*0.23)))
            $currentW=[math]::Max(190,$w-($navSide*2)-($navGap*2)-16)
            $prevBtn.Width=$navSide;$nextBtn.Width=$navSide;$currentNav.Width=$currentW
            $prevBtn.Height=42;$nextBtn.Height=42;$currentNav.Height=42
            $prevBtn.Font=$script:FontSmall;$nextBtn.Font=$script:FontSmall;$currentNav.Font=$script:FontSmall
            $prevBtn.Location=New-Object System.Drawing.Point(8,5)
            $currentNav.Location=New-Object System.Drawing.Point((8+$navSide+$navGap),5)
            $nextBtn.Location=New-Object System.Drawing.Point((8+$navSide+$navGap+$currentW+$navGap),5)
            $newBtn.Width=145;$newBtn.Height=34;$newBtn.Location=New-Object System.Drawing.Point(8,53)
            $deleteBtn.Width=70;$deleteBtn.Height=34;$deleteBtn.Location=New-Object System.Drawing.Point(158,53)
            $script:SaveStateLabel.Location=New-Object System.Drawing.Point([math]::Max(236,$w-$script:SaveStateLabel.Width-14),63)
            $newBtn.BringToFront();$deleteBtn.BringToFront();$prevBtn.BringToFront();$currentNav.BringToFront();$nextBtn.BringToFront();$script:SaveStateLabel.BringToFront()
        } catch { Write-LayoutError 'compact-bottom-nav' $_ }
        return
    }

    # ---------- NORMAL OPEN-BOOK MODE ----------
    $side=142; $bookLeft=$side; $bookTop=38
    $bookWidth=[math]::Max(720,$w-($side*2)); $bookHeight=[math]::Max(410,$h-$bottom.Height-48)
    $margin=20; $gut=18; $pageW=[int](($bookWidth-($margin*2)-$gut)/2); $pageH=$bookHeight-40

    try {
        $book.AutoScroll=$false
        $book.AutoScrollMinSize=New-Object System.Drawing.Size(0,0)
        $book.AutoScrollPosition=New-Object System.Drawing.Point(0,0)
        $book.Anchor='None'; $leftPage.Anchor='None'; $rightPage.Anchor='None'; $gutter.Anchor='None'
        $book.SetBounds($bookLeft,$bookTop,$bookWidth,$bookHeight)
        $leftPage.SetBounds($margin,20,$pageW,$pageH)
        $gutter.SetBounds(($margin+$pageW),25,$gut,[math]::Max(20,$pageH-10))
        $rightPage.SetBounds(($margin+$pageW+$gut),20,$pageW,$pageH)
        $book.Invalidate()
    } catch { Write-LayoutError 'book/pages' $_ }

    try {
        $titleFlourishL.Visible=$true; $titleFlourishR.Visible=$true
        $title.Location=New-Object System.Drawing.Point([int](($header.ClientSize.Width-$title.Width)/2),10)
        $titleFlourishL.Location=New-Object System.Drawing.Point(($title.Left-75),18)
        $titleFlourishR.Location=New-Object System.Drawing.Point(($title.Right+12),18)
        $searchBox.Width=205; $storyFilter.Width=170; $jumpCombo.Width=205; $updateBtn.Width=105
        $searchBox.Location=New-Object System.Drawing.Point(16,12)
        $searchHint.Location=New-Object System.Drawing.Point(24,18)
        $storyFilter.Location=New-Object System.Drawing.Point(230,11)
        $jumpCombo.Location=New-Object System.Drawing.Point(406,11)
        $updateBtn.Location=New-Object System.Drawing.Point([math]::Max(620,$header.ClientSize.Width-120),11)
        if($searchBox.Focused -or $searchBox.Text.Length -gt 0){$searchHint.Visible=$false}else{$searchHint.Visible=$true}
    } catch { Write-LayoutError 'header' $_ }

    try {
        $tabY=$bookTop+72; $i=0
        foreach($nm in $leftNames){
            $b=$script:SectionButtons[$nm]
            if($null -ne $b){$b.Width=138;$b.Height=52;$b.Font=$script:FontTab;$b.Location=New-Object System.Drawing.Point(7,($tabY+$i*61));$b.Visible=$true;$b.BringToFront()}
            $i++
        }
    } catch { Write-LayoutError 'left-tabs' $_ }

    try {
        $i=0
        foreach($nm in $rightNames){
            $b=$script:SectionButtons[$nm]
            if($null -ne $b){$b.Width=138;$b.Height=52;$b.Font=$script:FontTab;$b.Location=New-Object System.Drawing.Point(($w-145),($tabY+$i*61));$b.Visible=$true;$b.BringToFront()}
            $i++
        }
    } catch { Write-LayoutError 'right-tabs' $_ }

    try {
        $statusStart=$bookLeft+[int](($bookWidth-408)/2); $i=0
        foreach($st in @('Existing','In Progress','Blank')){
            $b=$script:StatusButtons[$st]
            if($null -ne $b){$b.Width=132;$b.Height=42;$b.Font=$script:FontTab;$b.Location=New-Object System.Drawing.Point(($statusStart+$i*138),2);$b.Visible=$true;$b.BringToFront()}
            $i++
        }
    } catch { Write-LayoutError 'status-tabs' $_ }

    try {
        $prevBtn.Width=205;$nextBtn.Width=205;$currentNav.Width=260
        $prevBtn.Height=45;$nextBtn.Height=45;$currentNav.Height=45
        $prevBtn.Font=$script:FontTab;$nextBtn.Font=$script:FontTab;$currentNav.Font=$script:FontTab
        $newBtn.Width=158;$newBtn.Height=38;$deleteBtn.Width=72;$deleteBtn.Height=38
        $navTotal=670; $navX=[math]::Max(260,[int](($w-$navTotal)/2))
        $prevBtn.Location=New-Object System.Drawing.Point($navX,12)
        $currentNav.Location=New-Object System.Drawing.Point(($navX+205),12)
        $nextBtn.Location=New-Object System.Drawing.Point(($navX+465),12)
        $newBtn.Location=New-Object System.Drawing.Point(14,15)
        $deleteBtn.Location=New-Object System.Drawing.Point(177,15)
        $script:SaveStateLabel.Location=New-Object System.Drawing.Point([math]::Max(930,$w-150),27)
        $newBtn.BringToFront();$deleteBtn.BringToFront();$prevBtn.BringToFront();$currentNav.BringToFront();$nextBtn.BringToFront();$script:SaveStateLabel.BringToFront()
    } catch { Write-LayoutError 'bottom-nav' $_ }
}
$form.Add_Resize({Layout-Book})
$main.Add_Resize({Layout-Book})
$searchBox.Add_Enter({$searchHint.Visible=$false});$searchBox.Add_Leave({if($searchBox.Text.Length -eq 0){$searchHint.Visible=$true}})
Layout-Book

$script:ActiveStatus='Existing'
if(@('Existing','In Progress','Blank') -contains [string]$script:Settings.LastStatus){$script:ActiveStatus=[string]$script:Settings.LastStatus}
$script:CurrentSection='Overview'
if($script:SectionOrder -contains [string]$script:Settings.LastSection){$script:CurrentSection=[string]$script:Settings.LastSection}
$script:Filtered=@()
$script:CurrentIndex=-1
$script:FieldControls=@{}
$script:Rendering=$false
$script:UndoStacks=@{}
$script:ToolTip=New-Object System.Windows.Forms.ToolTip
$script:ToolTip.AutoPopDelay=8000;$script:ToolTip.InitialDelay=350;$script:ToolTip.ReshowDelay=100
$script:LeftHost=$null;$script:RightHost=$null

function Get-CurrentCharacter {
    if ($script:CurrentIndex -lt 0 -or $script:CurrentIndex -ge $script:Filtered.Count) { return $null }
    return $script:Filtered[$script:CurrentIndex]
}
function Get-LockState($c,[string]$key) { return (@($c.Locks) -contains $key) }
function Toggle-Lock([string]$key) {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    $locks=@($c.Locks)
    if($locks -contains $key){ $c.Locks=@($locks | Where-Object {$_ -ne $key}) } else { $c.Locks=@($locks + $key) }
    $c.Modified=(Get-Date).ToString('o'); Schedule-Save; Render-CurrentCharacter
}
function Push-UndoState {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    $id=[string]$c.Id
    if(-not $script:UndoStacks.ContainsKey($id)){ $script:UndoStacks[$id]=New-Object System.Collections.ArrayList }
    $json=($c | ConvertTo-Json -Depth 8 -Compress)
    [void]$script:UndoStacks[$id].Add($json)
    while($script:UndoStacks[$id].Count -gt 10){ $script:UndoStacks[$id].RemoveAt(0) }
}
function Undo-Character {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    $id=[string]$c.Id
    if(-not $script:UndoStacks.ContainsKey($id) -or $script:UndoStacks[$id].Count -lt 1){ return }
    $stack=$script:UndoStacks[$id]; $json=[string]$stack[$stack.Count-1]; $stack.RemoveAt($stack.Count-1)
    $restored=Convert-ToCharacterRecord ($json | ConvertFrom-Json)
    for($i=0;$i -lt $script:Characters.Count;$i++){ if($script:Characters[$i].Id -eq $id){ $script:Characters[$i]=$restored; break } }
    Refresh-Navigation -KeepId $id; Schedule-Save
}
function Set-RandomizedFieldValue($c,[string]$key) {
    if($null -eq $c -or [string]::IsNullOrWhiteSpace($key) -or (Get-LockState $c $key)){return $false}
    $v=if($key -eq 'Nicknames'){Get-SmartNickname}else{Get-RandomText $key}
    if($key -eq 'Nicknames' -and [string]::IsNullOrWhiteSpace([string]$v)){$v='Ace'}
    if([string]::IsNullOrWhiteSpace([string]$v)){return $false}
    $c.Fields[$key]=[string]$v
    if($script:FieldControls.ContainsKey($key)){
        $was=$script:Rendering;$script:Rendering=$true
        try{$ctrl=$script:FieldControls[$key];if($ctrl -is [System.Windows.Forms.ComboBox]){if($ctrl.Items.Contains([string]$v)){$ctrl.SelectedItem=[string]$v}}else{$ctrl.Text=[string]$v}}finally{$script:Rendering=$was}
    }
    return $true
}
function Randomize-OneField([string]$key) {
    $c=Get-CurrentCharacter; if($null -eq $c -or (Get-LockState $c $key)){return}
    Push-UndoState
    if(Set-RandomizedFieldValue $c $key){
        if($c.FileStatus -eq 'Blank'){$c.FileStatus='In Progress';$script:ActiveStatus='In Progress'}
        $c.Modified=(Get-Date).ToString('o');Schedule-Save;Render-CurrentCharacter;Update-NavLabels
    }
}
function Randomize-Section {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    Push-UndoState
    foreach($d in $script:FieldDefs[$script:CurrentSection]){[void](Set-RandomizedFieldValue $c ([string]$d.Key))}
    $c.Modified=(Get-Date).ToString('o'); if($c.FileStatus -eq 'Blank'){$c.FileStatus='In Progress';$script:ActiveStatus='In Progress'}
    Schedule-Save;Refresh-Navigation -KeepId $c.Id -NoRender;Render-CurrentCharacter
}
function Randomize-Character {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    if((Show-Confirm 'Randomize every unlocked field in this character?') -ne [System.Windows.Forms.DialogResult]::Yes){return}
    Push-UndoState
    # FullName is randomized first so Nickname(s) can derive from the newly generated name.
    if(-not (Get-LockState $c 'FullName')){[void](Set-RandomizedFieldValue $c 'FullName')}
    foreach($key in $script:AllFieldKeys){if($key -ne 'FullName'){[void](Set-RandomizedFieldValue $c ([string]$key))}}
    if([string]::IsNullOrWhiteSpace([string]$c.Fields.Nicknames) -and -not (Get-LockState $c 'Nicknames')){$c.Fields.Nicknames=[string](Get-SmartNickname)}
    $c.FileStatus='In Progress'; $script:ActiveStatus='In Progress'; $c.Modified=(Get-Date).ToString('o')
    Schedule-Save;Refresh-Navigation -KeepId $c.Id -NoRender;Render-CurrentCharacter
}

function Scroll-BookHost($ctrl,[int]$delta) {
    try {
        $scrollHost=$ctrl
        while($null -ne $scrollHost -and -not ($scrollHost -is [System.Windows.Forms.ScrollableControl])){$scrollHost=$scrollHost.Parent}
        # Prefer the nearest auto-scrolling page-content panel.
        $walk=$ctrl
        while($null -ne $walk){
            if($walk.AutoScroll){
                $old=[math]::Abs([int]$walk.AutoScrollPosition.Y)
                $target=$old-[int]($delta/120)*70
                $max=[math]::Max(0,$walk.VerticalScroll.Maximum-$walk.VerticalScroll.LargeChange+1)
                $target=[math]::Max(0,[math]::Min($target,$max))
                $walk.AutoScrollPosition=New-Object System.Drawing.Point(0,$target)
                return
            }
            $walk=$walk.Parent
        }
    } catch {}
}

function New-PageContent([System.Windows.Forms.Panel]$page) {
    try{$contentHost=New-Object BookContentPanel}catch{$contentHost=New-Object System.Windows.Forms.Panel;$contentHost.AutoScroll=$true;$contentHost.BackColor=$script:Parchment}
    $contentHost.Location=New-Object System.Drawing.Point(18,66)
    $contentHost.Size=New-Object System.Drawing.Size([math]::Max(120,$page.ClientSize.Width-36),[math]::Max(120,$page.ClientSize.Height-128))
    $contentHost.Anchor='Top,Bottom,Left,Right'
    $contentHost.AutoScroll=$true
    $contentHost.Add_MouseWheel({
        param($sender,$e)
        try {
            $old=$sender.VerticalScroll.Value
            $target=$old-[int]($e.Delta/120)*70
            $target=[math]::Max($sender.VerticalScroll.Minimum,[math]::Min($target,$sender.VerticalScroll.Maximum-$sender.VerticalScroll.LargeChange+1))
            $sender.AutoScrollPosition=New-Object System.Drawing.Point(0,$target)
        } catch {}
    })
    $contentHost.Add_MouseEnter({try{$this.Focus()}catch{}})
    $page.Controls.Add($contentHost)
    return $contentHost
}
function Add-TopBookHeader([System.Windows.Forms.Panel]$page,[string]$text,[bool]$left=$false,[string]$kicker='') {
    if([string]::IsNullOrWhiteSpace($kicker)){if($left){$kicker='CHARACTER FILE'}else{$kicker='ARCHIVE DETAILS'}}
    $k=New-Object System.Windows.Forms.Label;$k.Text=$kicker.ToUpper();$k.Font=New-Object System.Drawing.Font('Georgia',7,[System.Drawing.FontStyle]::Bold);$k.ForeColor=[System.Drawing.Color]::FromArgb(128,87,50);$k.AutoSize=$true;$k.Location=New-Object System.Drawing.Point(26,13);$page.Controls.Add($k)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=$text;if($left){$lbl.Font=New-Object System.Drawing.Font('Georgia',20,[System.Drawing.FontStyle]::Bold)}else{$lbl.Font=New-Object System.Drawing.Font('Georgia',13,[System.Drawing.FontStyle]::Bold)};$lbl.ForeColor=$script:Ink;$lbl.AutoEllipsis=$true;$lbl.Location=New-Object System.Drawing.Point(26,29);$lbl.Size=New-Object System.Drawing.Size([math]::Max(140,$page.ClientSize.Width-52),30);$lbl.Anchor='Top,Left,Right';$page.Controls.Add($lbl)
    $rule=New-Object System.Windows.Forms.Panel;$rule.Height=1;$rule.BackColor=[System.Drawing.Color]::FromArgb(138,103,62);$rule.Location=New-Object System.Drawing.Point(25,61);$rule.Width=[math]::Max(100,$page.ClientSize.Width-50);$rule.Anchor='Top,Left,Right';$page.Controls.Add($rule)
}

# ---------------- FAMILY AUDIT: structured, folded, repeatable editor ----------------
if($null -eq $script:FamilyFoldState){
    $script:FamilyFoldState=@{Parent1=$false;Parent2=$false;Siblings=$false;Children=$false;OtherFamily=$false;FamilyHistory=$false}
}
if($null -eq $script:FamilyEntryFoldState){$script:FamilyEntryFoldState=@{}}
$script:FamilyGenderOptions=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')
$script:FamilyStatusOptions=@('Alive','Dead','Missing','Estranged','Unknown','Other')
$script:FamilyOccupationOptions=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')
$script:FamilyDynamicOptions=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')
$script:FamilyHistoryOptions=@('Adoption','Divorce / Separation','Estrangement','Death / Loss','Missing Relative','Family Secret','Abuse','Neglect','Addiction','Mental Illness','Chronic Illness','Disability','Incarceration','Crime','Poverty / Financial Hardship','Wealth / Inheritance','Immigration / Displacement','War / Conflict','Religious Conflict','Family Feud','Scandal','Supernatural Heritage','Found Family','Other / Custom')

function Get-FamilyArray([string]$Key){
    $c=Get-CurrentCharacter;if($null -eq $c){return @()}
    $raw=[string]$c.Fields[$Key];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{
        if($Key -eq 'Siblings'){return @([pscustomobject]@{Name='';Gender='';SiblingType='';AgeRelationship='';Status='';Occupation='';RelationshipDynamic='';Notes=$raw})}
        if($Key -eq 'Children'){return @([pscustomobject]@{Name='';Gender='';ChildType='';AgeLifeStage='';Status='';Occupation='';OtherParent='';RelationshipDynamic='';Notes=$raw})}
        if($Key -eq 'OtherFamily'){return @([pscustomobject]@{Name='';Gender='';Relationship='';Status='';Occupation='';RelationshipDynamic='';Importance='';Notes=$raw})}
        return @()
    }
}
function Set-FamilyArray([string]$Key,$Items){
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress
    $c.Fields[$Key]=$json;Mark-CharacterChanged $json
}
function Get-FamilyHistoryMap {
    $m=[ordered]@{};$c=Get-CurrentCharacter;if($null -eq $c){return $m}
    $raw=[string]$c.Fields['FamilyHistory'];if([string]::IsNullOrWhiteSpace($raw)){return $m}
    try{$o=$raw|ConvertFrom-Json;foreach($p in @($o.PSObject.Properties)){$m[[string]$p.Name]=[string]$p.Value}}catch{$m['Other / Custom']=$raw}
    return $m
}
function Set-FamilyHistoryMap($Map){
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $json=ConvertTo-Json -InputObject $Map -Depth 6 -Compress
    $c.Fields['FamilyHistory']=$json;Mark-CharacterChanged $json
}
function Toggle-FamilyFold([string]$Key){
    if(-not $script:FamilyFoldState.ContainsKey($Key)){$script:FamilyFoldState[$Key]=$false}
    $script:FamilyFoldState[$Key]=-not [bool]$script:FamilyFoldState[$Key];Render-CurrentCharacter
}
function Get-FamilyEntryFoldKey([string]$DataKey,[int]$Index){return ($DataKey+'|'+$Index)}
function Toggle-FamilyEntryFold([string]$DataKey,[int]$Index){
    $k=Get-FamilyEntryFoldKey $DataKey $Index
    if(-not $script:FamilyEntryFoldState.ContainsKey($k)){$script:FamilyEntryFoldState[$k]=$false}
    $script:FamilyEntryFoldState[$k]=-not [bool]$script:FamilyEntryFoldState[$k];Render-CurrentCharacter
}
function Add-FamilyHeader($page,[string]$Title,[string]$StateKey,[int]$Y){
    $open=[bool]$script:FamilyFoldState[$StateKey]
    $b=New-Object System.Windows.Forms.Button;$b.Text=if($open){'[-]  '+$Title}else{'[+]  '+$Title};$b.Tag=$StateKey;$b.Height=34;$b.Location=New-Object System.Drawing.Point(8,$Y);$b.Width=[math]::Max(190,$page.ClientSize.Width-22);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.Font=New-Object System.Drawing.Font('Georgia',9,[System.Drawing.FontStyle]::Bold);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$b.ForeColor=$script:Ink;$b.Add_Click({Toggle-FamilyFold ([string]$this.Tag)});$page.Controls.Add($b)
    return 40
}
function Add-FamilySmallDice($page,[object]$Tag,[int]$X,[int]$Y,[scriptblock]$Handler){
    $d=New-Object System.Windows.Forms.Button;$d.Text='🎲';$d.Tag=$Tag;$d.Width=30;$d.Height=27;$d.Location=New-Object System.Drawing.Point($X,$Y);$d.Anchor='Top,Right';$d.FlatStyle='Flat';$d.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$d.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$d.ForeColor=$script:Ink;$d.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$d.Add_Click($Handler);$page.Controls.Add($d);$script:ToolTip.SetToolTip($d,'Randomize this field');return $d
}
function Family-DirectChanged($ctrl){
    if($script:Rendering){return};$c=Get-CurrentCharacter;if($null -eq $c){return};$key=[string]$ctrl.Tag
    $v=if($ctrl -is [System.Windows.Forms.ComboBox]){[string]$ctrl.Text}else{[string]$ctrl.Text}
    $c.Fields[$key]=$v;Mark-CharacterChanged $v
}
function Add-FamilyDirectField($page,$Def,[int]$Y){
    $key=[string]$Def.Key;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(138,[int]($w*0.34));$inputX=$labelW+18;$inputW=[math]::Max(118,$w-$inputX-76)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(10,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,38);$page.Controls.Add($lbl)
    $control=$null;$height=44
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){
        $control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.Add_SelectedIndexChanged({Family-DirectChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Family-DirectChanged $this})}
    } elseif($type -eq 'MultiChoice'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true
        $c=Get-CurrentCharacter;$value=if($null -eq $c){''}else{[string]$c.Fields[$key]};$selected=@(Split-MultiChoiceValue $value);$control.Text=Get-MultiChoiceSummary $value
        $menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Font=$script:FontSmall;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}})
        foreach($opt in @($Def.Options)){$item=New-Object System.Windows.Forms.ToolStripMenuItem;$item.Text=[string]$opt;$item.CheckOnClick=$true;$item.Checked=($selected -contains [string]$opt);$item.Tag=[pscustomobject]@{Key=$key;Option=[string]$opt};$item.Add_Click({$t=$this.Tag;Set-MultiChoiceSelection ([string]$t.Key) ([string]$t.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($item)}
        $control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
    } else {
        $control=New-Object System.Windows.Forms.TextBox;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.BorderStyle='FixedSingle';if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=62;$height=76};$control.Add_TextChanged({Family-DirectChanged $this})
    }
    $control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control);$script:FieldControls[$key]=$control
    [void](Add-FamilySmallDice $page $key ($w-68) ($Y-3) {Randomize-OneField ([string]$this.Tag)})
    $lock=New-Object System.Windows.Forms.Button;$lock.Tag=$key;$lock.Width=30;$lock.Height=27;$lock.Location=New-Object System.Drawing.Point(($w-36),($Y-3));$lock.Anchor='Top,Right';$lock.FlatStyle='Flat';$lock.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$lock.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$lock.ForeColor=$script:Ink;$lock.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$lock.Add_Click({Toggle-Lock ([string]$this.Tag)});$page.Controls.Add($lock)
    return $height
}
function Add-FamilyParent($page,[string]$Which,[int]$Y){
    $title=if($Which -eq 'Parent1'){'Parent One'}else{'Parent Two'};$h=Add-FamilyHeader $page $title $Which $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState[$Which]){return $h}
    $prefix=if($Which -eq 'Parent1'){'Parent1'}else{'Parent2'}
    $defs=@($script:FieldDefs['Family']|Where-Object{[string]$_.Key -like ($prefix+'*')})
    $used=$h;foreach($d in $defs){$dh=Add-FamilyDirectField $page $d $Y;$Y+=$dh;$used+=$dh};return ($used+8)
}
function Get-FamilyRepeaterFields([string]$Kind){
    if($Kind -eq 'Sibling'){
        return @(
            [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
            [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
            [pscustomobject]@{Field='SiblingType';Label='Sibling Type';Type='Choice';Options=@('Full Sibling','Half-Sibling','Step-Sibling','Adoptive Sibling','Foster Sibling','Chosen / Found Sibling','Unknown','Other / Custom')},
            [pscustomobject]@{Field='AgeRelationship';Label='Age Relationship';Type='Choice';Options=@('Older','Younger','Same Age / Twin','Unknown','Other / Custom')},
            [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
            [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
            [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
            [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
        )
    }
    if($Kind -eq 'Child'){
        return @(
            [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
            [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
            [pscustomobject]@{Field='ChildType';Label='Child Type';Type='Choice';Options=@('Biological Child','Adopted Child','Stepchild','Foster Child','Ward / Dependent','Chosen / Found Family','Unknown','Other / Custom')},
            [pscustomobject]@{Field='AgeLifeStage';Label='Age / Life Stage';Type='Choice';Options=@('Infant','Child','Preteen','Teenager','Young Adult','Adult','Middle-Aged','Older Adult','Deceased','Unknown','Other / Custom')},
            [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
            [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
            [pscustomobject]@{Field='OtherParent';Label='Other Parent';Type='Text';Options=@()},
            [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
            [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
        )
    }
    return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
        [pscustomobject]@{Field='Relationship';Label='Relationship';Type='Choice';Options=@('Grandparent','Grandchild','Aunt / Uncle','Niece / Nephew','Cousin','In-Law','Guardian','Godparent','Chosen / Found Family','Distant Relative','Unknown','Other / Custom')},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
        [pscustomobject]@{Field='Importance';Label='Importance';Type='Choice';Options=@('Minor','Moderate','Important','Very Important','Central','Unknown')},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )
}
function New-FamilyEntry([string]$Kind){
    $o=[ordered]@{};foreach($d in @(Get-FamilyRepeaterFields $Kind)){$o[[string]$d.Field]=''};return [pscustomobject]$o
}
function Set-FamilyEntryValue([string]$DataKey,[int]$Index,[string]$Field,[string]$Value){
    $items=@(Get-FamilyArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$obj=$items[$Index];$obj|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-FamilyArray $DataKey $items
}
function Family-EntryChanged($ctrl){
    if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-FamilyEntryValue ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)
}
function Set-FamilyEntryMultiChoice([string]$DataKey,[int]$Index,[string]$Field,[string]$Option,[bool]$Selected){
    $items=@(Get-FamilyArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$cur=[string]$items[$Index].$Field;$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue $cur)){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-FamilyEntryValue $DataKey $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter
}
function Add-FamilyEntryField($page,[string]$DataKey,[int]$Index,[string]$Kind,$Def,[int]$Y){
    $items=@(Get-FamilyArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$field=[string]$Def.Field;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(126,[int]($w*0.32));$inputX=$labelW+28;$inputW=[math]::Max(105,$w-$inputX-48)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,36);$page.Controls.Add($lbl)
    $tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Kind=$Kind};$control=$null;$height=42;$value=[string]$obj.$field
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){
        $control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Text=$value;$control.Add_SelectedIndexChanged({Family-EntryChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Family-EntryChanged $this})}
    } elseif($type -eq 'MultiChoice'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true;$control.Text=Get-MultiChoiceSummary $value;$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options)){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=($selected -contains [string]$opt);$mi.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$x=$this.Tag;Set-FamilyEntryMultiChoice ([string]$x.DataKey) ([int]$x.Index) ([string]$x.Field) ([string]$x.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
    } else {
        $control=New-Object System.Windows.Forms.TextBox;$control.BorderStyle='FixedSingle';$control.Text=$value;if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=58;$height=70};$control.Add_TextChanged({Family-EntryChanged $this})
    }
    $control.Tag=$tag;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control)
    [void](Add-FamilySmallDice $page $tag ($w-36) ($Y-3) {Randomize-FamilyEntryField $this.Tag})
    return $height
}
function Render-FamilyEntry([System.Windows.Forms.Panel]$page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){
    $items=@(Get-FamilyArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$fk=Get-FamilyEntryFoldKey $DataKey $Index;if(-not $script:FamilyEntryFoldState.ContainsKey($fk)){$script:FamilyEntryFoldState[$fk]=$false};$open=[bool]$script:FamilyEntryFoldState[$fk]
    $name=[string]$obj.Name;if([string]::IsNullOrWhiteSpace($name)){$name="$Kind $($Index+1)"}
    $w=[math]::Max(320,$page.ClientSize.Width-26);$head=New-Object System.Windows.Forms.Button;$head.Text=if($open){'[-]  '+$name}else{'[+]  '+$name};$head.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$head.Location=New-Object System.Drawing.Point(18,$Y);$head.Size=New-Object System.Drawing.Size([math]::Max(150,$w-86),30);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.FlatStyle='Flat';$head.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,112,67);$head.BackColor=[System.Drawing.Color]::FromArgb(240,220,184);$head.ForeColor=$script:Ink;$head.Font=$script:FontSmall;$head.Add_Click({$t=$this.Tag;Toggle-FamilyEntryFold ([string]$t.DataKey) ([int]$t.Index)});$page.Controls.Add($head)
    $rm=New-Object System.Windows.Forms.Button;$rm.Text='×';$rm.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$rm.Location=New-Object System.Drawing.Point(($w-48),$Y);$rm.Size=New-Object System.Drawing.Size(30,30);$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.ForeColor=[System.Drawing.Color]::FromArgb(145,58,43);$rm.Add_Click({Remove-FamilyEntry $this.Tag});$page.Controls.Add($rm)
    $used=36;if(-not $open){return $used};$yy=$Y+38;foreach($d in @(Get-FamilyRepeaterFields $Kind)){$dh=Add-FamilyEntryField $page $DataKey $Index $Kind $d $yy;$yy+=$dh;$used+=$dh};return ($used+8)
}
function Add-FamilyEntryButton($page,[string]$DataKey,[string]$Kind,[int]$Y){
    $b=New-Object System.Windows.Forms.Button;$b.Text=('+ ADD '+$Kind.ToUpper());$b.Tag=[pscustomobject]@{DataKey=$DataKey;Kind=$Kind};$b.Location=New-Object System.Drawing.Point(18,$Y);$b.Size=New-Object System.Drawing.Size(130,29);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Add-FamilyEntry $this.Tag});$page.Controls.Add($b);return 36
}
function Add-FamilyEntry($Tag){$items=New-Object System.Collections.Generic.List[object];foreach($x in @(Get-FamilyArray ([string]$Tag.DataKey))){[void]$items.Add($x)};$obj=New-FamilyEntry ([string]$Tag.Kind);[void]$items.Add($obj);Set-FamilyArray ([string]$Tag.DataKey) @($items);$k=Get-FamilyEntryFoldKey ([string]$Tag.DataKey) ($items.Count-1);$script:FamilyEntryFoldState[$k]=$true;Render-CurrentCharacter}
function Remove-FamilyEntry($Tag){$old=@(Get-FamilyArray ([string]$Tag.DataKey));$new=New-Object System.Collections.Generic.List[object];for($i=0;$i -lt $old.Count;$i++){if($i -ne [int]$Tag.Index){[void]$new.Add($old[$i])}};Set-FamilyArray ([string]$Tag.DataKey) @($new);Render-CurrentCharacter}
function Add-FamilyRepeater($page,[string]$DataKey,[string]$Title,[string]$Kind,[int]$Y){$h=Add-FamilyHeader $page $Title $DataKey $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState[$DataKey]){return $h};$add=Add-FamilyEntryButton $page $DataKey $Kind $Y;$Y+=$add;$used=$h+$add;$items=@(Get-FamilyArray $DataKey);for($i=0;$i -lt $items.Count;$i++){$dh=Render-FamilyEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh};return ($used+8)}
function Set-FamilyHistorySelection([string]$Category,[bool]$Selected){$m=Get-FamilyHistoryMap;if($Selected){if(-not $m.Contains($Category)){$m[$Category]=''}}else{$m.Remove($Category)};Set-FamilyHistoryMap $m;Render-CurrentCharacter}
function Set-FamilyHistoryNote([string]$Category,[string]$Value){$m=Get-FamilyHistoryMap;if(-not $m.Contains($Category)){$m[$Category]=''};$m[$Category]=$Value;Set-FamilyHistoryMap $m}
function Randomize-FamilyHistoryCategory([string]$Category){$m=Get-FamilyHistoryMap;if(-not $m.Contains($Category)){$m[$Category]=''};$m[$Category]=[string](Get-Random -InputObject @('A defining event for this branch of the family.','Kept quiet for years and still affects current relationships.','Changed how the family relates to one another.','The full details are known by only a few relatives.'));Set-FamilyHistoryMap $m;Render-CurrentCharacter}
function Add-FamilyHistory($page,[int]$Y){
    $h=Add-FamilyHeader $page 'Important Family History' 'FamilyHistory' $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState['FamilyHistory']){return $h};$w=[math]::Max(320,$page.ClientSize.Width-26);$m=Get-FamilyHistoryMap;$btn=New-Object System.Windows.Forms.Button;$btn.Location=New-Object System.Drawing.Point(18,$Y);$btn.Size=New-Object System.Drawing.Size([math]::Max(150,$w-74),29);$btn.Anchor='Top,Left,Right';$btn.FlatStyle='Flat';$btn.TextAlign='MiddleLeft';$btn.Text=if($m.Count -eq 0){'Select family-history categories...  ▼'}else{('{0} selected  ▼' -f $m.Count)};$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});foreach($opt in $script:FamilyHistoryOptions){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=$opt;$mi.CheckOnClick=$true;$mi.Checked=$m.Contains($opt);$mi.Tag=$opt;$mi.Add_Click({Set-FamilyHistorySelection ([string]$this.Tag) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$btn.ContextMenuStrip=$menu;$btn.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}});$page.Controls.Add($btn);[void](Add-FamilySmallDice $page 'FamilyHistory' ($w-36) $Y {Randomize-OneField 'FamilyHistory'});$used=$h+38;$Y+=38
    foreach($cat in @($m.Keys)){$lbl=New-Object System.Windows.Forms.Label;$lbl.Text=([string]$cat+' — notes');$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size([math]::Max(140,$w-70),20);$lbl.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$lbl.ForeColor=$script:Muted;$page.Controls.Add($lbl);$tb=New-Object System.Windows.Forms.TextBox;$tb.Multiline=$true;$tb.ScrollBars='Vertical';$tb.Location=New-Object System.Drawing.Point(20,($Y+20));$tb.Size=New-Object System.Drawing.Size([math]::Max(140,$w-70),58);$tb.Anchor='Top,Left,Right';$tb.Text=[string]$m[$cat];$tb.Tag=$cat;$tb.Font=$script:FontSmall;$tb.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$tb.ForeColor=$script:Ink;$tb.Add_TextChanged({if($script:Rendering){return};Set-FamilyHistoryNote ([string]$this.Tag) ([string]$this.Text)});$page.Controls.Add($tb);[void](Add-FamilySmallDice $page $cat ($w-36) ($Y+20) {Randomize-FamilyHistoryCategory ([string]$this.Tag)});$Y+=86;$used+=86};return ($used+8)
}
function Get-FamilyEntryRandomValue([string]$Field,[string]$Kind){
    if($Field -eq 'Name' -or $Field -eq 'OtherParent'){if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)};return 'Alex Morgan'}
    if($Field -eq 'Gender'){return [string](Get-Random -InputObject $script:FamilyGenderOptions)}
    if($Field -eq 'Status'){return [string](Get-Random -InputObject $script:FamilyStatusOptions)}
    if($Field -eq 'Occupation'){return [string](Get-Random -InputObject $script:FamilyOccupationOptions)}
    if($Field -eq 'RelationshipDynamic'){return ((Get-Random -InputObject $script:FamilyDynamicOptions -Count (Get-Random -Minimum 1 -Maximum 4)) -join '; ')}
    if($Field -eq 'SiblingType'){return [string](Get-Random -InputObject @('Full Sibling','Half-Sibling','Step-Sibling','Adoptive Sibling','Foster Sibling','Chosen / Found Sibling'))}
    if($Field -eq 'AgeRelationship'){return [string](Get-Random -InputObject @('Older','Younger','Same Age / Twin','Unknown'))}
    if($Field -eq 'ChildType'){return [string](Get-Random -InputObject @('Biological Child','Adopted Child','Stepchild','Foster Child','Ward / Dependent','Chosen / Found Family'))}
    if($Field -eq 'AgeLifeStage'){return [string](Get-Random -InputObject @('Infant','Child','Preteen','Teenager','Young Adult','Adult','Middle-Aged','Older Adult'))}
    if($Field -eq 'Relationship'){return [string](Get-Random -InputObject @('Grandparent','Grandchild','Aunt / Uncle','Niece / Nephew','Cousin','In-Law','Guardian','Godparent','Chosen / Found Family','Distant Relative'))}
    if($Field -eq 'Importance'){return [string](Get-Random -InputObject @('Minor','Moderate','Important','Very Important','Central'))}
    if($Field -eq 'Notes'){return [string](Get-Random -InputObject @('Important to the character, but the details still need development.','Their history is complicated and changes over the course of the story.','A reliable source of support during difficult periods.','There is unresolved tension between them.'))}
    return ''
}
function Randomize-FamilyEntryField($Tag){$v=Get-FamilyEntryRandomValue ([string]$Tag.Field) ([string]$Tag.Kind);if(-not [string]::IsNullOrWhiteSpace($v)){Push-UndoState;Set-FamilyEntryValue ([string]$Tag.DataKey) ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}}
function Get-RandomFamilyStructuredValue([string]$Key){
    if($Key -eq 'FamilyHistory'){$m=[ordered]@{};$opts=Get-Random -InputObject $script:FamilyHistoryOptions -Count (Get-Random -Minimum 1 -Maximum 4);foreach($o in @($opts)){$m[[string]$o]=[string](Get-Random -InputObject @('A major event that still shapes the family.','The details are complicated and not openly discussed.','This changed several relationships in the family.'))};return (ConvertTo-Json -InputObject $m -Depth 5 -Compress)}
    $kind=if($Key -eq 'Siblings'){'Sibling'}elseif($Key -eq 'Children'){'Child'}else{'Other'};$obj=New-FamilyEntry $kind;foreach($d in @(Get-FamilyRepeaterFields $kind)){$obj|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-FamilyEntryRandomValue ([string]$d.Field) $kind) -Force};return (ConvertTo-Json -InputObject @($obj) -Depth 6 -Compress)
}
function Render-FamilySection($c,$leftHost,$rightHost){
    $y=12;$h=Add-FamilyParent $leftHost 'Parent1' $y;$y+=$h;$h=Add-FamilyParent $leftHost 'Parent2' $y;$y+=$h
    $y=12;$h=Add-FamilyRepeater $rightHost 'Siblings' 'Siblings' 'Sibling' $y;$y+=$h;$h=Add-FamilyRepeater $rightHost 'Children' 'Children' 'Child' $y;$y+=$h;$h=Add-FamilyRepeater $rightHost 'OtherFamily' 'Other Family' 'Other' $y;$y+=$h;$h=Add-FamilyHistory $rightHost $y;$y+=$h
}
# ---------------- END FAMILY AUDIT -------------------------------------------

# ---------------- RELATIONSHIPS AUDIT -----------------------------------------
$script:RelationshipStatusOptions=@('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','Complicated / Unclear','Unknown','Other / Custom')
$script:SexualityOptions=@('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown','Other / Custom')
$script:RelationshipGenderOptions=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')
$script:RelationshipPersonStatusOptions=@('Alive','Dead','Missing','Estranged','Unknown','Other / Custom')
$script:RelationshipOccupationOptions=$script:FamilyOccupationOptions
$script:RelationshipDynamicOptions=$script:FamilyDynamicOptions
$script:FriendTypeOptions=@('Best Friend','Close Friend','Friend','Childhood Friend','Family Friend','Work Friend','School Friend','Online Friend','Former Friend Reconnected','Found Family','Other / Custom','Unknown')
$script:ClosenessOptions=@('Acquaintance','Casual','Moderate','Close','Very Close','Best Friend','Complicated','Distant','Estranged','Unknown')
$script:EnemyTypeOptions=@('Not a Rival / N/A','Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival','Rival/Love Interest','Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest','Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other')
$script:ThreatLevelOptions=@('None','Low','Moderate','High','Severe','Extreme','Unknown')
$script:MentorTypeOptions=@('Teacher','Academic Mentor','Professional Mentor','Combat Mentor','Magic / Power Mentor','Religious / Spiritual Mentor','Life Mentor','Parental Mentor','Informal Mentor','Former Mentor','Other / Custom','Unknown')
$script:MentorshipStatusOptions=@('Active','Former','Occasional','Estranged','Ended Well','Ended Badly','Mentor Deceased','Mentor Missing','Unknown','Other / Custom')
$script:RelationshipFoldState=@{Friends=$true;Enemies=$true;Mentors=$true}
$script:RelationshipEntryFoldState=@{}

function Get-RelationshipArray([string]$Key){
    $c=Get-CurrentCharacter;if($null -eq $c){return @()}
    $raw=[string]$c.Fields[$Key];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{
        if($Key -eq 'Friends'){return @([pscustomobject]@{Name='';Gender='';FriendType='';Status='';Occupation='';RelationshipDynamic='';Closeness='';Notes=$raw})}
        if($Key -eq 'Enemies'){return @([pscustomobject]@{Name='';Gender='';EnemyType='';Status='';Occupation='';RelationshipDynamic='';ThreatLevel='';Notes=$raw})}
        if($Key -eq 'Mentors'){return @([pscustomobject]@{Name='';Gender='';MentorType='';Status='';Occupation='';RelationshipDynamic='';MentorshipStatus='';Notes=$raw})}
        return @()
    }
}
function Set-RelationshipArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress;$c.Fields[$Key]=$json;Mark-CharacterChanged $json}
function Toggle-RelationshipFold([string]$Key){if(-not $script:RelationshipFoldState.ContainsKey($Key)){$script:RelationshipFoldState[$Key]=$false};$script:RelationshipFoldState[$Key]=-not [bool]$script:RelationshipFoldState[$Key];Render-CurrentCharacter}
function Get-RelationshipEntryFoldKey([string]$DataKey,[int]$Index){return ($DataKey+'|'+$Index)}
function Toggle-RelationshipEntryFold([string]$DataKey,[int]$Index){$k=Get-RelationshipEntryFoldKey $DataKey $Index;if(-not $script:RelationshipEntryFoldState.ContainsKey($k)){$script:RelationshipEntryFoldState[$k]=$false};$script:RelationshipEntryFoldState[$k]=-not [bool]$script:RelationshipEntryFoldState[$k];Render-CurrentCharacter}
function Add-RelationshipHeader($page,[string]$Title,[string]$StateKey,[int]$Y){$open=[bool]$script:RelationshipFoldState[$StateKey];$b=New-Object System.Windows.Forms.Button;$b.Text=if($open){'[-]  '+$Title}else{'[+]  '+$Title};$b.Tag=$StateKey;$b.Height=34;$b.Location=New-Object System.Drawing.Point(8,$Y);$b.Width=[math]::Max(190,$page.ClientSize.Width-22);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.Font=New-Object System.Drawing.Font('Georgia',9,[System.Drawing.FontStyle]::Bold);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$b.ForeColor=$script:Ink;$b.Add_Click({Toggle-RelationshipFold ([string]$this.Tag)});$page.Controls.Add($b);return 40}
function Get-RelationshipRepeaterFields([string]$Kind){
    if($Kind -eq 'Friend'){return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='FriendType';Label='Friend Type';Type='Choice';Options=$script:FriendTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='Closeness';Label='Closeness';Type='Choice';Options=$script:ClosenessOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )}
    if($Kind -eq 'Enemy'){return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='EnemyType';Label='Enemy Type';Type='Choice';Options=$script:EnemyTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='ThreatLevel';Label='Threat Level';Type='Choice';Options=$script:ThreatLevelOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )}
    return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='MentorType';Label='Mentor Type';Type='Choice';Options=$script:MentorTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='MentorshipStatus';Label='Mentorship Status';Type='Choice';Options=$script:MentorshipStatusOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )
}
function New-RelationshipEntry([string]$Kind){$o=[ordered]@{};foreach($d in @(Get-RelationshipRepeaterFields $Kind)){$o[[string]$d.Field]=''};return [pscustomobject]$o}
function Set-RelationshipEntryValue([string]$DataKey,[int]$Index,[string]$Field,[string]$Value){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$obj=$items[$Index];$obj|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-RelationshipArray $DataKey $items}
function Relationship-EntryChanged($ctrl){if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-RelationshipEntryValue ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)}
function Set-RelationshipEntryMultiChoice([string]$DataKey,[int]$Index,[string]$Field,[string]$Option,[bool]$Selected){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$cur=[string]$items[$Index].$Field;$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue $cur)){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-RelationshipEntryValue $DataKey $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter}
function Get-RelationshipEntryRandomValue([string]$Field,[string]$Kind){
    if($Field -eq 'Name'){if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)};return 'Alex Morgan'}
    if($Field -eq 'Gender'){return [string](Get-Random -InputObject $script:RelationshipGenderOptions)}
    if($Field -eq 'Status'){return [string](Get-Random -InputObject $script:RelationshipPersonStatusOptions)}
    if($Field -eq 'Occupation'){return [string](Get-Random -InputObject $script:RelationshipOccupationOptions)}
    if($Field -eq 'RelationshipDynamic'){return ((Get-Random -InputObject $script:RelationshipDynamicOptions -Count (Get-Random -Minimum 1 -Maximum 4)) -join '; ')}
    if($Field -eq 'FriendType'){return [string](Get-Random -InputObject $script:FriendTypeOptions)}
    if($Field -eq 'Closeness'){return [string](Get-Random -InputObject $script:ClosenessOptions)}
    if($Field -eq 'EnemyType'){return [string](Get-Random -InputObject $script:EnemyTypeOptions)}
    if($Field -eq 'ThreatLevel'){return [string](Get-Random -InputObject $script:ThreatLevelOptions)}
    if($Field -eq 'MentorType'){return [string](Get-Random -InputObject $script:MentorTypeOptions)}
    if($Field -eq 'MentorshipStatus'){return [string](Get-Random -InputObject $script:MentorshipStatusOptions)}
    if($Field -eq 'Notes'){return [string](Get-Random -InputObject @('Their history with the character is complicated.','This relationship changes significantly over the course of the story.','They are an important influence on the character.','There is unresolved tension between them.'))}
    return ''
}
function Randomize-RelationshipEntryField($Tag){$v=Get-RelationshipEntryRandomValue ([string]$Tag.Field) ([string]$Tag.Kind);if(-not [string]::IsNullOrWhiteSpace($v)){Push-UndoState;Set-RelationshipEntryValue ([string]$Tag.DataKey) ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}}
function Get-RandomRelationshipStructuredValue([string]$Key){$kind=if($Key -eq 'Friends'){'Friend'}elseif($Key -eq 'Enemies'){'Enemy'}else{'Mentor'};$obj=New-RelationshipEntry $kind;foreach($d in @(Get-RelationshipRepeaterFields $kind)){$obj|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-RelationshipEntryRandomValue ([string]$d.Field) $kind) -Force};return (ConvertTo-Json -InputObject @($obj) -Depth 6 -Compress)}
function Add-RelationshipEntryField($page,[string]$DataKey,[int]$Index,[string]$Kind,$Def,[int]$Y){
    $items=@(Get-RelationshipArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$field=[string]$Def.Field;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(126,[int]($w*0.32));$inputX=$labelW+28;$inputW=[math]::Max(105,$w-$inputX-48)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,36);$page.Controls.Add($lbl)
    $tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Kind=$Kind};$control=$null;$height=42;$value=[string]$obj.$field
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){$control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Text=$value;$control.Add_SelectedIndexChanged({Relationship-EntryChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Relationship-EntryChanged $this})}}
    elseif($type -eq 'MultiChoice'){$control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true;$control.Text=Get-MultiChoiceSummary $value;$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options)){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=($selected -contains [string]$opt);$mi.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$x=$this.Tag;Set-RelationshipEntryMultiChoice ([string]$x.DataKey) ([int]$x.Index) ([string]$x.Field) ([string]$x.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})}
    else{$control=New-Object System.Windows.Forms.TextBox;$control.BorderStyle='FixedSingle';$control.Text=$value;if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=58;$height=70};$control.Add_TextChanged({Relationship-EntryChanged $this})}
    $control.Tag=$tag;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control);[void](Add-FamilySmallDice $page $tag ($w-36) ($Y-3) {Randomize-RelationshipEntryField $this.Tag});return $height
}
function Render-RelationshipEntry($page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){$items=@(Get-RelationshipArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$fk=Get-RelationshipEntryFoldKey $DataKey $Index;if(-not $script:RelationshipEntryFoldState.ContainsKey($fk)){$script:RelationshipEntryFoldState[$fk]=$false};$open=[bool]$script:RelationshipEntryFoldState[$fk];$name=[string]$obj.Name;if([string]::IsNullOrWhiteSpace($name)){$name="$Kind $($Index+1)"};$w=[math]::Max(320,$page.ClientSize.Width-26);$head=New-Object System.Windows.Forms.Button;$head.Text=if($open){'[-]  '+$name}else{'[+]  '+$name};$head.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$head.Location=New-Object System.Drawing.Point(18,$Y);$head.Size=New-Object System.Drawing.Size([math]::Max(150,$w-86),30);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.FlatStyle='Flat';$head.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,112,67);$head.BackColor=[System.Drawing.Color]::FromArgb(240,220,184);$head.ForeColor=$script:Ink;$head.Font=$script:FontSmall;$head.Add_Click({$t=$this.Tag;Toggle-RelationshipEntryFold ([string]$t.DataKey) ([int]$t.Index)});$page.Controls.Add($head);$rm=New-Object System.Windows.Forms.Button;$rm.Text='×';$rm.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$rm.Location=New-Object System.Drawing.Point(($w-48),$Y);$rm.Size=New-Object System.Drawing.Size(30,30);$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.ForeColor=[System.Drawing.Color]::FromArgb(145,58,43);$rm.Add_Click({Remove-RelationshipEntry $this.Tag});$page.Controls.Add($rm);$used=36;if(-not $open){return $used};$yy=$Y+38;foreach($d in @(Get-RelationshipRepeaterFields $Kind)){$dh=Add-RelationshipEntryField $page $DataKey $Index $Kind $d $yy;$yy+=$dh;$used+=$dh};return ($used+8)}
function Add-RelationshipEntryButton($page,[string]$DataKey,[string]$Kind,[int]$Y){$b=New-Object System.Windows.Forms.Button;$b.Text=('+ ADD '+$Kind.ToUpper());$b.Tag=[pscustomobject]@{DataKey=$DataKey;Kind=$Kind};$b.Location=New-Object System.Drawing.Point(18,$Y);$b.Size=New-Object System.Drawing.Size(140,29);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Add-RelationshipEntry $this.Tag});$page.Controls.Add($b);return 36}
function Add-RelationshipEntry($Tag){$items=New-Object System.Collections.Generic.List[object];foreach($x in @(Get-RelationshipArray ([string]$Tag.DataKey))){[void]$items.Add($x)};$obj=New-RelationshipEntry ([string]$Tag.Kind);[void]$items.Add($obj);Set-RelationshipArray ([string]$Tag.DataKey) @($items);$k=Get-RelationshipEntryFoldKey ([string]$Tag.DataKey) ($items.Count-1);$script:RelationshipEntryFoldState[$k]=$true;Render-CurrentCharacter}
function Remove-RelationshipEntry($Tag){$old=@(Get-RelationshipArray ([string]$Tag.DataKey));$new=New-Object System.Collections.Generic.List[object];for($i=0;$i -lt $old.Count;$i++){if($i -ne [int]$Tag.Index){[void]$new.Add($old[$i])}};Set-RelationshipArray ([string]$Tag.DataKey) @($new);Render-CurrentCharacter}
function Add-RelationshipRepeater($page,[string]$DataKey,[string]$Title,[string]$Kind,[int]$Y){$h=Add-RelationshipHeader $page $Title $DataKey $Y;$Y+=$h;if(-not [bool]$script:RelationshipFoldState[$DataKey]){return $h};$add=Add-RelationshipEntryButton $page $DataKey $Kind $Y;$Y+=$add;$used=$h+$add;$items=@(Get-RelationshipArray $DataKey);for($i=0;$i -lt $items.Count;$i++){$dh=Render-RelationshipEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh};return ($used+8)}
function Render-RelationshipsSection($c,$leftHost,$rightHost){
    $defs=@($script:FieldDefs['Relationships']);$top=@('Partner','RelationshipStatus','Sexuality');$y=12
    foreach($key in $top){$d=$defs|Where-Object{$_.Key -eq $key}|Select-Object -First 1;if($null -ne $d){$h=Add-FieldControl $leftHost $d $y;$y+=$h}}
    $rb=New-Object System.Windows.Forms.Button;$rb.Text='🎲  RANDOMIZE RELATIONSHIPS';$rb.Location=New-Object System.Drawing.Point(18,$y);$rb.Size=New-Object System.Drawing.Size([math]::Max(190,$leftHost.ClientSize.Width-40),32);$rb.Anchor='Top,Left,Right';$rb.FlatStyle='Flat';$rb.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$rb.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$rb.ForeColor=$script:Ink;$rb.Font=$script:FontSmall;$rb.Add_Click({Randomize-Section});$leftHost.Controls.Add($rb);$y+=42
    $h=Add-RelationshipRepeater $leftHost 'Friends' 'Friends' 'Friend' $y;$y+=$h
    $y=12;$h=Add-RelationshipRepeater $rightHost 'Enemies' 'Enemies' 'Enemy' $y;$y+=$h;$h=Add-RelationshipRepeater $rightHost 'Mentors' 'Mentors' 'Mentor' $y;$y+=$h
}
# ---------------- END RELATIONSHIPS AUDIT -------------------------------------

function Add-FieldControl([System.Windows.Forms.Panel]$page,$def,[int]$y,[int]$height=48) {
    $key=[string]$def.Key;$type=[string]$def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(138,[int]($w*0.34));$inputX=$labelW+18;$rightPad=76;$inputW=[math]::Max(118,$w-$inputX-$rightPad)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(10,$y);$lbl.Size=New-Object System.Drawing.Size($labelW,38);$lbl.Add_MouseWheel({param($s,$e);Scroll-BookHost $this $e.Delta});$page.Controls.Add($lbl)
    $control=$null;$isMulti=($type -eq 'Multi' -or $type -eq 'Large' -or $type -eq 'LifeEvents')

    if($type -eq 'Choice' -or $type -eq 'EditChoice' -or $type -eq 'Swatch'){
        $control=New-Object System.Windows.Forms.ComboBox
        if($type -eq 'EditChoice'){$control.DropDownStyle='DropDown'}else{$control.DropDownStyle='DropDownList'}
        [void]$control.Items.AddRange([object[]]$def.Options);$control.Location=New-Object System.Drawing.Point($inputX,($y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key
        if($type -eq 'Swatch'){
            $control.DrawMode='OwnerDrawFixed';$control.ItemHeight=24
            $control.Add_DrawItem({
                param($sender,$e)
                try {
                    $e.DrawBackground()
                    if($e.Index -ge 0){
                        $text=[string]$sender.Items[$e.Index];$hex=''
                        try {$map=$script:SwatchColors[[string]$sender.Tag];if($null -ne $map -and $map.ContainsKey($text)){$hex=[string]$map[$text]}} catch {}
                        $swatchColor=if([string]::IsNullOrWhiteSpace($hex)){[System.Drawing.Color]::LightGray}else{Convert-HexToColor $hex}
                        $swatchBrush=New-Object System.Drawing.SolidBrush($swatchColor);try{$e.Graphics.FillRectangle($swatchBrush,$e.Bounds.X+5,$e.Bounds.Y+4,18,16)}finally{$swatchBrush.Dispose()}
                        $e.Graphics.DrawRectangle([System.Drawing.Pens]::DimGray,$e.Bounds.X+5,$e.Bounds.Y+4,18,16)
                        $selected=(($e.State -band [System.Windows.Forms.DrawItemState]::Selected) -ne 0);$textColor=if($selected){[System.Drawing.SystemColors]::HighlightText}else{$script:Ink}
                        $textBrush=New-Object System.Drawing.SolidBrush($textColor);try{$e.Graphics.DrawString($text,$sender.Font,$textBrush,[float]($e.Bounds.X+30),[float]($e.Bounds.Y+4))}finally{$textBrush.Dispose()}
                    }
                    $e.DrawFocusRectangle()
                } catch {}
            })
        }
        $control.Add_SelectedIndexChanged({if($script:Rendering){return};Field-ControlChanged $this})
        if($type -eq 'EditChoice'){$control.Add_TextChanged({if($script:Rendering){return};Field-ControlChanged $this})}
    }
    elseif($type -eq 'MultiChoice'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.Location=New-Object System.Drawing.Point($inputX,($y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key
        $control.FlatStyle='Flat';$control.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true
        $value='';$c=Get-CurrentCharacter;if($null -ne $c){$value=[string]$c.Fields[$key]};$selected=@(Split-MultiChoiceValue $value);$control.Text=Get-MultiChoiceSummary $value
        $menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Font=$script:FontSmall
        $menu.Add_Closing({param($sender,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}})
        $menuOptions=New-Object System.Collections.Generic.List[string]
        foreach($opt in @($def.Options)){if(-not $menuOptions.Contains([string]$opt)){[void]$menuOptions.Add([string]$opt)}}
        foreach($existing in $selected){if(-not $menuOptions.Contains([string]$existing)){[void]$menuOptions.Add([string]$existing)}}
        foreach($opt in $menuOptions){
            $item=New-Object System.Windows.Forms.ToolStripMenuItem;$item.Text=$opt;$item.CheckOnClick=$true;$item.Checked=($selected -contains $opt);$item.Tag=[pscustomobject]@{Key=$key;Option=$opt}
            $item.Add_Click({if($script:Rendering){return};$t=$this.Tag;Set-MultiChoiceSelection ([string]$t.Key) ([string]$t.Option) ([bool]$this.Checked)})
            [void]$menu.Items.Add($item)
        }
        $control.ContextMenuStrip=$menu
        $control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
    }
    elseif($type -eq 'LifeEvents'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.Location=New-Object System.Drawing.Point($inputX,($y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key
        $control.FlatStyle='Flat';$control.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true
        $value='';$c=Get-CurrentCharacter;if($null -ne $c){$value=[string]$c.Fields[$key]};$eventMap=ConvertFrom-LifeEvents $value
        if($eventMap.Count -eq 0){$control.Text='Select life events...  ▼'}elseif($eventMap.Count -eq 1){$control.Text=([string](@($eventMap.Keys)[0])+'  ▼')}else{$control.Text=('{0} selected  ▼' -f $eventMap.Count)}
        $menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Font=$script:FontSmall
        $menuOptions=New-Object System.Collections.Generic.List[string]
        foreach($opt in @($def.Options)){if(-not $menuOptions.Contains([string]$opt)){[void]$menuOptions.Add([string]$opt)}}
        foreach($existing in @($eventMap.Keys)){if(-not $menuOptions.Contains([string]$existing)){[void]$menuOptions.Add([string]$existing)}}
        foreach($opt in $menuOptions){
            $item=New-Object System.Windows.Forms.ToolStripMenuItem;$item.Text=$opt;$item.CheckOnClick=$true;$item.Checked=$eventMap.Contains($opt);$item.Tag=[pscustomobject]@{Key=$key;Category=$opt}
            $item.Add_Click({if($script:Rendering){return};$t=$this.Tag;Set-LifeEventSelection ([string]$t.Key) ([string]$t.Category) ([bool]$this.Checked)})
            [void]$menu.Items.Add($item)
        }
        $control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
        $noteY=$y+36
        foreach($category in @($eventMap.Keys)){
            $noteLabel=New-Object System.Windows.Forms.Label;$noteLabel.Text=([string]$category+' — notes');$noteLabel.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$noteLabel.ForeColor=$script:Muted;$noteLabel.Location=New-Object System.Drawing.Point($inputX,$noteY);$noteLabel.Size=New-Object System.Drawing.Size($inputW,20);$noteLabel.Anchor='Top,Left,Right';$page.Controls.Add($noteLabel)
            $noteBox=New-Object System.Windows.Forms.TextBox;$noteBox.Multiline=$true;$noteBox.ScrollBars='Vertical';$noteBox.BorderStyle='FixedSingle';$noteBox.Font=$script:FontSmall;$noteBox.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$noteBox.ForeColor=$script:Ink;$noteBox.Location=New-Object System.Drawing.Point($inputX,($noteY+20));$noteBox.Size=New-Object System.Drawing.Size($inputW,58);$noteBox.Anchor='Top,Left,Right';$noteBox.Text=[string]$eventMap[$category];$noteBox.Tag=[pscustomobject]@{Key=$key;Category=[string]$category}
            $noteBox.Add_TextChanged({if($script:Rendering){return};$t=$this.Tag;Set-LifeEventNote ([string]$t.Key) ([string]$t.Category) ([string]$this.Text)})
            $page.Controls.Add($noteBox);$noteY+=86
        }
        $height=[math]::Max(48,(42+($eventMap.Count*86)))
    }
    else{
        $control=New-Object System.Windows.Forms.TextBox;$control.Location=New-Object System.Drawing.Point($inputX,($y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.BorderStyle='FixedSingle'
        if($isMulti){$control.Multiline=$true;$control.ScrollBars='Vertical';if($type -eq 'Large'){$control.Height=118}else{$control.Height=62};$height=$control.Height+14}
        $control.Add_TextChanged({if($script:Rendering){return};Field-ControlChanged $this})
    }
    $control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';if(-not $isMulti){$control.Add_MouseWheel({param($s,$e);Scroll-BookHost $this $e.Delta})};$page.Controls.Add($control);$script:FieldControls[$key]=$control
    $dice=New-Object System.Windows.Forms.Button;$dice.Text='🎲';$dice.Tag=$key;$dice.Width=30;$dice.Height=27;$dice.Location=New-Object System.Drawing.Point(($w-68),($y-3));$dice.Anchor='Top,Right';$dice.FlatStyle='Flat';$dice.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$dice.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$dice.ForeColor=$script:Ink;$dice.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$dice.Add_Click({Randomize-OneField ([string]$this.Tag)});$dice.Add_MouseWheel({param($s,$e);Scroll-BookHost $this $e.Delta});$page.Controls.Add($dice);$script:ToolTip.SetToolTip($dice,'Randomize this field')
    $lock=New-Object System.Windows.Forms.Button;$lock.Tag=$key;$lock.Width=30;$lock.Height=27;$lock.Location=New-Object System.Drawing.Point(($w-36),($y-3));$lock.Anchor='Top,Right';$lock.FlatStyle='Flat';$lock.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$lock.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$lock.ForeColor=$script:Ink;$lock.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$lock.Add_Click({Toggle-Lock ([string]$this.Tag)});$lock.Add_MouseWheel({param($s,$e);Scroll-BookHost $this $e.Delta});$page.Controls.Add($lock);$script:ToolTip.SetToolTip($lock,'Lock / unlock this field')
    return $height
}
function Field-ControlChanged($ctrl) {
    $c=Get-CurrentCharacter;if($null -eq $c){return};$key=[string]$ctrl.Tag;$value=[string]$ctrl.Text
    if($ctrl -is [System.Windows.Forms.ComboBox]){$def=Get-FieldDefinition $key;if($null -ne $def -and [string]$def.Type -eq 'EditChoice'){$value=[string]$ctrl.Text}else{$value=[string]$ctrl.SelectedItem}}
    $c.Fields[$key]=$value;$c.Modified=(Get-Date).ToString('o');$moved=$false
    if($c.FileStatus -eq 'Blank' -and -not [string]::IsNullOrWhiteSpace($value)){$c.FileStatus='In Progress';$script:ActiveStatus='In Progress';$moved=$true};Schedule-Save;if($moved -or $key -eq 'FullName' -or $key -eq 'StoryTitle'){Refresh-Navigation -KeepId $c.Id -NoRender};Update-NavLabels
}
function New-LabeledActionButton([string]$text,[int]$x,[int]$y,[int]$width) {
    $b=New-Object System.Windows.Forms.Button
    $b.Text=$text;$b.Width=$width;$b.Height=36;$b.Location=New-Object System.Drawing.Point($x,$y);$b.Anchor='Bottom,Left'
    $b.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$b.FlatStyle='Flat';$b.FlatAppearance.BorderSize=1
    $b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=[System.Drawing.Color]::FromArgb(55,37,24)
    return $b
}
function Add-BookActions([System.Windows.Forms.Panel]$page) {
    $y=[math]::Max(80,$page.ClientSize.Height-55)
    $section=New-LabeledActionButton 'RANDOMIZE SECTION' 16 $y 154;$section.Add_Click({Randomize-Section});$page.Controls.Add($section);$section.BringToFront();$script:ToolTip.SetToolTip($section,'Randomize every unlocked field in the current section')
    $random=New-LabeledActionButton 'RANDOMIZE CHARACTER' 176 $y 174;$random.Add_Click({Randomize-Character});$page.Controls.Add($random);$random.BringToFront();$script:ToolTip.SetToolTip($random,'Randomize every unlocked field in this character')
    $undo=New-LabeledActionButton 'UNDO RANDOMIZE' 356 $y 132;$undo.Add_Click({Undo-Character});$page.Controls.Add($undo);$undo.BringToFront();$script:ToolTip.SetToolTip($undo,'Restore the character to the state before the last randomization')
}
function Add-OverviewExtras($c,[System.Windows.Forms.Panel]$contentHost) {
    $frame=New-Object System.Windows.Forms.Panel;$frame.Location=New-Object System.Drawing.Point(12,8);$frame.Size=New-Object System.Drawing.Size(178,216);$frame.BackColor=[System.Drawing.Color]::FromArgb(137,101,60);$contentHost.Controls.Add($frame)
    $portraitBox=New-Object System.Windows.Forms.PictureBox;$portraitBox.Location=New-Object System.Drawing.Point(5,5);$portraitBox.Size=New-Object System.Drawing.Size(168,206);$portraitBox.SizeMode='Zoom';$portraitBox.BackColor=[System.Drawing.Color]::FromArgb(218,194,151);$frame.Controls.Add($portraitBox)
    if($c.PortraitPath -and (Test-Path -LiteralPath $c.PortraitPath)){try{$img=[System.Drawing.Image]::FromFile($c.PortraitPath);$portraitBox.Image=New-Object System.Drawing.Bitmap($img);$img.Dispose()}catch{}}
    try{$portraitBtn=New-Object OrnateButton}catch{$portraitBtn=New-Object System.Windows.Forms.Button};$portraitBtn.Text='ADD / CHANGE PORTRAIT';$portraitBtn.Width=124;$portraitBtn.Height=29;$portraitBtn.Location=New-Object System.Drawing.Point(12,230);$portraitBtn.Font=$script:FontSmall;$portraitBtn.Add_Click({Choose-Portrait});$contentHost.Controls.Add($portraitBtn)
    try{$portraitRemove=New-Object OrnateButton}catch{$portraitRemove=New-Object System.Windows.Forms.Button};$portraitRemove.Text='REMOVE';$portraitRemove.Width=50;$portraitRemove.Height=29;$portraitRemove.Location=New-Object System.Drawing.Point(140,230);$portraitRemove.Font=New-Object System.Drawing.Font('Georgia',7);$portraitRemove.Add_Click({Remove-Portrait});$contentHost.Controls.Add($portraitRemove)
    $fileNo=New-Object System.Windows.Forms.Label;$fileNo.Text=('FILE {0:0000}' -f [int]$c.FileNumber);$fileNo.Font=$script:FontTab;$fileNo.ForeColor=[System.Drawing.Color]::FromArgb(131,67,45);$fileNo.AutoSize=$true;$fileNo.Location=New-Object System.Drawing.Point(210,12);$contentHost.Controls.Add($fileNo)
    $role=New-Object System.Windows.Forms.Label;$role.Text=([string]$c.Fields.CharacterRole).ToUpper();$role.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$role.ForeColor=[System.Drawing.Color]::FromArgb(131,67,45);$role.AutoSize=$true;$role.Location=New-Object System.Drawing.Point(210,38);$contentHost.Controls.Add($role)
    $completion=Get-Completion $c;$comp=New-Object System.Windows.Forms.Label;$comp.Text="COMPLETION  $completion%";$comp.Font=$script:FontSmall;$comp.ForeColor=$script:Muted;$comp.AutoSize=$true;$comp.Location=New-Object System.Drawing.Point(210,66);$contentHost.Controls.Add($comp)
    $fsLabel=New-Object System.Windows.Forms.Label;$fsLabel.Text='FILE STATUS';$fsLabel.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$fsLabel.ForeColor=$script:Ink;$fsLabel.AutoSize=$true;$fsLabel.Location=New-Object System.Drawing.Point(210,99);$contentHost.Controls.Add($fsLabel)
    $fs=New-Object System.Windows.Forms.ComboBox;$fs.DropDownStyle='DropDownList';[void]$fs.Items.AddRange([object[]]@('Existing','In Progress','Blank'));$fs.Location=New-Object System.Drawing.Point(210,119);$fs.Width=[math]::Max(120,$contentHost.ClientSize.Width-225);$fs.Anchor='Top,Left,Right';$fs.Font=$script:FontSmall;$fs.SelectedItem=$c.FileStatus;$fs.Add_SelectedIndexChanged({if($script:Rendering){return};$cc=Get-CurrentCharacter;if($null -ne $cc){$cc.FileStatus=[string]$this.SelectedItem;$cc.Modified=(Get-Date).ToString('o');Schedule-Save;$script:ActiveStatus=$cc.FileStatus;Refresh-Navigation -KeepId $cc.Id}});$contentHost.Controls.Add($fs)
    $hint=New-Object System.Windows.Forms.Label;$hint.Text='Locked fields survive section and full-character randomization.';$hint.Font=New-Object System.Drawing.Font('Georgia',7,[System.Drawing.FontStyle]::Italic);$hint.ForeColor=$script:Muted;$hint.Location=New-Object System.Drawing.Point(210,158);$hint.Size=New-Object System.Drawing.Size([math]::Max(120,$contentHost.ClientSize.Width-225),54);$hint.Anchor='Top,Left,Right';$contentHost.Controls.Add($hint)
}
function Get-Completion($c) {
    $filled=0; $total=0
    foreach($key in $script:AllFieldKeys){ $total++; if(-not [string]::IsNullOrWhiteSpace([string]$c.Fields[$key])){$filled++} }
    if($total -eq 0){return 0}; return [math]::Round(($filled/$total)*100)
}
function Remove-Portrait {
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $c.PortraitPath='';$c.Modified=(Get-Date).ToString('o');Schedule-Save;Render-CurrentCharacter
}

function Choose-Portrait {
    $c=Get-CurrentCharacter; if($null -eq $c){return}
    $dlg=New-Object System.Windows.Forms.OpenFileDialog; $dlg.Filter='Images|*.png;*.jpg;*.jpeg;*.bmp;*.gif|All files|*.*'
    if($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){
        try { $ext=[System.IO.Path]::GetExtension($dlg.FileName); $dest=Join-Path $script:MediaRoot ($c.Id+$ext); Copy-Item -LiteralPath $dlg.FileName -Destination $dest -Force; $c.PortraitPath=$dest; $c.Modified=(Get-Date).ToString('o'); Schedule-Save; Render-CurrentCharacter } catch { Show-Error $_.Exception.Message }
    }
}

function Render-EmptyState {
    $leftPage.Controls.Clear();$rightPage.Controls.Clear();$script:FieldControls=@{}
    Add-TopBookHeader $leftPage 'NO FILES HERE' $true $script:ActiveStatus
    $contentHost=New-PageContent $leftPage
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text="This section of the book is empty.`r`n`r`nUse + NEW BLANK FILE to start a character.";$lbl.Font=$script:FontHeading;$lbl.ForeColor=$script:Muted;$lbl.Size=New-Object System.Drawing.Size([math]::Max(260,$contentHost.ClientSize.Width-50),150);$lbl.Location=New-Object System.Drawing.Point(28,80);$contentHost.Controls.Add($lbl)
    Add-TopBookHeader $rightPage $script:ActiveStatus.ToUpper() $false 'BOOK DIVIDER'
}
function Render-CurrentCharacter {
    $script:Rendering=$true
    try {
        foreach($nm in $script:SectionButtons.Keys){$btn=$script:SectionButtons[$nm];try{$btn.ActiveTab=($nm -eq $script:CurrentSection);$btn.Invalidate()}catch{if($nm -eq $script:CurrentSection){$btn.FlatAppearance.BorderSize=3}else{$btn.FlatAppearance.BorderSize=1}}}
        foreach($st in $script:StatusButtons.Keys){$btn=$script:StatusButtons[$st];try{$btn.ActiveTab=($st -eq $script:ActiveStatus);$btn.Invalidate()}catch{if($st -eq $script:ActiveStatus){$btn.BackColor=$script:Parchment}else{$btn.BackColor=$script:Parchment2}}}
        $leftPage.Controls.Clear();$rightPage.Controls.Clear();$script:FieldControls=@{}
        $c=Get-CurrentCharacter;if($null -eq $c){Render-EmptyState;Update-NavLabels;return}
        $name='UNTITLED CHARACTER';if(-not [string]::IsNullOrWhiteSpace([string]$c.Fields.FullName)){$name=[string]$c.Fields.FullName}
        Add-TopBookHeader $leftPage $name $true ('FILE {0:0000}' -f [int]$c.FileNumber)
        Add-TopBookHeader $rightPage ($script:CurrentSection.ToUpper()) $false 'CHARACTER DETAILS'
        $leftHost=New-PageContent $leftPage;$rightHost=New-PageContent $rightPage;$script:LeftHost=$leftHost;$script:RightHost=$rightHost;$defs=@($script:FieldDefs[$script:CurrentSection])
        if($script:CurrentSection -eq 'Overview'){
            Add-OverviewExtras $c $leftHost
            $overviewLeftKeys=@('FullName','Nicknames','StoryTitle','Partner','CharacterRole','LifeStatus')
            $leftDefs=@($defs|Where-Object{$overviewLeftKeys -contains $_.Key});$rightDefs=@($defs|Where-Object{$overviewLeftKeys -notcontains $_.Key})
            $y=278;foreach($d in $leftDefs){$h=Add-FieldControl $leftHost $d $y;$y+=$h}
            $y=12;foreach($d in $rightDefs){$h=Add-FieldControl $rightHost $d $y;$y+=$h}
        } elseif($script:CurrentSection -eq 'Family'){
            Render-FamilySection $c $leftHost $rightHost
        } elseif($script:CurrentSection -eq 'Relationships'){
            Render-RelationshipsSection $c $leftHost $rightHost
        } else {
            $split=[math]::Ceiling($defs.Count/2);$leftDefs=@($defs|Select-Object -First $split);$rightDefs=@($defs|Select-Object -Skip $split)
            $y=12;foreach($d in $leftDefs){$h=Add-FieldControl $leftHost $d $y;$y+=$h}
            $y=12;foreach($d in $rightDefs){$h=Add-FieldControl $rightHost $d $y;$y+=$h}
        }
        foreach($key in $script:FieldControls.Keys){
            $ctrl=$script:FieldControls[$key];$value=[string]$c.Fields[$key];$def=Get-FieldDefinition $key;$type=if($null -eq $def){''}else{[string]$def.Type}
            if($type -eq 'MultiChoice'){$ctrl.Text=Get-MultiChoiceSummary $value}
            elseif($type -eq 'LifeEvents'){}
            elseif($ctrl -is [System.Windows.Forms.ComboBox]){
                if($type -eq 'EditChoice'){$ctrl.Text=$value}
                elseif($ctrl.Items.Contains($value)){$ctrl.SelectedItem=$value}
                elseif($ctrl.Items.Count -gt 0){$ctrl.SelectedIndex=0}
            }else{$ctrl.Text=$value}
            foreach($pnl in @($leftHost,$rightHost)){foreach($p in @($pnl.Controls)){if($p -is [System.Windows.Forms.Button] -and [string]$p.Tag -eq $key -and $p.Width -eq 30){if($p.Location.X -gt ($pnl.ClientSize.Width-55)){if(Get-LockState $c $key){$p.Text='🔒'}else{$p.Text='🔓'}}}}}
        }
        Add-BookActions $leftPage;Update-NavLabels
    } finally {$script:Rendering=$false}
}
function Save-BrowseState {
    $c=Get-CurrentCharacter
    if($null -ne $c){$script:Settings.LastCharacterId=[string]$c.Id}
    $script:Settings.LastSection=[string]$script:CurrentSection
    $script:Settings.LastStatus=[string]$script:ActiveStatus
    try{if($null -ne $script:LeftHost){$script:Settings.ScrollLeft=[math]::Abs([int]$script:LeftHost.AutoScrollPosition.Y)}}catch{}
    try{if($null -ne $script:RightHost){$script:Settings.ScrollRight=[math]::Abs([int]$script:RightHost.AutoScrollPosition.Y)}}catch{}
    Schedule-Save
}

function Animate-BookPages([int]$Direction,[int]$Count,[bool]$Whole=$false) {
    if($null -eq $book -or $book.ClientSize.Width -lt 300 -or $book.ClientSize.Height -lt 200){return}
    $count=[math]::Max(1,[math]::Min(6,$Count))
    $center=[int]($book.ClientSize.Width/2);$half=[int](($book.ClientSize.Width-56)/2);$top=22;$height=[math]::Max(120,$book.ClientSize.Height-44)
    $frames=if($Whole){10}else{6};$pause=if($Whole){18}else{10}
    for($n=0;$n -lt $count;$n++){
        $sheet=New-Object System.Windows.Forms.Panel;$sheet.BackColor=if(($n%2)-eq 0){[System.Drawing.Color]::FromArgb(245,225,188)}else{[System.Drawing.Color]::FromArgb(234,210,170)}
        $sheet.Top=$top;$sheet.Height=$height;$sheet.Width=$half;$sheet.Left=if($Direction -ge 0){$center}else{$center-$half}
        $sheet.BorderStyle='FixedSingle';$book.Controls.Add($sheet);$sheet.BringToFront();$book.Refresh()
        # Fold the source page toward the gutter.
        for($f=0;$f -le $frames;$f++){
            $remain=[math]::Max(10,[int]($half*(1-($f/$frames))))
            $sheet.Width=$remain
            if($Direction -ge 0){$sheet.Left=$center}else{$sheet.Left=$center-$remain}
            $sheet.Refresh();$book.Refresh();[System.Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds $pause
        }
        # Open the sheet onto the destination side.
        for($f=1;$f -le $frames;$f++){
            $grow=[math]::Max(10,[int]($half*($f/$frames)));$sheet.Width=$grow
            if($Direction -ge 0){$sheet.Left=$center-$grow}else{$sheet.Left=$center}
            $sheet.Refresh();$book.Refresh();[System.Windows.Forms.Application]::DoEvents();Start-Sleep -Milliseconds $pause
        }
        $book.Controls.Remove($sheet);$sheet.Dispose();$book.Refresh()
    }
}

function Go-ToSection([string]$Target) {
    if([string]::IsNullOrWhiteSpace($Target) -or $Target -eq $script:CurrentSection){return}
    $from=[array]::IndexOf($script:SectionOrder,$script:CurrentSection)
    $to=[array]::IndexOf($script:SectionOrder,$Target)
    if($from -lt 0 -or $to -lt 0){$script:CurrentSection=$Target;Render-CurrentCharacter;return}
    Save-BrowseState
    $direction=if($to -gt $from){1}else{-1}
    $distance=[math]::Abs($to-$from)
    Animate-BookPages $direction $distance $false
    $script:CurrentSection=$Target
    $script:Settings.LastSection=$Target
    Render-CurrentCharacter
    Schedule-Save
}

function Update-NavLabels {
    $c=Get-CurrentCharacter
    if($null -eq $c){ $currentNav.Text='NO CHARACTER'; $prevBtn.Text='‹ PREVIOUS'; $nextBtn.Text='NEXT ›'; return }
    $name='Untitled Character'; if($c.Fields.FullName){$name=[string]$c.Fields.FullName}
    $currentNav.Text="CURRENT`r`n$name"
    if($script:Filtered.Count -gt 1){
        $pi=($script:CurrentIndex-1+$script:Filtered.Count)%$script:Filtered.Count; $ni=($script:CurrentIndex+1)%$script:Filtered.Count
        $pn='Untitled'; if($script:Filtered[$pi].Fields.FullName){$pn=$script:Filtered[$pi].Fields.FullName}
        $nn='Untitled'; if($script:Filtered[$ni].Fields.FullName){$nn=$script:Filtered[$ni].Fields.FullName}
        $prevBtn.Text="‹  PREVIOUS`r`n$pn"; $nextBtn.Text="NEXT  ›`r`n$nn"
    } else { $prevBtn.Text='‹ PREVIOUS'; $nextBtn.Text='NEXT ›' }
}
function Refresh-StoryFilter {
    $wasRendering = $script:Rendering
    $script:Rendering = $true
    try {
        $current=[string]$storyFilter.SelectedItem
        $stories=@($script:Characters | ForEach-Object {[string]$_.Fields.StoryTitle} | Where-Object {$_} | Sort-Object -Unique)
        $storyFilter.Items.Clear(); [void]$storyFilter.Items.Add('All Stories'); foreach($s in $stories){[void]$storyFilter.Items.Add($s)}
        if($current -and $storyFilter.Items.Contains($current)){$storyFilter.SelectedItem=$current}else{$storyFilter.SelectedIndex=0}
    } finally { $script:Rendering = $wasRendering }
}
function Refresh-Navigation {
    param([string]$KeepId='', [switch]$NoRender)
    if(-not $KeepId){ $cur=Get-CurrentCharacter; if($null -ne $cur){$KeepId=[string]$cur.Id} }
    $q=$searchBox.Text.Trim().ToLowerInvariant(); $sf=[string]$storyFilter.SelectedItem
    $list=@($script:Characters | Where-Object {
        $_.FileStatus -eq $script:ActiveStatus -and
        (($sf -eq '' -or $sf -eq 'All Stories') -or ([string]$_.Fields.StoryTitle -eq $sf)) -and
        (($q -eq '') -or ([string]$_.Fields.FullName).ToLowerInvariant().Contains($q) -or ([string]$_.Fields.StoryTitle).ToLowerInvariant().Contains($q) -or ([string]$_.Fields.Partner).ToLowerInvariant().Contains($q))
    } | Sort-Object FileNumber)
    $script:Filtered=$list; $script:CurrentIndex=-1
    for($i=0;$i -lt $list.Count;$i++){if($list[$i].Id -eq $KeepId){$script:CurrentIndex=$i;break}}
    if($script:CurrentIndex -lt 0 -and $list.Count -gt 0){$script:CurrentIndex=0}
    $wasRendering=$script:Rendering;$script:Rendering=$true
    try {
        $jumpCombo.Items.Clear(); foreach($c in $list){$nm='Untitled Character'; if($c.Fields.FullName){$nm=$c.Fields.FullName}; [void]$jumpCombo.Items.Add(('{0:0000} — {1}' -f [int]$c.FileNumber,$nm))}
        if($script:CurrentIndex -ge 0 -and $jumpCombo.Items.Count -gt $script:CurrentIndex){$jumpCombo.SelectedIndex=$script:CurrentIndex}
    } finally {$script:Rendering=$wasRendering}
    Refresh-StoryFilter
    if(-not $NoRender){Render-CurrentCharacter}else{Update-NavLabels}
}

$prevBtn.Add_Click({ if($script:Filtered.Count -gt 0){ Save-BrowseState; Animate-BookPages -1 1 $true; $script:CurrentIndex=($script:CurrentIndex-1+$script:Filtered.Count)%$script:Filtered.Count; $script:Rendering=$true;try{$jumpCombo.SelectedIndex=$script:CurrentIndex}finally{$script:Rendering=$false};Render-CurrentCharacter;Save-BrowseState } })
$nextBtn.Add_Click({ if($script:Filtered.Count -gt 0){ Save-BrowseState; Animate-BookPages 1 1 $true; $script:CurrentIndex=($script:CurrentIndex+1)%$script:Filtered.Count; $script:Rendering=$true;try{$jumpCombo.SelectedIndex=$script:CurrentIndex}finally{$script:Rendering=$false};Render-CurrentCharacter;Save-BrowseState } })
$newBtn.Add_Click({ $c=New-CharacterRecord; $script:Characters+=,$c; $script:ActiveStatus='Blank'; Schedule-Save; Refresh-Navigation -KeepId $c.Id })
$deleteBtn.Add_Click({ $c=Get-CurrentCharacter; if($null -eq $c){return}; $nm='this blank file'; if($c.Fields.FullName){$nm=$c.Fields.FullName}; if((Show-Confirm "Delete $nm?`r`n`r`nThis removes the character record. Portrait files are left in your data folder for safety.") -eq [System.Windows.Forms.DialogResult]::Yes){ $id=$c.Id; $script:Characters=@($script:Characters | Where-Object {$_.Id -ne $id}); Save-AllData; Refresh-Navigation } })
$searchBox.Add_TextChanged({ Refresh-Navigation })
$storyFilter.Add_SelectedIndexChanged({ if(-not $script:Rendering){ Refresh-Navigation } })
$jumpCombo.Add_SelectedIndexChanged({ if(-not $script:Rendering -and $jumpCombo.SelectedIndex -ge 0 -and $jumpCombo.SelectedIndex -lt $script:Filtered.Count){Save-BrowseState;$dir=if($jumpCombo.SelectedIndex -ge $script:CurrentIndex){1}else{-1};Animate-BookPages $dir 1 $true;$script:CurrentIndex=$jumpCombo.SelectedIndex;Render-CurrentCharacter;Save-BrowseState} })
$form.Add_FormClosing({ Save-BrowseState; Save-AllData })

# First-run convenience: start with one genuinely blank page, not a fake example character.
if($script:Characters.Count -eq 0){ $script:Characters += ,(New-CharacterRecord); Save-AllData; $script:ActiveStatus='Blank' }

Refresh-StoryFilter
Refresh-Navigation -KeepId ([string]$script:Settings.LastCharacterId)

# Final layout pass after the real window handle, DPI scale, and Dock layout exist.
# Without this, some Windows setups can retain startup bounds for the right page and
# leave header/navigation controls piled at their default 0,0 positions.
$form.Add_Shown({
    try {
        Layout-Book
        Render-CurrentCharacter
        Layout-Book
    } catch { Write-LayoutError 'shown-pass' $_ }
})

# Delayed automatic update check so startup remains fast.
if(Should-AutoCheck){
    $updateTimer=New-Object System.Windows.Forms.Timer; $updateTimer.Interval=3500
    $updateTimer.Add_Tick({$this.Stop(); Check-ForRemoteUpdate $true})
    $updateTimer.Start()
}

[void]$form.ShowDialog()
