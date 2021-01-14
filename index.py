import asyncio
import independentreserve as ir
import baseline
import time
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


async def replace_orders(orders):
    global current_orders
    print(orders)
    filled_offers = []
    filled_bids = []
    for item in orders:
        if item['OrderType'] == 'LimitOffer':
            filled_offers.append(item)
        if item['OrderType'] == 'LimitBid':
            filled_bids.append(item)

    # for replace the order most far from the baseline price first
    filled_temp_bids = sorted(filled_bids, key=(lambda x: x['Price']))

    for item_offer in filled_offers:
        response = API.place_limit_order(
            item_offer['Price'],
            item_offer['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitOffer'
        )
        await asyncio.sleep(1)
        for order_offer in current_orders:
            if order_offer['OrderGuid'] == item_offer['OrderGuid']:
                current_orders.remove(order_offer)

        print(f'filled offer replaced {response}')
    for item_bid in filled_temp_bids:
        response = API.place_limit_order(
            item_bid['Price'],
            item_bid['Volume'],
            primary_currency_code=PC,
            secondary_currency_code=SC,
            order_type='LimitBid'
        )
        await asyncio.sleep(1)
        for order_bid in current_orders:
            if order_bid['OrderGuid'] == item_bid['OrderGuid']:
                current_orders.remove(order_bid)
        print(f'filled bid replaced {response}')


async def replace_partial_filled_orders(orders):
    for item in orders:
        API.cancel_order(item['OrderGuid'])
        await asyncio.sleep(1)

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

        if item['OrderType'] == 'LimitBid' and sec_balance > item['Value']:
            response = API.place_limit_order(
                item['Price'],
                item['Volume'],
                primary_currency_code=PC,
                secondary_currency_code=SC,
                order_type='LimitBid'
            )
            await asyncio.sleep(1)
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
        print(f'replaced partial filled orders after cancel that. \n {response}')


# check CT and account balance
async def check_limit(BP, UBP):
    global current_orders
    filled_orders = []
    partial_filled_orders = []
    pri_balance, sec_balance = await get_balance()
    if UBP == 0:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(BP)
        print(f'Start -> BP = {BP}, UBP = {UBP}')
        if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
            current_orders = await send_limit(BP)
    else:
        offer_reserved_amount, bid_reserved_amount = get_reserved_amount(UBP)
        CT = get_ct(BP, UBP)
        print(f'BP = {BP}, UBP = {UBP}, CT = {CT}')
        if CT > SCT:
            await cancel_all_orders()
            if pri_balance > offer_reserved_amount and sec_balance > bid_reserved_amount:
                current_orders = await send_limit(UBP)

        else:
            print(f'No place new orders because CT < {SCT}')
            print(f'CT < {SCT}, so checking filled orders and replacing.')
            recent_closed_filled_orders = await handle_filled_orders()
            recent_open_orders = await get_open_orders_info()
            print(f'current orders are {len(current_orders)} ones')

            # process for partial filled orders
            for item in recent_open_orders['Data']:
                if item['Status'] == 'PartiallyFilled':
                    partial_filled_orders.append(item)
            if len(partial_filled_orders) > 0:
                await replace_partial_filled_orders(partial_filled_orders)
            else:
                print('No partial filled orders')

            # process for filled orders
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
                        filled_orders.append(f_order)
            if len(filled_orders) > 0:
                await replace_orders(filled_orders)
            else:
                print('No filled orders')


# baseline price
BP = baseline.current()

while True:
    if START is True:
        asyncio.run(check_limit(BP, UBP))
        UBP = BP
        START = False
    else:
        BP = UBP
        UBP = baseline.current()
        asyncio.run(check_limit(BP, UBP))
    time.sleep(20)
