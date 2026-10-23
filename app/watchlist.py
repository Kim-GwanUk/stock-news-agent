def filter_stocks(stocks,query='',kind='전체'):
    query=''.join(query.split()).casefold()
    return [s for s in stocks if (kind=='전체' or s['kind']==kind)
            and (query in ''.join(s['name'].split()).casefold() or query in s['code'])]
