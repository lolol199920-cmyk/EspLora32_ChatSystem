from machine import Pin, SoftI2C
from time import sleep_ms, ticks_ms, ticks_diff
from sx1262 import SX1262
import ssd1306

# Change to "2" on the second board
DEVICE_ID = "1"

MESSAGES = [
    ("H:1", "HALLO!"),
    ("Q:1", "WIE GEHTS?"),
    ("F:1", "GUT :)"),
    ("F:2", "SCHLECHT :("),
    ("F:3", "GEHT SO"),
    ("A:1", "JA"),
    ("A:2", "NEIN"),
    ("Q:2", "BIST DU DA?"),
    ("H:2", "TSCHUESS"),
    ("E:1", "DANKE!"),
]

def phrase_for(code):
    for item_code, phrase in MESSAGES:
        if item_code == code:
            return phrase
    return code

# OLED power and reset
Pin(36, Pin.OUT).value(0)
sleep_ms(100)

reset = Pin(21, Pin.OUT)
reset.value(0)
sleep_ms(50)
reset.value(1)
sleep_ms(100)

i2c = SoftI2C(sda=Pin(17), scl=Pin(18), freq=100000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

# PRG button
button = Pin(0, Pin.IN, Pin.PULL_UP)

history = []
selected = 0
was_pressed = False
press_start = 0

def add_message(sender, phrase):
    history.append(sender + "> " + phrase)
    if len(history) > 5:
        history.pop(0)

def draw_screen():
    oled.fill(0)
    oled.text("MICROCLUSTER " + DEVICE_ID, 0, 0)
    oled.text("----------------", 0, 8)

    for i, line in enumerate(history):
        oled.text(line[:16], 0, 16 + i * 8)

    code, phrase = MESSAGES[selected]
    oled.text((">" + code + " " + phrase)[:16], 0, 56)
    oled.show()

def send_selected():
    code, phrase = MESSAGES[selected]
    packet = ("MC1|" + DEVICE_ID + "|" + code).encode()

    try:
        radio.send(packet)
        add_message(DEVICE_ID, phrase)
        print("TX:", packet)
        draw_screen()
    except Exception as error:
        print("TX ERROR:", error)

def receive_packet(data, status):
    if status != 0 or not data:
        print("RX STATUS:", status)
        return

    try:
        packet = data.decode().strip()
        parts = packet.split("|")

        if len(parts) != 3 or parts[0] != "MC1":
            return

        sender = parts[1]
        code = parts[2]

        if sender == DEVICE_ID:
            return

        add_message(sender, phrase_for(code))
        print("RX:", packet)
        draw_screen()

    except Exception as error:
        print("RX ERROR:", error)

def radio_callback(events):
    if events & SX1262.RX_DONE:
        try:
            data, status = radio.recv()
            receive_packet(data, status)
        except Exception as error:
            print("RX CALLBACK ERROR:", error)

    if events & SX1262.TX_DONE:
        print("TX DONE")

# LoRa configuration
radio = SX1262(
    spi_bus=1,
    clk=9,
    mosi=10,
    miso=11,
    cs=8,
    irq=14,
    rst=12,
    gpio=13
)

radio.begin(
    freq=868.0,
    bw=125.0,
    sf=7,
    cr=5,
    syncWord=0x12,
    power=2,
    blocking=True
)

radio.setBlockingCallback(False, radio_callback)

add_message("-", "BEREIT")
draw_screen()

print("MICROCLUSTER", DEVICE_ID, "READY")

while True:
    pressed = button.value() == 0

    if pressed and not was_pressed:
        press_start = ticks_ms()

    if not pressed and was_pressed:
        duration = ticks_diff(ticks_ms(), press_start)

        if duration >= 700:
            send_selected()
        else:
            selected = (selected + 1) % len(MESSAGES)
            code, phrase = MESSAGES[selected]
            print("SELECT:", code, phrase)
            draw_screen()

    was_pressed = pressed
    sleep_ms(10)
