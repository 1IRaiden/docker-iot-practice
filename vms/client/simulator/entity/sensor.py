import random
import math

BIRTH_YEAR  = 2003   # <-- замените на свой год рождения
BIRTH_MONTH = 7      # <-- замените на свой месяц рождения


class Sensor:
    value: float
    name: str
    type: str

    def __init__(self, name):
        self.name = name

    def generate_new_value(self):
        pass

    def get_data(self):
        return self.value

    def __str__(self):
        return {"type": self.type, "name": self.name, "value": self.value}


class Temperature(Sensor):
    """Датчик температуры, градусы Цельсия."""
    BASE = 20.0

    def __init__(self, name):
        super().__init__(name)
        self.type = "temperature"
        self._step = 0

    def generate_new_value(self):
        self.value = round(
            self.BASE + math.sin(self._step / 10) * BIRTH_MONTH * 0.3
            + random.uniform(-0.5, 0.5), 2
        )
        self._step += 1


class Pressure(Sensor):
    """Датчик атмосферного давления, hPa."""
    BASE = 1013.25

    def __init__(self, name):
        super().__init__(name)
        self.type = "pressure"
        self._step = 0

    def generate_new_value(self):
        delta = random.uniform(-1, 1) * (BIRTH_YEAR % 100) / 50.0
        self.value = round(
            self.BASE + math.cos(self._step / 15) * 5 + delta, 2
        )
        self._step += 1


class Current(Sensor):
    """Датчик потребляемого тока, Ампер."""
    def __init__(self, name):
        super().__init__(name)
        self.type = "current"
        self._step = 0

    def generate_new_value(self):
        self.value = round(
            abs(math.sin(self._step * math.pi / (BIRTH_MONTH * 3))) * 10
            + random.uniform(0, 0.5), 2
        )
        self._step += 1


class Humidity(Sensor):
    """Датчик относительной влажности, %."""
    BASE = 55.0

    def __init__(self, name):
        super().__init__(name)
        self.type = "humidity"
        self._step = 0

    def generate_new_value(self):
        amplitude = (BIRTH_YEAR % 10) + 5
        self.value = round(
            self.BASE + math.cos(self._step / 20) * amplitude
            + random.uniform(-1, 1), 2
        )
        self.value = max(0.0, min(100.0, self.value))
        self._step += 1
