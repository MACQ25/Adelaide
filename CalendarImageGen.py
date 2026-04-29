import os

from PIL import Image, ImageDraw, ImageFont, ImageColor
from datetime import date as dt
import calendar
import asyncio

w, h = 1420, 1200

def channel(i, c, size, startFill, stopFill, degree=0.2):
    """calculate the value of a single color channel for a single pixel"""
    return startFill[c] + int((i * degree / size) * (stopFill[c] - startFill[c]))


def color(i, size, startFill, stopFill, degree=0.2):
    """calculate the RGB value of a single pixel"""
    return tuple([channel(i, c, size, startFill, stopFill, degree) for c in range(3)])


def round_corner(radius):
    """Draw a round corner"""
    corner = Image.new("RGBA", (radius, radius), (0, 0, 0, 0))
    draw = ImageDraw.Draw(corner)
    draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill="blue")
    return corner


def apply_grad_to_corner(corner, gradient):
    width, height = corner.size

    for i in range(height):
        gradPos = 0
        for j in range(width):
            pos = (i, j)
            pix = corner.getpixel(pos)
            gradPos += 1
            if pix[3] != 0:
                corner.putpixel(pos, gradient[gradPos])

    return corner


def round_rectangle(size, radius, startFill, stopFill, degree):
    """Draw a rounded rectangle"""
    width, height = size
    rectangle = Image.new("RGBA", size)

    gradient = [color(i, height, startFill, stopFill, degree) for i in range(width)]

    modGrad = []
    for i in range(height):
        modGrad += [gradient[j] for j in range(width)]
    rectangle.putdata(modGrad)


    # upper left
    corner = round_corner(radius)
    apply_grad_to_corner(corner, gradient)
    rectangle.paste(corner, (0, 0))


    # lower left
    corner = corner.rotate(90)
    apply_grad_to_corner(corner, gradient)
    rectangle.paste(corner, (0, height - radius))


    # lower right
    gradient.reverse()
    corner = corner.rotate(90)
    apply_grad_to_corner(corner, gradient)
    rectangle.paste(corner, (width - radius, height - radius))


    # upper right
    corner = corner.rotate(90)
    apply_grad_to_corner(corner, gradient)
    rectangle.paste(corner, (width - radius, 0))


    return rectangle


"""
Basically taken from the following Stack Overflow question
https://stackoverflow.com/questions/70420891/how-do-i-create-a-calendar-using-pillow-in-python
"""

async def draw(guild_id: int, events: list):

    font_path = os.getenv("FONT_PATH", "arialbd.ttf")

    weekdays = ImageFont.truetype(font_path, 32)
    font = ImageFont.truetype(font_path, 16)

    img = Image.new("RGBA",(w,h), (255,255,255))
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
    x_offset_val = 160
    y_offset_val = 40
    displacement = 20

    while i <= month_len[1]:
        c = cols[k]
        draw.text((c,r), str(i), fill=(0, 0, 0), font=font)

        internal_x_offset = c + x_offset_val
        ln_displacement = 0
        for n, ent in enumerate(events[i - 1]):
            event_name = ent[0]

            if len(event_name) > 16:
                total_height = y_offset_val + displacement
                ln_displacement += displacement
                i_displace = True
            else:
                total_height = y_offset_val
                i_displace = False

            # This calculation is 100% the worst thing ever but its a funny kludge if ever
            internal_y_offset = r - 15 + (y_offset_val * (n + 1)) + (10 * n) + (ln_displacement - displacement if i_displace else ln_displacement)

            color1 = ImageColor.getrgb(ent[1][0])
            color2 =  ImageColor.getrgb(ent[1][1] if len(ent[1]) > 1 else ent[1][0])
            degree = ent[1][2] if len(ent[1]) > 2 else 0.2

            rectangle = round_rectangle((x_offset_val, total_height), 10, startFill=color1, stopFill=color2, degree=degree)
            img.paste(im=rectangle, box=(int(c), internal_y_offset), mask=rectangle.split()[3])
            #draw.rounded_rectangle((c, internal_y_offset, internal_x_offset, internal_y_offset + y_offset_val), radius=10, fill=ent[1])

            if i_displace:

                conv  = str(event_name).split()
                conv.reverse()
                upper = ""

                while len(upper) <= 16:
                    if len(upper) + len(conv[-1]) < 17:
                        upper += conv.pop() + " "
                    else: break

                upper.strip()
                conv.reverse()
                lower = " ".join(conv)

                if len(lower) > 16:
                    lower = f"{lower[:13]}..."

                draw.text(((c + internal_x_offset)//2, ((2 * internal_y_offset) + y_offset_val)//2), upper, fill=(0, 0, 0), font=font, anchor="mm")
                draw.text(((c + internal_x_offset)//2, ((2 * internal_y_offset) + (y_offset_val * 2))//2), lower, fill=(0, 0, 0), font=font, anchor="mm")

            else:
                draw.text(((c + internal_x_offset)//2, (internal_y_offset + internal_y_offset + y_offset_val)//2), event_name, fill=(0, 0, 0), font=font, anchor="mm")

        i += 1
        k = (k + 1) % 7
        if not k:
            j += 1
            r = rows[j]

    file_output = f"output/{str(guild_id)}.png"
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, img.save, file_output, "PNG")
    return file_output