from PIL import Image, ImageDraw, ImageFont
import datetime
from datetime import date as dt
import calendar
import asyncio
from functools import partial

"""
Basically taken from the following Stack Overflow question
https://stackoverflow.com/questions/70420891/how-do-i-create-a-calendar-using-pillow-in-python
"""

async def draw(guild_id: int, events: list):
    weekdays = ImageFont.truetype("arialbd.ttf", 32)
    font = ImageFont.truetype("arialbd.ttf", 16)

    w, h = 1420, 1200

    img = Image.new("RGB",(w,h), (255,255,255))
    draw = ImageDraw.Draw(img)

    top_span = 80
    border = 10
    h_start = border + top_span
    h_end = h - border
    w_start = border
    w_end = w - border
    stepsizeV = int((w - (border * 2)) / 7)
    stepsizeH = int((h - (top_span + (border * 2))) / 5)

    for x in range (border, w, stepsizeV):
        draw.line(((x, h_start), (x, h_end)), fill=1, width=3)

    for x in range (border + top_span, h, stepsizeH):
        draw.line(((w_start, x), (w_end, x)), fill=50, width=3)

    cols = []
    rows = []

    days = { 0:'Sun', 1:'Mon', 2:'Tue', 3:'Wed', 4:'Thu', 5:'Fri', 6:'Sat'}
    i = 0
    for x in range(border, w, stepsizeV):
        if i < 7:
            cols.append(x + stepsizeV / 10)
            draw.text((x + (stepsizeV / 2) - 30, top_span/2), days[i], fill=(0, 0, 0), font=weekdays)
        i += 1


    for x in range(h_start, h, stepsizeH):
        line = ((w_start, x),(w_end, x))
        rows.append(x + stepsizeH // 10)
        draw.line(line, fill=50, width=3)

    current_date = dt.today()
    date =int(current_date.strftime('%d'))
    month = int(current_date.strftime('%m'))
    year = int(current_date.strftime('%y'))

    month_len = calendar.monthrange(year, month)
    k = (dt.today().replace(day=1).weekday() + 1) % 7
    i = 1
    j = 0
    r = rows[j]
    while i <= month_len[1]:
        c = cols[k]
        draw.text((c,r), str(i), fill=(0, 0, 0), font=font)

        internal_x_offset = c + 160
        for n, ent in enumerate(events[i - 1]):
            # This calculation is 100% the worst thing ever but its a funny kludge if ever
            internal_y_offset = r - 15 + (40 * (n + 1)) + (10 * n)

            draw.rounded_rectangle((c, internal_y_offset, internal_x_offset, internal_y_offset + 40), radius=10, fill=ent[1])
            draw.text(((c + internal_x_offset)//2, (internal_y_offset + internal_y_offset + 40)//2), ent[0], fill=(0, 0, 0), font=font, anchor="mm")

        i += 1
        k = (k + 1) % 7
        if not k:
            j += 1
            r = rows[j]

    file_output = f"output/{str(guild_id)}.jpeg"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(img.save, file_output, "JPEG"))
    return file_output