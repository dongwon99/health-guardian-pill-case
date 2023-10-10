#!/usr/bin/python
# -*- coding: utf-8 -*-

#import
import requests
import urllib
import json
import time
import datetime
import grovepi
import os
import grove_rgb_lcd as lcd
import RPi.GPIO as GPIO
from gtts import gTTS
from flask import Flask
from flask import render_template
from threading import Thread
import zFinal_detector as cam


#사용자로부터 약 종류, 알람 날짜 입력
def inputAlarm(drugs, todayRecords):
	f = open("test", 'r')
	n = 0
	
	while True:
		t = f.readline().split()
		if not t: break;
		
		size = len(t)
		for i in range(size):
			drugs[n][i] = t[i]
		n = n+1

	f.close()
	return n	
#당일 알려줘야하는 약 확인(요일)
def getTodayList(drugsToday, drugs, num):
	w = ["월", "화", "수", "목", "금", "토", "일"]
	week = datetime.datetime.today().weekday()
	
	t = 0
	for i in range(num):
		for j in drugs[i][1]:
			if(w[week] == j):
				drugsToday[t] = drugs[i]
				t = t+1
	return t
#현재시간 반환
def now():
	nowtime = datetime.datetime.now()
	nowtime = str(nowtime).split(" ")
	nowtime = nowtime[1].split('.')
	nowtime = nowtime[0].split(':')
	return (nowtime[0] + ":" + nowtime[1])
#복용해야하는 약 종류를 스피커로 출력
def drugsSpeak(drugs):
	tts = gTTS(text = drugs, lang='ko')
	tts.save("takeMedicine.mp3")
	os.system("mpg321 takeMedicine.mp3")
#복용 후 복용 정보를 저장할 주소 반환(시간)
def getSaveTime(currentTime):
	saveTime = currentTime.split(':')[0]
	if(int(saveTime) >= 4 and int(saveTime) <= 11):
		saveTime = 0
	elif(int(saveTime) >= 12 and int(saveTime) <= 17):
		saveTime = 1
	else:
		saveTime = 2
	return saveTime
#라인 메세지 전송
def sendText(msg):
	url = 'https://notify-api.line.me/api/notify'
	payload = 'message=' + msg
	headers = {
		'Content-Type' : "application/x-www-form-urlencoded",
		'Cache-Control' : "no-cache",
		'Authorization' : "Bearer " + key
	}
	response = requests.request("POST", url, data=payload, headers=headers)
	responseJson = json.loads(response.text)
	return responseJson
#알람 멈추기
def stopAlarm():
	grovepi.digitalWrite(led, 0)
	grovepi.digitalWrite(buzzer,0)
	lcd.setText('')
	lcd.setRGB(0,0,0)
	


#라인 key
key = '29SvKqRmEX0sUsiYlUsQ7WArcUPMwMWCp74ccEzWZ9Y'

#I/O 장치 세팅 pin : 모터
ultra = 3
led = 2
buzzer = 4

grovepi.pinMode(buzzer, "OUTPUT")
grovepi.pinMode(led, "OUTPUT")

GPIO.setmode(GPIO.BCM)


app = Flask(__name__)



#전체 약 종류/ 당일 복용해야하는 약 종류 리스트
drugs = [[0 for _ in range(5)] for _ in range(4)]
drugsToday = [[0 for _ in range(5)] for _ in range(4)]

#약 복용 정보(일주일치)/ 요일 list/ 케이스 a~d
todayRecords = {
	'mon': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'tue': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'wen': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'tur': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'fri': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'sat': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]},
	'sun': {'a': [False, False, False], 'b' : [False, False, False], 'c' : [False, False, False], 'd' : [False, False, False]}
	}
mon = ['mon', 'tue', 'wen', 'tur', 'fri', 'sat', 'sun']
a = ['a','b','c','d']	


temp = 0				#당일 복용해야하는 약의 개수
takeNum = [0,0,0,0]		#당일 복용해야하는 약의 인덱스(drugs의 주소)
take = False			#약을 복용할 시간이 되었는지 여부
takeConfirm = False		#약을 복용하였는지
week = 0				#요일 인덱스


#전체 약 종류, 약 개수 확인
drugsNum = inputAlarm(drugs,todayRecords)
drugsTodayNum = 0

#알람 함수
def work():
	while True:
		global temp, take, takeConfirm, camOn, week
		
		#오늘 복용해야하는 약 List, 개수 반환
		drugsTodayNum = getTodayList(drugsToday, drugs, drugsNum)
		#요일 확인(숫자로 0:월, 1:화)
		week = datetime.datetime.today().weekday()
		
		while True:
			#시간 확인
			currentTime = now()
			if(currentTime == "00:01"):
				break
			
			#복용 시간 확인(알람)
			for i in range(drugsTodayNum):                          
				for j in drugsToday[i]:
					#현재시간과 입력받은 알람 시간이 맞다면
					if(j == currentTime):
						#복용해야하는 약의 주소 저장
						takeNum[temp] = i
						temp = temp+1
						#복용해야함
						take = True
						
			#복용해야하는 약이 있다면
			if(take):
				take = False
				begin = time.time()
				
				#복용 시간대 확인(아침,점심,저녁)
				saveTime = getSaveTime(currentTime)
				
				#복용 약 내용 알림
				s = ""
				for i in range(temp):
					s = s + " " +drugsToday[takeNum[i]][0]	
				s = s + "를 먹을 시간입니다."
				
				print(s)
				lcd.setRGB(0,255,0)
				lcd.setText("Take Your Medicines")
			
				#실제 복용 확인
				try:
					#복용 알람 울리기
					grovepi.digitalWrite(led, 1)
					drugsSpeak(s)
					grovepi.digitalWrite(buzzer,1)
					takeConfirm = cam.detect(begin, takeConfirm)	
														
				except KeyboardInterrupt:
					exit
				except IOError:
					print ("Error")
					exit
				
				if(takeConfirm):
					#복용을 하러 온 경우
					print("take ok")
					#복용 후 남은 개수 확인
					dis = grovepi.ultrasonicRead(ultra)
					if dis >= 4:
						sendText('lack of medicine')
				else:
					#오지 않은 경우 라인 메세지 발송
					print("not take")
					print(sendText("did not take medicine!!!"))
				stopAlarm()
	
				#복용 정보 등록
				for i in range(temp):
					#mon : 요일 정보가 담긴 list
					#week : 요일 주소(0:월, 1:화)
					#a = [a,b,c,d] 케이스 a~d
					#takeNum : 복용해야하는 약의 주소가 있음(0 : n번째 약, 1 : j번째 약..)
					#saveTime : 아침, 점심, 저녁
					todayRecords[mon[week]][a[takeNum[i]]][saveTime] = takeConfirm
				time.sleep(40)
				
			print("sleep..")
			time.sleep(1)
			
				
			
			
			


@app.route("/")
def main():
	
	return render_template('main.html', **todayRecords)
	
if __name__ == '__main__':
	th1 = Thread(target=work, args=())
	th2 = Thread(target=app.run, args=('0.0.0.0', 8888, False))
	th1.start()
	th2.start()
	th1.join()
	th2.join()

