# Get free proxies
If you are working on web scraping project an due to some reason your IP is getting blocked. Don't worry, simply use this API to get a list of free proxies from the internet.

This script is built using Python and FastAPI.

While using requests library, just pass each proxy as :

```
proxies = {"https": proxy}  
requests.get(url, proxies=proxies, timeout=10)
```
