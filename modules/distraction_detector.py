import time


class DistractionDetector:

    def __init__(self):

        self.distracted = False
        self.start_time = 0
        self.duration = 0


    def update(self, phone_detected):

        current_time = time.time()

        if phone_detected:

            if not self.distracted:

                self.distracted = True
                self.start_time = current_time

            self.duration = current_time - self.start_time

        else:

            self.distracted = False
            self.duration = 0


        return self.duration
