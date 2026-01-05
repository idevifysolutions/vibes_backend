"""
app/utils/unit_converter.py
Unit conversion utilities
"""
import logging

logger = logging.getLogger(__name__)


# Unit conversion dictionaries
WEIGHT_UNITS = {
    'gm': 1, 'g': 1, 'grams': 1, 'gram': 1,
    'kg': 1000, 'kilogram': 1000, 'kilograms': 1000,
    'oz': 28.3495, 'ounce': 28.3495, 'ounces': 28.3495,
    'lb': 453.592, 'lbs': 453.592, 'pound': 453.592, 'pounds': 453.592
}

VOLUME_UNITS = {
    'ml': 1, 'milliliter': 1, 'milliliters': 1,
    'l': 1000, 'liter': 1000, 'liters': 1000, 'litre': 1000, 'litres': 1000,
    'cup': 240, 'cups': 240,
    'tablespoon': 15, 'tablespoons': 15, 'tbsp': 15,
    'teaspoon': 5, 'teaspoons': 5, 'tsp': 5,
    'gallon': 3785.41, 'gallons': 3785.41,
    'quart': 946.353, 'quarts': 946.353,
    'pint': 473.176, 'pints': 473.176,
    'fl oz': 29.5735, 'fluid ounce': 29.5735, 'fluid ounces': 29.5735
}

COUNT_UNITS = {
    'piece': 1, 'pieces': 1, 'pc': 1, 'pcs': 1,
    'item': 1, 'items': 1, 'unit': 1, 'units': 1,
    'pack': 1, 'packs': 1, 'packet': 1, 'packets': 1,
    'dozen': 12, 'doz': 12
}


def normalize_unit(unit: str) -> str:
    """Normalize unit string to lowercase and stripped"""
    return unit.lower().strip()


def get_unit_category(unit: str) -> str:
    """Determine the category of a unit (weight, volume, count)"""
    unit = normalize_unit(unit)
    
    if unit in WEIGHT_UNITS:
        return "weight"
    elif unit in VOLUME_UNITS:
        return "volume"
    elif unit in COUNT_UNITS:
        return "count"
    else:
        return "unknown"


def convert_to_base_unit(quantity: float, from_unit: str, to_unit: str) -> float:
    """
    Convert quantity from one unit to another within the same category
    
    Args:
        quantity: Amount to convert
        from_unit: Source unit
        to_unit: Target unit
        
    Returns:
        Converted quantity
    """
    from_unit = normalize_unit(from_unit)
    to_unit = normalize_unit(to_unit)
    
    # If units are the same, no conversion needed
    if from_unit == to_unit:
        return quantity
    
    # Determine categories
    from_category = get_unit_category(from_unit)
    to_category = get_unit_category(to_unit)
    
    # Check if both units are in the same category
    if from_category != to_category:
        logger.warning(
            f"Cannot convert from {from_unit} ({from_category}) to {to_unit} ({to_category}) - incompatible unit types"
        )
        return quantity  # Return as-is
    
    # Perform conversion based on category
    if from_category == "weight":
        base_quantity = quantity * WEIGHT_UNITS[from_unit]
        return base_quantity / WEIGHT_UNITS[to_unit]
    
    elif from_category == "volume":
        base_quantity = quantity * VOLUME_UNITS[from_unit]
        return base_quantity / VOLUME_UNITS[to_unit]
    
    elif from_category == "count":
        base_quantity = quantity * COUNT_UNITS[from_unit]
        return base_quantity / COUNT_UNITS[to_unit]
    
    else:
        logger.warning(f"Unknown unit category: {from_category}")
        return quantity


def convert_from_base_unit(quantity: float, target_unit: str, base_unit: str) -> float:
    """
    Convert from base unit back to target unit
    Convenience wrapper around convert_to_base_unit
    """
    return convert_to_base_unit(quantity, base_unit, target_unit)


def are_units_compatible(unit1: str, unit2: str) -> bool:
    """Check if two units can be converted between each other"""
    cat1 = get_unit_category(normalize_unit(unit1))
    cat2 = get_unit_category(normalize_unit(unit2))
    return cat1 == cat2 and cat1 != "unknown"