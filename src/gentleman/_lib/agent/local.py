from pydantic_ai.agent import  WrapperAgent

class LocalAgent(WrapperAgent):

    def __init__(self, wrapped, card):
        super().__init__(wrapped)
        self._card = card

    @property
    def card(self): return self._card

