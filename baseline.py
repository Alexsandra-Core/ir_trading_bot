import requests
import json
import independentreserve as ir

connection = ir.PublicMethods()


# get DAIAUD
def current():
    # get average price for BTCDAI from binance
    payload = {}
    headers = {}
    url = 'https://api3.binance.com/api/v3/avgPrice?symbol=BTCDAI'
    BTCDAI = json.loads(requests.request('GET', url, headers=headers, data=payload).text)['price']

    # get BTCAUD from ir
    BTCAUD = connection.get_market_summary(primary_currency_code="Xbt", secondary_currency_code="Aud")['LastPrice']

    # get DAIAUD
    AUDDAI = float(BTCDAI) / BTCAUD
    DAIAUD = 1 / AUDDAI
    return DAIAUD
