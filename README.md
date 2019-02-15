# Crypto-Currency Trading Framework

## How to install


## Package Structure
```txt
.
├── coza
│   ├── api
│   │	├── exchange
│   │	|   ├── base.py
│   │	|   ├── coinone.py
│   │	|   └── exception.py
│   │	├── private
│   │	└── public
│   ├── exchange
│   │	├── base_exchange.py
│   │	└── coinone.py
│   ├── objects
│   │	├── context.py
│   │	├── order.py
│   │	└── result.py
│   ├── ta  # contains several technical analysis functions. 
│   │   ├── momentum.py
│   │   ├── others.py
│   │   ├── strategy.py
│   │   ├── trend.py
│   │   ├── utils.py
│   │   ├── volatility.py
│   │   ├── volume.py
│   │   └── wrapper.py
│   ├── algorithms.py
│   ├── backtest.py
│   ├── bot.py  
│   ├── config.py  
│   ├── errors.py
│   ├── logger.py
│   ├── settings.py
│   ├── utils.py
│   └── various_utils.py
└── setup.py
```

## Support TA
```txt

TA
├── Volume
│	├── Accumulation/Distribution Index (ADI)
│	├── On-Balance Volume (OBV)
│	├── On-Balance Volume mean (OBV mean)
│	├── Chaikin Money Flow (CMF)
│	├── Force Index (FI)
│	├── Ease of Movement (EoM, EMV)
│	├── Volume-price Trend (VPT)
│	└── Negative Volume Index (NVI)
├── Volatility
│	├── Average True Range (ATR)
│	├──	Bollinger Bands (BB)
│	├── Keltner Channel (KC)
│	└── Donchain Channel (DC)
├── Trend
│	├── Moving Average Converence Divergence (MACD)
│	├── Average Directional Movement Index (ADX)
│	├── Vortex Indicator (VI)
│	├── Trix (TRIX)
│	├── Mass Index (MI)
│	├── Commodity Channel Index (CCI)
│	├── Detrended Price Oscillator (DPO)
│	├──	KST Oscillator (KST)
│	└── Ichimoku Kinkō Hyō (Ichimoku)
├── Momentum
│	├── Money Flow Index (MFI)
│	├── Relative Strength Index (RSI)
│	├── True strength index (TSI)
│	├── Ultimate Oscillator (UO)
│	├── Stochastic Oschillator (SR)
│	├── Williams %R (WR)
│	├── Awesome Oscillator (AO)
│	├── Stochastic RSI
│	└──	Stochastic RSI %K %D
├── Strategy
│	├── Golden Cross
│	├── Dead Cross
│	├── Lower than bollinger lower bound rolling
│	└── Upper than bollinger upper bound rolling
└── Others
	├── Daily Return (DR) 
	└── Cumulative Return (CR)

```
