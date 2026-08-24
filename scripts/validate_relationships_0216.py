# Retrigger after sanitizing smart apostrophes inherited from the Family base.
import json, pathlib, runpy, shutil

root = pathlib.Path('.')
builder = root/'tools/the-files-relationships-build-safe.py'
builder_text = builder.read_text(encoding='utf-8')
builder_text = builder_text.replace("It''s Complicated", "Complicated / Unclear")
needle = "launcher = launcher.replace('v0.2.15', 'v0.2.16')"
insert = "core = core.replace('’', \"''\").replace('‘', \"''\")\n" + needle
if needle not in builder_text:
    raise SystemExit('Could not install smart-apostrophe sanitizer')
builder_text = builder_text.replace(needle, insert, 1)
builder.write_text(builder_text, encoding='utf-8')
runpy.run_path(str(builder), run_name='__main__')
source = root/'the-files/relationships-0.2.16-build-validation.json'
report = json.loads(source.read_text(encoding='utf-8'))
if report.get('version') != '0.2.16' or report.get('baseVersion') != '0.2.15':
    raise SystemExit('Unexpected build/base version')
if report.get('missingRequiredTokens'):
    raise SystemExit('Required relationship/family tokens missing')
if report.get('forbiddenUserDataPaths'):
    raise SystemExit('Forbidden user-data path detected')
if report.get('encodedCommandPresent'):
    raise SystemExit('EncodedCommand handoff detected')
if not report.get('jsonRoundTrip'):
    raise SystemExit('Payload JSON round-trip failed')
core_path = root/'.relationship-safe-validation/TheFilesCore.ps1'
val = root/'.relationship-validation'
shutil.rmtree(val, ignore_errors=True)
val.mkdir()
shutil.copy2(root/'.relationship-safe-validation/TheFiles.ps1', val/'TheFiles.ps1')
shutil.copy2(core_path, val/'TheFilesCore.ps1')
(root/'the-files/relationships-0.2.16-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
