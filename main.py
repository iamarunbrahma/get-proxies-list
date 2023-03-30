from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup

import warnings
warnings.filterwarnings("ignore")

app = FastAPI()

def extract_proxies():
  headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
  response_1 = requests.get("https://free-proxy-list.net/", headers=headers, timeout=10)
  response_2 = requests.get("https://www.sslproxies.org/", headers=headers, timeout=10)

  soup_1 = BeautifulSoup(response_1.content, "lxml")
  proxy_tbl_1 = soup_1.find('table', {'class':'table table-striped table-bordered'})
  soup_2 = BeautifulSoup(response_2.content, "lxml")
  proxy_tbl_2 = soup_2.find('table', {'class':'table table-striped table-bordered'})

  headers_1 = [th.text.lower() for th in proxy_tbl_1.find("thead").find("tr").find_all("th")]

  table_content_1 = [
      {header: td.text for header, td in zip(headers_1, tr.find_all("td"))}
      for tr in proxy_tbl_1.find("tbody").find_all("tr")
  ]

  headers_2 = [th.text.lower() for th in proxy_tbl_2.find("thead").find("tr").find_all("th")]

  table_content_2 = [
      {header: td.text for header, td in zip(headers_2, tr.find_all("td"))}
      for tr in proxy_tbl_2.find("tbody").find_all("tr")
  ]

  return table_content_1, table_content_2


def get_proxies():
  proxy_lst = []
  table_content_1, table_content_2 = extract_proxies()

  for ele in table_content_1:
    last_checked = int(ele['last checked'].split()[0])
    if last_checked <= 5 and ele['https'] == 'yes' and ele['anonymity'] == 'elite proxy':
      proxy = ele['ip address']+':'+ele['port']
      proxy_lst.append(proxy)

  for ele in table_content_2:
    last_checked = int(ele['last checked'].split()[0])
    if last_checked <= 5 and ele['https'] == 'yes' and ele['anonymity'] == 'elite proxy':
      proxy = ele['ip address']+':'+ele['port']
      proxy_lst.append(proxy)
  
  return proxy_lst


@app.get("/")
def output_proxies():
  proxy_lst = get_proxies()
  if proxy_lst:
    return {'proxies':proxy_lst}
  return {'proxies':'Not found'}
