
class State:

    def __init__(self):
        self.playing = None

    def play(self, what):
        self.playing = what

    def __repr__(self):
        s = self.playing if self.playing else ''
        return 'Sate({})'.format(s)


state = State()
