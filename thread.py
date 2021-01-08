import independentreserve as ir
from multiprocessing import Process, Queue
connection = ir.PublicMethods()
api = ir.PrivateMethods('1f9a5ac7-8535-40a8-a506-552db0cb4450', '7ac9d52652274f2cb80a1915babb8e9c')


def submit_bid(price, volumn, pri_code, sec_code, result):
    total = []
    response = api.place_limit_order(
        price,
        volumn,
        primary_currency_code=pri_code,
        secondary_currency_code=sec_code,
        order_type='LimitBid'
    )
    total.append(response)
    result.put(total)
    return


def submit_offer(price, volumn, pri_code, sec_code, result):
    total = []
    response = api.place_limit_order(
        price,
        volumn,
        pri_code,
        primary_currency_code=pri_code,
        secondary_currency_code=sec_code,
        order_type='LimitOffer'
    )
    total.append(response)
    result.put(total)
    return


def send_limit():
    result = Queue()
    bid1 = Process(target=submit_bid, args=(1.3, 1, 'Dai', 'Aud', result))
    bid2 = Process(target=submit_bid, args=(1.3, 1, 'Dai', 'Aud', result))
    bid3 = Process(target=submit_bid, args=(1.3, 1, 'Dai', 'Aud', result))
    bid4 = Process(target=submit_bid, args=(1.3, 1, 'Dai', 'Aud', result))

    offer1 = Process(target=submit_offer, args=(1, 1, 'Dai', 'Aud', result))
    offer2 = Process(target=submit_offer, args=(1, 1, 'Dai', 'Aud', result))
    offer3 = Process(target=submit_offer, args=(1, 1, 'Dai', 'Aud', result))
    offer4 = Process(target=submit_offer, args=(1, 1, 'Dai', 'Aud', result))

    bid1.start()
    bid2.start()
    bid3.start()
    bid4.start()

    offer1.start()
    offer2.start()
    offer3.start()
    offer4.start()

    bid1.join()
    bid2.join()
    bid3.join()
    bid4.join()

    offer1.join()
    offer2.join()
    offer3.join()
    offer4.join()

    result.put('STOP')
    total = []
    while True:
        tmp = result.get()
        if tmp == 'STOP':
            break
        else:
            total += tmp
    print(f'Result: {total}')
    return total


if __name__ == '__main__':
    send_limit()
