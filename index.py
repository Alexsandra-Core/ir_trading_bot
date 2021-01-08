import independentreserve as ir
import baseline
import time
import json
from order import cancel_all_orders
from order import account_balance
from order import get_order_amount

with open('config.json', 'r') as file:
    config = json.loads(file.read())

# public api client
CONNECTION = ir.PublicMethods()

# private api client
API = ir.PrivateMethods(config['ApiKey'], config['ApiSecret'])

# Change_Threshold set by user
SCT = config['CT']

# baseline price
BP = baseline.current()

# baseline uploaded baseline price after 10s
UBP = None

# order data for 4offers
ORDER_OFFER = config['Data']['Offer']

# order data for 4bids
ORDER_BID = config['Data']['Bid']

# account balance
AB = account_balance()


# get CT value which should be get every 10s
def get_ct(BP, UBP):
    CT = (UBP - BP) / BP * 100
    return CT


# order 4bids and 4offers in ORDER_DATA
def send_limit():
    total_response = []
    for order in ORDER_OFFER:
        if account_balance()[13]['AvailableBalance'] > order['volume']:
            response = API.place_limit_order(
                order['price'],
                order['volume'],
                primary_currency_code=order['primary_currency_code'],
                secondary_currency_code=order['secondary_currency_code'],
                order_type=order['order_type']
            )
            total_response.append(response)
        else:
            if account_balance()[13]['AvailableBalance'] == 0:
                return
            else:
                response = API.place_limit_order(
                    order['price'],
                    account_balance()[0]['AvailableBalance'],
                    primary_currency_code=order['primary_currency_code'],
                    secondary_currency_code=order['secondary_currency_code'],
                    order_type=order['order_type']
                )
                total_response.append(response)

    for order in ORDER_BID:
        if account_balance()[0]['AvailableBalance'] > order['volume'] * order['price']:
            response = API.place_limit_order(
                order['price'],
                order['volume'],
                primary_currency_code=order['primary_currency_code'],
                secondary_currency_code=order['secondary_currency_code'],
                order_type=order['order_type']
            )
            total_response.append(response)
        else:
            if account_balance()[13]['AvailableBalance'] == 0:
                return
            else:

                response = API.place_limit_order(
                    order['price'],
                    account_balance()[0]['AvailableBalance'] / order['price'],
                    primary_currency_code=order['primary_currency_code'],
                    secondary_currency_code=order['secondary_currency_code'],
                    order_type=order['order_type']
                )
                total_response.append(response)

    print(total_response)


# check CT and account balance
def check_limit(BP, UBP):
    if UBP is None: # for first order
        send_limit()
    else:
        CT = get_ct(BP, UBP)
        print(f'BP={BP} UBP={UBP} CT={CT}')
        print(f'Balance: {AB[0]["AvailableBalance"]}Aud, {AB[13]["AvailableBalance"]}Dai\n')
        if CT > SCT:
            cancel_all_orders()
            send_limit()


while True:
    check_limit(BP, UBP)
    time.sleep(10)
    if UBP is None:
        UBP = baseline.current()
    else:
        BP = UBP
        UBP = baseline.current()
