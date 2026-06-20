from enum import Enum


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT =  "LIMIT"

class PositionState(str, Enum):
    OPEN      = "OPEN"
    TRIGGERED = "TRIGGERED"
    STOPPED   = "STOPPED"
    TRIGGERED_BY_CLOSE = "TRIGGERED_BY_CLOSE"
    STOPPED_BY_CLOSE = "TRIGGERED_BY_CLOSE"
    LIQUID = "LIQUID"

class LiquidyType(str, Enum):
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"