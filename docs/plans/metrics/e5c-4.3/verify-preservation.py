from pathlib import Path
import hashlib,json,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[4]
BASE='0609db55cdbc830db661ad99b9b643781eff0ba5'
out=Path(__file__).parent/'evidence'
canvas=Image.new('RGB',(1440,220),'#211f1d');draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
draw.text((20,16),'E5c-4.3 | Prova de identidade: mesmos componentes, sem comparação de métricas',font=font,fill='#f2f4f6')
for i,team in enumerate(['BAL','DAL','NE']):
 im=Image.open(out/f'theme-{team}.png');im.thumbnail((452,125));canvas.paste(im,(20+i*472,65));draw.text((20+i*472,178),team,font=font,fill='#f2f4f6')
canvas.save(out/'themes-side-by-side.png')
paths=['web-ui/local-editorial/broadcast/BroadcastReading.tsx','web-ui/local-editorial/broadcast/broadcast.css','web-ui/local-editorial/broadcast/themes.ts','web-ui/local-editorial/broadcast/fonts.css','web-ui/local-editorial/broadcast/type-proof.html','web-ui/local-editorial/observations/format.ts','web-ui/local-editorial/observations/model.ts','web-ui/local-editorial/observations/client.ts','web-ui/build/observations.ts','web-ui/build/local-editorial.ts']
preserved={}
for p in paths:
 before=subprocess.check_output(['git','show',f'{BASE}:{p}'],cwd=ROOT);after=(ROOT/p).read_bytes();assert before==after,p;preserved[p]=hashlib.sha256(after).hexdigest()
protected=['contracts','etl-pipeline','core-api','supabase','web-ui/public','docs/static-snapshot-contract.md']
for p in protected:assert not subprocess.check_output(['git','diff',BASE,'--',p],cwd=ROOT),p
refs=Path('/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/visual-broadcast/2026-10-20')
refpaths=[refs/'DESIGN.md',refs/'refinement-4.3/HANDOFF.md',refs/'refinement-4.3/references.json',*sorted((refs/'refinement-4.3/references').glob('*.png'))]
reference_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in refpaths}
font_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'web-ui/local-editorial/broadcast/assets').glob('*.woff2')}
def lum(h):
 vals=[int(h[i:i+2],16)/255 for i in (1,3,5)];vals=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in vals];return sum(a*b for a,b in zip(vals,[.2126,.7152,.0722]))
pairs={'ink/paper':('#18232B','#D6DCE1'),'muted/paper':('#46525C','#D6DCE1'),'muted/limits':('#46525C','#C9D1D7'),'controls':('#46525C','#E9EDF0'),'BAL/name':('#F2F4F6','#241773'),'DAL/name':('#002244','#B6BFC7'),'NE/name':('#F2F4F6','#002244'),'context':('#F2F4F6','#38434B')}
contrast={k:round((max(lum(a),lum(b))+.05)/(min(lum(a),lum(b))+.05),2) for k,(a,b) in pairs.items()};assert all(v>=4.5 for v in contrast.values())
(out/'preservation.json').write_text(json.dumps({'base':BASE,'previousAndAcceptedFiles':preserved,'protectedTreesUnchanged':protected,'referenceInputs':reference_hashes,'fontFiles':font_hashes,'textContrast':contrast},indent=2))
print(json.dumps(contrast,indent=2))
