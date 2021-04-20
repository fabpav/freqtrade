# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

import talib.abstract as ta
from pandas import DataFrame
from typing import Dict, Any, Callable, List
from functools import reduce

from skopt.space import Categorical, Dimension, Integer, Real

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.optimize.hyperopt_interface import IHyperOpt

class_name = 'DefaultHyperOpts'


class SMAOPT(IHyperOpt):
    """
    Default hyperopt provided by freqtrade bot.
    You can override it with your own hyperopt
    """

    @staticmethod
    def populate_indicators(dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['sell-rsi'] = ta.RSI(dataframe)

        # SMA - Simple Moving Average
        dataframe['sma5'] = ta.SMA(dataframe, timeperiod=5)
        dataframe['sma14'] = ta.SMA(dataframe, timeperiod=14)
        dataframe['sma20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma200'] = ta.SMA(dataframe, timeperiod=200)

        # Chart type
        # ------------------------------------
        # Heikinashi stategy
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']


        #dataframe['sar'] = ta.SAR(dataframe)
        return dataframe

    @staticmethod
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy parameters to be used by hyperopt
        """
        def populate_buy_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Buy strategy Hyperopt will build and use
            """
            conditions = []
            # GUARDS AND TRENDS
            if 'rsi-enabled' in params and params['rsi-enabled']:
                conditions.append(dataframe['rsi'] > params['rsi-value'])

            # TRIGGERS
            if 'trigger' in params:
                if params['trigger'] == 'sma5':
                    conditions.append(dataframe['ha_close'] < dataframe['sma5'])
                if params['trigger'] == 'sma14':
                    conditions.append(dataframe['ha_close'] < dataframe['sma14'])
                if params['trigger'] == 'sma20':
                    conditions.append(dataframe['ha_close'] < dataframe['sma20'])
                if params['trigger'] == 'sma50':
                    conditions.append(dataframe['ha_close'] < dataframe['sma50'])
                if params['trigger'] == 'sma200':
                    conditions.append(dataframe['ha_close'] < dataframe['sma200'])

            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

            return dataframe

        return populate_buy_trend

    @staticmethod
    def indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching strategy parameters
        """
        return [
            Integer(5, 60, name='rsi-value'),
            Categorical([True, False], name='rsi-enabled'),
            Categorical(['sma5','sma14','sma20','sma50''sma200' ], name='trigger')
        ]

    @staticmethod
    def sell_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the sell strategy parameters to be used by hyperopt
        """
        def populate_sell_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            """
            Sell strategy Hyperopt will build and use
            """
            # print(params)
            conditions = []
            # GUARDS AND TRENDS
            if 'sell-rsi-enabled' in params and params['sell-rsi-enabled']:
                conditions.append(dataframe['rsi'] > params['sell-rsi-value'])

            # TRIGGERS
            if 'sell-trigger' in params:
                if params['sell-trigger'] == 'sell-sma5':
                    conditions.append(dataframe['close'] > dataframe['sma5'])
                if params['sell-trigger'] == 'sell-sma14':
                    conditions.append(dataframe['close'] > dataframe['sma14'])
                if params['sell-trigger'] == 'sell-sma20':
                    conditions.append(dataframe['close'] > dataframe['sma20'])
                if params['sell-trigger'] == 'sell-sma50':
                    conditions.append(dataframe['close'] > dataframe['sma50'])
                if params['sell-trigger'] == 'sell-sma200':
                    conditions.append(dataframe['close'] > dataframe['sma200'])

            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'sell'] = 1

            return dataframe

        return populate_sell_trend

    @staticmethod
    def sell_indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching sell strategy parameters
        """
        return [
            Integer(30, 100, name='sell-rsi-value'),
            Categorical([True, False], name='sell-rsi-enabled'),
            Categorical(['sell-sma5',
                         'sell-sma14',
                         'sell-sma20',
                         'sell-sma50',
                         'sell-sma200'], name='sell-trigger')
        ]

    @staticmethod
    def generate_roi_table(params: Dict) -> Dict[int, float]:
        """
        Generate the ROI table that will be used by Hyperopt
        """
        roi_table = {}
        roi_table[0] = params['roi_p1'] + params['roi_p2'] + params['roi_p3']
        roi_table[params['roi_t3']] = params['roi_p1'] + params['roi_p2']
        roi_table[params['roi_t3'] + params['roi_t2']] = params['roi_p1']
        roi_table[params['roi_t3'] + params['roi_t2'] + params['roi_t1']] = 0

        return roi_table

    @staticmethod
    def stoploss_space() -> List[Dimension]:
        """
        Stoploss Value to search
        """
        return [
            Real(-0.5, -0.02, name='stoploss'),
        ]

    @staticmethod
    def roi_space() -> List[Dimension]:
        """
        Values to search for each ROI steps
        """
        return [
            Integer(10, 120, name='roi_t1'),
            Integer(10, 60, name='roi_t2'),
            Integer(10, 40, name='roi_t3'),
            Real(0.01, 0.04, name='roi_p1'),
            Real(0.01, 0.07, name='roi_p2'),
            Real(0.01, 0.20, name='roi_p3'),
        ]

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators. Should be a copy of from strategy
        must align to populate_indicators in this file
        Only used when --spaces does not include buy
        """
        dataframe.loc[
            (
                (
                    (qtpylib.crossed(dataframe['ha_close'], dataframe['sma14'],direction="above"))
                    |(qtpylib.crossed(dataframe['ha_close'], dataframe['ha_close'].shift(1),direction="above")
                    &dataframe['ha_close'] > dataframe['sma14'])
                )
                &(dataframe['ha_close'] < dataframe['ha_open']) #latest HA candle is bearish, HA_Close < HA_Open
                &(abs(dataframe['ha_close']-dataframe['ha_open']) > abs(dataframe['ha_close'].shift(1)-dataframe['ha_open'].shift(1)))#current candle body is longer than previous candle body
                &(dataframe['ha_close'].shift(1) < dataframe['ha_open'].shift(1)) #  previous candle was bearish
                &(dataframe['ha_open'] != dataframe['ha_high'])#latest candle has no upper wick HA_Open == HA_High
                &(dataframe['rsi'] < 60)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators. Should be a copy of from strategy
        must align to populate_indicators in this file
        Only used when --spaces does not include sell
        """
        dataframe.loc[
            (
                (
                    (qtpylib.crossed(dataframe['ha_close'], dataframe['ha_close'].shift(1),direction="above")
                    &(dataframe['ha_low'] < dataframe['sma14']))
                )
            ),
            'sell'] = 1
        return dataframe
