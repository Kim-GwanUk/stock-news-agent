"""Quiet paper palette with a mountain vignette reserved for the masthead."""
import streamlit as st
import base64
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def mountains():
    return base64.b64encode((Path(__file__).parent/'assets'/'ink-mountains.png').read_bytes()).decode()

def masthead():
    grain='''<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".76" numOctaves="3" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".045"/></feComponentTransfer></filter><rect width="100%" height="100%" filter="url(#grain)" opacity=".65"/></svg>'''
    grain_src=base64.b64encode(grain.encode()).decode()
    markup='''
    <style>
    [data-testid="stApp"]{
      background-color:#fafbfa;
      background-image:url("data:image/svg+xml;base64,GRAIN_DATA");
      background-attachment:fixed;
    }
    [data-testid="stHeader"]{background:transparent}
    [data-testid="stMainBlockContainer"]{position:relative}
    [data-testid="stSidebar"]{
      background-color:#f2f4f2;
      background-image:none;
    }
    [data-testid="stMain"] [data-testid="stMetric"]{background:transparent;border:0;padding:10px 8px}
    [data-testid="stMain"] [class*="st-key-ink_news_"]{
      background:transparent;border:0!important;
      border-radius:0!important;padding:30px 0 36px!important;position:relative;
    }
    [data-testid="stMain"] [class*="st-key-ink_news_"]::before{
      content:none;
    }
    .st-key-ink_price{padding:12px 0 32px}
    [data-testid="stMain"] [class*="st-key-ink_news_"] h3{font-size:1.35rem;line-height:1.55;font-weight:500}
    [data-testid="stMain"] [class*="st-key-ink_news_"] [data-testid="stExpander"],
    .st-key-ink_price [data-testid="stExpander"]{border:0;background:transparent;border-radius:0}
    [data-testid="stMain"] [class*="st-key-ink_news_"] [data-testid="stExpander"] details,
    .st-key-ink_price [data-testid="stExpander"] details{border:0;background:transparent;border-radius:0}
    [data-testid="stMain"] [class*="st-key-ink_news_"] [data-testid="stMarkdownContainer"] p{line-height:1.8}
    [data-testid="stButton"] button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"]{
      background:#252a27;
      color:#fff;border:1px solid #252a27;border-radius:3px;
      box-shadow:none;font-weight:500;
    }
    [data-testid="stSelectbox"] [role="combobox"]{border-radius:3px}
    button:focus-visible,input:focus-visible,[role="combobox"]:focus-visible{outline:2px solid #606d63!important;outline-offset:3px}
    .ink-masthead{position:relative;isolation:isolate;display:flex;align-items:center;min-height:180px;margin:0 0 40px;overflow:hidden}
    .ink-heading{position:relative;z-index:2;width:52%;padding:24px 0}
    .ink-masthead h1{font-family:"Batang","Noto Serif KR",serif!important;font-size:40px!important;font-weight:500!important;letter-spacing:.10em!important;color:#202420;margin:0!important;padding:0!important;line-height:1.5;white-space:nowrap}
    .ink-masthead p{font-size:11px;letter-spacing:.10em;color:#767b76;margin:12px 0 0;white-space:nowrap}
    .ink-mountain{position:absolute;right:0;top:0;width:48%;height:100%;object-fit:cover;object-position:center 18%;opacity:.46;filter:grayscale(1);mix-blend-mode:multiply;mask-image:linear-gradient(to right,transparent 0%,#000 24%,#000 76%,transparent 100%),linear-gradient(to bottom,transparent 0%,#000 28%,#000 65%,transparent 100%);mask-composite:intersect;pointer-events:none;z-index:0}
    [data-testid="stSidebar"]{border-right:1px solid #dcdcd8}
    [data-testid="stSidebar"] h3{font-family:"Batang",serif;letter-spacing:.07em;border:0;padding-bottom:8px}
    [data-testid="stExpander"]{background:rgba(252,253,252,.78);border-color:#d5dad5}
    [data-testid="stButton"] button{transition:background-color .15s,border-color .15s}
    [data-testid="stButton"] button:hover{border-color:#282828}
    [data-testid="stMain"] h2,[data-testid="stMain"] h3{letter-spacing:-.025em}
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]{box-shadow:none}
    @media(max-width:700px){.ink-masthead{min-height:150px;margin-bottom:28px}.ink-masthead h1{font-size:30px!important}.ink-masthead p{font-size:10px;letter-spacing:.04em}.ink-mountain{opacity:.38}
      [data-testid="stMain"] [class*="st-key-ink_news_"]{padding:24px 0 30px!important}
      [data-testid="stApp"]{background-size:180px 180px}
    }
    </style>
    <header class="ink-masthead">
      <div class="ink-heading"><h1>천기누설</h1><p>국내주식 · 뉴스와 기록</p></div>
      <img class="ink-mountain" src="data:image/png;base64,MOUNTAIN_DATA" alt="" aria-hidden="true">
    </header>
    '''
    markup=markup.replace('GRAIN_DATA',grain_src)
    markup=markup.replace('MOUNTAIN_DATA',mountains())
    st.html(markup)
