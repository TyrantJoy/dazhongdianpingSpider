import re
import requests
import bs4
import csv
import sys
import pymongo
from bs4 import BeautifulSoup
import time
from fake_useragent import UserAgent

client = pymongo.MongoClient(host='localhost', port=27017)
db = client.dazhongdianping
CSS_collection = db.CSS
SVG_collection = db.SVG
COMM_collection = db.COMMENT_DATA

def get_CSS_URL(htmlContent):
    result = re.findall('<link rel="stylesheet" type="text/css" href="//s3plus(.*?)">', htmlContent, re.S)
    cssUrl = 'http://s3plus' + result[0]
    return cssUrl

def get_CSS_Content(CSSUrl, CSS_collection):
    ua = UserAgent(verify_ssl=False)
    headers = {
        'User-Agent':ua.random,
        'Accept-Language':'zh-CN,zh;q=0.9'
    }
    result = CSS_collection.find_one({'url':CSSUrl})
    if result:
        return result['content']
    else:
        try:
            CSSContent = requests.get(CSSUrl, headers=headers).text
        except:
            print('CSS文件内容获取失败~~~被制裁啦~~~')
        else:
            css_item = {
                'url':CSSUrl,
                'content':CSSContent
            }
            CSS_collection.insert_one(css_item)
            return CSSContent

def get_SVG_URL(CSSContent):
    pattern = '[class^=".*?"].*?background-image: url[(](.*?)[)];background-repeat'
    SVG_URL_list = list()
    try:
        result = re.findall(pattern, CSSContent, re.S)
    except:
        print('CSS文件内容为空~~~上一步出错啦~~~')
    else:
        for url in result:
            url = "http:" + url
            SVG_URL_list.append(url)

    return SVG_URL_list

def get_SVG_Content(SVG_URL_list, SVG_collection):
    SVG_dic = dict()
    ua = UserAgent(verify_ssl=False)
    headers = {
        'User-Agent':ua.random,
        'Accept-Language':'zh-CN,zh;q=0.9'
    }
    for url in SVG_URL_list:
        result = SVG_collection.find_one({'url':url})
        if result:
            SVG_dic[url] = result['content']
        else:
            try:
                SVGContent = requests.get(url, headers=headers).text
            except:
                print(url, '获取svg内容出错啦~~~被制裁啦~~~')
            else:
                svg_item = {
                    'url':url,
                    'content':SVGContent
                }
                SVG_collection.insert_one(svg_item)
                SVG_dic[url] = SVGContent
    return SVG_dic

def get_Word_SVG_URL(prefix, CSSContent, SVG_dic):
    pattern = '\[class.*?="' + prefix + '.*?"\].*?background-image: url[(](.*?)[)];background-repeat'
    result = re.findall(pattern, CSSContent, re.S)
    if result:
        SVGUrl = 'http:' + result[0]
        return SVGUrl
    else:
        print('可恶的大众点评又换加密机制了~~~未获取到坐标信息，可能是标签前缀位数不对')

    

def get_Word_Point(className, CSSContent):
    point = re.findall(className + '{background:-(.*?).0px.*?-(.*?).0px', CSSContent, re.S)
    x = int(int(point[0][0])/14)
    y = int(point[0][1]) + 23
    return x, y

def get_Word_Content(SVGUrl, x, y, SVG_dic):
    SVGContent = SVG_dic[SVGUrl]
    result = re.findall('<text x="0" y="' + str(y) + '">(.*?)</text>', SVGContent, re.S)
    if result:
        return result[0][x]
    else:
        return get_Word_Content_B(SVGUrl, x, y, SVG_dic)

def get_Word_Content_B(SVGUrl, x, y, SVG_dic):
    SVGContent = SVG_dic[SVGUrl]
    soup = BeautifulSoup(SVGContent, 'lxml')
    paths = soup.find_all(name='path')
    key = dict()
    value = dict()
    for path in paths:
        index = re.findall('M0 (.*?) H600', str(path['d']))
        key[int(index[0])] = int(path['id'])

    datas = re.findall('<textPath xlink:href=".*?" textLength=".*?">(.*?)</textPath>', SVGContent, re.S)
    for data in datas:
        value[datas.index(data) + 1] = data
    
    return value[key[y]][x]



        
def get_User_Name(comment_div):
    user_name_div = comment_div.find_all(name='div', attrs={'class':'dper-info'})[0]
    user_name = user_name_div.a.string.strip()
    return user_name

def get_Food_List(comment_div):
    food = list()
    try:
        like_food_div = comment_div.find_all(name='div', attrs={'class':'review-recommend'})[0]
        food_a_list = like_food_div.find_all(name='a')
    except :
        pass
    else:
        for a in food_a_list:
            food.append(a.string)
    return food

def get_Comment_Time(comment_div):
    time_span = comment_div.find_all(name='span', attrs={'class':'time'})[0]
    comment_time = time_span.string.strip()
    return comment_time

def get_Zan_Reponse_Num(comment_div):
    num_em = comment_div.find_all(name='em', attrs={'class':'col-exp'})
    if num_em:
        if len(num_em) == 1:
            zan_num = num_em[0].string[1]
            response_num = 0
        else:
            zan_num = num_em[0].string[1]
            response_num = num_em[1].string[1]
    else:
        zan_num = 0
        response_num = 0
    return zan_num, response_num

def get_Comment_Content(comment_div,  CSSContent, SVG_dic):
    try:
        comment = comment_div.find_all(name='div', attrs={'class':'review-words Hide'})[0]
    except:
        comment = comment_div.find_all(name='div', attrs={'class':'review-words'})[0]
    
    comment_content = list()
    for tag in comment:
        if isinstance(tag, bs4.element.Tag):
            if tag.name == 'svgmtsi':
                className = str(tag['class'][0])
                prefix = str(tag['class'][0])[0:2]
                SVGUrl = get_Word_SVG_URL(prefix, CSSContent, SVG_dic)
                x, y = get_Word_Point(className, CSSContent)
                word = get_Word_Content(SVGUrl, x, y, SVG_dic)
                comment_content.append(word)
        elif isinstance(tag, bs4.element.NavigableString):
            comment_content.append(str(tag))
    return "".join(comment_content).strip()


with open(sys.argv[1], 'r', encoding='utf-8') as file:
    htmlContent = file.read()

soup = BeautifulSoup(htmlContent, 'lxml')
comment_div_list = soup.find_all(name='div', attrs={'class':'main-review'})
CSSUrl = get_CSS_URL(htmlContent)
CSSContent = get_CSS_Content(CSSUrl, CSS_collection)
SVG_URL_list = get_SVG_URL(CSSContent)
SVG_dic = get_SVG_Content(SVG_URL_list, SVG_collection)
data_list = list()
for comment_div in comment_div_list:
    data = dict()
    user_name = get_User_Name(comment_div) 
    food = get_Food_List(comment_div)
    comment_time = get_Comment_Time(comment_div)
    zan_num, response_num = get_Zan_Reponse_Num(comment_div)
    comment_content = get_Comment_Content(comment_div, CSSContent, SVG_dic)
    food = ",".join(food)
    data = {
        'userID':user_name,
        'likeFood':food,
        'commentTime':comment_time,
        'zanNum':zan_num,
        'responseNum':response_num,
        'content':comment_content
    }
    data_list.append(data)

print("已经从%s收集到%d条评论数据~~,正在写入数据库~~" %(sys.argv[1], len(data_list)))
COMM_collection.insert_many(data_list)
print("数据已经成功写入~~")
print("\n")

