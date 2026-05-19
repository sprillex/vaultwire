# VaultWire Physical Design & Enclosure Specifications

## Overview
This document outlines the physical design considerations, constraints, and recommendations for the VaultWire hardware enclosure. As a standalone, hardware-hardened credential injector built on a Raspberry Pi Zero 2 W, the physical enclosure plays a critical role in the system's overall security posture.

## Case Form Factor
The final dimensions and materials for the VaultWire case are currently under development. The current focus is on a functional prototype.

### Key Considerations:
*   **Thermal Management:** The Pi Zero 2 W can generate heat under load. The case design must allow for adequate passive cooling, potentially incorporating a thermal pad bridging the CPU to a metal heatsink or case element.
*   **Port Access:** The design must restrict access strictly to necessary ports:
    *   **USB OTG (Data):** Must be accessible for the interconnect cable to the host.
    *   **Power/Input:** Depending on the finalized design for the dedicated keyboard interface, specific GPIO pins or a secondary USB port (via an internal hub) must be securely routed.
    *   **MicroSD Card Slot:** Access to the MicroSD card must be restricted to prevent unauthorized extraction.

## Hardware Maintenance Switch
VaultWire relies on a physical toggle to switch between its two operational modes.

*   **Development Implementation:** For early hardware iterations, the mode switch is implemented by manually bridging a specific GPIO pin to ground.
*   **Production Implementation:** The final enclosure will feature a recessed or discrete manual slide switch.
*   **Fail-Safe Design:** The default state (unbridged/open circuit) must always correspond to **Vault Mode (HID Keyboard)**. Mass Storage Mode (Sync) is only activated when the switch is explicitly closed, ensuring that if the switch fails, the device remains in its secure, read-only state.

## Physical Tampering & Security
Because VaultWire relies on the integrity of the Pi's operating system, physical access to the device is a significant attack vector (e.g., an Evil Maid attack where the SD card is swapped for a compromised image).

### Recommendations:
1.  **Tamper-Evident Seals:** Once the final enclosure is assembled, apply serialized, holographic tamper-evident seals across the seams of the case. Any attempt to open the case to access the internal components or the SD card slot should leave a visible void pattern, alerting the user to potential compromise.
2.  **Epoxy Potting (Optional):** For extreme threat models, consider potting the internal components (excluding the necessary connection ports) in an opaque epoxy resin to make hardware extraction or probing nearly impossible without destroying the device.

## Future Expansions (Stretch Goals)
The case design must be adaptable to accommodate future planned hardware expansions:
*   **Display Integration:** The top plate of the enclosure should allow for the integration of a small physical screen (e.g., a standard 0.96" or 1.3" OLED SPI module) to provide state feedback ("Locked", "Ready for ID", "Error"). This will be implemented once the final form factor is selected.