from .rsi_mean_reversion import RSIMeanReversion
from .ma_crossover import MACrossover
from .bollinger_bands import BollingerBands
from .macd_crossover import MACDCrossover
from .breakout import Breakout
from .ema_crossover import EMACrossover
from .rsi_volume import RSIVolume
from .stochastic import Stochastic
from .atr_breakout import ATRBreakout
from .williams_r import WilliamsR

ALL_STRATEGIES = [
    RSIMeanReversion(),
    MACrossover(),
    BollingerBands(),
    MACDCrossover(),
    Breakout(),
    EMACrossover(),
    RSIVolume(),
    Stochastic(),
    ATRBreakout(),
    WilliamsR(),
]
