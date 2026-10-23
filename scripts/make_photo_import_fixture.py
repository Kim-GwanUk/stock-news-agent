"""A synthetic registration test sheet; not a user's financial account."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',30)
im=Image.new('RGB',(1100,500),'#faf9f6'); draw=ImageDraw.Draw(im)
lines=['종목 등록 테스트용 목록 (가상 입력 포함)','종목명                              종목코드',
       '삼성전자                            005930','현대차                              005380',
       '현대차                              005380','가상비상장기업                      999999',
       '현대차                              005930','삼성전?                             0059??']
for i,line in enumerate(lines): draw.text((30,20+i*57),line,font=font,fill='#292929')
im.save(Path('output/photo-import-fixture.png'))
