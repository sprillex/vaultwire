This is a stretch goal to be refined and possibly implemented at a later date.

Phase 1: The Challenge (Host to Pi)

    You plug VaultWire into your Linux Mint PC.

    The companion app generates a random, single-use security string (a nonce).

    The companion app rapidly toggles your PC's Caps Lock state like a high-speed telegraph, converting that security string into binary code (1 for LED On, 0 for LED Off).

    The Pi reads these raw state changes directly from its emulated keyboard driver and reconstructs the string.

Phase 2: The Response (Pi to Host)

    The Pi takes its entire static, read-only operating system partition and hashes it using SHA-256, mixed with the random challenge string it just received.

    The Pi mimics a keyboard and rapidly types the resulting hash signature back up the wire into the waiting companion app terminal window.

Phase 3: The Verdict

    The companion app calculates what the answer should look like using its own local master hash record.

    If the two signatures match perfectly, the companion app signals approval, and the Pi releases its lock screen to let you type your master database password. If it fails, the Pi halts instantly.

🛡️ Why This Setup Wins

    No Serial Drivers Needed: The Pi remains a pure USB keyboard device to your operating system; you don't have to configure composite network or serial gadget profiles.

    Immune to Replay Attacks: Because the challenge string is entirely unique every time you boot, an attacker cannot record an old, valid hash sequence and play it back to trick the PC.

    Zero Trust Anchor: The Pi doesn't need to protect its own verification keys; the trust is entirely anchored inside your secure Linux Mint machine.
