import time

from ScheduleAutoManager import ScheduleAutoManager

if __name__ == '__main__':
    a = ScheduleAutoManager()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        a.stop()