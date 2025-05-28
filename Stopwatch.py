from RPLCD.i2c import CharLCD
import threading
import signal
import sys
import RPi.GPIO as GPIO
import time
def second_to_time(sec):
    t_second = sec % 60
    t_min = (sec//60)%60
    t_hour = sec // 3600
    return (t_hour,t_min,t_second)

def time_to_second(time_list:list):
    second = time_list[0] + time_list[1]*60+time_list[2]*3600
    return second
Cr = (
    0x00,
    0x1B,
    0x1B,
    0x04,
    0x0E,
    0x0A,
    0x00,
    0x00
)
InverteCr = (
    0x1F,
    0x04,
    0x04,
    0x1B,
    0x11,
    0x15,
    0x1F,
    0x1F
)
Y = (
    0x00,
    0x11,
    0x0A,
    0x04,
    0x04,
    0x04,
    0x04,
    0x04
)
Z = (
    0x00,
    0x1F,
    0x02,
    0x04,
    0x08,
    0x10,
    0x1F,
    0x00
)
BUZZER = 26
LIGHT = [18,23,24,25,8]
SW1 = 21
SW2 = 20
time_index = 1
time_list = [0,0,0]
second_cnt = 0
second_tot = 0
TIME_SET = 0.5
lcd = CharLCD("PCF8574",0x27)
begin_timer_flag = False
stop_timer_flag = False
end_timer_flag = False
refresh_flag = False
light_flag = False
buzzer_tag = 0
start_tag = 0
set_time_flag = False
def init():
    global time_list,time_index,second_cnt,second_tot,begin_timer_flag,stop_timer_flag,end_timer_flag
    global refresh_flag,set_time_flag,start_tag,light_flag,buzzer_tag
    time_index = 1
    buzzer_tag = 0
    time_list = [0,0,0]
    second_cnt = 0
    start_tag = 0
    second_tot = 0
    begin_timer_flag = False
    stop_timer_flag = False
    light_flag = False
    end_timer_flag = False
    refresh_flag = False
    set_time_flag = False
def SW1_press_callback(channel):
    global begin_timer_flag,set_time_flag,time_index,stop_timer_flag
    if set_time_flag:
        time_index += 1
        if time_index == 4:
            time_index = 1
            set_time_flag = False
        return
    if not begin_timer_flag:
        set_time_flag = True
    #按钮暂停
    if begin_timer_flag:
        stop_timer_flag = not stop_timer_flag
def SW2_press_callback(channel):
    global begin_timer_flag,set_time_flag,second_cnt,time_list,start_tag
    if set_time_flag:
        if(time_index<3):
            time_list[time_index-1] = (time_list[time_index-1] + 1 )%60
        else:
            time_list[time_index-1] = (time_list[time_index-1] + 1 )%24
        second_cnt  = time_to_second(time_list)
        return
    if not begin_timer_flag:
        start_tag = second_tot
        begin_timer_flag = True
    else:
        init()
def timer_interrupt():
    global refresh_flag,second_tot
    refresh_flag = True
    second_tot += 1
    timer = threading.Timer(TIME_SET,timer_interrupt)
    timer.start()
def signal_handler(sig,frame):
    GPIO.cleanup()
    sys.exit(0)
timer_interrupt()
def print_time(sec):
    lcd.cursor_pos = (0,3)
    ans_time = second_to_time(sec)
    hour_string = str(ans_time[0]//10) + str(ans_time[0]%10)
    min_string = str(ans_time[1]//10) + str(ans_time[1]%10)
    sec_string = str(ans_time[2]//10) + str(ans_time[2]%10)
    lcd.write_string(hour_string+":"+min_string+":"+sec_string)
    sys.stdout.write('\r' +hour_string+":"+min_string+":"+sec_string)
try:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER,GPIO.OUT)
    GPIO.setup(20,GPIO.IN,pull_up_down = GPIO.PUD_UP)
    GPIO.setup(21,GPIO.IN,pull_up_down = GPIO.PUD_UP)
    GPIO.setup(LIGHT,GPIO.OUT)
    GPIO.add_event_detect(SW1,GPIO.FALLING,callback = SW1_press_callback,bouncetime = 200)
    GPIO.add_event_detect(SW2,GPIO.FALLING,callback = SW2_press_callback,bouncetime = 200)
    p = GPIO.PWM(BUZZER,50)
    lcd.create_char(0,Y)
    lcd.create_char(1,Z)
    lcd.create_char(2,Cr)
    lcd.create_char(3,InverteCr)
    signal.signal(signal.SIGINT,signal_handler)
    while True:
        if refresh_flag:
            refresh_flag = False
            lcd.clear()
            print_time(second_cnt)
            lcd.cursor_pos = (0,0)
            if second_tot % 2 == 0:
                lcd.write_string("\x02")
            else:
                lcd.write_string("\x03")
            lcd.cursor_pos = (0,1)
            if second_tot % 2 == 0:
                lcd.write_string("\x00")
            else:
                lcd.write_string("\x01")
            #还未开始
            if not begin_timer_flag:
                #设置模式
                if set_time_flag:
                    lcd.cursor_pos = (1,0)
                    lcd.write_string("SW1:MODE SW2:ADD")
                    if time_index == 1:
                        if second_tot % 2 == 0:
                            lcd.cursor_pos = (0,13)
                            lcd.write_string("SEC")
                    elif time_index == 2:
                        if second_tot % 2 == 0:
                            lcd.cursor_pos = (0,13)
                            lcd.write_string("MIN")
                    elif time_index == 3:
                        if second_tot % 2 == 0:
                            lcd.cursor_pos = (0,14)
                            lcd.write_string("HR")
                #菜单模式
                else:
                    lcd.cursor_pos = (1,0)
                    lcd.write_string("SW1:SET SW2:RUN")
            #开始计时
            if begin_timer_flag:
                if second_cnt == 0:
                    if buzzer_tag == 0:
                        buzzer_tag = second_tot
                    GPIO.output(LIGHT,second_cnt%2)
                    if (second_tot - buzzer_tag) % 2 == 0 and (second_tot - buzzer_tag)/2 <= 5:
                        p.ChangeDutyCycle(10+9*(second_tot - buzzer_tag))
                        GPIO.output(BUZZER,GPIO.HIGH)
                        time.sleep(0.1)
                        GPIO.output(BUZZER,GPIO.LOW)
                        time.sleep(0.1)
                        GPIO.output(BUZZER,GPIO.HIGH)
                        time.sleep(0.1)
                        GPIO.output(BUZZER,GPIO.LOW)
                    end_timer_flag = True
                    lcd.cursor_pos = (1,1)
                    lcd.write_string("SW2 TO RESET")
                    continue
                lcd.cursor_pos = (1,0)
                lcd.write_string("SW1:STOP SW2:RES")
                if (not stop_timer_flag) and (second_tot - start_tag) % 2 == 0:
                    second_cnt -= 1
                    light_flag = not light_flag
                    GPIO.output(LIGHT,light_flag)
                if stop_timer_flag:
                    GPIO.output(LIGHT,GPIO.LOW)
                    if second_tot % 2 == 0:
                        lcd.clear()
                        lcd.cursor_pos = (1,0)
                        lcd.write_string("SW1:STOP SW2:RES")
                

except Exception as e:
    print(e)
    GPIO.output(BUZZER,GPIO.LOW)
    GPIO.cleanup()
    lcd.clear()
    lcd.cursor_pos = (1,3)
    lcd.write_string(" THE END ")
    