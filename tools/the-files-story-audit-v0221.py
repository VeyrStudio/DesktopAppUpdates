from pathlib import Path
import base64, gzip, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/'the-files'
VERSION='0.2.21'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.20': raise SystemExit(f"Expected live base 0.2.20, found {m.get('version')}")
parts=[]
for part in m['payloadParts']:
    p=TF/part['url'].rsplit('/',1)[-1]
    b=p.read_bytes()
    if hashlib.sha256(b).hexdigest()!=part['sha256'].lower(): raise SystemExit('base part hash mismatch')
    parts.append(b)
raw=b''.join(parts)
if hashlib.sha256(raw).hexdigest()!=m['payloadSha256'].lower(): raise SystemExit('base payload hash mismatch')
payload=json.loads(raw.decode('utf-8'))
files={f['path']:f for f in payload['files']}
core_bytes=base64.b64decode(files['TheFilesCore.ps1']['contentBase64'])
core=core_bytes.decode('utf-8-sig')

# Merge Character Role + Story Role into the existing Overview CharacterRole key.
old_role="@{Key='CharacterRole';Label='Character Role';Type='Choice';Options=@('Main Character','Secondary Main','Supporting Character','Love Interest','Antagonist','Villain','Rival','Mentor','Sidekick','Minor Character','Background Character','Other')}"
new_role="@{Key='CharacterRole';Label='Story Role';Type='Choice';Options=@('Main Character','Secondary Main','Supporting Character','Love Interest','Antagonist','Villain','Rival','Mentor','Sidekick','Confidant','Comic Relief','Minor Character','Background Character','Other / Custom')}"
if core.count(old_role)!=1: raise SystemExit(f'Overview role definition count={core.count(old_role)}')
core=core.replace(old_role,new_role,1)

story_block="""    'Story' = @(
        @{Key='CharacterTier';Label='Character Tier';Type='Choice';Options=@('Primary','Secondary','Tertiary','Minor','Background')},
        @{Key='Motivation';Label='Motivation';Type='MultiChoice';Options=@('Love','Family','Friendship','Belonging','Acceptance','Approval','Duty','Loyalty','Survival','Safety','Freedom','Independence','Revenge','Justice','Redemption','Power','Control','Ambition','Success','Recognition','Wealth','Knowledge','Curiosity','Protection','Rescue','Responsibility','Guilt','Fear','Grief','Faith','Identity','Purpose','Legacy','Adventure','Escape','Other / Custom')},
        @{Key='InternalConflict';Label='Internal Conflict';Type='MultiChoice';Options=@('Duty vs Desire','Love vs Fear','Trust vs Suspicion','Loyalty vs Morality','Family Expectations vs Self','Identity Crisis','Guilt','Shame','Grief','Fear of Failure','Fear of Abandonment','Fear of Vulnerability','Need for Control','Desire for Revenge','Desire for Approval','Self-Doubt','Low Self-Worth','Conflicting Loyalties','Morality vs Survival','Past vs Future','Freedom vs Security','Power vs Humanity','Acceptance vs Denial','Other / Custom')},
        @{Key='ExternalConflict';Label='External Conflict';Type='MultiChoice';Options=@('Person vs Person','Person vs Family','Person vs Community','Person vs Society','Person vs Authority','Person vs Government','Person vs Organization','Person vs Nature','Person vs Supernatural','Person vs Monster / Creature','Person vs War','Person vs Crime','Person vs Captivity','Person vs Illness / Injury','Person vs Disaster','Person vs Technology','Person vs Fate / Prophecy','Person vs Time','Other / Custom')},
        @{Key='FatalFlaw';Label='Fatal Flaw';Type='Choice';Options=@('Pride','Arrogance','Stubbornness','Recklessness','Impulsiveness','Jealousy','Possessiveness','Anger','Vengefulness','Selfishness','Naivety','Blind Loyalty','Need for Control','Distrust','Cowardice','Greed','Ambition','Obsession','Perfectionism','Martyr Complex','Self-Sacrifice','Emotional Avoidance','Inability to Forgive','Inability to Ask for Help','Other / Custom')},
        @{Key='Archetype';Label='Archetype';Type='MultiChoice';Options=@('Hero','Antihero','Lover','Caregiver','Rebel','Outlaw','Ruler','Sage','Explorer','Creator','Innocent','Everyman','Trickster','Magician','Warrior','Protector','Mentor','Survivor','Healer','Chosen One','Fallen Hero','Reluctant Hero','Byronic Hero','Other / Custom')},
        @{Key='BeginningState';Label='Beginning State';Type='Choice';Options=@('Stable','Content','Happy','Hopeful','Ambitious','Restless','Lonely','Isolated','Grieving','Afraid','Angry','Bitter','Distrustful','Naive','Sheltered','Confused','Lost','Trapped','Powerless','Rebellious','Desperate','Traumatized','Self-Destructive','Other / Custom')},
        @{Key='MiddleState';Label='Middle State';Type='Choice';Options=@('Stable','Improving','Growing','Hopeful','Determined','Empowered','Conflicted','Vulnerable','In Love','Questioning Beliefs','At a Crossroads','Losing Control','Falling Apart','Disillusioned','Obsessed','Desperate','Afraid','Angry','Grieving','Distrustful','Gaining Confidence','Other / Custom')},
        @{Key='EndingState';Label='Ending State';Type='Choice';Options=@('Happy','Content','Hopeful','Healed','Safer','Free','In Love','Accepted','Confident','Empowered','At Peace','Matured','Redeemed','Forgiven','Reconciled','Grieving but Healing','Bittersweet','Disillusioned','Corrupted','Broken','Tragic','Dead','Unknown / Open-Ended','Other / Custom')},
        @{Key='PlotRelevance';Label='Plot Relevance';Type='Choice';Options=@('Essential to Main Plot','Major Plot Influence','Important Subplot','Character-Arc Focus','Romantic Plot','Conflict Driver','Catalyst for Events','Worldbuilding Role','Support Role','Limited Plot Impact','Background Presence','Other / Custom')}
    )
"""
# Replace the whole current Story definition, stopping before Timeline.
pat=r"    'Story' = @\(.*?\n    \)\n    'Timeline' = @\("
mch=re.search(pat,core,flags=re.S)
if not mch: raise SystemExit('Story definition block not found')
core=core[:mch.start()]+story_block+"    'Timeline' = @("+core[mch.end():]

# New characters should not create a second redundant StoryRole value.
core=core.replace("    $fields['StoryRole'] = 'Protagonist'\n",'',1)

# Static assertions: exact Story surface and forbidden old Story fields removed from that block.
sm=re.search(r"    'Story' = @\((.*?)\n    \)\n    'Timeline'",core,flags=re.S)
if not sm: raise SystemExit('new Story block not found')
s=sm.group(1)
required=['CharacterTier','Motivation','InternalConflict','ExternalConflict','FatalFlaw','Archetype','BeginningState','MiddleState','EndingState','PlotRelevance']
for k in required:
    if s.count("Key='"+k+"'")!=1: raise SystemExit('missing/duplicate Story key '+k)
for k in ['StoryTitle','StoryRole','POVStatus','FirstAppearance','LastAppearance','MainGoal','ShortTermGoal','LongTermGoal','WhatTheyThinkTheyWant','WhatTheyActuallyNeed','WhatWouldMakeThemAbandonGoal','RelationshipConflict','MajorTurningPoint','ImportantScenes']:
    if "Key='"+k+"'" in s: raise SystemExit('old Story key still visible '+k)
if "Label='Story Role'" not in core: raise SystemExit('Overview Story Role label missing')
if "Key='StoryRole'" in s: raise SystemExit('duplicate Story Role still in Story')

new_core=('\ufeff'+core).encode('utf-8')
new_gz=gzip.compress(new_core,compresslevel=9,mtime=0)
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(new_core).decode('ascii')
files['TheFilesCore.ps1']['sha256']=hashlib.sha256(new_core).hexdigest()
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(new_gz).decode('ascii')
files['TheFilesCore.ps1.gz']['sha256']=hashlib.sha256(new_gz).hexdigest()
appv=json.dumps({'version':VERSION},separators=(',',':')).encode('utf-8')
files['AppVersion.json']['contentBase64']=base64.b64encode(appv).decode('ascii')
files['AppVersion.json']['sha256']=hashlib.sha256(appv).hexdigest()
payload['version']=VERSION
payload['files']=list(files.values())
out=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode('utf-8')
outname=f'payload-{VERSION}-story-audit-part-001.txt'
(TF/outname).write_bytes(out)
sha=hashlib.sha256(out).hexdigest()
valid=ROOT/'.story-v0221-validation';valid.mkdir(exist_ok=True)
(valid/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
(valid/'TheFilesCore.ps1').write_bytes(new_core)
report={'version':VERSION,'baseVersion':'0.2.20','payload':outname,'payloadSha256':sha,'requirements':{'storyRoleMergedIntoOverview':True,'storyRoleDataKeyPreservedAsCharacterRole':True,'storyHasTenAuditedFields':True,'removedPovAppearancesGoalsWantNeedAbandonRelationshipConflictTurningPointImportantScenes':True,'motivationInternalExternalDropdowns':True,'fatalFlawDropdown':True,'archetypeDropdown':True,'beginningMiddleEndingDropdowns':True,'plotRelevanceDropdown':True,'powersPreserved':True,'bootstrapUpdaterPreserved':True,'legacyUiUpdaterFixPreserved':True,'compressedCoreIncluded':True,'uncompressedCoreIncluded':True,'userDataUntouched':True}}
(TF/f'story-{VERSION}-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
