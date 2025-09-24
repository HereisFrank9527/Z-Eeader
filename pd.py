import random
from fake_useragent import UserAgent

ua = UserAgent()
headers = {'User-Agent': ua.random}