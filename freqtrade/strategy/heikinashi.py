# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

import talib.abstract as ta
from pandas import DataFrame

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.indicator_helpers import fishers_inverse
from freqtrade.strategy.interface import IStrategy


class Heikinashi(IStrategy):

    # Minimal ROI designed for the strategy
    minimal_roi = {
        #"0": 0.12250667136494789,
        #"23": 0.036994945972001564,
        #"52": 0.015844736888046832,
        #"155": 0
    }

    # Optimal stoploss designed for the strategy
    stoploss = -0.1

    # Optimal ticker interval for the strategy
    ticker_interval = '1h'

    # Optional order type mapping
    order_types = {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False,
        'trailing_stop': False
    }

    # Optional time in force for orders
    order_time_in_force = {
        'buy': 'gtc',
        'sell': 'gtc',
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Raw data from the exchange and parsed by parse_ticker_dataframe()
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """

        # Chart type
        # ------------------------------------
        # Heikinashi stategy
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']


        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (dataframe['ha_close'] < dataframe['ha_open']) #latest HA candle is bearish, HA_Close < HA_Open
                &(abs(dataframe['ha_close']-dataframe['ha_open']) > abs(dataframe['ha_close'].shift(1)-dataframe['ha_open'].shift(1)))#current candle body is longer than previous candle body
                &(dataframe['ha_close'].shift(1) < dataframe['ha_open'].shift(1)) #  previous candle was bearish
                &(dataframe['ha_open'] == dataframe['ha_high'])#latest candle has no upper wick HA_Open == HA_High

            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (dataframe['ha_close'] > dataframe['ha_open']) #latest HA candle is bullish, HA_Close > HA_Open
                &(abs(dataframe['ha_close']-dataframe['ha_open']) > abs(dataframe['ha_close'].shift(1)-dataframe['ha_open'].shift(1)))#current candle body is longer than previous candle body
                &(dataframe['ha_close'].shift(1) > dataframe['ha_open'].shift(1))#  previous candle was bullish
                &(dataframe['ha_open'] == dataframe['ha_low'])#    latest candle has no upper wick HA_Open == HA_Low
            ),
            'sell'] = 1
        return dataframe
