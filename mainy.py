from phew import access_point, connect_to_wifi, is_connected_to_wifi, dns, server
from phew.template import render_template
import json
import machine
import os
import utime
import _thread
import gc

AP_NAME = "Shorty's Customs"
AP_DOMAIN = "shortyscustoms.net"
AP_TEMPLATE_PATH = "ap_templates"
APP_TEMPLATE_PATH = "app_templates"
WIFI_FILE = "wifi.json"
IP_ADDRESS = "ip.json"
SCHEDULES = "schedules.json"
TOGGLE_SCHEDULE = "toggle.json"
WIFI_MAX_ATTEMPTS = 3


global schedule_toggle
schedule_toggle = None

onboard_led = machine.Pin("LED", machine.Pin.OUT)

def format_time(time_i, format_hour):     
        if format_hour == 'AM':
            if time_i == 12:
                times = 0
                return times
            else:
                return time_i
        elif format_hour == 'PM':
            if not time_i == 12:
                times = time_i + 12
                return times
            else:
                return time_i

def find_time(time, format_hour):
    find_i = time.find(':')
    if find_i == 1:
        time_i = int(time[0])
        time_format = format_time(time_i, format_hour)
        return time_format
    elif find_i == 2:
        time_i = int(time[0:2])
        time_format = format_time(time_i, format_hour)
        return time_format
    
    
def schedule_light():
    gc.collect()
    print("memory")
    print(gc.mem_free())
    start = 's'
    end = 'e'
    format_hour = 'ampm'
    os.stat(SCHEDULES)
    with open(SCHEDULES) as f:
        schedule_database = json.load(f)
        while True:
            f.close()
            gc.collect()
            print('going into db')
            print(gc.mem_free())
            utime.sleep(5)
            os.stat(SCHEDULES)
            with open(SCHEDULES) as f:
                schedule_database = json.load(f)
                for s_keys in schedule_database.keys():
                    utime.sleep(1)
                    current_time = utime.localtime()
                    print("test 1")
                    s_key = int(s_keys[1])
                    if s_key == current_time[6]:
                        if s_keys[0] == start:
                            if not schedule_database[s_keys] == 'Off':
                                s_key_sday = str(s_keys[1])
                                s_key_eday = end + s_key_sday
                                print("start on")
                                if not schedule_database[s_key_eday] == 'Off':
                                    print("start off")
                                    time_start_f = start + s_key_sday + format_hour
                                    time_end_f = end + s_key_sday + format_hour
                                    check_start_time = find_time(schedule_database[s_keys], schedule_database[time_start_f])
                                    check_end_time = find_time(schedule_database[s_key_eday], schedule_database[time_end_f])
                                    if check_start_time == current_time[3]:
                                        print("found right time: test 2")
                                        if onboard_led.value() == 0:
                                            print("light on")
                                            onboard_led.value(1)
                                    elif check_end_time == current_time[3]:
                                        if onboard_led.value() == 1:
                                            print("test 3")
                                            onboard_led.value(0)
                                            print("turn light off")
                                            f.close()
                                            schedule_light()
                                   
                                            
                                    
                                    
                                            
def machine_reset():
    utime.sleep(1)
    print("Resetting...")
    machine.reset()

def setup_mode():
    print("Entering setup mode...")
    
    def ap_index(request):
        if request.headers.get("host").lower() != AP_DOMAIN.lower():
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN.lower())

        return render_template(f"{AP_TEMPLATE_PATH}/index.html")

    def ap_configure(request):
        print("Saving wifi credentials...")

        with open(WIFI_FILE, "w") as f:
            json.dump(request.form, f)
            f.close()

        # Reboot from new thread after we have responded to the user.
        _thread.start_new_thread(machine_reset, ())
        return render_template(f"{AP_TEMPLATE_PATH}/configured.html", ssid = request.form["ssid"])
        
    def ap_catch_all(request):
        if request.headers.get("host") != AP_DOMAIN:
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN)

        return "Not found.", 404

    server.add_route("/", handler = ap_index, methods = ["GET"])
    server.add_route("/configure", handler = ap_configure, methods = ["POST"])
    server.set_callback(ap_catch_all)

    ap = access_point(AP_NAME)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)


def display_ip():
    print("Entering display mode")
    
    def ap_index(request):
        if request.headers.get("host").lower() != AP_DOMAIN.lower():
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN.lower())
        
        with open(IP_ADDRESS) as f:
            ip_address_status = json.load(f)
            ip = ip_address_status["ipa"]
            
        return render_template(f"{AP_TEMPLATE_PATH}/display_index.html", ip_num = ip)
    
    
    def app_restart(request):
        machine_reset()
        return "OK"
    
    
    def ap_catch_all(request):
        if request.headers.get("host") != AP_DOMAIN:
            return render_template(f"{AP_TEMPLATE_PATH}/redirect.html", domain = AP_DOMAIN)

        return "Not found.", 404
    
    server.add_route("/", handler = ap_index, methods = ["GET"])
    server.add_route("/reset", handler = app_restart, methods = ["GET"])
    server.set_callback(ap_catch_all)
    
    ap = access_point(AP_NAME)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)

def application_mode():
    print("Entering application mode.")
    with open(TOGGLE_SCHEDULE) as f:
        toggle = json.load(f)
        if toggle['schedule_toggle'] == 'on':
            _thread.start_new_thread(schedule_light, ())
            
    
    

    def app_index(request):
        save_alert = None
        light_state = None
        
        # opens toggle json file to update toggle switch
        with open(TOGGLE_SCHEDULE) as f:
            toggle = json.load(f)
            global schedule_toggle
            if toggle['schedule_toggle'] == 'on':
                schedule_toggle = 'checked'
            elif toggle['schedule_toggle'] == 'off':
                schedule_toggle = None
       
        # checks for from request for shcedules
        if request.form:
            save_alert = 'on'
            with open(SCHEDULES, "w") as f:
                json.dump(request.form, f)
                f.close()
            
        if onboard_led.value() == 1:
            light_state = 'checked'
        
        
        os.stat(SCHEDULES)
        with open(SCHEDULES) as f:
            schedule_databas = json.load(f)
            monday_start = schedule_databas['s0']
            monday_sampm = schedule_databas['s0ampm']
            monday_end = schedule_databas['e0']
            monday_eampm = schedule_databas['e0ampm']
                
            tuesday_start = schedule_databas['s1']   
            tuesday_sampm = schedule_databas['s1ampm']
            tuesday_end = schedule_databas['e1']
            tuesday_eampm = schedule_databas['e1ampm']
            
            wednesday_start = schedule_databas['s2']
            wednesday_sampm = schedule_databas['s2ampm']
            wednesday_end = schedule_databas['e2']
            wednesday_eampm = schedule_databas['e2ampm']
            
            thursday_start = schedule_databas['s3']
            thursday_sampm = schedule_databas['s3ampm']
            thursday_end = schedule_databas['e3']
            thursday_eampm = schedule_databas['e3ampm']
            
            friday_start = schedule_databas['s4']  
            friday_sampm = schedule_databas['s4ampm']  
            friday_end = schedule_databas['e4']
            friday_eampm = schedule_databas['e4ampm']
            
            saturday_start = schedule_databas['s5']
            saturday_sampm = schedule_databas['s5ampm']
            saturday_end = schedule_databas['e5']
            saturday_eampm = schedule_databas['e5ampm']
            
            sunday_start = schedule_databas['s6']
            sunday_sampm = schedule_databas['s6ampm']
            sunday_end = schedule_databas['e6'] 
            sunday_eampm = schedule_databas['e6ampm']    
            f.close()
        
        
        return render_template(f"{APP_TEMPLATE_PATH}/index.html", light_status=light_state, schedule_status=schedule_toggle, sa=save_alert, 
                               ms=monday_start, msampm=monday_sampm, me=monday_end, meampm=monday_eampm,
                               ts=tuesday_start, tsampm=tuesday_sampm, te=tuesday_end, teampm=tuesday_eampm,
                               ws=wednesday_start, wsampm=wednesday_sampm, we=wednesday_end, weampm=wednesday_eampm,
                               ths=thursday_start, thsampm=thursday_sampm, the=thursday_end, theampm=thursday_eampm,
                               fs=friday_start, fsampm=friday_sampm, fe=friday_end, feampm=friday_eampm,
                               ss=saturday_start, ssampm=saturday_sampm, se=saturday_end, seampm=saturday_eampm,
                               sus=sunday_start, susampm=sunday_sampm, sue=sunday_end, sueampm=sunday_eampm)

    def app_schedule_toggle_off(request):
        with open(TOGGLE_SCHEDULE, 'r') as f:
            toggle_state = json.load(f)
        toggle_state["schedule_toggle"]="off"
        with open(TOGGLE_SCHEDULE, 'w') as f:
            json.dump(toggle_state, f)
            print(toggle_state)
            f.close()
        return "OK"
    
    def app_schedule_toggle_on(request):
        with open(TOGGLE_SCHEDULE, 'r') as f:
            toggle_state = json.load(f)
        toggle_state["schedule_toggle"]="on"
        with open(TOGGLE_SCHEDULE, 'w') as f:
            json.dump(toggle_state, f)
            print(toggle_state)
            f.close()
        return "OK"
            
    def app_toggle(request):
        print(request)
        onboard_led.toggle()
        return "OK"
    
    def app_get_temperature(request):
        # Not particularly reliable but uses built in hardware.
        # Demos how to incorporate senasor data into this application.
        # The front end polls this route and displays the output.
        # Replace code here with something else for a 'real' sensor.
        # Algorithm used here is from:
        # https://www.coderdojotc.org/micropython/advanced-labs/03-internal-temperature/
        sensor_temp = machine.ADC(4)
        reading = sensor_temp.read_u16() * (3.3 / (65535))
        temperature = 27 - (reading - 0.706)/0.001721
        return f"{round(temperature, 1)}"
    
    def app_reset(request):
        # Deleting the WIFI configuration file will cause the device to reboot as
        # the access point and request new configuration.
        os.remove(WIFI_FILE)
        # Reboot from new thread after we have responded to the user.
        _thread.start_new_thread(machine_reset, ())
        return render_template(f"{APP_TEMPLATE_PATH}/reset.html", access_point_ssid = AP_NAME)

    def app_catch_all(request):
        return "Not found.", 404

    server.add_route("/", handler = app_index, methods = ["GET"])
    server.add_route("/schedule_off", handler = app_schedule_toggle_off, methods = ["GET"])
    server.add_route("/schedule_on", handler = app_schedule_toggle_on, methods = ["GET"])
    server.add_route("/toggle", handler = app_toggle, methods = ["GET"])
    server.add_route("/", handler = app_index, methods = ["POST"])
    server.add_route("/temperature", handler = app_get_temperature, methods = ["GET"])
    server.add_route("/reset", handler = app_reset, methods = ["GET"])
    # Add other routes for your application...
    server.set_callback(app_catch_all)
############################################################################
# This file was created, and don't need to show IP address if it hasn't changed
try:
    os.stat(IP_ADDRESS)
    # Figure out which mode to start up in...
    try:
        os.stat(WIFI_FILE)

        # File was found, attempt to connect to wifi...
        with open(WIFI_FILE) as f:
            wifi_current_attempt = 1
            wifi_credentials = json.load(f)
            
            while (wifi_current_attempt < WIFI_MAX_ATTEMPTS):
                ip_address = connect_to_wifi(wifi_credentials["ssid"], wifi_credentials["password"])

                if is_connected_to_wifi():
                    print(f"Connected to wifi, IP address {ip_address}")
                    break
                else:
                    wifi_current_attempt += 1
        
        with open(IP_ADDRESS) as f:
            ip_address_status = json.load(f)
            if ip_address_status["ipa"] == ip_address:
                application_mode()
            else:
                print("updating IP address in json file")
                # update IP address in json file
                json_ip_Data = {"ipa": ip_address}
                try:
                    with open(IP_ADDRESS, "w") as f:
                        json.dump(json_ip_Data, f)
                        f.close()
                    display_ip()
                except:
                    print("Error! Could not update file with new IP address")
            
    except Exception:
        # Either no wifi configuration file found, or something went wrong, 
        # so go into setup mode.
        setup_mode()  
             
except:
    try:
        os.stat(WIFI_FILE)

        # File was found, attempt to connect to wifi...
        with open(WIFI_FILE) as f:
            wifi_current_attempt = 1
            wifi_credentials = json.load(f)
            
            while (wifi_current_attempt < WIFI_MAX_ATTEMPTS):
                ip_address = connect_to_wifi(wifi_credentials["ssid"], wifi_credentials["password"])

                if is_connected_to_wifi():
                    print(f"Connected to wifi, IP address {ip_address}")
                    break
                else:
                    wifi_current_attempt += 1
    
    
        print("Saving IP Address to show to user")
        
        json_ip_Data = {"ipa": ip_address}
        
        try:
            with open(IP_ADDRESS, "w") as f:
                json.dump(json_ip_Data, f)
                f.close()
        except:
            print("Error! Could not save file with IP address and restart attempts")
    
    
        if is_connected_to_wifi():
            display_ip() # turns pico back into a Access point and displays IP address, and restarts itself
                                                       
        
        else:
            
            # Bad configuration, delete the credentials file, reboot
            # into setup mode to get new credentials from the user.
            print("Bad wifi connection!")
            print(wifi_credentials)
            os.remove(WIFI_FILE)
            os.remove(IP_ADDRESS)
            machine_reset()

    except Exception:
        # Either no wifi configuration file found, or something went wrong, 
        # so go into setup mode.
        setup_mode()

# Start the web server...
server.run()
