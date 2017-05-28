"""
Contains functions to perform technical analysis on pandas OHLCV data frames
"""
import logging
from typing import Union

import pandas as pd

import pytech.utils.pandas_utils as pd_utils
from pytech.utils.decorators import memoize

logger = logging.getLogger(__name__)


@memoize
def sma(df: pd.DataFrame,
        period: int = 50,
        col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Simple moving average

    :param df: The data frame to perform the sma on.
    :param period: The length of the moving average
    :param col: The column in the data frame to use.
    :return: A series with the simple moving average
    """
    sma = df[col].rolling(center=False,
                          window=period,
                          min_periods=period - 1).mean()
    return sma.dropna()


@memoize
def smm(df: pd.DataFrame,
        period: int = 50,
        col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Compute the simple moving median over a given period.

    :param df: The data frame.
    :param period: The number of days to use.
    :param col: The name of the column to use to compute the median.
    :return: Series containing the simple moving median.

    """
    return df[col].rolling(center=False,
                           window=period,
                           min_periods=period - 1).median()


@memoize
def ewma(df: pd.DataFrame, period: int = 50,
         col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Exponential weighted moving average.

    :param df:
    :param period:
    :param col:
    :return:
    """
    return df[col].ewm(ignore_na=False,
                       min_periods=period - 1,
                       span=period).mean()


# noinspection PyTypeChecker,PyUnresolvedReferences
@memoize
def triple_ewma(df: pd.DataFrame, period: int = 50,
                col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Triple Exponential Weighted Moving Average.

    :param df: The data frame to preform the calculation on.
    :param period: The number of periods.
    :param col: The column to perform the calculation on.
    :return:
    """
    ewma_ = ewma(df, period, col)

    triple_ema = 3 * ewma_

    ema_ema_ema = (ewma_.ewm(ignore_na=False, span=period).mean()
                   .ewm(ignore_na=False, span=period).mean())

    series = triple_ema - 3 * (ewma_.ewm(ignore_na=False,
                                         min_periods=period - 1,
                                         span=period).mean()) + ema_ema_ema
    return series.dropna()


@memoize
def triangle_ma(df: pd.DataFrame, period: int = 50,
                col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Triangle Moving Average. The SMA of the SMA.

    :param df: The data frame to preform the calculation on.
    :param period: The number of periods.
    :param col: The column to use to do the calculation.
    :return:
    """
    sma_ = sma(df, period, col)

    return sma_.rolling(center=False, window=period,
                        min_periods=period - 1).mean().dropna()


@memoize
def trix(df: pd.DataFrame, period: int = 50,
         col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Triple Exponential Moving Average Oscillator (trix)

    Calculates the tripe EMA of `n` periods and finds the percent change
    between 1 period of EMA3

    Oscillates around 0. positive numbers indicate a bullish indicator.

    :param df: The data frame to preform the calculation on.
    :param period: The number of periods.
    :param col: The column to use to do the calculation.
    :return:
    """
    emwa_one = ewma(df, period, col)

    emwa_two = emwa_one.ewm(ignore_na=False,
                            min_periods=period - 1,
                            span=period).mean()

    emwa_three = emwa_two.ewm(ignore_na=False,
                              min_periods=period - 1,
                              span=period).mean()

    return emwa_three.pct_change(periods=1).dropna()


@memoize
def efficiency_ratio(df: pd.DataFrame, period: int = 10,
                     col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Kaufman Efficiency Indicator.
    Oscillates between +100 and -100 where positive is bullish.

    :param df: The data frame to preform the calculation on.
    :param period: The number of periods.
    :param col: The column to use to do the calculation.
    :return:
    """
    change = df[col].diff(periods=period).abs()
    vol = df[col].diff().abs().rolling(window=period).sum()
    return pd.Series(change / vol).dropna()


@memoize
def kama(df: pd.DataFrame, period: int = 20,
         col: str = pd_utils.ADJ_CLOSE_COL,
         efficiency_ratio_periods: int = 10,
         ema_fast: int = 2,
         ema_slow: int = 30) -> pd.Series:
    """
    Kaufman's Adaptive Moving Average.

    :param df: The data frame.
    :param period:
    :param col: The column to use.
    :param efficiency_ratio_periods: Number of periods to use for the
        Efficiency Ratio.
    :param ema_fast: Number of periods to use for the fastest EMA constant.
    :param ema_slow: Number of periods to use for the slowest EMA constant.
    :return:
    """
    er = efficiency_ratio(df, efficiency_ratio_periods, col)
    fast_alpha = 2 / (ema_fast + 1)
    slow_alpha = 2 / (ema_slow + 1)

    # smoothing constant
    sc = pd.Series((er * (fast_alpha - slow_alpha) + slow_alpha) ** 2)
    sma_ = sma(df, period, col)

    kama_ = []

    for smooth, ma, price in zip(iter(sc.items()),
                                 iter(sma_.shift(-1).items()),
                                 iter(df[col].items())):
        try:
            kama_.append(kama_[-1] + smooth[1] * (price[1] - kama_[-1]))
        except IndexError:
            if pd.notnull(ma[1]):
                kama_.append(ma[1] + smooth[1] * (price[1] - ma[1]))
            else:
                kama_.append(None)

    return pd.Series(kama_, index=sma_.index, name='KAMA')


@memoize
def zero_lag_ema(df: pd.DataFrame, period: int = 30,
                 col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Zero Lag Exponential Moving Average.

    :param df: The data frame.
    :param period: Number of periods.
    :param col: The column to use.
    :return:
    """
    lag = (period - 1) / 2
    return pd.Series(df[col] + (df[col].diff(lag)),
                     name='Zero Lag EMA').dropna()


def wma(df: pd.DataFrame, period: int = 30,
        col: str = pd_utils.ADJ_CLOSE_COL):
    """
    Weighted Moving Average.

    :param df:
    :param period:
    :param col:
    :return:
    """
    wma_ = []

    for chunk in _chunks(df, period, col):
        try:
            wma_.append(_chunked_wma(chunk, period))
        except AttributeError:
            wma_.append(None)

    wma_ = wma_.reverse()
    return wma_


def _chunks(df: Union[pd.DataFrame, pd.Series],
            period: int,
            col: str = pd_utils.ADJ_CLOSE_COL):
    """
    Create `n` chunks based on the number of periods.

    :param df:
    :param period:
    :param col:
    :return:
    """
    try:
        df_rev = df[col].iloc[::-1]
    except KeyError:
        df_rev = df.iloc[::-1]

    for i in enumerate(df_rev):
        chunk = df_rev.iloc[i[0]:i[0] + period]
        if len(chunk) != period:
            yield None
        else:
            yield chunk


def _chunked_wma(chunk, period) -> float:
    denominator = (period * (period + 1)) / 2

    ma = []

    for price, i in zip(chunk.iloc[::-1].tolist(),
                        list(range(period + 1))[1:]):
        ma.append(price * (i / denominator))

    return sum(ma)


def true_range(df: pd.DataFrame, period: int = 14):
    """
    Finds the true range a asset is trading within.
    Most recent period's high - most recent periods low.
    Absolute value of the most recent period's high minus the previous close.
    Absolute value of the most recent period's low minus the previous close.

    :param df:
    :param period:
    :return:
    """
    high_low = pd.Series(df[pd_utils.HIGH_COL].tail(period)
                         - df[pd_utils.LOW_COL].tail(period),
                         name='high_low')

    high_close = pd.Series(df[pd_utils.HIGH_COL].tail(period)
                           - (df[pd_utils.CLOSE_COL].shift(-1)
                              .abs().tail(period)),
                           name='high_prev_close')

    low_close = pd.Series(df[pd_utils.CLOSE_COL].shift(-1).tail(period)
                          - df[pd_utils.LOW_COL].abs().tail(period),
                          name='prev_close_low')

    true_range = pd.concat([high_low, high_close, low_close], axis=1)
    true_range_list = []

    for row in true_range.itertuples():
        # TODO: fix this so it doesn't throw an exception for weekends
        try:
            true_range_list.append(max(row.high_low,
                                       row.high_prev_close,
                                       row.prev_close_low))
        except TypeError:
            continue

    return pd.Series(true_range_list, name='Average True Range')


def avg_true_range(df: pd.DataFrame, period=14):
    """
    Moving average of an asset's true range.

    :param df: The data frame with the OHLCV data.
    :param period:
    :return:
    """
    tr = true_range(df, period * 2)
    return pd.Series(tr.rolling(center=False,
                                window=period,
                                min_periods=period - 1).mean()).tail(period)


def smoothed_ma(df: pd.DataFrame,
                period: int = 30,
                col: str = pd_utils.ADJ_CLOSE_COL) -> pd.Series:
    """
    Moving average where equal weights are given to historic
    and current prices
    :param df:
    :param period:
    :param col:
    :return:
    """
    return df[col].ewm(alpha=1 / period).mean()


def rsi(df: pd.DataFrame, period: int = 14, col: str = pd_utils.ADJ_CLOSE_COL):
    """
    Relative strength indicator.

    RSI oscillates between 0 and 100 and traditionally
    +70 is considered overbought and under 30 is oversold.

    :param df:
    :param period:
    :param col:
    :return:
    """
    rsi_series = pd.DataFrame()
    gain = [0]
    loss = [0]

    for row, shifted_row in zip(iter(df[col].items()),
                                iter(df[col].shift(-1).items())):
        if row[1] - shifted_row[1] > 0:
            gain.append(row[1] - shifted_row[1])
            loss.append(0)
        elif row[1] - shifted_row[1] < 0:
            gain.append(0)
            loss.append(abs(row[1] - shifted_row[1]))
        elif row[1] - shifted_row[1] == 0:
            gain.append(0)
            loss.append(0)

    rsi_series['gain'] = gain
    rsi_series['loss'] = loss

    avg_gain = rsi_series['gain'].rolling(window=period).mean()
    avg_loss = rsi_series['loss'].rolling(window=period).mean()
    relative_strength = avg_gain / avg_loss
    return pd.Series(100 - (100 / (1 + relative_strength)), name='RSI')


def macd_signal(df: pd.DataFrame, period_fast: int = 12, period_slow: int = 26,
                signal: int = 9, col: str = pd_utils.ADJ_CLOSE_COL):
    """
    When the MACD falls below the signal line this is a bearish signal,
    and vice versa.
    When security price diverges from MACD it signals the end of a trend.
    If MACD rises dramatically quickly, the shorter moving averages pulls
    away from the slow moving average, it is a signal that the security is
    overbought and should come back to normal levels soon.

    As with any signals this can be misleading and should be combined with
    something to avoid being faked out.

    NOTE: be careful changing the default periods,
    the method wont break but this is the 'traditional' way of doing this.

    :param df:
    :param period_fast: Traditionally 12.
    :param period_slow: Traditionally 26.
    :param signal: Traditionally 9.
    :param col: The name of the column.
    :return:
    """
    ema_fast = pd.Series(df[col].ewm(ignore_na=False,
                                     min_periods=period_fast - 1,
                                     span=period_fast).mean())

    ema_slow = pd.Series(df[col].ewm(ignore_na=False,
                                     min_periods=period_slow - 1,
                                     span=period_slow).mean())

    macd_series = pd.Series(ema_fast - ema_slow)

    macd_signal_series = pd.Series(macd_series.ewm(ignore_na=False,
                                                   span=signal).mean())

    return pd.concat([macd_signal_series, macd_series], axis=1)


def dmi(df: pd.DataFrame, period: int = 14):
    """
    DMI also known as Average Directional Movement Index (ADX)

    This is a lagging indicator that only indicates a trend's strength rather
    than trend direction so it is best coupled with another movement indicator
    to determine the strength of a trend.

    A strategy created by Alexander Elder states a buy signal is triggered
    when the DMI peaks and starts to decline, when the positive dmi is above
    the negative dmi.
    A sell signal is triggered when dmi stops falling and goes flat.

    :param df:
    :param period:
    :return:
    """
    temp_df = pd.DataFrame()
    temp_df['up_move'] = df[pd_utils.HIGH_COL].diff()
    temp_df['down_move'] = df[pd_utils.LOW_COL].diff()

    positive_dm = []
    negative_dm = []

    for row in temp_df.itertuples():
        if row.up_move > row.down_move and row.up_move > 0:
            positive_dm.append(row.up_move)
        else:
            positive_dm.append(0)
        if row.down_move > row.up_move and row.down_move > 0:
            negative_dm.append(row.down_move)
        else:
            negative_dm.append(0)

    temp_df['positive_dm'] = positive_dm
    temp_df['negative_dm'] = negative_dm

    atr = avg_true_range(df, period=period * 6)

    dir_plus = pd.Series(
            100 * (temp_df['positive_dm'] / atr).ewm(span=period,
                                                     min_periods=period - 1).mean())

    dir_minus = pd.Series(
            100 * (temp_df['negative_dm'] / atr).ewm(span=period,
                                                     min_periods=period - 1).mean())
    return pd.concat([dir_plus, dir_minus])


def bollinger_bands(df: pd.DataFrame,
                    period: int = 30,
                    col: str = pd_utils.ADJ_CLOSE_COL):
    """
    TODO.
    :param df:
    :param period:
    :param col:
    :return:
    """
    std_dev = df[col].std()
    middle_band = sma(df, period=period, col=col)
    upper_bband = pd.Series(middle_band + (2 * std_dev),
                            name='upper_bband')
    lower_bband = pd.Series(middle_band - (2 * std_dev),
                            name='lower_bband')

    percent_b = (df[col] - lower_bband) / (upper_bband - lower_bband)

    b_bandwidth = pd.Series((upper_bband - lower_bband) / middle_band)

    return pd.concat([upper_bband, middle_band, lower_bband, b_bandwidth,
                      percent_b], axis=1)