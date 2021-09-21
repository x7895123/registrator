import re


def convert(data):
    try:
        if first_part := re.search(r"\d{3},", data):
            first_part = first_part.group()
            first_part = hex(int(first_part[0:-1]))
            second_part = hex(int(re.search(r",\d{5}", data).group()[1:]))
            result = str(first_part[2:] + second_part[2:]).upper()
            return result
    except:
        return None


if __name__ == '__main__':
    print(convert('Em-Marine[4000] 023,21644'))