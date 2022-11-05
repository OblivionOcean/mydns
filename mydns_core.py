import dns.resolver as getdns # DNS获取
import dns_db as ddb # 数据库
import yaml # 配置文件
import dnslib # DNS服务器
from dnslib.server import * # DNS服务器
import sys
import time # 时间
from pythonping import ping #ping
import _thread # 多线程
import json #解析JOSN

document = open('configs.yml', mode='r', encoding='utf-8').read()# 读取本地配置文件
configs = yaml.load(document, Loader=yaml.FullLoader)# yml解析配置文件
dnsls = []# dns函数库
for i in configs['dns']:# 遍历配置文件中的DNS
    dnsls.append({'function': getdns.Resolver(configure=False), 'data': i})# 将函数放入DNS库
    dnsls[len(dnsls) - 1]['function'].nameservers = i['dns'] # 设定DNS函数的IP


def set_NXDOMAIN(domain, type):# 快速返回NXDOMAIN
    return {'domain': domain + ':' + type, 'fast': [], 'all': [], 'NXDOMAIN': True} # 返回


def get_dns_on_network(domain, type):
    def bubbleSort(arr):# 冒泡排序
        n = len(arr)
        # 遍历所有数组元素
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j]['time'] > arr[j + 1]['time']:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
    ls = [] # 数据缓存
    for i in dnsls:
        try:
            r = i['function'].resolve(domain, type)
            for x in r.response.answer:
                for j in x.items:
                    ls.append({'value': j.to_text(), 'type': str(j.rdtype)[10:], 'teams': i['data']['name']})
        except:
            continue
    if ls != []:# 判断全部所以DNS是否有数据
        try:
            for i in ls:
                try:
                    i['time'] = ping(i['value']).rtt_avg_ms# 存入ping的时间
                except:
                    i['time'] = 10000# 如果域名不响应设置时间无穷大
            bubbleSort(ls) # 对返回值按时间排序（从小到大）
            ddb.update(domain + ':' + type, ls, ls[:int(configs['fastNumber'])], 'false') # 存入数据库
        except:
            ddb.update(domain + ':' + type, ls, ls[:int(configs['fastNumber'])], 'false')# 即使报错也存到数据库
    #else:
        #ddb.update(domain + ':' + type, [], [], 'true') # 将NXDOMAIN存入数据库
    print('\033[33m更新\033[0m', domain, type) # 提示


def get_dns(domain, type):
    start = time.time() # 开始计时
    ddbf = ddb.find(domain + ':' + type)# 查询域名
    if ddbf:# 是否有返回
        end = time.time()# 结束计时
        if ddbf['NXDOMAIN']:# 检查域名是否存在
            print('————————————————\n查询\033[31m失败\033[0m：\n域名：', domain, '\n类型：', type, '\n解析耗时：', (end - start),
                  '\n报错：', '没有记录', '\n方式：数据库获取\n————————————————')# 输出日志
        else:
            print('————————————————\n查询\033[32m成功\033[0m：\n域名：', domain, '\n类型：', type, '\n解析耗时：', (end - start),
                  '\n数据：', ddbf, '\n方式：数据库获取\n————————————————')# 输出日志
        return ddbf# 返回数据
    if configs['type'] == 'data' and not ddbf:# 检查运行模式如果是本地且未记录数据
            end = time.time()# 结束计时
            print('————————————————\n查询\033[32m成功\033[0m：\n域名：', domain, '\n类型：', type, '\n解析耗时：', (end - start),
                  '\n数据：', ddbf, '\n方式：数据库获取\n————————————————')# 输出日志
            return set_NXDOMAIN(domain, type)# 返回数据
    ls = []# 缓存
    try:
        res = getdns.Resolver(configure=False)# 配置DSN请求
        res.nameservers = configs['default']# 获取默认DNS
        r = res.resolve(domain, type)# 获取数据
        for x in r.response.answer:
            for j in x.items:
                ls.append({'value': j.to_text(), 'type': str(j.rdtype)[10:], 'teams': 'default'})#返回值加入缓存
        ddb.update(domain + ':' + type, ls, ls, 'false')# 将未记录的加入数据库
        end = time.time()# 结束计时
        print('————————————————\n查询\033[32m成功\033[0m：\n域名：', domain, '\n类型：', type, '\n解析耗时：', (end - start), '\n数据：',
              ({'domain': domain + ':' + type, 'fast': ls, 'all': [], 'NXDOMAIN': False}),
              '\n方式：实时获取\n————————————————')# 输出日志
        return {'domain': domain + ':' + type, 'fast': ls, 'all': [], 'NXDOMAIN': False}# 输出日志
    except Exception as e:
        if type == 'AAAA':# 如果请求的是IPv6，且报错则尝试IPv4值
            return get_dns(domain, 'A')
        else:
            end = time.time()# 结束计时
            print('————————————————\n查询\033[31m失败\033[0m：\n域名：', domain, '\n类型：', type, '\n解析耗时：', (end - start),
                  '\n报错：', e, '\n方式：实时获取\n————————————————')# 输出日志
            return set_NXDOMAIN(domain, type)# 返回NXDOMAIN


class TestResolver:
    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        qtype = request.q.qtype
        if qtype == 'HTTPS':
            qtype = 'A'
        dns_answer = get_dns(str(qname), str(dnslib.QTYPE[qtype]))
        if not dns_answer['NXDOMAIN']:
            for i in dns_answer['fast']:
                if type(i) == str:
                    f = json.loads(i)
                else:
                    f = i
                answer = RR(rname=qname, ttl=64, rdata=dnslib.A('0.0.0.0'))
                if f["type"] == 'A':
                    answer = RR(rname=qname, ttl=64, rdata=dnslib.A(f['value']))
                elif f["type"] == 'AAAA':
                    answer = RR(rname=qname, ttl=240, rdata=dnslib.AAAA(f['value']))
                elif f["type"] == 'CNAME':
                    a = get_dns(f['value'], 'A')
                    if not a['NXDOMAIN']:
                        if type(a['fast'][0]) == str:
                            f = json.loads(a['fast'][0])
                        else:
                            f = a['fast'][0]
                        try:
                            if f['type'] == 'A':
                                answer = RR(rname=qname, ttl=240,
                                            rdata=dnslib.A(f['value']))
                            else:
                                continue
                        except Exception as e:
                            print(f['value'])
                reply.add_answer(answer)
        else:
            ## 未匹配到时的返回值
            reply.header.rcode = getattr(RCODE, 'NXDOMAIN')
        return reply


def main():
    resolver = TestResolver()
    logger = DNSLogger(prefix=False)
    dns_server = DNSServer(resolver, port=53, address='0.0.0.0', logger=logger)
    dns_server.start_thread()
    print('''
————————————————————————————————————————————————————
        __  ___      ____  _   _______
       /  |/  /_  __/ __ \/ | / / ___/
      / /|_/ / / / / / / /  |/ /\__ \ 
     / /  / / /_/ / /_/ / /|  /___/ /
    /_/  /_/\__, /_____/_/ |_//____/ 
           /____/
           
开发者：Fgaoxing
版本：1.0.0
提示：DNS已启动，如果未设置DNS，请把DNS IPv4改为\033[34m127.0.0.1\033[0m，IPv6改为\033[34m::1\033[0m
————————————————————————————————————————————————————
           ''')
    try:
        while True:
            time.sleep(60)
            sys.stderr.flush()
            sys.stdout.flush()
    except KeyboardInterrupt:
        sys.exit(0)


def uptmp():
    while True:
        if configs['type'] == 'dns':
            for j in set(ddb.get_ls()):
                get_dns_on_network(j.split(':')[0], j.split(':')[1])# 要求更新
        time.sleep(configs['timeout'])


if __name__ == '__main__':
    _thread.start_new_thread(uptmp, ())
    main()