from abc import ABC, abstractmethod


class Skill(ABC):
    @abstractmethod
    def can_handle(self, command: str) -> bool:
        pass

    @abstractmethod
    def execute(self, command: str) -> str:
        pass