import pygame
import os


class AlarmController:

    def __init__(self, sound_file, threshold=70):

        self.threshold = threshold
        self.alarm_active = False

        # Absolute path to sound file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sound_path = os.path.join(base_dir, sound_file)

        # Initialize mixer
        pygame.mixer.init()

        # Load sound
        try:
            pygame.mixer.music.load(self.sound_path)
            print(f"Alarm sound loaded: {self.sound_path}")
        except Exception as e:
            print("Failed to load alarm sound:", e)


    def update(self, risk_score):

        if risk_score >= self.threshold:

            if not self.alarm_active:
                print("ALARM TRIGGERED")
                pygame.mixer.music.play(-1)  # infinite loop
                self.alarm_active = True

        else:

            if self.alarm_active:
                print("ALARM STOPPED")
                pygame.mixer.music.stop()
                self.alarm_active = False
