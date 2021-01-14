import json
import independentreserve as ir
import asyncio

with open('config.json', 'r') as file:
    config = json.loads(file.read())

API = ir.PrivateMethods(config['ApiKey'], config['ApiSecret'])


# get account balance info for symbol
async def get_balance():
    pri_code = config['CurrencyCode']['primary']
    sec_code = config['CurrencyCode']['secondary']

    account_balance = API.get_accounts()
    await asyncio.sleep(1)
    pri_balance = None
    pri_available_balance = None
    sec_balance = None
    sec_available_balance = None

    for item in account_balance:
        if item['CurrencyCode'] == pri_code:
            pri_balance = item['TotalBalance']
            pri_available_balance = item['AvailableBalance']
        if item['CurrencyCode'] == sec_code:
            sec_balance = item['TotalBalance']
            sec_available_balance = item['AvailableBalance']

    print(f'\n{config["CurrencyCode"]["primary"]} total balance: {pri_balance}')
    print(f'{config["CurrencyCode"]["secondary"]} total balance: {sec_balance}')
    print(f'{config["CurrencyCode"]["primary"]} available balance: {pri_available_balance}')
    print(f'{config["CurrencyCode"]["secondary"]} available balance: {sec_available_balance}\n')

    return pri_available_balance, sec_available_balance


def get_reserved_amount(ubp):
    offer_reserved_amount = 0
    bid_reserved_amount = 0

    for item in config['Data']['Offer']:
        offer_reserved_amount += item['volume']
    for item in config['Data']['Bid']:
        bid_reserved_amount += (ubp - ubp * item['price']) * item['volume']
    return offer_reserved_amount, bid_reserved_amount


def get_limit_price():
    offers = []
    bids = []
    for item in config['Data']['Offer']:
        offers.append(item['price'])
    for item in config['Data']['Bid']:
        bids.append(item['price'])
    return max(offers), max(bids)

