import datetime as dt

def format_dates(dates:str, start_time:int=19):
    date_list = dates.split(",")
    current = dt.datetime.now()
    for i, d in enumerate(date_list):
        try:
            spl = [int(itm.strip()) for itm in d.split("-")]
            if len(spl) == 1:
                date_stamp = dt.datetime(current.year, current.month, spl[0], hour=start_time)
            elif len(spl) == 2:
                date_stamp = dt.datetime(current.year, spl[0], spl[1], hour=start_time)
            else:
                date_stamp = dt.datetime(spl[0], spl[1], spl[2], hour=start_time)
            date_list[i] = date_stamp.__str__()
        except TypeError:
            raise TypeError()
        except ValueError:
            raise ValueError()
    return date_list

class Event:

    def __init__(self, owner:int, name:str, description:str, colour:str, mode:str, dates:str, starts:int, duration:int, location:str = "The Interwebs",
                 recurrence: tuple = tuple(), attendees: tuple = tuple()):
        # Unique information saved on its own folder, relational style
        self.owner = owner

        # Individual information saved also on its own folder
        self.summary = name
        self.description = description
        self.location = location
        # Saved on the above folder, divided because these are important to be reflected on the calendar
        self.color = colour
        self.custom_modified = False
        self.custom_set = ''
        self.frequency = mode

        # Saved on a general ID tracked list of dates, based on server
        self.dates = format_dates(dates, start_time=starts)
        self.starts = starts
        self.duration = duration

        # Vestigial, ignore them until further notice
        # self.recurrence = recurrence
        # self.attendees = attendees


    def __str__(self):
        return (f"Owner: {self.owner}, Summary: {self.summary}, "
                f"Location: {self.location}, Description: {self.description}, Color: {self.color}, "
                f"Frequency: {self.frequency}, Dates: {self.dates}, Starts: {self.starts}, Duration: {self.duration}, "
                f"Recurrence: {self.recurrence}, Attendees: {self.attendees}")
