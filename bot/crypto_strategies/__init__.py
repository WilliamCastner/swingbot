from .rsi_mean_reversion import CryptoRSI
from .breakout_24 import Breakout24
from .bollinger_bands import CryptoBollinger
from .macd_crossover import CryptoMACD
from .ema_crossover import CryptoEMA
from .stochastic import CryptoStochastic
from .williams_r import CryptoWilliamsR
from .atr_keltner import CryptoATR
from .rsi_volume import CryptoRSIVolume
from .momentum_3day import Momentum3Day

ALL_CRYPTO_STRATEGIES = [
    CryptoRSI(),
    Breakout24(),
    CryptoBollinger(),
    CryptoMACD(),
    CryptoEMA(),
    CryptoStochastic(),
    CryptoWilliamsR(),
    CryptoATR(),
    CryptoRSIVolume(),
    Momentum3Day(),
]
