import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("Painel de Sinais com Backtesting da Estratégia")

# --- Inputs da Sidebar ---
st.sidebar.header("Configurações do Ativo")
symbol = st.sidebar.text_input("Símbolo (ex: BTC-USD)", value="BTC-USD")
interval = st.sidebar.selectbox("Intervalo", ["1h", "1d", "1wk"], index=1)
period = st.sidebar.selectbox("Período", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

# --- Parâmetros dos Indicadores ---
st.sidebar.header("Parâmetros dos Indicadores")
ema_window = st.sidebar.number_input("Janela da EMA", value=9)
macd_fast = st.sidebar.number_input("MACD - Janela Rápida", value=12)
macd_slow = st.sidebar.number_input("MACD - Janela Lenta", value=26)
macd_sign = st.sidebar.number_input("MACD - Janela de Sinal", value=9)
rsi_window = st.sidebar.number_input("RSI - Janela", value=14)
rsi_overbought = st.sidebar.number_input("RSI - Nível de Sobrecompra", value=70)
rsi_oversold = st.sidebar.number_input("RSI - Nível de Sobrevenda", value=30)

# --- Parâmetros do Backtesting ---
st.sidebar.header("Parâmetros do Backtesting")
initial_capital = st.sidebar.number_input("Capital Inicial ($)", value=10000.0)

if st.sidebar.button("Executar Análise e Backtesting"):
    # Baixa os dados do yfinance
    data = yf.download(tickers=symbol, period=period, interval=interval)
    
    if data.empty:
        st.error("Nenhum dado encontrado. Verifique o símbolo e o período.")
    else:
        # --- CORREÇÃO DEFINITIVA: Normalizar as colunas do DataFrame ---
        # Remove o MultiIndex de colunas, se houver, e renomeia para o padrão.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1) # Remove o nível do ticker
        
        # Garante que os nomes das colunas estão em maiúsculas (Open, High, Low, Close)
        data.columns = [col.capitalize() for col in data.columns]

        if 'Close' not in data.columns:
            st.error("A coluna 'Close' não foi encontrada após o download. Não é possível continuar.")
            st.stop()
        
        # Agora, 'close_prices' tem a garantia de ser uma Série 1D
        close_prices = data['Close'].dropna()

        if close_prices.empty:
            st.error("Não há dados de preço de fechamento válidos para processar.")
        else:
            # --- 1. Cálculo dos Indicadores ---
            # Envolvemos os cálculos em um bloco try/except para capturar outros erros inesperados
            try:
                data['EMA'] = EMAIndicator(close=close_prices, window=ema_window).ema_indicator()
                macd = MACD(close=close_prices, window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_sign)
                data['MACD'] = macd.macd()
                data['Signal'] = macd.macd_signal()
                data['RSI'] = RSIIndicator(close=close_prices, window=rsi_window).rsi()
                
                data.dropna(inplace=True)
            except Exception as e:
                st.error(f"Ocorreu um erro durante o cálculo dos indicadores: {e}")
                st.stop()

            if data.empty:
                st.warning("Não há dados suficientes para realizar o backtesting após o cálculo dos indicadores.")
                st.stop()

            # --- 2. Geração de Sinais ---
            data['Sinal_Compra'] = (data['MACD'] > data['Signal']) & (data['MACD'].shift(1) <= data['Signal'].shift(1)) & (data['RSI'] < rsi_overbought)
            data['Sinal_Venda'] = (data['MACD'] < data['Signal']) & (data['MACD'].shift(1) >= data['Signal'].shift(1)) & (data['RSI'] > rsi_oversold)

            # --- 3. Execução do Backtesting ---
            # (O restante do código de backtesting e plotagem continua aqui, sem alterações)
            st.header("Resultados do Backtesting")
            
            capital = initial_capital
            position = 0
            trades = []
            
            for i in range(len(data)):
                if data['Sinal_Compra'].iloc[i] and position == 0:
                    buy_price = data['Close'].iloc[i]
                    position = capital / buy_price
                    trades.append({'type': 'buy', 'price': buy_price, 'date': data.index[i], 'capital': capital})
                
                elif data['Sinal_Venda'].iloc[i] and position > 0:
                    sell_price = data['Close'].iloc[i]
                    capital = position * sell_price
                    position = 0
                    trades.append({'type': 'sell', 'price': sell_price, 'date': data.index[i], 'capital': capital})

            if position > 0:
                final_price = data['Close'].iloc[-1]
                capital = position * final_price
                trades.append({'type': 'sell', 'price': final_price, 'date': data.index[-1], 'capital': capital})

            final_capital = capital
            total_return = ((final_capital - initial_capital) / initial_capital) * 100
            buy_and_hold_return = ((data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]) * 100
            
            num_trades = len([t for t in trades if t['type'] == 'buy'])
            win_rate = 0
            winning_trades = 0
            losing_trades = 0
            
            if num_trades > 0:
                buy_trades_capital = [t['capital'] for t in trades if t['type'] == 'buy']
                sell_trades_capital = [t['capital'] for t in trades if t['type'] == 'sell']
                
                for i in range(num_trades):
                    if i < len(sell_trades_capital) and i < len(buy_trades_capital):
                        if sell_trades_capital[i] > buy_trades_capital[i]:
                            winning_trades += 1
                        else:
                            losing_trades += 1
                win_rate = (winning_trades / num_trades) * 100

            col1, col2, col3 = st.columns(3)
            col1.metric("Retorno da Estratégia", f"{total_return:.2f}%")
            col2.metric("Retorno Buy & Hold", f"{buy_and_hold_return:.2f}%")
            col3.metric("Número de Trades", num_trades)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Capital Final", f"${final_capital:,.2f}")
            col2.metric("Taxa de Acerto", f"{win_rate:.2f}%")
            col3.metric("Trades Vencedores/Perdedores", f"{winning_trades}/{losing_trades}")

            st.subheader("Evolução do Capital vs. Buy and Hold")
            if not trades:
                st.warning("Nenhum trade foi executado.")
            else:
                trade_log = pd.DataFrame(trades)
                capital_evolution = pd.concat([
                    pd.DataFrame({'date': [data.index[0]], 'capital': [initial_capital]}),
                    trade_log[trade_log['type'] == 'sell'][['date', 'capital']]
                ]).set_index('date').sort_index()
                
                buy_and_hold_evolution = (data['Close'] / data['Close'].iloc[0]) * initial_capital

                fig, ax = plt.subplots(figsize=(12, 6))
                ax.plot(capital_evolution.index, capital_evolution['capital'], label='Estratégia MACD+RSI', marker='o', linestyle='-')
                ax.plot(buy_and_hold_evolution.index, buy_and_hold_evolution, label='Estratégia Buy & Hold', linestyle='--')
                ax.set_title("Crescimento do Capital")
                ax.legend()
                st.pyplot(fig)
