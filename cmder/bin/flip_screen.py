import rotatescreen as rts

class Screen:

   def __init__(self):
      self.screen = rts.get_secondary_displays()[0]
      self.curr_pos = self.screen.current_orientation


   def flip_screen(self):
      if self.curr_pos == 0 :
         self.screen.set_portrait_flipped()
      else :
         self.screen.set_landscape()


if __name__ == "__main__":
   scnd_screen = Screen()
   scnd_screen.flip_screen()
   del scnd_screen