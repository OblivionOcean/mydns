import sqlite3
import time

def get_ls():
    conn = sqlite3.connect("dns.db", timeout=10, check_same_thread=False)
    c = conn.cursor()
    cursor = c.execute("SELECT domain from dns")
    ls = []
    for row in cursor:
        ls.append(row[0])
    conn.commit()
    conn.close()
    return ls

def list_join(list, x):
    a = ''
    for i in list:
        a += str(i) + x
    return a[:-3].replace("'",'"')


def find(domain):
    conn = sqlite3.connect("dns.db", timeout=10, check_same_thread=False)
    c = conn.cursor()
    c.execute("select * from dns where domain='" + domain + "'")
    res = c.fetchall()
    if len(res) >= 1:
        res = res[0]
        if res[1]=='':
            all=[]
        elif '/,/' in res[1]:
            all = res[1].split('/,/')
        else:
            all = [res[1]]
        if res[2]=='':
            fast=[]
        elif '/,/' in res[2]:
            fast = res[2].split('/,/')
        else:
            fast=[res[2]]
        if res[3] == 'false':
            NXDOMAIN = False
        else:
            NXDOMAIN = True
        conn.commit()
        conn.close()
        return {'domain': res[0], 'all': all, 'fast': fast, 'NXDOMAIN': NXDOMAIN, 'time': res[4]}



def update(domain, all, fast, NXDOMAIN):
    conn = sqlite3.connect("dns.db", timeout=10, check_same_thread=False)
    c = conn.cursor()
    all = list_join(all, '/,/')
    fast = list_join(fast, '/,/')
    if find(domain)==None:
        c.execute("INSERT INTO dns (domain,'all',fast,NXDOMAIN,time) VALUES ('" + domain + "','" + all + "','" + fast + "','" + str(NXDOMAIN) + "'," + str(time.time()) + ")")
    else:
        c.execute("UPDATE dns set 'all'='" + all + "' where domain='" + domain + "'")
        c.execute("UPDATE dns set 'fast'='" + fast + "' where domain='" + domain + "'")
        c.execute("UPDATE dns set 'NXDOMAIN'='" + str(NXDOMAIN) + "' where domain='" + domain + "'")
        c.execute("UPDATE dns set 'time'=" + str(time.time()) + " where domain='" + domain + "'")
    conn.commit()
    conn.close()