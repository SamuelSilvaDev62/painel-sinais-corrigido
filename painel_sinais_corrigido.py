
    import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator # Importa o indicador RSI

st.set_page_config(layout="wide")
st.title("Painel de Sinais - Estratégia MACD + EMA + RSI")

# --- Inputs da Sidebar ---
st.sidebar.header("Configurações")
symbol = st.sidebar.text_input("Símbolo (ex: EURUSD=X)", value="EURUSD=X")
interval = st.sidebar.selectbox("Intervalo", ["1m", "5m", "15m", "30m", "1h", "1d"], index=1)
period = st.sidebar.selectbox("Período", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)

# --- Parâmetros dos Indicadores ---
st.sidebar.header("Parâmetros dos Indicadores")
ema_window = st.sidebar.number_input("Janela da EMA", value=9)
macd_fast = st.sidebar.number_input("MACD - Janela Rápida", value=12)
macd_slow = st.sidebar.number_input("MACD - Janela Lenta", value=26)
macd_sign = st.sidebar.number_input("MACD - Janela de Sinal", value=9)
rsi_window = st.sidebar.number_input("RSI - Janela", value=14)
rsi_overbought = st.sidebar.number_input("RSI - Nível de Sobrecompra", value=70)
rsi_oversold = st.sidebar.number_input("RSI - Nível de Sobrevenda", value=30)


if st.sidebar.button("Analisar Ativo"):
    # Baixa os dados do yfinance
    data = yf.download(tickers=symbol, period=period, interval=interval)
    
    if data.empty:
        st.error("Nenhum dado encontrado. Verifique o símbolo e tente novamente.")
    else:
        # Garante que a coluna 'Close' seja do tipo float
        close_prices = data['Close'].astype(float)

        # --- Cálculos dos Indicadores ---
        
        # EMA
        data['EMA'] = EMAIndicator(close=close_prices, window=ema_window).ema_indicator()

        # MACD
        macd_indicator = MACD(close=close_prices, window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_sign)
        data['MACD'] = macd_indicator.macd()
        data['Signal'] = macd_indicator.macd_signal()
        data['MACD_Hist'] = macd_indicator.macd_diff()

        # RSI (NOVO)
        data['RSI'] = RSIIndicator(close=close_prices, window=rsi_window).rsi()

        # Remove linhas com NaN geradas pelos indicadores
        data.dropna(inplace=True)

        # --- Plot dos Gráficos ---
        st.header(f"Análise Técnica de {symbol}")

        # Gráfico de Preço + EMA
        fig_price, ax_price = plt.subplots(figsize=(12, 6))
        ax_price.plot(data.index, data['Close'], label='Preço de Fechamento')
        ax_price.plot(data.index, data['EMA'], label=f'EMA {ema_window}', linestyle='--')
        ax_price.set_title(f'{symbol} - Preço e Média Móvel Exponencial')
        ax_price.legend()
        st.pyplot(fig_price)

        # Gráfico do MACD
        fig_macd, ax_macd = plt.subplots(figsize=(12, 4))
        ax_macd.plot(data.index, data['MACD'], label='Linha MACD')
        ax_macd.plot(data.index, data['Signal'], label='Linha de Sinal', linestyle='--')
        colors = ['g' if val >= 0 else 'r' for val in data['MACD_Hist']]
        ax_macd.bar(data.index, data['MACD_Hist'], label='Histograma', color=colors, width=0.001)
        ax_macd.axhline(0, color='gray', linewidth=1, linestyle='--')
        ax_macd.set_title("Indicador MACD")
        ax_macd.legend()
        st.pyplot(fig_macd)

        # Gráfico do RSI (NOVO)
        st.subheader("Indicador RSI (Índice de Força Relativa)")
        fig_rsi, ax_rsi = plt.subplots(figsize=(12, 4))
        ax_rsi.plot(data.index, data['RSI'], label=f'RSI {rsi_window}')
        ax_rsi.axhline(rsi_overbought, color='red', linestyle='--', label=f'Sobrecompra ({rsi_overbought})')
        ax_rsi.axhline(rsi_oversold, color='green', linestyle='--', label=f'Sobrevenda ({rsi_oversold})')
        ax_rsi.set_title("RSI")
        ax_rsi.legend()
        st.pyplot(fig_rsi)

        # --- Geração e Exibição de Sinais com Confirmação do RSI ---
        st.header("Sinais de Compra/Venda (MACD + Confirmação RSI)")
        
        # Sinal de Compra: Cruzamento do MACD + RSI não sobrecomprado
        data['Sinal_Compra'] = (data['MACD'] > data['Signal']) & \
                               (data['MACD'].shift(1) <= data['Signal'].shift(1)) & \
                               (data['RSI'] < rsi_overbought)
        
        # Sinal de Venda: Cruzamento do MACD + RSI não sobrevendido
        data['Sinal_Venda'] = (data['MACD'] < data['Signal']) & \
                              (data['MACD'].shift(1) >= data['Signal'].shift(1)) & \
                              (data['RSI'] > rsi_oversold)

        # Filtra e exibe os últimos 10 sinais
        sinais = data[(data['Sinal_Compra']) | (data['Sinal_Venda'])].copy()
        if not sinais.empty:
            sinais['Tipo de Sinal'] = sinais.apply(lambda row: 'Compra' if row['Sinal_Compra'] else 'Venda', axis=1)
            st.dataframe(sinais[['Close', 'Tipo de Sinal', 'MACD', 'Signal', 'RSI']].tail(10))
        else:
            st.warning("Nenhum sinal encontrado para os critérios definidos no período selecionado.")
