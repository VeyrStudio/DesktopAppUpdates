import pathlib
p=pathlib.Path('scripts/build_relationships_0216.py')
src=p.read_text(encoding='utf-8')
a=src.index('# Static PowerShell parse')
b=src.index('# Update packed core')
replacement=r'''# Static PowerShell parse for the newly inserted Relationships module.
(OUT/'RelationshipHelper.ps1').write_text(helper,encoding='utf-8-sig')
if subprocess.run(['bash','-lc','command -v pwsh >/dev/null'],check=False).returncode==0:
    check=subprocess.run(['pwsh','-NoProfile','-Command',"$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('build-out/RelationshipHelper.ps1',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error ('line '+$_.Extent.StartLineNumber+': '+$_.Message)};exit 1}"],text=True,capture_output=True)
    if check.returncode: print(check.stdout,check.stderr); raise SystemExit('Relationships module PowerShell parser failed')
'''
src=src[:a]+replacement+src[b:]
exec(compile(src,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
