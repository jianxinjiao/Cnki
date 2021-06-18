import os
import re
import base64

import pandas as pd
from bs4 import BeautifulSoup
from html.parser import HTMLParser


class MyHTMLParser(HTMLParser):
    res_list = list()
    value = 0
    label_list = ['div', 'br', 'p', 'title', 'ul', 'li', 'table', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.res_list.append([self.value, 'data', '\n'])
        else:
            self.value += 1
            self.res_list.append([self.value, 'starttag', tag])

    def handle_endtag(self, tag):
        self.res_list.append([self.value, 'endtag', tag])
        self.value -= 1

    def handle_data(self, data):
        data = data.replace(' ', '')
        if data:
            self.res_list.append([self.value, 'data', data])

    def get_join_str(self):
        _res_str = str()
        _res = self.res_list  # 临时变量
        for i in range(len(_res)):
            if i == 0 or i == len(_res) - 1:
                continue
            tree_label = _res[i][1]
            tree_value = _res[i][2]

            if tree_label == 'endtag' and tree_value in self.label_list:
                if _res[i-1][1] == 'endtag' and _res[i-1][2] in self.label_list:
                    pass
                else:
                    _res_str += '\n'

            if tree_label == 'data':
                _res_str += tree_value
        if not _res_str.replace('\n', '').replace(' ', ''):
            _res_str = ''
        return _res_str


def remove_html_label(html_str: str):
    re_script = re.compile('<script.*?</script>', re.I)
    re_style = re.compile('<style.*?</style>', re.I)
    re_style = re.compile('<iframe.*?</iframe>', re.I)
    re_notes = re.compile('<!--.*?-->', re.I)
    re_span = re.compile('<span style="display:none".*?</span>', re.I)
    # 格式处理
    html_str = html_str.replace('\n', '')

    new_html_str = re_script.sub('', html_str)
    new_html_str = re_style.sub('', new_html_str)
    new_html_str = re_notes.sub('', new_html_str)
    new_html_str = re_span.sub('', new_html_str)

    return new_html_str


def get_text_str(html_str: str):
    html_str = remove_html_label(html_str)
    parser = MyHTMLParser()
    parser.res_list = list()
    parser.value = 0
    parser.feed(html_str)
    html_text = parser.get_join_str()

    return html_text


def get_table_list(table_str: str):
    soup = BeautifulSoup(table_str, 'lxml')
    table_trs = soup.findAll('tr')
    tr_val_list = list()  # [*, *, ...]
    for tr_i in range(len(table_trs)):
        table_tds_ths = table_trs[tr_i].findAll(['td', 'th'])
        # if len(table_tds_ths) == 0:
        #     continue
        td_th_val_list = list()
        for td_th_i in range(len(table_tds_ths)):

            val = table_tds_ths[td_th_i].getText()
            colspan = table_tds_ths[td_th_i].get('colspan')
            rowspan = table_tds_ths[td_th_i].get('rowspan')

            if rowspan:
                try:
                    rowspan = int(rowspan)
                except ValueError:
                    rowspan = 1
                insert_val = [val, int(rowspan)]
            else:
                insert_val = [val, 1]

            if colspan:
                try:
                    colspan = int(colspan)
                except ValueError:
                    colspan = 1
                td_th_val_list += [insert_val] * int(colspan)
            else:
                td_th_val_list.append(insert_val)
        if len(td_th_val_list) == 0:
            return ''
        if tr_i == 0:
            tr_val_list.append(td_th_val_list)
        else:
            td_th_val_list.reverse()
            res_td_th_list = list()
            for i in tr_val_list[tr_i - 1]:
                if i[1] > 1:
                    res_td_th_list.append([i[0], i[1] - 1])
                else:
                    try:
                        td_th_val = td_th_val_list.pop()
                    except IndexError:
                        continue
                    res_td_th_list.append(td_th_val)

            tr_val_list.append(res_td_th_list)

    res_list = [[y[0] for y in x] for x in tr_val_list]

    return res_list


def panduanFlag(table_val):
    sign = ['\xa0', '\u3000', '']
    table_val = list(set(table_val))
    for x in table_val:
        if x not in sign:
            return True
    return False


def split_table(table_list):
    flag_list = [0]
    table_start = 0
    table_end = 0
    for i in range(len(table_list)):
        if 1 not in flag_list and len(set(table_list[i])) != 1:
            flag_list.append(1)
            table_start = i
        if len(set(table_list[i])) == 1 and 1 in flag_list:
            table_end = i
            break
    if table_end == 0:
        table_end = len(table_list)
    text_start_list = table_list[:table_start]  # [] / [[], []]
    table = table_list[table_start: table_end]  # [[], []]
    text_end_list = table_list[table_end:]  # [] / [[], []]
    col_len = len(table[0])
    fill_list = [''] * col_len
    text_start_list = [x[0] for x in text_start_list if len(x) > 0 and x[0].replace(' ', '').replace('\n', '').replace('\xa0', '')]
    if text_start_list:
        text_start_list = text_start_list + [''] * (col_len - len(text_start_list))
    else:
        text_start_list = fill_list
    table.insert(0, fill_list)

    text_end_list = [x[0] for x in text_end_list if len(x) > 0 and x[0].replace(' ', '').replace('\n', '')]
    if text_end_list:
        text_end_list = [[x] + [''] * (col_len - 1) for x in text_end_list]
    else:
        text_end_list = fill_list
    # res_list = [text_start_list] + table + [text_end_list]
    res_list = [text_start_list] + table

    return res_list


def handle_table_list(table_list: list):
    table_list = [x for x in table_list if panduanFlag(x)]
    if len(table_list) == 0:
        return ''
    if len(table_list[0]) == 1:
        res = '。\n'.join(x[0] for x in table_list if len(x) != 0)
    elif len(table_list[0]) == 2:
        flag = False
        for x in table_list:
            a = x[-1].strip()
            if len(a) > 0 and a[-1].isdigit():
                flag = True
                break
        res = split_table(table_list) if flag else '。\n'.join([','.join(x) for x in table_list])
    else:
        res = split_table(table_list)
    return res


def get_title_list(text_str: str):
    text_list = text_str.split('\n')
    text_list.reverse()
    unit = ''
    for text in text_list:
        title = text.strip(' ').replace('\xa0', '').replace('\t', '').replace('\u3000', '')
        if len(title) > 0 and title.startswith('单位'):
            unit = title
        elif len(title) > 0:
            title = title.replace(" ", "##")[:50]
            if len(unit) > 0:
                title = title + '&&' + unit
            return title
    return ''


def extract_txt_table(html_text):
    html_str = remove_html_label(html_text)
    soup = BeautifulSoup(html_str, 'lxml')
    table_ys = soup.findAll('table')
    if len(table_ys) == 0:
        txt_str = get_text_str(html_str)
        return txt_str, []
    table_list = list()
    for table in table_ys:
        if len(re.findall('</table>', str(table), re.S)) == 1:
            table_list.append(str(table))
    soup_str = str(soup)
    html_list = list()
    for i in range(len(table_list)):
        split_list = soup_str.split(table_list[i])
        other_str = split_list[0]
        soup_str = split_list[1]
        if len(split_list) > 2:
            soup_str = f'{table_list[i]}'.join(split_list[1:])
        html_list += [get_text_str(other_str), get_table_list(table_list[i])]
        if i == len(table_list)-1:
            html_list.append(get_text_str(soup_str))
    html_list = [x for x in html_list if x]  # 去掉空值
    html_list = [x if type(x) == str else handle_table_list(x) for x in html_list]
    table_res = list()
    for i in range(len(html_list)):
        if i == 0:
            if type(html_list[i]) == str:
                type_flag = 0
            else:
                type_flag = 1
            table_res.append(html_list[i])
            continue
        if type(html_list[i]) == str:
            if type_flag == 0:
                table_res[-1] = table_res[-1] + '\n' + html_list[i]
            else:
                table_res.append(html_list[i])
                type_flag = 0
        else:
            table_res.append(html_list[i])
            type_flag = 1
    txt_list, table_list = [], []
    for i in range(len(table_res)):
        value = table_res[i]
        if isinstance(value, list):
            if len(value[0][0]) > 0:
                title_str = value[0][0].strip().replace(' ', '_')
            else:
                if i != 0 and isinstance(table_res[i -1], str):
                    title_str = get_title_list(table_res[i - 1])
                else:
                    title_str = '未找到标题'
            if len(value) > 2 and len(value[0]) > 0:
                value_list = [[title_str, ''*(len(value[0])-1)]] + value[2:]
                df = pd.DataFrame(value_list)
                filePath = r'./data/table.xlsx'
                df.to_excel(filePath, header=None, index=None)
                with open(filePath, 'rb') as f:
                    table_str = f.read()
                encodestr = base64.b64encode(table_str)
                table_br = encodestr.decode()
                if os.path.exists(filePath):
                    os.remove(filePath)
                table_list.append({"title": title_str, "content": table_br})
        elif isinstance(value, str):
            value = value.replace(' ', '').replace('。\n', '\n').replace('\n', '。\n')
            txt_list.append(value)
    txt_str = '\n'.join(txt_list).replace('\n。', '')

    return txt_str, table_list
