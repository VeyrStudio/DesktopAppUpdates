from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.31'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.30': raise SystemExit(f"Expected 0.2.30 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode()); files={f['path']:f for f in p['files']}
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')

# Master palette: dark leather / aged parchment / antique brass.
palette={
'Paper':(224,199,155),'PaperLight':(239,218,178),'PaperDark':(193,157,105),'Ink':(49,34,24),
'Gold':(184,139,69),'GoldDark':(112,75,38),'Leather':(48,29,20),'Muted':(112,84,58),'SelectedTab':(118,71,40),
'DarkWood':(24,15,11),'PanelDark':(34,22,16)
}
for name,rgb in palette.items():
    pat=rf"\$script:{name}\s*=\s*\[System\.Drawing\.Color\]::FromArgb\([^\r\n]+\)"
    repl=f"$script:{name} = [System.Drawing.Color]::FromArgb({rgb[0]},{rgb[1]},{rgb[2]})"
    core,_n=re.subn(pat,repl,core,count=1)

# Typography closer to the visual master while staying on built-in Windows fonts.
font_repls={
"$script:FontSerif = New-Object System.Drawing.Font('Georgia',10)":"$script:FontSerif = New-Object System.Drawing.Font('Georgia',10.5)",
"$script:FontSmall = New-Object System.Drawing.Font('Georgia',9)":"$script:FontSmall = New-Object System.Drawing.Font('Georgia',9.25)",
"$script:FontHeading = New-Object System.Drawing.Font('Georgia',16,[System.Drawing.FontStyle]::Bold)":"$script:FontHeading = New-Object System.Drawing.Font('Georgia',16,[System.Drawing.FontStyle]::Regular)",
"$script:FontTitle = New-Object System.Drawing.Font('Georgia',26,[System.Drawing.FontStyle]::Bold)":"$script:FontTitle = New-Object System.Drawing.Font('Georgia',27,[System.Drawing.FontStyle]::Regular)",
"$script:FontTab = New-Object System.Drawing.Font('Georgia',10,[System.Drawing.FontStyle]::Bold)":"$script:FontTab = New-Object System.Drawing.Font('Georgia',10,[System.Drawing.FontStyle]::Regular)"
}
for old,new in font_repls.items():
    if old in core: core=core.replace(old,new,1)

# Inject recursive styling immediately before Render-CurrentCharacter so the function exists
# before any page redraw can call it.
marker='function Apply-BookMasterSkin {'
if marker not in core:
    insert=r'''
function Apply-BookMasterSkin {
    $paper=[System.Drawing.Color]::FromArgb(232,207,164)
    $ink=[System.Drawing.Color]::FromArgb(48,32,22)
    $brass=[System.Drawing.Color]::FromArgb(153,108,52)
    function Style-BookControl([System.Windows.Forms.Control]$ctrl){
        if($null -eq $ctrl){return}
        try{
            $tn=$ctrl.GetType().Name
            if($ctrl -is [System.Windows.Forms.TextBox]){
                $ctrl.BackColor=[System.Drawing.Color]::FromArgb(239,220,184);$ctrl.ForeColor=$ink;$ctrl.BorderStyle=[System.Windows.Forms.BorderStyle]::FixedSingle;$ctrl.Font=$script:FontSerif
            } elseif($ctrl -is [System.Windows.Forms.ComboBox]){
                $ctrl.BackColor=[System.Drawing.Color]::FromArgb(239,220,184);$ctrl.ForeColor=$ink;$ctrl.FlatStyle=[System.Windows.Forms.FlatStyle]::Flat;$ctrl.Font=$script:FontSerif
            } elseif($ctrl -is [System.Windows.Forms.NumericUpDown]){
                $ctrl.BackColor=[System.Drawing.Color]::FromArgb(239,220,184);$ctrl.ForeColor=$ink;$ctrl.BorderStyle=[System.Windows.Forms.BorderStyle]::FixedSingle;$ctrl.Font=$script:FontSerif
            } elseif($ctrl -is [System.Windows.Forms.CheckBox] -or $ctrl -is [System.Windows.Forms.RadioButton]){
                $ctrl.ForeColor=$ink;$ctrl.Font=$script:FontSerif
            } elseif($ctrl -is [System.Windows.Forms.Label]){
                if(-not ($ctrl.ForeColor.R -gt 175 -and $ctrl.ForeColor.G -gt 175 -and $ctrl.ForeColor.B -gt 175)){$ctrl.ForeColor=$ink}
                if($ctrl.Font.Size -ge 15){$ctrl.Font=$script:FontHeading}elseif($ctrl.Font.Size -le 9.5){$ctrl.Font=$script:FontSmall}else{$ctrl.Font=$script:FontSerif}
            } elseif($ctrl -is [System.Windows.Forms.GroupBox]){
                $ctrl.ForeColor=$ink;$ctrl.Font=$script:FontSerif
            } elseif($ctrl -is [System.Windows.Forms.Panel] -or $ctrl -is [System.Windows.Forms.FlowLayoutPanel] -or $ctrl -is [System.Windows.Forms.TableLayoutPanel]){
                if($tn -notmatch 'Book|Tab|Frame|Ornate'){
                    $bc=$ctrl.BackColor
                    if($bc.A -eq 0 -or ($bc.R -gt 120 -and $bc.G -gt 100)){$ctrl.BackColor=$paper}
                }
            } elseif($ctrl -is [System.Windows.Forms.Button]){
                if($tn -notmatch 'Book|Ornate'){
                    $ctrl.FlatStyle=[System.Windows.Forms.FlatStyle]::Flat;$ctrl.FlatAppearance.BorderSize=1;$ctrl.FlatAppearance.BorderColor=$brass
                    $ctrl.BackColor=[System.Drawing.Color]::FromArgb(205,170,115);$ctrl.ForeColor=$ink;$ctrl.Font=$script:FontSerif
                }
            }
        }catch{}
        foreach($child in @($ctrl.Controls)){Style-BookControl $child}
    }
    try{Style-BookControl $leftPage;Style-BookControl $rightPage}catch{}
}
'''
    idx=core.find('\nfunction Render-CurrentCharacter {')
    if idx<0: raise SystemExit('Render-CurrentCharacter insertion point not found')
    core=core[:idx]+insert+core[idx:]

# Run the visual skin after every page render so navigation/refresh cannot revert it.
render_anchor='        Add-BookActions $leftPage;Update-NavLabels'
if render_anchor not in core: raise SystemExit('render completion anchor not found')
core=core.replace(render_anchor,render_anchor+';Apply-BookMasterSkin',1)

# Reference image explicitly excludes page-turning: disable the existing animation while preserving navigation.
anim_anchor='function Animate-BookPages([int]$Direction,[int]$Count,[bool]$Whole=$false) {'
if anim_anchor not in core: raise SystemExit('page animation function not found')
core=core.replace(anim_anchor,anim_anchor+'\n    return',1)

# Strengthen existing custom-drawn shell colors without changing geometry.
repls={
'BackColor = Color.FromArgb(62,40,27);':'BackColor = Color.FromArgb(38,23,16);',
'Color.FromArgb(185,184,139,69)':'Color.FromArgb(215,176,126,58)',
'Color.FromArgb(120,236,211,168)':'Color.FromArgb(105,232,204,154)',
'Color.FromArgb(246,226,191)':'Color.FromArgb(248,225,181)',
'Color.FromArgb(236,210,163)':'Color.FromArgb(225,194,143)',
'Color.FromArgb(191,150,94)':'Color.FromArgb(122,74,42)',
'Color.FromArgb(164,108,68,36)':'Color.FromArgb(190,101,62,31)',
'Color.FromArgb(235,211,168)':'Color.FromArgb(226,197,151)',
'Color.FromArgb(203,171,117)':'Color.FromArgb(186,143,88)',
'Color.FromArgb(150,105,70,39)':'Color.FromArgb(185,103,68,32)'
}
for old,new in repls.items(): core=core.replace(old,new)

raw=core.encode('utf-8-sig')
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode()
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'));app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode()).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']);f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION;p['files']=list(files.values());out=json.dumps(p,separators=(',',':')).encode();name='payload-0.2.31-book-master-skin-part-001.txt';(TF/name).write_bytes(out);sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    data=base64.b64decode(f['contentBase64']);assert hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
assert gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))==raw
checks={
'bookMasterSkin':marker in core,'skinAppliedEveryRender':(render_anchor+';Apply-BookMasterSkin') in core,
'pageTurnDisabled':anim_anchor+'\n    return' in core,
'customBookFramePreserved':'class BookFramePanel' in core,'customBookPagePreserved':'class BookPagePanel' in core,'customTabsPreserved':'class BookTabButton' in core,'customStatusTabsPreserved':'class BookStatusTabButton' in core,
'ornateButtonsPreserved':'class OrnateButton' in core,'customNotesPreserved':'function Render-NotesSection' in core,
'timelinePreserved':'function Render-TimelineSection' in core,'storyPreserved':"'Story' = @(" in core,'powersPreserved':'function Render-PowersSection' in core,
'colorPickerPersistencePreserved':'CustomColors' in core,'userDataSeparate':"TheFiles\\Data" in core,
'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True}
if not all(checks.values()): raise SystemExit('validation marker failed: '+str(checks))
val={'version':VERSION,'baseVersion':'0.2.30','payload':name,'payloadSha256':sha,'requirements':checks}
(TF/'book-master-skin-0.2.31-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.book-v0231-validation';vd.mkdir(exist_ok=True);(vd/'TheFilesCore.ps1').write_bytes(raw);(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
print(json.dumps(val,indent=2))
