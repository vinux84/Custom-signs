from phew import access_point, connect_to_wifi, is_connected_to_wifi, dns, server
from phew.template import render_template
import json
import machine
import os
import utime
import _thread

AP_NAME = "Shorty's Customs"
AP_DOMAIN = "shortyscustoms.net"
AP_TEMPLATE_PATH = "ap_templates"
APP_TEMPLATE_PATH = "app_templates"
WIFI_FILE = "wifi.json"
IP_ADDRESS = "ip.json"
WIFI_MAX_ATTEMPTS = 3

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
    server.add_route("/toggle", handler = app_restart, methods = ["GET"])
    server.set_callback(ap_catch_all)
    
    ap = access_point(AP_NAME)
    ip = ap.ifconfig()[0]
    dns.run_catchall(ip)

def application_mode():
    print("Entering application mode.")
    onboard_led = machine.Pin("LED", machine.Pin.OUT)

    def app_index(request):
        return render_template(f"{APP_TEMPLATE_PATH}/index.html")

    def app_toggle_led(request):
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
    server.add_route("/toggle", handler = app_toggle_led, methods = ["GET"])
    server.add_route("/temperature", handler = app_get_temperature, methods = ["GET"])
    server.add_route("/reset", handler = app_reset, methods = ["GET"])
    # Add other routes for your application...
    server.set_callback(app_catch_all)

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
                # update IP address in json file
                json_ip_Data["ipa"]=ip_address
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
