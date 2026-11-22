from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'three'))
import blocks
blocks.SIZE=(464,726)
for step in range(9):
 for mouth in ('closed','A','O','E','F','blink'):
  a=step/8
  im=blocks.draw(3,'closed' if mouth=='blink' else mouth,-.45,1 if mouth=='blink' else 0,.16+a*.19,0,0,0,-.32,a)
  # Stable canvas and ground anchor for the complete pose sequence.
  im.crop((19,0,445,690)).save(f'source/three-{step}-{mouth}.webp',lossless=True)
im=Image.open('source/three-5-closed.webp'); im.thumbnail((180,180)); icon=Image.new('RGBA',(200,200));icon.alpha_composite(im,((200-im.width)//2,10));icon.save('icons/three.png')
base=ImageOps.fit(Image.open('sets/park.png').convert('RGB'),(1536,864)).convert('RGBA')
d=ImageDraw.Draw(base); font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',38)
d.line([(0,34),(375,73),(768,90),(1161,73),(1536,34)],fill='#684736',width=5)
for i in range(19):
 x=25+i*81;y=int(36+52*(1-((x-768)/768)**2))
 d.polygon([(x,y),(x+44,y+2),(x+21,y+48)],fill=['#e78b60','#f2c356','#619b8b','#ce7584'][i%4])
# A painted theatre platform under the cast.
d.polygon([(0,684),(1536,684),(1536,864),(0,864)],fill='#c0986b')
for i in range(18):
 x=i*120-210;d.line((x+60,684,x,864),fill='#ac8156',width=2)
d.line((0,684,1536,684),fill='#f3d992',width=6)
d.rounded_rectangle((26,100,320,180),radius=17,fill='#215650',outline='#f3d99f',width=4)
d.text((172,140),'ZOO SHOW',font=font,anchor='mm',fill='#fff0c9')
base.save('sets/zoo.png')
