import independentreserve as ir
import baseline
import time
import datetime
import json
from order import cancel_all_orders
from order import order_log
from symbol import get_balance
from symbol import get_reserved_amount
from order import handle_filled_orders
from order import get_open_orders_info

# read all info use set in config
with open('config.json', 'r') as file:
    config = json.loads(file.read())

# public api client
CONNECTION = ir.PublicMethods()

# private api client
API = ir.PrivateMethods(config['ApiKey'], config['ApiSecret'])

# Change_Threshold set by user
SCT = config['CT']

# get primary and secondary currency code
PC = config['CurrencyCode']['primary']
SC = config['CurrencyCode']['secondary']

# updated baseline price after 10s
UBP = 0

# order data for 4offers
ORDER_OFFER = config['Data']['Offer']

# order data for 4bids
ORDER_BID = config['Data']['Bid']

# bot start flag
START = True

# after submit orders
current_orders = []

# baseline price
BP = baseline.current()

# get interval for the order cycle
interval = config['CheckTimeInterval']


# get CT value which should be get every 10s
def get_ct(BP, UBP):
    return abs((UBP - BP) / BP * 100)


# order 4bids and 4offers in ORDER_DATA
def send_limit(CBP):
    total_response = []
    for order in ORDER_OFFER:
        response = API.place_limit_order(
            CBP + CBP * order['price'],
            order['volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        time.sleep(1)
        total_response.append(response)

    for order in ORDER_BID:
        response = API.place_limit_order(
            CBP - CBP * order['price'],
            order['volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        time.sleep(1)
        total_response.append(response)

    order_log(total_response)
    return total_response


def replace_orders(order):
    if order['OrderType'] == 'LimitOffer':
        response = API.place_limit_order(
            order['Price'],
            order['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        time.sleep(1)
        return response

    if order['OrderType'] == 'LimitBid':
        response = API.place_limit_order(
            order['Price'],
            order['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        time.sleep(1)
        return response


def replace_partial_filled_orders(item):
    pri_balance, sec_balance = get_balance()
    if item['OrderType'] == 'LimitOffer' and item['Volume'] < pri_balance:
        response = API.place_limit_order(
            item['Price'],
            item['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        time.sleep(1)
        return response

    if item['OrderType'] == 'LimitOffer' and item['Volume'] > pri_balance:
        if pri_balance > 0:
            response = API.place_limit_order(
                item['Price'],
                pri_balance,
                primary_currency_code=PC,
                secondary_currency_code=SC,
                order_type='LimitOffer'
            )
            time.sleep(1)
            return response

    if item['OrderType'] == 'LimitBid' and item['Volume'] * item['Price'] < sec_balance:
        response = API.place_limit_order(
            item['Price'],
            item['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        time.sleep(1)
        return response

    if item['OrderType'] == 'LimitBid' and item['Volume'] * item['Price'] > sec_balance:
        if sec_balance > 0:
            response = API.place_limit_order(
                item['Price'],
                sec_balance / item['Volume'],
                primary_currency_code=PC,
                secondary_currency_code=SC,
                order_type='LimitBid'
            )
            time.sleep(1)
            return response


# check CT and account balance
def check_limit(BP, UBP):
    global current_orders
    pri_balance, sec_balance = get_balance()
    print(f'Timestamp: {datetime.datetime.now()}')

    if UBP == 0:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(BP)
        print(f'Start -> BP = {BP}')
        if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
            current_orders = send_limit(BP)
        else:
            print('UBP: Account balance is not available')
    else:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(UBP)
        CT = get_ct(BP, UBP)
        print(f'BP = {BP}, UBP = {UBP}, CT = {CT}')
        if CT > SCT:
            cancel_all_orders()
            print(f'CT > {SCT}: Cancelled all orders')
            if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
                current_orders = send_limit(UBP)
            else:
                print('Account balance is not available')
        else:
            print(f'CT < {SCT}: Check order status...')
            recent_open_orders = get_open_orders_info()

            for ite in recent_open_orders['Data']:
                print(f'{ite["OrderGuid"]}, {ite["OrderType"]}, {ite["Price"]}, {ite["Volume"]}')

            # process for filled orders
            recent_closed_filled_orders = handle_filled_orders()

            for item1 in current_orders:
                for item2 in recent_closed_filled_orders:
                    if item2['OrderGuid'] == item1['OrderGuid'] and item2['Status'] == 'Filled':
                        f_order = {
                            'OrderGuid': item2['OrderGuid'],
                            'OrderType': item2['OrderType'],
                            'Volume': item2['Volume'],
                            'Price': item2['Price'],
                            'Status': item2['Status']
                        }

                        print(f'\n{"* * * * * * * * *" * 5}')
                        current_orders = list(filter(lambda i: i['OrderGuid'] != f_order['OrderGuid'], current_orders))

                        print(f_order['OrderGuid'], f_order['OrderType'], f_order['Price'], f_order['Volume'], f_order['Status'])

                        filled_replace_response = replace_orders(f_order)
                        print(filled_replace_response['OrderGuid'],
                              filled_replace_response['Type'],
                              filled_replace_response['Price'],
                              filled_replace_response['VolumeOrdered'],
                              filled_replace_response['Status'])

                        current_orders.append(filled_replace_response)

            # process for partial filled orders
            for item in recent_open_orders['Data']:
                if item['Status'] == 'PartiallyFilled':
                    print(f'\n{"* * * * * * * * *" * 5}')

                    print(item['OrderGuid'], item['OrderType'], item['Price'], item['Volume'], item['Status'])
                    cancel_res = API.cancel_order(item['OrderGuid'])
                    time.sleep(1)
                    print(cancel_res['OrderGuid'],
                          cancel_res['Type'],
                          cancel_res['Price'],
                          cancel_res['VolumeOrdered'],
                          cancel_res['Status'])

                    current_orders = list(filter(lambda i: i['OrderGuid'] != item['OrderGuid'], current_orders))

                    replace_res = replace_partial_filled_orders(item)
                    print(replace_res['OrderGuid'], replace_res['Type'], replace_res['Price'], replace_res['VolumeOrdered'], replace_res['Status'])

                    current_orders.append(replace_res)


while True:
    if START is True:
        check_limit(BP, UBP)
        UBP = BP
        START = False
    else:
        BP = UBP
        UBP = baseline.current()
        check_limit(BP, UBP)
    time.sleep(interval)
