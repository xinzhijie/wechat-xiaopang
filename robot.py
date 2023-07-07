# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
import csv
from wcferry import Wcf, WxMsg
import linecache
import random
from configuration import Config
from func_chatgpt import ChatGPT
from func_chengyu import cy
from func_http import Http
from func_news import News
from func_music import music
from job_mgmt import Job
import datetime
import schedule
import re
from urllib import parse

class Robot(Job):
    """个性化自己的机器人
    """
    wxidAll = []

    def __init__(self, config: Config, wcf: Wcf) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        self.chat = None
        chatgpt = self.config.CHATGPT
        if chatgpt:
            self.chat = ChatGPT(chatgpt.get("key"), chatgpt.get("api"), chatgpt.get("proxy"), chatgpt.get("prompt"))

    def clear_variables(self):
        self.wxidAll = []
        pass

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)

    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#|?|？])(.*)$", msg.content)
        # [('#', '天天向上')]
        if texts:
            flag = texts[0][0]
            text = texts[0][1]
            if flag == "#":  # 接龙
                if cy.isChengyu(text):
                    rsp = cy.getNext(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True
            elif flag in ["?", "？"]:  # 查词
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

        return status

    def toChouqian(self, msg: WxMsg) -> bool:
        if msg.sender in self.wxidAll:
            rsp = '每日最多一签！多抽不准哦！请明天再来吧！'
            self.sendTextMsg(rsp, msg.roomid, msg.sender)
        else:
            self.wxidAll.append(msg.sender)
            a = random.randrange(1, 381)
            line = linecache.getline(r'chouqian.csv', a)
            list = line.split("  ")
            line = ''
            for i in list:
                if i != '':
                    line = line + i + '\n ------------------\n'
            rsp = line
            self.sendTextMsg(rsp, msg.roomid, msg.sender)
        return True


    def toMusic(self, msg: WxMsg) -> bool:
        rsp = music.getMusic(msg.content)
        self.sendTextMsg(rsp, msg.roomid, msg.sender)
        return True

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        print(msg.content + "---")

        if not self.chat:  # 没接 ChatGPT，固定回复
            rsp = "你@我干嘛？"
        else:  # 接了 ChatGPT，智能回复
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            rsp = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))

        if rsp:
            if msg.from_group():
                self.sendTextMsg(rsp, msg.roomid, msg.sender)
            else:
                self.sendTextMsg(rsp, msg.sender)

            return True
        else:
            self.LOG.error(f"无法从 ChatGPT 获得答案")
            return False

    def sub(self, content: WxMsg):
        url = r'<url>(.*?)</url>'
        result = ""
        try:
            result = re.findall(url, content.content)[0]
        except Exception as e:
            result = content.content
        result = str(result).replace("amp;", "").replace("amp;", "").replace("amp;", "").replace("amp;", "").replace("amp;", "")
        query = parse.urlparse(result).query
        qq = "https://v.qq.com/x/cover/"
        if query != "":
            p = parse.parse_qs(query)
            result = qq + p['cid'][0] + "/" + p["vid"][0] + ".html"
        else:
            result = content.content
        return result

    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        content = "xx天气信息为："
        receivers = msg.roomid
        self.sendTextMsg(content, receivers, msg.sender)
        """
        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                if '蓉妹抽签' in msg.content:
                    self.toChouqian(msg)
                else:
                    self.toAt(msg)
            elif msg.content.startswith("#"):
                self.toMusic(msg)

            elif 'v.qq.com' in msg.content:
                result = self.sub(msg)
                # "https://v.qq.com/x/cover/mzc00200al2pm69/i0046m93twi.html"
                self.sendTextMsg("https://my-bucket-zlw1xqi-1257248029.cos-website.ap-guangzhou.myqcloud.com/?" + result, msg.roomid, msg.sender)
            # if msg.content == '抽签':                # 其他消息
            #     self.toChouqian(msg)

            return  # 处理完群聊信息，后面就不需要处理了

        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            # else:
            #     self.sendTextMsg("<a href=\"http://www.xmyeditor.com\">小蚂蚁编辑器</a>点击蓝字进入", msg.sender)

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：nofity@all
        """
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            wxids = at_list.split(",")
            for wxid in wxids:
                # 这里偷个懒，直接 @昵称。有必要的话可以通过 MicroMsg.db 里的 ChatRoom 表，解析群昵称
                ats += f" @{self.allContacts.get(wxid, '')}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三，微信规定需这样写，否则@不生效
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        schedule.every().day.at("23:59").do(self.clear_variables)
        while True:
            schedule.run_pending()
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = xml.attrib["scene"]
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def enableHTTP(self) -> None:
        """暴露 HTTP 发送消息接口供外部调用，不配置则忽略"""
        c = self.config.HTTP
        if not c:
            return

        home = "https://github.com/lich0821/WeChatFerry"
        http = Http(wcf=self.wcf,
                    title="API for send text",
                    description=f"Github: <a href='{home}'>WeChatFerry</a>", )
        Http.start(http, c["host"], c["port"])
        self.LOG.info(f"HTTP listening on http://{c['host']}:{c['port']}")

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        for r in receivers:
            self.sendTextMsg(news, r)
