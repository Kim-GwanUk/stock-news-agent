"""Read-only source/access check; never print credentials or authenticated URLs."""
import json, os, sys, io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import config
import httpx
import pandas as pd

def main():
    out={}
    with httpx.Client(timeout=30,trust_env=False,follow_redirects=True) as client:
        stocks=client.get('http://127.0.0.1:8000/stocks').json()
        out['stocks']=stocks
        codes={s['code'] for s in stocks}
        out['as_of']='20261020'
        out['apis']={}
        for path in ['idx/krx_dd_trd','idx/kospi_dd_trd','idx/kosdaq_dd_trd','sto/stk_isu_base_info','sto/ksq_isu_base_info']:
            try:
                r=client.get('https://data-dbg.krx.co.kr/svc/apis/'+path,params={'basDd':'20261020'},headers={'AUTH_KEY':os.environ['KRX_API_KEY']})
                try: data=r.json()
                except ValueError: data={}
                rows=data.get('OutBlock_1',[])
                item={'http_status':r.status_code,'count':len(rows),'fields':list(rows[0]) if rows else [],
                      'message':{k:v for k,v in data.items() if k!='OutBlock_1'}}
                item['rows']=rows if path.startswith('idx/') else [a for a in rows if a.get('ISU_SRT_CD') in codes]
                out['apis'][path]=item
                print(path, r.status_code,len(rows),json.dumps(item['message'],ensure_ascii=False),flush=True)
            except Exception as exc: out['apis'][path]={'error_type':type(exc).__name__}
        try:
            url='https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
            r=client.get(url)
            r.encoding='euc-kr'
            tables=pd.read_html(io.StringIO(r.text))
            table=tables[0]
            table['종목코드']=table['종목코드'].astype(str).str.zfill(6)
            out['kind']={'source':url,'rows':table[table['종목코드'].isin(codes)].fillna('').to_dict('records')}
            print('KIND',json.dumps(out['kind']['rows'],ensure_ascii=False,default=str),flush=True)
        except Exception as exc: out['kind']={'error_type':type(exc).__name__}
    Path('output/sector-source-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
main()
