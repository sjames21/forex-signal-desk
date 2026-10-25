import os
import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title='FX Signal Desk', page_icon='📈', layout='wide')
st.markdown('''<style>.block-container{padding-top:1.2rem;max-width:1000px}div[data-testid="stMetric"]{background:#15203312;border:1px solid #8883;border-radius:12px;padding:12px}</style>''',unsafe_allow_html=True)
st.title('📈 FX Signal Desk')
st.caption('Mobile forex scanner • Closed-candle signals • Manual refresh')
PAIRS=['EUR/USD','GBP/USD','USD/JPY','USD/CAD','AUD/USD','NZD/USD','USD/CHF','EUR/JPY','GBP/JPY']
try: secret=st.secrets.get('TWELVE_DATA_API_KEY','')
except Exception: secret=''
key=secret or os.environ.get('TWELVE_DATA_API_KEY','')
if not key:
    key=st.text_input('Twelve Data API key (kept in this browser session)',type='password')
if not key:
    st.info('Add TWELVE_DATA_API_KEY to Streamlit Cloud secrets, or enter your key above to begin.')
    st.stop()
with st.expander('⚙️ Scanner settings',expanded=True):
    pairs=st.multiselect('Pairs',PAIRS,default=PAIRS[:4])
    tf=st.selectbox('Chart interval',['5min','15min','30min','1h','4h'],index=1)
    atr_mult=st.slider('Stop distance (ATR)',1.0,3.0,1.5,0.25)
    st.caption('Free tier: 8 credits/min and 800/day. Start with 4 pairs. The scan uses 1 request per pair.')

@st.cache_data(ttl=60,show_spinner=False)
def fetch(pair,interval,api_key):
    response=requests.get('https://api.twelvedata.com/time_series',params={'symbol':pair,'interval':interval,'outputsize':250,'apikey':api_key,'timezone':'UTC'},timeout=20)
    response.raise_for_status()
    data=response.json()
    if not isinstance(data,dict) or 'values' not in data:
        raise ValueError(data.get('message','No candles returned') if isinstance(data,dict) else 'Invalid response')
    df=pd.DataFrame(data['values'])
    if len(df)<210: raise ValueError('Insufficient history for EMA200')
    for col in ('open','high','low','close'): df[col]=pd.to_numeric(df[col],errors='coerce')
    df['datetime']=pd.to_datetime(df['datetime'],utc=True)
    return df.sort_values('datetime').dropna().reset_index(drop=True)

def analyze(pair,df,interval,multiple):
    # Drop the newest candle: API may return a still-forming candle.
    df=df.iloc[:-1].copy()
    c=df.close
    e50=c.ewm(span=50,adjust=False).mean()
    e200=c.ewm(span=200,adjust=False).mean()
    delta=c.diff()
    up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rsi=100-100/(1+up/down.replace(0,float('nan')))
    prev=c.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-prev).abs(),(df.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    price=float(c.iloc[-1]); a=float(atr.iloc[-1]); rv=float(rsi.iloc[-1]); digits=3 if 'JPY' in pair else 5
    buy=price>e50.iloc[-1]>e200.iloc[-1] and 50<rv<70 and price>c.iloc[-2]
    sell=price<e50.iloc[-1]<e200.iloc[-1] and 30<rv<50 and price<c.iloc[-2]
    side='BUY' if buy else 'SELL' if sell else 'WAIT'
    sl=price-multiple*a if buy else price+multiple*a if sell else None
    tp=price+2*multiple*a if buy else price-2*multiple*a if sell else None
    return {'Pair':pair,'Signal':side,'Close':round(price,digits),'RSI':round(rv,1),'EMA50':round(float(e50.iloc[-1]),digits),'EMA200':round(float(e200.iloc[-1]),digits),'Stop':round(sl,digits) if sl is not None else '—','Target (2R)':round(tp,digits) if tp is not None else '—','Last closed candle (UTC)':df.datetime.iloc[-1].strftime('%Y-%m-%d %H:%M')}

if st.button('🔄 Scan market',type='primary',use_container_width=True):
    if not pairs: st.warning('Select at least one pair.')
    else:
        rows=[]; errors=[]
        with st.spinner('Fetching candles and calculating signals...'):
            for pair in pairs:
                try:
                    rows.append(analyze(pair,fetch(pair,tf,key),tf,atr_mult))
                except Exception as exc: errors.append(f'{pair}: {exc}')
                time.sleep(0.2)
        st.session_state['rows']=rows
        st.session_state['errors']=errors
        st.session_state['scanned_at']=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M:%S UTC')
if 'rows' in st.session_state:
    rows=st.session_state['rows']
    st.caption('Last scan: '+st.session_state['scanned_at'])
    a,b,c=st.columns(3)
    a.metric('BUY',sum(r['Signal']=='BUY' for r in rows))
    b.metric('SELL',sum(r['Signal']=='SELL' for r in rows))
    c.metric('WAIT',sum(r['Signal']=='WAIT' for r in rows))
    for r in rows:
        with st.container(border=True):
            st.subheader(f"{r['Pair']} — {r['Signal']}")
            x,y,z=st.columns(3)
            x.metric('Close',r['Close']); y.metric('RSI',r['RSI']); z.metric('Target',r['Target (2R)'])
            st.caption(f"Stop: {r['Stop']} · EMA50: {r['EMA50']} · EMA200: {r['EMA200']} · Candle: {r['Last closed candle (UTC)']}")
    st.download_button('Download scan CSV',pd.DataFrame(rows).to_csv(index=False).encode(),'forex_signals.csv','text/csv',use_container_width=True)
    for err in st.session_state['errors']: st.warning(err)
st.divider()
st.caption('Educational signals only. Entry reference is the last completed candle close, not an executable quote. Spread, slippage, news and market hours are not modeled. Signals can fail; test on demo before trading. No trades are placed and no push notifications are sent.')
