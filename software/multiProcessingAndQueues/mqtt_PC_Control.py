import paho.mqtt.client as mqtt
import time
import math
import paho.mqtt.publish as publish

publish.single("PythonPowerSupply/iSet", 900, hostname="test.mosquitto.org")
publish.single("PythonPowerSupply/vSet", 100, hostname="test.mosquitto.org")

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("PythonPowerSupply/iMon")
    
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))
      

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("test.mosquitto.org", 1883, 60)
client.loop_forever()

    
    
#publish.single("PythonPowerSupply/preset", "Red", hostname="test.mosquitto.org")
#publish.single("PythonPowerSupply/preset", "Yellow", hostname="test.mosquitto.org")
#publish.single("PythonPowerSupply/preset", "Blue", hostname="test.mosquitto.org")


#v = int(round(600.0 + 600.0 * math.sin(0.2*math.pi*(time.time() - start_t))))
#publish.single("PythonPowerSupply/vSet", v, hostname="test.mosquitto.org")
    
#print("published")
    