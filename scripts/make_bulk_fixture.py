from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
Path('output/bulk-stocks.csv').write_text('종목코드,구분\n005380,관심\n000270,관심\n035420,관심\n035720,보유\n',encoding='utf-8-sig')
im=Image.new('RGB',(900,330),'#faf9f6'); d=ImageDraw.Draw(im)
f=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',32)
for i,t in enumerate(['사진 등록 검증용 종목 목록','LG화학      051910','삼성SDI     006400','KB금융      105560']): d.text((30,25+65*i),t,font=f,fill='#303030')
im.save('output/bulk-stocks.png')
