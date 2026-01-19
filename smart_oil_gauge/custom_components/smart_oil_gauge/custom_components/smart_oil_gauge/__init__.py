from .const import DOMAIN
from .coordinator import SmartOilGaugeCoordinator

async def async_setup_entry(hass, entry):
    coordinator = SmartOilGaugeCoordinator(
        hass,
        entry.data["username"],
        entry.data["password"],
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True
