from pathlib import Path
src=Path('tools/the-files-visual-geometry-v0232.py').read_text(encoding='utf-8')
needle="old_notes=\"function Render-NotesSection"
inject=r'''# Robustly mirror the first BookTabButton created inside the right-side loop regardless of whitespace.
_right_start=core.find("foreach($nm in $rightNames){")
if _right_start<0: raise SystemExit('right section loop not found')
_right_end=core.find("foreach($nm in",_right_start+1)
if _right_end<0: _right_end=core.find("$bottom",_right_start)
if _right_end<0: _right_end=min(len(core),_right_start+5000)
_right_block=core[_right_start:_right_end]
if '$b.Mirror=$true' not in _right_block:
    _right_block2,nm=re.subn(r'(New-Object\s+BookTabButton\s*;)',r'\1 $b.Mirror=$true;',_right_block,count=1)
    if nm!=1: raise SystemExit('right BookTabButton creation not found')
    core=core[:_right_start]+_right_block2+core[_right_end:]
'''
if needle not in src: raise SystemExit('builder injection point not found')
src=src.replace(needle,inject+'\n'+needle,1)
exec(compile(src,'the-files-visual-geometry-v0232-final','exec'),globals(),globals())
