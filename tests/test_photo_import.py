import io
import pytest
from PIL import Image
from app.photo_import import PhotoRow,inspect_photo,prepare_image

CAT=[{'code':'005930','name':'삼성전자','market':'KOSPI'},
     {'code':'005380','name':'현대차','market':'KOSPI'}]

def row(name='',code='',clear=True): return PhotoRow(name=name,code=code,clear=clear)

def test_uncertain_mismatch_duplicates_and_unknown():
    rows=inspect_photo([row('삼성전자','005930'),row('현대차','005380'),row('현대차','005380'),
        row('가상비상장기업','999999'),row('현대차','005930'),row('현대차','O05380'),row('현대차','005380',False)],CAT,[CAT[0]])
    assert [r['valid'] for r in rows]==[False,True,False,False,False,False,False]
    assert '이미 등록' in rows[0]['status'] and '중복' in rows[2]['status']
    assert '목록에 없음' in rows[3]['status'] and '일치하지' in rows[4]['status']
    assert '불확실' in rows[5]['status'] and '불확실' in rows[6]['status']
    assert rows[4]['read_name']=='현대차' and rows[4]['name']=='삼성전자'

def test_uncertain_does_not_consume_valid_later_row():
    rows=inspect_photo([row('현대차','005380',False),row('현대차','005380')],CAT,[])
    assert [r['valid'] for r in rows]==[False,True]
    assert inspect_photo([],CAT,[])==[]
    assert not inspect_photo([row('삼성')],CAT,[])[0]['valid']
    assert inspect_photo([row('현대차')],CAT,[])[0]['valid']

@pytest.mark.parametrize('raw',[b'',b'not a picture',b'x'*5_000_001],ids=['empty','invalid','oversized'])
def test_bad_images_rejected(raw):
    with pytest.raises(ValueError): prepare_image(raw)

def test_valid_image_reencoded_without_metadata():
    raw=io.BytesIO(); Image.new('RGB',(50,30),'white').save(raw,format='JPEG')
    clean=prepare_image(raw.getvalue())
    with Image.open(io.BytesIO(clean)) as im:
        assert im.format=='PNG' and im.size==(50,30) and not im.getexif()
