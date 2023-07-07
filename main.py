#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import signal

from wcferry import Wcf

from configuration import Config
from robot import Robot
import requests
import json


def weather_report(robot: Robot) -> None:
    """模拟发送天气预报
    """

    # 获取接收人
    receivers = ["35014668951@chatroom"]

    # 获取天气，需要自己实现，可以参考 https://gitee.com/lch0821/WeatherScrapy 获取天气。
    # daily.fxDate，今天白天，daily.textDay，偏南daily.windDirDay+daily.windScaleDay级左右，风速为daily.windSpeedDay，今天夜里，daily.textNight，偏南daily.windDirNight+daily.windScaleNight级左右，风速为daily.windSpeedNight。总降水量：daily.precip，紫外线强度：daily.uvIndex。气温:daily.tempMin～daily.tempMax℃。
    url = "https://devapi.qweather.com/v7/weather/3d?location=101010100&key=1d5b7aa46cea4d039c2aa14b4d191728"
    rsp = requests.get(url=url, headers=None, data=None)
    daily = json.loads(rsp.text)["daily"][0]
    result = daily["fxDate"] + "，北京，气温:" + daily["tempMin"]+"～"+daily["tempMax"]+ "℃。" +"总降水量："+daily["precip"]+"，紫外线强度："+daily["uvIndex"]+"。"+"今天白天，"+daily["textDay"]+"，"+daily["windDirDay"]+daily["windScaleDay"]+"级左右，风速为"\
             +daily["windSpeedDay"]+"。今天夜里，"+daily["textNight"]+"，偏南"+daily["windDirNight"]+daily["windScaleNight"]\
             +"级左右，风速为"+daily["windSpeedNight"] + "。"
    # print(result)
    report = result

    for r in receivers:
        robot.sendTextMsg(report, r)
        # robot.sendTextMsg(report, r, "nofity@all")   # 发送消息并@所有人


def weibo_report(robot: Robot) -> None:
    """weibo
    """

    # 获取接收人
    receivers = ["35014668951@chatroom"]

    url = "https://apis.tianapi.com/weibohot/index?key=532a7310e75b7deab5f95144c0760041"
    rsp = requests.get(url=url, headers=None, data=None)
    daily = json.loads(rsp.text)["result"]["list"]
    result = ""
    for i in range(len(daily)):
        if i < 8:
            result += str(i + 1) + "." + daily[i]["hotword"] + "。\n"
    result = "微博熱搜榜：\n" + result
    print(result)
    report = result

    for r in receivers:
        robot.sendTextMsg(report, r)
    #     # robot.sendTextMsg(report, r, "nofity@all")   # 发送消息并@所有人


def main():
    config = Config()
    wcf = Wcf(debug=True)

    def handler(sig, frame):
        wcf.cleanup()  # 退出前清理环境
        exit(0)

    signal.signal(signal.SIGINT, handler)

    robot = Robot(config, wcf)
    robot.LOG.info("正在启动机器人···")

    # 机器人启动发送测试消息
    robot.sendTextMsg("机器人启动成功！", "filehelper")

    # 暴露 HTTP 接口供发送消息，需要在配置文件中取消 http 注释
    # 接口文档：http://localhost:9999/docs
    # 访问示例：
    # 1. 浏览器访问：http://localhost:9999/send?msg=hello%20world&receiver=filehelper
    # 2. curl -X 'GET' 'http://localhost:9999/send?msg=hello%20world&receiver=filehelper' -H 'accept: application/json'
    robot.enableHTTP()

    # 接收消息
    robot.enableRecvMsg()

    # 每天 7 点发送天气预报
    robot.onEveryTime("08:00", weather_report, robot=robot)

    # 每天 7:30 发送新闻
    robot.onEveryTime("08:01", weibo_report, robot=robot)

    # 让机器人一直跑
    robot.keepRunningAndBlockProcess()


if __name__ == "__main__":
    main()