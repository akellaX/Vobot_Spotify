import lvgl as lv
import urequests

# App Configuration
NAME = "Spotify Player"
CAN_BE_AUTO_SWITCHED = True
ICON = "./spotify.png"
USER_ID = "vobot"
SERVER_URL = "http://192.168.0.57:3000"

# LVGL Widgets
scr = None
img = None
track_label = None

def show_track():
    global img, track_label
    
    try:
        # Get track data
        response = urequests.get(f"{SERVER_URL}/current-track?userId={USER_ID}")
        track_data = response.json()
        response.close()
        
        track_name = track_data.get('track', 'No track')
        art_url = track_data.get('art_url', '')
    except:
        track_name = "Connection Error"
        art_url = ''

    # Create album art
    if art_url:
        try:
            art_response = urequests.get(art_url)
            img_data = art_response.content
            art_response.close()
            
            print(img_data)
            
            img = lv.img(scr)
            img_dsc = lv.img_dsc_t({
                'data_size': len(img_data),
                'data': img_data
            })
            img.set_src(img_dsc)
            img.set_size(200, 200)
            img.align(lv.ALIGN.TOP_MID, 0, 20)
        except:
            pass

    # Create track label
    track_label = lv.label(scr)
    track_label.set_text(track_name)
    track_label.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    track_label.set_style_text_color(lv.color_hex(0xFFFFFF), lv.PART.MAIN)
    track_label.set_style_text_font(lv.font_montserrat(24), lv.PART.MAIN)

def on_start():
    global scr
    scr = lv.scr_act()
    scr.set_style_bg_color(lv.color_hex(0x000000), lv.PART.MAIN)
    show_track()

def on_stop():
    if scr:
        scr.clean()
        scr.del_async()
        scr = None

def event_handler(event):
    pass