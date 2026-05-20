#!/usr/bin/env python3
"""Mo's Void - a terminal simulator/tycoon game."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable, Dict, List, Optional


@dataclass
class Item:
    name: str
    cost: int
    description: str
    apply: Callable[["GameState"], str]


@dataclass
class GameState:
    day: int = 1
    credits: int = 60
    scrap: int = 0
    food: int = 2
    health: int = 90
    energy: int = 85
    mood: int = 70
    pressure: int = 0
    beacon_level: int = 0
    escape_progress: int = 0
    salvage_level: int = 1
    active_buffs: Dict[str, int] = field(default_factory=dict)
    purchased_upgrades: set[str] = field(default_factory=set)
    running: bool = True

    def tick_buffs(self) -> None:
        expired = []
        for buff, turns in self.active_buffs.items():
            self.active_buffs[buff] = turns - 1
            if self.active_buffs[buff] <= 0:
                expired.append(buff)
        for buff in expired:
            del self.active_buffs[buff]

    def clamp(self) -> None:
        self.health = max(0, min(100, self.health))
        self.energy = max(0, min(100, self.energy))
        self.mood = max(0, min(100, self.mood))
        self.pressure = max(0, min(100, self.pressure))
        self.escape_progress = max(0, min(100, self.escape_progress))

    def daily_decay(self) -> None:
        if self.food > 0:
            self.food -= 1
            self.energy += 2
        else:
            self.health -= 10
            self.mood -= 8
        self.energy -= 7
        self.mood -= 5
        self.pressure += 4
        self.tick_buffs()
        self.clamp()


class MosVoidGame:
    def __init__(self) -> None:
        self.state = GameState()
        self.shop_items: List[Item] = [
            Item("Ration Crate", 25, "+3 food", self.buy_rations),
            Item("Comfy Blanket", 40, "+12 mood, +8 energy", self.buy_blanket),
            Item("Med Patch", 45, "+22 health", self.buy_med_patch),
            Item("Scrap Magnet", 65, "Permanent +1 salvage level", self.buy_magnet),
            Item("Beacon Core", 80, "Upgrade rescue beacon", self.buy_beacon_core),
            Item("Null Shield", 90, "Reduce pressure gain for 4 days", self.buy_null_shield),
        ]

    # --- Shop handlers ---
    def buy_rations(self, s: GameState) -> str:
        s.food += 3
        return "Mo stocked up on rations. No starving today."

    def buy_blanket(self, s: GameState) -> str:
        s.mood += 12
        s.energy += 8
        s.clamp()
        return "Mo wraps up in the cosmic blanket and chills out."

    def buy_med_patch(self, s: GameState) -> str:
        s.health += 22
        s.clamp()
        return "Med patch applied. Bruises and void burns fading."

    def buy_magnet(self, s: GameState) -> str:
        if "Scrap Magnet" in s.purchased_upgrades:
            return "Already installed."
        s.salvage_level += 1
        s.purchased_upgrades.add("Scrap Magnet")
        return "Scrap Magnet online: salvage runs are stronger now."

    def buy_beacon_core(self, s: GameState) -> str:
        if s.beacon_level >= 3:
            return "Beacon is already maxed out."
        s.beacon_level += 1
        s.escape_progress += 8
        s.clamp()
        return f"Beacon boosted to level {s.beacon_level}. Rescue signal intensifies."

    def buy_null_shield(self, s: GameState) -> str:
        s.active_buffs["null_shield"] = 4
        return "Null Shield activated: pressure rises slower for 4 days."

    # --- Actions ---
    def salvage_run(self) -> str:
        s = self.state
        base = random.randint(14, 26)
        level_bonus = s.salvage_level * 6
        haul = base + level_bonus + random.randint(-3, 3)
        if "focus" in s.active_buffs:
            haul += 8
        s.credits += haul
        s.energy -= random.randint(9, 15)
        s.health -= random.randint(2, 7)
        s.escape_progress += random.randint(1, 5)
        s.pressure += random.randint(1, 5)
        s.clamp()
        return f"Salvage run pulled {haul} credits worth of relic scrap."

    def rest(self) -> str:
        s = self.state
        if s.food <= 0:
            s.mood -= 4
            return "No food to rest properly. Mo feels rough."
        s.energy += random.randint(16, 24)
        s.health += random.randint(6, 10)
        s.mood += random.randint(5, 9)
        s.pressure -= random.randint(2, 6)
        s.clamp()
        return "Mo gets real rest in a quiet void pocket."

    def train(self) -> str:
        s = self.state
        s.energy -= random.randint(7, 12)
        s.health += random.randint(4, 8)
        s.mood += random.randint(2, 7)
        s.escape_progress += random.randint(2, 6)
        s.active_buffs["focus"] = 3
        s.clamp()
        return "Mo trains hard and enters focus mode for 3 days."

    def engineer(self) -> str:
        s = self.state
        if s.beacon_level == 0:
            s.escape_progress += random.randint(1, 3)
            s.energy -= 8
            return "Mo sketches a rough beacon plan. Need a Beacon Core soon."
        gain = random.randint(5, 12) + (2 * s.beacon_level)
        s.escape_progress += gain
        s.energy -= random.randint(8, 13)
        s.mood += random.randint(1, 4)
        s.pressure += random.randint(0, 3)
        s.clamp()
        return f"Beacon engineering session successful: +{gain}% escape progress."

    # --- Events ---
    def random_event(self) -> str:
        s = self.state
        roll = random.random()
        shielded = "null_shield" in s.active_buffs

        if roll < 0.16:
            bonus = random.randint(15, 40)
            s.credits += bonus
            return f"Lucky void cache discovered: +{bonus} credits."

        if roll < 0.32:
            dmg = random.randint(6, 13)
            pressure_hit = random.randint(4, 9)
            if shielded:
                pressure_hit //= 2
            s.health -= dmg
            s.pressure += pressure_hit
            s.clamp()
            return "A void storm tears through camp. Mo hangs on."

        if roll < 0.45:
            s.food += 2
            s.mood += 5
            s.clamp()
            return "A friendly drifter trades supplies with Mo."

        if roll < 0.57:
            gain = random.randint(3, 8)
            s.escape_progress += gain
            s.clamp()
            return f"Signal anomaly mapped. Escape route clarity +{gain}%."

        return "Quiet day in the void... for now."

    # --- Core game loop helpers ---
    def show_status(self) -> None:
        s = self.state
        print("\n" + "=" * 64)
        print(f"DAY {s.day}  |  Credits: {s.credits}  Food: {s.food}  Beacon Lv: {s.beacon_level}")
        print(
            f"Health: {s.health:3d}  Energy: {s.energy:3d}  Mood: {s.mood:3d}  "
            f"Void Pressure: {s.pressure:3d}"
        )
        print(f"Escape Progress: {s.escape_progress}%")
        if s.active_buffs:
            buffs = ", ".join(f"{k}({v})" for k, v in s.active_buffs.items())
            print(f"Active Buffs: {buffs}")
        print("=" * 64)

    def show_menu(self) -> None:
        print("\nChoose an action:")
        print("1) Salvage run (earn credits)")
        print("2) Rest (recover stats)")
        print("3) Train (boost progress + focus buff)")
        print("4) Engineer beacon")
        print("5) Shop")
        print("6) End run")

    def visit_shop(self) -> None:
        s = self.state
        while True:
            print("\n--- VOID SHOP ---")
            for i, item in enumerate(self.shop_items, start=1):
                print(f"{i}) {item.name:<13} {item.cost:>3}c  - {item.description}")
            print("0) Leave shop")
            choice = input("Buy what? > ").strip()
            if choice == "0":
                return
            if not choice.isdigit():
                print("Invalid pick.")
                continue
            item_index = int(choice)
            if not (1 <= item_index <= len(self.shop_items)):
                print("Invalid pick.")
                continue
            item = self.shop_items[item_index - 1]
            if s.credits < item.cost:
                print("Not enough credits.")
                continue
            s.credits -= item.cost
            print(item.apply(s))

    def check_end_conditions(self) -> Optional[str]:
        s = self.state
        if s.health <= 0:
            s.running = False
            return "Mo couldn't survive the void. Run failed."
        if s.energy <= 0:
            s.running = False
            return "Mo collapsed from exhaustion. Run failed."
        if s.pressure >= 100:
            s.running = False
            return "The void consumed the camp. Run failed."
        if s.escape_progress >= 100 and s.beacon_level >= 2:
            s.running = False
            return "Rescue lock achieved! Mo escapes the void in style!"
        return None

    def play_turn(self) -> None:
        s = self.state
        self.show_status()
        self.show_menu()
        choice = input("> ").strip()

        action_map = {
            "1": self.salvage_run,
            "2": self.rest,
            "3": self.train,
            "4": self.engineer,
        }

        if choice in action_map:
            print(action_map[choice]())
        elif choice == "5":
            self.visit_shop()
        elif choice == "6":
            s.running = False
            print("Mo ends this run and prepares for another shot.")
            return
        else:
            print("Invalid choice. Time slips away in the void...")
            s.mood -= 2

        event_text = self.random_event()
        print(f"Event: {event_text}")

        if "null_shield" in s.active_buffs:
            s.pressure = max(0, s.pressure - 2)

        s.daily_decay()

        ending = self.check_end_conditions()
        if ending:
            print("\n" + ending)
        else:
            s.day += 1

    def run(self) -> None:
        print("\n🌌  MO'S VOID: SIMULATOR / TYCOON  🌌")
        print(
            "Guide Mo through the void. Buy upgrades, manage stats, and "
            "build a rescue beacon to escape."
        )
        print("Win by reaching 100% escape progress with at least Beacon Level 2.\n")

        while self.state.running:
            self.play_turn()

        print("\nFinal stats:")
        self.show_status()
        print("Thanks for playing Mo's Void.")


def main() -> None:
    random.seed()
    MosVoidGame().run()


if __name__ == "__main__":
    main()
