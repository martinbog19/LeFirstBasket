import string
# from unidecode import unidecode


def getId(tag) :
    return tag['href'].split('/')[-1].split('.html')[0]


def normalize_name(x) :

    for suffix in [' Jr.', ' Sr.', ' III', ' II', ' IV', ' Jr', ' Sr'] :
        x = x.replace(suffix, '')
    x = x.translate(str.maketrans('', '', string.punctuation))

    return unidecode(x).lower()