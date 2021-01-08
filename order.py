import independentreserve as ir
import json

with open('config.json', 'r') as file:
    config = json.loads(file.read())

CONNECTION = ir.PublicMethods()
API = ir.PrivateMethods(config['ApiKey'], config['ApiSecret'])


def get_open_orders_info():
    open_orders = API.get_open_orders(
        primary_currency_code="Dai",
        secondary_currency_code="Aud",
        page_index=1,
        page_size=10
    )
    return open_orders


def cancel_all_orders():
    guid_collection = []
    orders_info = get_open_orders_info()
    if len(orders_info['Data']) > 0:
        for item in orders_info['Data']:
            guid_collection.append(item['OrderGuid'])

        for item in guid_collection:
            API.cancel_order(item)
    else:
        return


def account_balance():
    response = API.get_accounts()
    return response


def get_order_amount():
    offer_amount = 0
    bid_amount = 0
    for item in config['Data']['Offer']:
        offer_amount += item['volume']
    for item in config['Data']['Bid']:
        bid_amount += item['volume'] * item['price']

    return offer_amount, bid_amount


if __name__ == '__main__':
    account_balance()
    # cancel_all_orders()
    # get_order_amount()
