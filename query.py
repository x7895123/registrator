from request import select_request, card_info_request, dml_request


def get_card_info(card_data):
    return card_info_request(card_data)


def acc_info_old(card_data):
    account = select_request(f"""
        SELECT FIRST 1 idaccount, phone, datebegin, cabinet, owner
            FROM (
            SELECT a.id idaccount, v.PHONE phone, udf_formatdatetime('dd.mm.yy hh:mm:ss', a.DATEBEGIN) datebegin, trim(c2.NAME) cabinet, trim(c1.NAME) owner
            FROM RESTAURANT_ACCOUNTCABINETS ac
                JOIN RESTAURANT_ACCOUNTS a ON a.ID = ac.IDACCOUNT
                JOIN RESTAURANT_CABINETCARDS cc1 ON cc1.ID = a.IDCARD
                JOIN RESTAURANT_CABINETS c1 ON c1.ID = cc1.IDCABINET 
                JOIN RESTAURANT_CABINETCARDS cc2 ON cc2.ID = ac.IDCABINETCARD
                JOIN RESTAURANT_CABINETS c2 ON c2.ID = cc2.IDCABINET
                LEFT OUTER JOIN RESTAURANT_VIPCUSTOMERS rv ON rv.ID =a.IDVIPCUSTOMER 
                LEFT OUTER JOIN VIPCUSTOMER v ON v.ID = rv.IDVIPINFO
            WHERE cc2.CARDDATA = '{card_data}' 
            
            union ALL
            
            SELECT a.id idaccount, v.PHONE phone, udf_formatdatetime('dd.mm.yy hh:mm:ss', a.DATEBEGIN) datebegin, trim(c.NAME) cabinet, trim(c.NAME) owner
            FROM RESTAURANT_ACCOUNTS a 
                JOIN RESTAURANT_CABINETCARDS cc ON cc.ID = a.IDCARD
                JOIN RESTAURANT_CABINETS c ON c.ID = cc.IDCABINET 
                LEFT OUTER JOIN RESTAURANT_VIPCUSTOMERS rv ON rv.ID =a.IDVIPCUSTOMER 
                LEFT OUTER JOIN VIPCUSTOMER v ON v.ID = rv.IDVIPINFO
            WHERE cc.CARDDATA = '{card_data}'
            )
        ORDER BY idaccount DESC 
    """)

    result = dict()

    if account:
        result.update({'account': account[0]})

        idaccount = account[0][0]
        sql = f"""
            select 
                trim(r.NAME) name,
                count(*) quantity,
                sum(AR.PRICE * G.QUANTITY) as amount 
            from RESTAURANT_ACCOUNTRESOURCES ar
                    join restaurant_accounts a on a.id = ar.idaccount
                    left outer join RESTAURANT_GETPRICEFORRESOURCE(AR.IDRESOURCE, ar.idaccount, AR.DATEBEGIN, current_timestamp) G on 1 = 1
                    JOIN RESTAURANT_RESOURCES r ON r.ID = ar.IDRESOURCE 
            WHERE
                ar.IDACCOUNT = {idaccount} and
                ar.IDSTATE = 0
            GROUP BY ar.ID, r.NAME 

            union all

            /* Кухня и бар*/
            select 
                trim(O.FULLNAME) name,
                count(*) quantity,
                sum(O.SUMMA) as amount
            from RESTAURANT_ORDERS O
                    join RESTAURANT_SERVICES s on s.id = o.idservice
                    join restaurant_accounts a on a.id = o.idaccount
            where
                o.IDACCOUNT = {idaccount}
            GROUP BY O.FULLNAME 
        """
        orders = select_request(sql)
        result.update({'orders': orders})

        sql = f"SELECT sum(ap.SUMMAPAYMENT) FROM RESTAURANT_ACCOUNTPAYMENTS ap WHERE ap.IDACCOUNT = {idaccount}"
        if payment := select_request(sql):
            result.update({'payment': payment[0][0]})
        else:
            result.update({'payment': 0})

    return result


def update_phone(idaccount, idvip, phone):
    result = -1
    if idaccount > 0:
        result = select_request(f'select idvip, idrvip from UD_UPDATE_account_client({idaccount}, {phone})')
    elif idvip > 0:
        result = dml_request(f"update vipcustomer set phone = '{phone}' where id = {idvip}")
    return result


if __name__ == '__main__':
    print(get_card_info('3F381C') or 'NA')