import independentreserve as ir
import json
import asyncio
import time

with open('config.json', 'r') as file:
    config = json.loads(file.read())

CONNECTION = ir.PublicMethods()
API = ir.PrivateMethods(config['ApiKey'], config['ApiSecret'])


def get_open_orders_info():
    open_orders = API.get_open_orders(
        primary_currency_code=config['CurrencyCode']['primary'],
        secondary_currency_code=config['CurrencyCode']['secondary'],
        page_index=1,
        page_size=25
    )
    time.sleep(1)
    return open_orders


def guid_collection_for_open_orders():
    guid_collection = []
    orders_info = get_open_orders_info()
    if len(orders_info['Data']) > 0:
        for item in orders_info['Data']:
            guid_collection.append(item['OrderGuid'])
        return guid_collection
    else:
        return None


def cancel_all_orders():
    total_orders = guid_collection_for_open_orders()
    if total_orders is None:
        print('Empty open orders')
    else:
        for item in total_orders:
            API.cancel_order(item)
            time.sleep(1)


def account_balance():
    response = API.get_accounts()
    time.sleep(1)
    print(response)
    return response


def handle_filled_orders():
    closed_filled_orders = API.get_closed_filled_orders(
        primary_currency_code=config['CurrencyCode']['primary'],
        secondary_currency_code=config['CurrencyCode']['secondary'],
        page_index=1,
        page_size=50
    )
    time.sleep(1)
    return closed_filled_orders['Data'][0:16]


def get_order_amount():
    offer_amount = 0
    bid_amount = 0
    for item in config['Data']['Offer']:
        offer_amount += item['volume']
    for item in config['Data']['Bid']:
        bid_amount += item['volume'] * item['price']

    return offer_amount, bid_amount


def order_log(res):
    for item in res:
        print(f'{item["Type"]} - Volume: {item["VolumeOrdered"]}, Price: {item["Price"]}')

if __name__ == '__main__':
    # asyncio.run(handle_filled_orders())
    # account_balance()
    # asyncio.run(get_open_orders_info())
    cancel_all_orders()
    # get_order_amount()
