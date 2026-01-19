from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data["smart_oil_gauge"][entry.entry_id]
    async_add_entities([
        OilGallonsSensor(coordinator),
        OilPercentSensor(coordinator),
        OilBatterySensor(coordinator),
        OilStatusSensor(coordinator),
    ])

class OilGallonsSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Oil Remaining"
    _attr_unit_of_measurement = "gal"
    _attr_icon = "mdi:barrel"

    @property
    def unique_id(self):
        return f"smart_oil_gauge_{self.coordinator.data['tank_id']}_gallons"

    @property
    def native_value(self):
        return float(self.coordinator.data["sensor_gallons"])

class OilPercentSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Oil Tank Level"
    _attr_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:gas-station"

    @property
    def unique_id(self):
        return f"smart_oil_gauge_{self.coordinator.data['tank_id']}_percent"

    @property
    def native_value(self):
        gallons = float(self.coordinator.data["sensor_gallons"])
        capacity = float(self.coordinator.data["fillable"])
        return round((gallons / capacity) * 100, 1)

class OilBatterySensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Oil Sensor Battery"
    _attr_icon = "mdi:battery"

    @property
    def unique_id(self):
        return f"smart_oil_gauge_{self.coordinator.data['tank_id']}_battery"

    @property
    def native_value(self):
        return self.coordinator.data.get("battery")

class OilStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Oil Sensor Status"
    _attr_icon = "mdi:check-circle"

    @property
    def unique_id(self):
        return f"smart_oil_gauge_{self.coordinator.data['tank_id']}_status"

    @property
    def native_value(self):
        return self.coordinator.data.get("sensor_status")
