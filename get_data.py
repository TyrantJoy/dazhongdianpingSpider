import requests
import time
import re
import sys
from fake_useragent import UserAgent
ua = UserAgent(verify_ssl=False)

url = 'http://www.dianping.com/shop/' + sys.argv[1] + '/review_all'

for i in range(2, int(sys.argv[2])):
    headers = {
        'User-Agent': ua.random,
        'Referer': url + '/p' + str(i-1), 
        'Cookie': sys.argv[3]
    }
    u = url + '/p' + str(i)
    result = requests.get(u, headers=headers).text
    a = re.findall('<p class="not-found-words">抱歉！页面无法访问......</p>', result, re.S)
    b = re.findall("<div class='logo' id='logo'>验证中心</div>", result, re.S)
    if a:
        print('IP被封，死心了吧')
        temp = input()
    elif b:
        print('去浏览器进行手工验证')
        temp = input()
    else:
        with open(str(i)+ '.html', 'w', encoding='utf-8') as file:
            file.write(result)
        print(u + '已经下载完毕')
        time.sleep(5)
