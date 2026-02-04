from decimal import Decimal
from enum import Enum

UNIT_CONVERT = {

    "kg": Decimal("1000"),
    "gm": Decimal("1"),
    "mg": Decimal("0.001"),
    "liter": Decimal("1000"),
    "ml":  Decimal("1"),
}

def _normalize_unit(unit) -> str:
    if isinstance(unit, Enum):
        return unit.value.lower()
    return str(unit).strip().lower()


def convert_quantity_unit(value: Decimal, from_unit, to_unit) -> Decimal:
    
    from_unit_str = _normalize_unit(from_unit)
    to_unit_str = _normalize_unit(to_unit)

    if from_unit == to_unit:
        return value
    
    from_unit_factor = UNIT_CONVERT.get(from_unit_str)
    to_unit_factor = UNIT_CONVERT.get(to_unit_str)

    if from_unit_factor is None:
        raise ValueError(f"Unknown unit: {from_unit}")
    if to_unit_factor is None:
        raise ValueError(f"Unknown unit: {to_unit}")
    
    weight_units = {"kg","gm","mg"}
    volume_units = {"liter","ml"}

    from_is_weight = from_unit.lower() in weight_units
    to_is_weight = to_unit.lower() in weight_units

    if from_is_weight != to_is_weight:
        raise ValueError(
            f"Incompatible units: cannot convert {from_unit} to {to_unit}"
        )
    
    base_value = value * from_unit_factor
    return base_value / to_unit_factor
