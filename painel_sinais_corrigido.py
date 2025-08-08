import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.trend import EMAIndicator, MACD

st.set_page_config(layout="wide")
st.title("Painel de Sinais - Estratégia MACD + EMA")

symbol = st.sidebar.text_input("Símbolo (ex: EURUSD=X)", value="EURUSD=X")
interval = st.sidebar.selectbox("Intervalo", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)
period = st.sidebar.selectbox("Período", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)

if st.sidebar.button("Buscar dados"):
    data = yf.download(symbol, interval=interval, period=period)
    
    if data.empty:
        st.error("Nenhum dado encontrado. Verifique o símbolo e tente novamente.")
    else:
        data.dropna(inplace=True)

        # EMA 9 corretamente como Series
        ema_indicator = EMAIndicator(close=data['Close'].squeeze(), window=9)
        data['EMA9'] = ema_indicator.ema_indicator()

        # MACD corretamente
        macd_indicator = MACD(close=data['Close'])
        data['MACD'] = macd_indicator.macd()
        data['Signal'] = macd_indicator.macd_signal()

        # Plot Preço + EMA
        st.subheader(f"Gráfico de {symbol} com EMA9")
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(data.index, data['Close'], label='Preço')
        ax.plot(data.index, data['EMA9'], label='EMA9', linestyle='--')
        ax.set_title(f'{symbol} - Preço e EMA9')
        ax.legend()
        st.pyplot(fig)

        # Plot MACD
        st.subheader("Indicador MACD")
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(data.index, data['MACD'], label='MACD')
        ax.plot(data.index, data['Signal'], label='Signal', linestyle='--')
        ax.axhline(0, color='gray', linewidth=1, linestyle='--')
        ax.set_title("MACD x Signal")
        ax.legend()
        st.pyplot(fig)

        # Sinais de entrada e saída
        st.subheader("Sinais")
        data['Sinal_Entrada'] = (data['MACD'] > data['Signal']) & (data['MACD'].shift(1) <= data['Signal'].shift(1))
        data['Sinal_Saida'] = (data['MACD'] < data['Signal']) & (data['MACD'].shift(1) >= data['Signal'].shift(1))

        sinais = data[data['Sinal_Entrada'] | data['Sinal_Saida']][['Close', 'MACD', 'Signal', 'Sinal_Entrada', 'Sinal_Saida']]
        st.dataframe(sinais.tail(10))
