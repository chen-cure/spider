#
import json
import sqlite3
import time
import requests
import  pygal
from wordcloud import WordCloud

def get_one_product_one_page_comments(pid, pageno=1):
    """
    取一个商品的一页评论
    :param pid: 商品id
    :param pageno: 评论第n页
    :return: [{'content': ''}, {}]
    """
    base_url = 'https://club.jd.com/comment/productPageComments.action'

    # 本次请求头只用伪造user-agent即可，但前端时间测试需要cookie字段
    headers = {
        # 'Cookie': '__jdu=16096534364451068756302;',
        # 'Referer': 'https://item.jd.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
    }

    # tips:从开发者工具network请求头下面的query params复制下来再调整。使用编辑器列编辑模式 alt+shift+鼠标拖动。
    params = {
        #'callback': 'fetchJSON_comment98',
        'productId': pid,  # 商品id
        'score': 0,
        'sortType': 5,
        'page': pageno,                  # 第n页  经测试最大99页，之后只有概括数据无详细数据。
        'pageSize': 10,
        'isShadowSku': 0,
        'rid': 0,
        'fold': 1
    }

    resp = requests.get(base_url, headers=headers, params=params)
    status_code = resp.status_code
    comments_json = resp.text
    print(comments_json)
    # 京东评论接口返回jsonp格式，涉及跨域问题。需要将先jsonp转json。
    # 方法1：python字符串方法删除固定长度无用字符串;2(推荐)上网找从jsonp过滤json正则;3本例中发现修改参数可以直接返回json

    comments_obj = json.loads(comments_json)
    print(comments_obj)
    comments = comments_obj['comments']
    return comments

def write_comment_to_db(c, cursor):
    cid = c['id']
    content = c['content']
    creation_time = c['creationTime']
    images = c.get('images', None)
    product_color = c['productColor']
    product_Size = c['productSize']

    # 为避免重复插入，先判断
    # cursor.execute("""select * form comments where cid=?""", [cid])
    # if not cursor.fetchone:
    # [(cid, '内容', '绿色', '2021-'), ()]

    # 一条评论写入数据库
    cursor.execute("""
        insert into comments (cid, content, product_color, creation_time)
        values (?, ?, ?, ?);
    """, [cid, content, product_color, creation_time])

def db_init():
    # 数据库初始化
    connect = sqlite3.connect('./jd.db')
    cursor = connect.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            cid INTEGER,
            content TEXT,
            product_color TEXT,
            creation_time DATETIME
        );
        """)
    return connect,cursor

def words_image():
    # connect, cursor = db_init()
    cursor.execute("""
        select * from comments;
    """)
    comments_rs = cursor.fetchall()
    # print(comments_rs)
    comment = []
    for c in comments_rs:
        content = c[2]
        comment.append(content)
    # print(comment)

    with open('./dict/stop_words_zh.txt', mode='r', encoding='utf-8') as f:
        stop_words = f.read().splitlines()
        # print(stop_words)

    comment_list = []
    for word in comment:
        if word not in stop_words:
            comment_list.append(word)
    # print(comment_list)
    comment_str = ' '.join(comment_list)
    # print(comment_str)

    wc = WordCloud(font_path='./STXINGKA.TTF',  # 中文字体文件
          background_color='white',
          width=1000,
          height=800,
          min_font_size=50,
          max_font_size=300,
          prefer_horizontal=0.5,
          mode='RGB',
          colormap='viridis',
    ).generate(comment_str)
    wc.to_file('./京东评论词云图.png')

def tabulation_image():
    cursor.execute("""select count(id) from comments;""")
    comment_amount = cursor.fetchall()
    user_amount = comment_amount[0][0]
    print('用户总数:', user_amount)
    cursor.execute("""select count(id),product_color from comments group by product_color;""")
    rs = cursor.fetchall()
    print(rs)

    colors = {
    }
    for r in rs:
        num = r[0]
        color = r[1]
        colors[color] = round(num / user_amount * 100, 2)
        # colors[color]= num
    print(colors)
    bar_chart = pygal.Bar()
    bar_chart_title = 'iPhone12颜色销量图表'
    bar_chart.x_labels = ['白色', '红色', '绿色', '蓝色', '黑色']
    bar_chart.add('占比（销量/总销量）', [colors['白色'], colors['红色'], colors['绿色'], colors['蓝色'], colors['黑色']])
    bar_chart.render_to_file('./iphone12销量.svg')

if __name__ == '__main__':
    connect,cursor = db_init()
    words_image()
    tabulation_image()
    product_id = 100009077475
    for pageno in range(1, 100):

        one_page_comments = get_one_product_one_page_comments(product_id, pageno)
        for c in one_page_comments:
            write_comment_to_db(c,cursor)
        connect.commit()
        print(f'第{pageno}页数据插入完成')
        time.sleep(1)
    connect.close()