import base64
import hashlib
import httpx
import pandas as pd
import streamlit as st
from app.stock_import import TEMPLATE

def request(base,path,payload):
    try:
        with httpx.Client(timeout=75,trust_env=False) as client:
            response=client.post(base+path,json=payload)
        if response.is_error:
            detail=response.json().get('detail')
            st.error(detail if isinstance(detail,str) else '입력 형식을 확인해 주세요.')
            return None
        return response.json()
    except (httpx.HTTPError,ValueError):
        st.error('서버 연결을 확인하지 못했습니다. 다시 시도해 주세요.')
        return None

@st.dialog('CSV로 종목 등록',width='large')
def show(base):
    st.caption('파일 선택 → 목록 검사 → 선택한 종목 등록')
    st.download_button('CSV 양식 받기',TEMPLATE.encode('utf-8-sig'),'종목_등록_양식.csv','text/csv')
    st.caption('종목코드 또는 정확한 종목명 필수 · 구분: 관심 / 보유(생략 시 관심) · UTF-8 / CP949 · 최대 500행, 1MB')
    uploaded=st.file_uploader('종목 CSV 파일',type=['csv'],key='stock_csv_file')
    if not uploaded: return
    raw=uploaded.getvalue(); digest=hashlib.sha256(raw).hexdigest()
    if st.session_state.get('csv_digest')!=digest:
        st.session_state.pop('csv_preview',None)
        st.session_state['csv_digest']=digest
    if len(raw)>1_000_000:
        st.error('CSV는 1MB 이하로 올려 주세요.')
        return
    if st.button('목록 검사',type='primary'):
        st.session_state.pop('csv_preview',None)
        with st.spinner('KRX 상장 목록과 비교하고 있습니다.'):
            result=request(base,'/stocks/import/preview',{'content':base64.b64encode(raw).decode()})
        if result: st.session_state['csv_preview']=result
    preview=st.session_state.get('csv_preview')
    if not preview: return
    rows=preview['rows']; valid=[r for r in rows if r['valid']]
    st.markdown(f"**등록 가능 {len(valid)}개 · 제외 {len(rows)-len(valid)}개**")
    frame=pd.DataFrame(rows).rename(columns={'row':'CSV 행','code':'종목코드','name':'종목명','market':'시장','kind':'구분','status':'검사 결과','as_of':'상장 목록 기준일'})
    st.dataframe(frame.drop(columns=['valid']),hide_index=True,width='stretch')
    st.caption('KRX 최근 제공 목록 기준입니다. 조회 실패 시 비상장으로 처리하지 않습니다. 미리보기는 30분간 유효합니다.')
    choices={r['row']:r for r in valid}
    picked=st.multiselect('등록할 종목 선택',list(choices),
        default=list(choices),
        format_func=lambda i:f"{choices[i]['name']} · {choices[i]['code']} · {choices[i]['kind']}",
        key='csv_selected_'+preview['token'])
    st.caption(f"선택 {len(picked)}개 · 등록 개수 제한 없음 · 기존 종목은 변경하지 않습니다.")
    if st.button('선택한 종목 등록',type='primary',disabled=not picked):
        with st.spinner('선택한 종목을 등록합니다.'):
            result=request(base,'/stocks/import/commit',{'token':preview['token'],'rows':picked})
        if result is not None:
            st.session_state['csv_done']=f"CSV에서 {len(result['added'])}개 등록했습니다. 이미 등록된 {result['skipped']}개는 건너뛰었습니다."
            st.session_state.pop('csv_preview',None)
            st.rerun()
