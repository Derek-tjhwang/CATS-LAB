# Crypto-Currency Trading Framework

## Package Structure
```txt
.
├── coza
│   ├── bot.py  # contains a bot context class.
│   ├── config.py  
│   ├── errors.py
│   ├── history.py
│   ├── logger.py
│   ├── ta  # contains several technical analysis functions. 
│   │   ├── momentum.py
│   │   ├── others.py
│   │   ├── strategy.py
│   │   ├── trend.py
│   │   ├── utils.py
│   │   ├── volatility.py
│   │   ├── volume.py
│   │   └── wrapper.py
│   ├── trade.py  # contains the main loop statement for trading.
│   ├── backtest.py
│   ├── utils.py
│   └── various_utils.py
├── docs
├── scripts
│   ├── backtest_entrypoint.py
│   └── trader_entrypoint.py
├── Exmples
│	├── Simple_Examples
│	└── Combination_Examples
├── setup.py
├── source_it_to_set_private.sh
├── tool_build_doc.sh  # build a sphinx document html.
└── tool_make_sdist.sh  # make a python package distribution.
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

Example directory contains some trading strategies. 

