import lvgl as lv
import urequests
import uasyncio as asyncio
import utime
import uio

# App Configuration
NAME = "Spotify Player"
CAN_BE_AUTO_SWITCHED = True
ICON = "./spotify.png"
USER_ID = "vobot"
SERVER_URL = "http://192.168.0.57:3000"
DEBUG = True  # Toggle verbose logging

# LVGL Widgets
scr = None
art_img = None
track_label = None
artist_label = None

# Style Configuration
FONT_COLOR = lv.color_hex(0xFFFFFF)
BG_COLOR = lv.color_hex(0x000000)
FONT_SIZE = 24

def log(message):
    if DEBUG:
        timestamp = utime.localtime()
        print(f"[{timestamp[3]:02}:{timestamp[4]:02}:{timestamp[5]:02}] {message}")

async def update_track_info():
    global art_img, track_label, artist_label
    log("Starting track info update")
    
    try:
        log(f"Attempting to fetch track metadata from {SERVER_URL}")
        url = f"{SERVER_URL}/current-track?userId={USER_ID}"
        log(f"Request URL: {url}")
        
        response = urequests.get(url)
        log(f"Received response status: {response.status_code}")
        
        if response.status_code != 200:
            log(f"Error response content: {response.text}")
            response.close()
            raise Exception(f"HTTP Error {response.status_code}")
            
        track_response = response.json()
        response.close()
        log("Successfully parsed track metadata")
        log(f"Track data: {str(track_response)[:60]}...")  # Truncate for display

        log("Attempting to fetch album art")
        art_url = track_response['art_url']
        log(f"Art URL: {art_url}")
        
        art_response = urequests.get(art_url)
        log(f"Art response status: {art_response.status_code}")
        log(f"Art content length: {len(art_response.content)} bytes")
        
        img_data = art_response.content
        art_response.close()
        
        log("Creating LVGL image descriptor")
        img_dsc = lv.img_dsc_t({
            'data_size': len(img_data),
            'data': img_data
        })
        log(f"Image descriptor created: {len(img_data)} bytes")

        log("Updating UI elements")
        art_img.set_src(img_dsc)
        track_label.set_text(track_response['track'])
        artist_label.set_text(track_response['artist'])
        log("UI update complete")
        
        log(f"Set track: {track_response['track']}")
        log(f"Set artist: {track_response['artist']}")

    except Exception as e:
        log("Exception occurred during update:")
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        log(buf.getvalue())
        
        track_label.set_text("No track playing")
        artist_label.set_text("")
        log("Reset UI to default state")

def create_ui():
    global scr, art_img, track_label, artist_label
    log("Initializing UI components")
    
    try:
        scr = lv.obj()
        scr.set_style_bg_color(BG_COLOR, lv.PART.MAIN)
        log("Screen created and styled")

        art_img = lv.img(scr)
        art_img.set_size(320, 240)
        art_img.align(lv.ALIGN.TOP_MID, 0, 10)
        log("Album art container created")

        info_cont = lv.obj(scr)
        info_cont.set_size(300, 60)
        info_cont.align(lv.ALIGN.BOTTOM_MID, 0, -10)
        info_cont.set_style_bg_opa(150, lv.PART.MAIN)
        info_cont.set_style_bg_color(lv.color_hex(0x000000), lv.PART.MAIN)
        log("Info container created")

        track_label = lv.label(info_cont)
        track_label.set_size(280, 30)
        track_label.align(lv.ALIGN.TOP_LEFT, 5, 5)
        track_label.set_style_text_color(FONT_COLOR, lv.PART.MAIN)
        track_label.set_style_text_font(lv.font_montserrat(FONT_SIZE), lv.PART.MAIN)
        log("Track label created")

        artist_label = lv.label(info_cont)
        artist_label.set_size(280, 30)
        artist_label.align(lv.ALIGN.BOTTOM_LEFT, 5, -5)
        artist_label.set_style_text_color(FONT_COLOR, lv.PART.MAIN)
        artist_label.set_style_text_font(lv.font_montserrat(FONT_SIZE-4), lv.PART.MAIN)
        log("Artist label created")

    except Exception as e:
        log("UI creation failed:")
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        log(buf.getvalue())
        raise

async def on_start():
    log("App starting...")
    try:
        create_ui()
        lv.scr_load(scr)
        log("Screen loaded successfully")

        log("Performing initial update")
        await update_track_info()
        log("Initial update complete")

        log("Starting update loop")
        while True:
            log("Sleeping for 10 seconds")
            await asyncio.sleep(10)
            log("Wakeup - checking for updates")
            await update_track_info()
            log("Update check completed")

    except Exception as e:
        log("Error in on_start:")
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        log(buf.getvalue())

async def on_stop():
    global scr
    log("App stopping...")
    if scr:
        log("Cleaning up screen resources")
        scr.clean()
        scr.del_async()
        scr = None
        log("Screen resources released")

def event_handler(event):
    try:
        log(f"Event received: {str(event)}")
        e_code = event.get_code()
        
        if e_code == lv.EVENT.KEY:
            e_key = event.get_key()
            log(f"Key event detected: {e_key}")
            if e_key == lv.KEY.ENTER:
                log("ENTER key pressed - triggering manual update")
                asyncio.create_task(update_track_info())
                
        elif e_code == lv.EVENT.FOCUSED:
            log("Focus event received")
            if not lv.group_get_default().get_editing():
                log("Enabling editing mode")
                lv.group_get_default().set_editing(True)
                
    except Exception as e:
        log("Event handler error:")
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        log(buf.getvalue())

try:
    log("Initializing group controls")
    lv.group_get_default().add_obj(scr)
    lv.group_focus_obj(scr)
    scr.add_event(event_handler, lv.EVENT.ALL, None)
except Exception as e:
    log("Group initialization failed:")
    buf = uio.StringIO()
    sys.print_exception(e, buf)
    log(buf.getvalue())