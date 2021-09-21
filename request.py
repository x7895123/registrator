import requests
from config import config


# IP = '85.92.121.219:30005'
# IP = '192.168.1.119:4041'
# IP = '127.0.0.1:80'
# IP = '85.92.121.219:4042'
# IP = '11.10.0.2:8080'

IP = config()['ip']


def prepare_sql(sql):
    sql = sql.replace("\n", " ")
    sql = ' '.join(sql.split())
    return sql


def json_request(url, payload):
    headers = {'content-type': "application/json"}
    auth = ('dude', 'Hold My Beer')
    response = requests.request("POST", url, data=payload.encode('utf-8'), headers=headers, auth=auth)
    # print(response.status_code)
    return response.json() if response.status_code == 200 else {}


def select_request(sql, ip=IP):
    url = f"http://{ip}/dql"
    payload = '{{"sql": "{}"}}'.format(prepare_sql(sql))
    return json_request(url, payload)


def dml_request(sql, ip=IP):
    url = "http://{}/dml".format(ip)
    payload = '{{"sql": "{}"}}'.format(prepare_sql(sql))
    return json_request(url, payload)


def get_qr(data, ip=IP):
    url = "http://{}/qr".format(ip)
    payload = f'{{"data": "{data}", "from_color": "#000956","to_color": "#503056"}}'.encode('UTF-8')
    # print(payload)
    headers = {'content-type': "application/json"}
    response = requests.request("POST", url, data=payload, headers=headers)

    if response.status_code == 200:
        return response.content
    else:
        return None


def card_info_request(card_data, ip=IP):
    url = f"http://{ip}/card_info"
    payload = f'{{"card_data": "{card_data}"}}'
    return json_request(url, payload)


if __name__ == '__main__':
    print(card_info_request("3F26DE"))
    print(card_info_request("5A8B00"))
