import os
import json
import pandas as pd
import pytech.utils as utils

from sources.restclient import (
    RestClient,
    HTTPAction,
    RestClientError,
)
from utils import (
    DateRange,
    Dict,
)


class TiingoClient(RestClient):
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(**kwargs)
        self._base_url = 'https://api.tiingo.com'
        self.api_key = os.environ.get('TIINGO_API_KEY', api_key)

        if self.api_key is None:
            raise KeyError('Must set TIINGO_API_KEY.')

        self._headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'pytech-client'
        }

    @property
    def base_url(self):
        return self._base_url

    @property
    def headers(self):
        return self._headers

    def _get_dt_params(self, date_range: DateRange):
        params = {}

        if date_range is None:
            return params

        if date_range.start is not None:
            params['startDate'] = date_range.start.strftime('%Y-%m-%d')

        if date_range.end is not None:
            params['endDate'] = date_range.end.strftime('%Y-%m-%d')

        return params

    def get_ticker_metadata(self, ticker: str) -> Dict[str, str]:
        """
        Returns metadata for a single ticker.
        :param ticker: the ticker for the asset.
        :return: a :class:`pd.DataFrame` with the response.
        """
        resp = self._request(f'/tiingo/daily/{ticker}')
        return resp.json()

    def get_ticker_prices(self, ticker: str,
                          date_range: DateRange = None,
                          freq: str = 'daily',
                          fmt: str = 'json') -> pd.DataFrame:
        url = f'/tiingo/daily/{ticker}/prices'
        params = {
            'format': fmt,
            'resampleFreq': freq,
        }

        params.update(self._get_dt_params(date_range))

        resp = self._request(url=url, params=params)

        df = pd.read_json(json.dumps(resp.json()))

        if df.empty:
            raise RestClientError('Empty DataFrame was returned')

        df[utils.DATE_COL] = df[utils.DATE_COL].apply(utils.parse_date)
        return df

    def get_intra_day(self, ticker: str,
                      date_range: DateRange = None,
                      freq: str = '5min',
                      **kwargs):
        url = f'/iex/{ticker}/prices'
        params = {
            'ticker': ticker,
            'resampleFreq': freq
        }
        params.update(self._get_dt_params(date_range))

        resp = self._request(url, params=params)
        df = pd.read_json(json.dumps(resp.json()))

        if df.empty:
            raise RestClientError('Empty DataFrame was returned')
        else:
            return df

    def get_historical_data(self, ticker: str,
                            date_range: DateRange,
                            freq: str = 'Daily',
                            adjusted: bool = True):
        pass