"""CSV inspection: no fuzzy matches and no writes before explicit selection."""
import csv
import io
import re

TEMPLATE = '종목코드,종목명,구분\n005930,삼성전자,관심\n000660,SK하이닉스,보유\n'

def inspect_csv(raw, catalog, existing):
    if len(raw)>1_000_000: raise ValueError('CSV는 1MB 이하로 올려 주세요.')
    for encoding in ('utf-8-sig','cp949'):
        try:
            text=raw.decode(encoding)
            break
        except UnicodeDecodeError: pass
    else: raise ValueError('UTF-8 또는 CP949 CSV 파일을 사용해 주세요.')
    reader=csv.DictReader(io.StringIO(text),strict=True)
    aliases={'종목코드':'code','code':'code','종목명':'name','name':'name','구분':'kind','kind':'kind'}
    headers=[aliases.get((h or '').strip().lower(),(h or '').strip()) for h in (reader.fieldnames or [])]
    if not ({'code','name'} & set(headers)):
        raise ValueError('첫 행에 종목코드 또는 종목명 열이 필요합니다. 양식을 내려받아 주세요.')
    if len(headers)!=len(set(headers)): raise ValueError('중복된 열 이름이 있습니다.')
    bycode={s['code']:s for s in catalog if s.get('market') in ('KOSPI','KOSDAQ')}
    norm=lambda s: re.sub(r'\s+','',s).casefold()
    byname={}
    for s in bycode.values(): byname.setdefault(norm(s['name']),[]).append(s)
    seen=set(); registered={s['code'] for s in existing}; rows=[]
    try:
        for idx,values in enumerate(reader,2):
            if len(rows)>=500: raise ValueError('한 번에 500행 이하로 확인해 주세요.')
            data=dict(zip(headers,[values.get(h) for h in reader.fieldnames]))
            code=(data.get('code') or '').strip(); name=(data.get('name') or '').strip()
            kind=(data.get('kind') or '관심').strip(); reason=''; stock=None
            if None in values or any(v is None for v in values.values()): reason='열 개수가 맞지 않습니다'
            elif kind not in ('관심','보유'): reason='구분은 관심 또는 보유만 가능합니다'
            elif code:
                if not re.fullmatch(r'\d{1,6}',code): reason='종목코드는 숫자 6자리여야 합니다'
                else:
                    code=code.zfill(6); stock=bycode.get(code)
                    if not stock: reason='KRX 상장 목록에 없음 · 비상장·상장폐지·지원 외 시장 또는 코드 오류 확인'
                    elif name and norm(name)!=norm(stock['name']): reason='종목코드와 종목명이 일치하지 않습니다'
            elif name:
                matches=byname.get(norm(name),[])
                if len(matches)==1: stock=matches[0]; code=stock['code']
                else: reason='정확한 상장 종목명을 찾지 못했습니다 · 종목코드로 확인해 주세요'
            else: reason='종목코드 또는 종목명이 필요합니다'
            if not reason:
                if code in registered: reason='이미 등록된 종목 · 기존 구분 유지'
                elif code in seen: reason='CSV 안의 중복 종목'
                else: seen.add(code)
            rows.append({'row':idx,'code':code,'name':stock['name'] if stock else name,
                         'market':stock['market'] if stock else '', 'kind':kind,
                         'status':reason or '등록 가능','valid':not reason,
                         'as_of':stock.get('as_of','') if stock else ''})
    except csv.Error: raise ValueError('CSV 구문이 잘못되었습니다. 따옴표와 구분자를 확인해 주세요.') from None
    if not rows: raise ValueError('종목 데이터가 없습니다.')
    return rows
