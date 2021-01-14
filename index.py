import asyncio
import independentreserve as ir
import baseline
import time
import multiprocessing
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


# get CT value which should be get every 10s
def get_ct(BP, UBP):
    return abs((UBP - BP) / BP * 100)


# order 4bids and 4offers in ORDER_DATA
async def send_limit(CBP):
    total_response = []
    for order in ORDER_OFFER:
        response = API.place_limit_order(
            CBP + CBP * order['price'],
            order['volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        await asyncio.sleep(1)
        total_response.append(response)

    for order in ORDER_BID:
        response = API.place_limit_order(
            CBP - CBP * order['price'],
            order['volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        await asyncio.sleep(1)
        total_response.append(response)

    order_log(total_response)
    return total_response


async def replace_orders(order):
    if order['OrderType'] == 'LimitOffer':
        response = API.place_limit_order(
            order['Price'],
            order['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        await asyncio.sleep(1)
        return response

    if order['OrderType'] == 'LimitBid':
        response = API.place_limit_order(
            order['Price'],
            order['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        await asyncio.sleep(1)
        return response


async def replace_partial_filled_orders(item):
    replace_response = []
    pri_balance, sec_balance = await get_balance()
    if item['OrderType'] == 'LimitOffer' and pri_balance > item['Volume']:
        response = API.place_limit_order(
            item['Price'],
            item['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        await asyncio.sleep(1)
        print('balance available, so reserved amount was offered')
        replace_response.append(response)

    if item['OrderType'] == 'LimitOffer' and pri_balance < item['Volume']:
        if pri_balance > 0:
            response = API.place_limit_order(
                item['Price'],
                pri_balance,
                primary_currency_code=PC,
                secondary_currency_code=SC,
                order_type='LimitOffer'
            )
            await asyncio.sleep(1)
            print('balance is not available, so balance was offered')
            replace_response.append(response)

    if item['OrderType'] == 'LimitBid' and sec_balance > item['Value']:
        response = API.place_limit_order(
            item['Price'],
            item['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        await asyncio.sleep(1)
        print('balance available, so reserved amount was bidded')
        replace_response.append(response)

    if item['OrderType'] == 'LimitBid' and sec_balance < item['Value']:
        if sec_balance > 0:
            response = API.place_limit_order(
                item['Price'],
                sec_balance / item['Volume'],
                primary_currency_code=PC,
                secondary_currency_code=SC,
                order_type='LimitBid'
            )
            await asyncio.sleep(1)
            print('balance is not available, so amount for balance was bidded')
            replace_response.append(response)

    return replace_response


# check CT and account balance
async def check_limit(BP, UBP):
    global current_orders
    pri_balance, sec_balance = await get_balance()
    if UBP == 0:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(BP)
        print(f'Start -> BP = {BP}, UBP = {UBP}')
        if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
            current_orders = await send_limit(BP)
    else:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(UBP)
        CT = get_ct(BP, UBP)
        if CT > SCT:
            print(f'CT > {SCT} =>')
            await cancel_all_orders()
            if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
                current_orders = await send_limit(UBP)
            else:
                print('Account balance is not available')
        else:
            print(f'CT < {SCT} => \nso checking filled orders and replacing.')
            recent_closed_filled_orders = await handle_filled_orders()
            recent_open_orders = await get_open_orders_info()

            # process for partial filled orders
            for item in recent_open_orders['Data']:
                if item['Status'] == 'PartiallyFilled':
                    print(f'This order is partially filled.\n{item}')
                    print(f'So, we have to cancel this order and replace')
                    cancel_response = API.cancel_order(item['OrderGuid'])
                    await asyncio.sleep(1)
                    print(f'Cancelled this order. Look this response\n{cancel_response}')
                    replace_response = replace_partial_filled_orders(item)
                    print(f'replace this order.\n{replace_response}')

            # process for filled orders
            for item1 in current_orders:
                for item2 in recent_closed_filled_orders:
                    if item2['OrderGuid'] == item1['OrderGuid']:
                        f_order = {
                            'OrderGuid': item2['OrderGuid'],
                            'OrderType': item2['OrderType'],
                            'Volume': item2['Volume'],
                            'Price': item2['Price'],
                            'Status': item2['Status']
                        }
                        print(f'This order is filled.\n{f_order}')
                        print(f'So, we have to replace this order')
                        filled_replace_response = replace_orders(f_order)
                        print(f'replaced\n{filled_replace_response}')


def start():
    global BP, UBP, START
    while True:
        if START is True:
            asyncio.run(check_limit(BP, UBP))
            UBP = BP
            START = False
        else:
            BP = UBP
            UBP = baseline.current()
            asyncio.run(check_limit(BP, UBP))
        time.sleep(30)


if __name__ == '__main__':
    p = multiprocessing.Process(target=start, name="Start", args=(10,))
    p.start()
    time.sleep(3600)
    p.terminate()
    p.join()
