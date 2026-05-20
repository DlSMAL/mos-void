#!/usr/bin/env python3
"""Mo's Void - a terminal simulator/tycoon game."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable, Dict, List, Optional


BANNER_ART = r"""
███╗   ███╗ ██████╗ ███████╗    ██╗   ██╗ ██████╗ ██╗██████╗
████╗ ████║██╔═══██╗██╔════╝    ██║   ██║██╔═══██╗██║██╔══██╗
██╔████╔██║██║   ██║███████╗    ██║   ██║██║   ██║██║██║  ██║
██║╚██╔╝██║██║   ██║╚════██║    ╚██╗ ██╔╝██║   ██║██║██║  ██║
██║ ╚═╝ ██║╚██████╔╝███████║     ╚████╔╝ ╚██████╔╝██║██████╔╝
╚═╝     ╚═╝ ╚═════╝ ╚══════╝      ╚═══╝   ╚═════╝ ╚═╝╚═════╝
"""

CAMP_ART = r"""
      .      *       .
   *       .      .      .
      .       /\
            _/  \_      .
        ___/  /\  \___
       /___\_/__\_/___\
         ||  ||  ||
         ||  ||  ||     [MO'S CAMP]
"""

BEACON_ART = r"""
              /\
             /  \
            /====\
           /  ||  \
          /___||___\
              ||
              ||        <<< SIGNAL >>>
           ___||___
          /________\
"""

MISSION_DEFINITIONS = [
    ("Complete 2 salvage runs today", "salvage", 2, 30, 5),
    ("Train 2 times today", "train", 2, 22, 6),
    ("Engineer beacon once today", "engineer", 1, 20, 8),
    ("Scout the rift 2 times today", "scout", 2, 24, 6),
]
CRAFT_SCRAP_COST = 8
BEACON_EVENT_THRESHOLD = 0.62
BEACON_EVENT_MIN_LEVEL = 2
MAX_DRONE_LEVEL = 3
WIN_BEACON_LEVEL = 3
MAX_BEACON_LEVEL = 4
BEACON_CORE_PROGRESS_BONUS = 9
BEACON_ENGINEERING_MULTIPLIER = 3


@dataclass
class Item:
    name: str
    cost: int
    description: str
    apply: Callable[["GameState"], str]


@dataclass
class DailyMission:
    text: str
    kind: str
    goal: int
    reward_credits: int
    reward_progress: int
    progress: int = 0
    completed: bool = False


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
    drone_level: int = 0
    detail_score: int = 0
    active_buffs: Dict[str, int] = field(default_factory=dict)
    purchased_upgrades: set[str] = field(default_factory=set)
    running: bool = True
    difficulty: str = "standard"
    decay_scale: float = 1.0
    reward_scale: float = 1.0
    daily_mission: Optional[DailyMission] = None

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

    def scaled(self, value: int, reward: bool = False) -> int:
        factor = self.reward_scale if reward else self.decay_scale
        return int(round(value * factor))

    def daily_decay(self) -> None:
        if self.food > 0:
            self.food -= 1
            self.energy += self.scaled(2)
        else:
            self.health -= self.scaled(10)
            self.mood -= self.scaled(8)
        self.energy -= self.scaled(7)
        self.mood -= self.scaled(5)
        self.pressure += self.scaled(4)
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
            Item("Scout Drone", 90, "Permanent +1 drone level", self.buy_drone),
            Item("Beacon Core", 95, "Upgrade rescue beacon", self.buy_beacon_core),
            Item("Null Shield", 90, "Reduce pressure gain for 4 days", self.buy_null_shield),
        ]

    # --- Setup ---
    def choose_difficulty(self) -> None:
        print("Choose difficulty:")
        print("1) Chill (safer, slower score gain)")
        print("2) Standard")
        print("3) Nightmare (hard but high score)")
        picked = input("> ").strip()

        s = self.state
        if picked == "1":
            s.difficulty = "chill"
            s.decay_scale = 0.8
            s.reward_scale = 0.9
        elif picked == "3":
            s.difficulty = "nightmare"
            s.decay_scale = 1.25
            s.reward_scale = 1.2
        else:
            s.difficulty = "standard"
            s.decay_scale = 1.0
            s.reward_scale = 1.0

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

    def buy_drone(self, s: GameState) -> str:
        if s.drone_level >= MAX_DRONE_LEVEL:
            return "Scout Drone is already maxed out."
        s.drone_level += 1
        s.escape_progress += s.scaled(3, reward=True)
        s.clamp()
        return f"Scout Drone upgraded to level {s.drone_level}. Mapping improves."

    def buy_beacon_core(self, s: GameState) -> str:
        if s.beacon_level >= MAX_BEACON_LEVEL:
            return "Beacon is already maxed out."
        s.beacon_level += 1
        s.escape_progress += s.scaled(BEACON_CORE_PROGRESS_BONUS, reward=True)
        s.clamp()
        return f"Beacon boosted to level {s.beacon_level}. Rescue signal intensifies."

    def buy_null_shield(self, s: GameState) -> str:
        s.active_buffs["null_shield"] = 4
        return "Null Shield activated: pressure rises slower for 4 days."

    # --- Mission helpers ---
    def roll_daily_mission(self) -> None:
        s = self.state
        mission_pool = [DailyMission(*definition) for definition in MISSION_DEFINITIONS]
        s.daily_mission = random.choice(mission_pool)

    def update_mission(self, kind: str) -> Optional[str]:
        s = self.state
        m = s.daily_mission
        if not m or m.completed or m.kind != kind:
            return None
        m.progress += 1
        if m.progress >= m.goal:
            m.completed = True
            s.credits += s.scaled(m.reward_credits, reward=True)
            s.escape_progress += s.scaled(m.reward_progress, reward=True)
            s.detail_score += s.scaled(15, reward=True)
            s.clamp()
            return (
                f"Mission complete! +{s.scaled(m.reward_credits, reward=True)} credits, "
                f"+{s.scaled(m.reward_progress, reward=True)}% progress."
            )
        return f"Mission progress: {m.progress}/{m.goal}"

    # --- Actions ---
    def salvage_run(self) -> str:
        s = self.state
        base = random.randint(14, 26)
        level_bonus = s.salvage_level * 6
        drone_bonus = s.drone_level * 4
        haul = base + level_bonus + drone_bonus + random.randint(-3, 3)
        if "focus" in s.active_buffs:
            haul += 8
        haul = s.scaled(haul, reward=True)
        s.credits += haul
        s.scrap += random.randint(1, 4) + s.drone_level
        s.energy -= s.scaled(random.randint(9, 15))
        s.health -= s.scaled(random.randint(2, 7))
        s.escape_progress += s.scaled(random.randint(1, 5), reward=True)
        s.pressure += s.scaled(random.randint(1, 5))
        s.detail_score += s.scaled(6, reward=True)
        s.clamp()
        return f"Salvage run pulled {haul} credits and boosted your scrap reserves."

    def rest(self) -> str:
        s = self.state
        if s.food <= 0:
            s.mood -= s.scaled(4)
            return "No food to rest properly. Mo feels rough."
        s.energy += s.scaled(random.randint(16, 24), reward=True)
        s.health += s.scaled(random.randint(6, 10), reward=True)
        s.mood += s.scaled(random.randint(5, 9), reward=True)
        s.pressure -= s.scaled(random.randint(2, 6), reward=True)
        s.detail_score += s.scaled(3, reward=True)
        s.clamp()
        return "Mo gets real rest in a quiet void pocket."

    def train(self) -> str:
        s = self.state
        s.energy -= s.scaled(random.randint(7, 12))
        s.health += s.scaled(random.randint(4, 8), reward=True)
        s.mood += s.scaled(random.randint(2, 7), reward=True)
        s.escape_progress += s.scaled(random.randint(2, 6), reward=True)
        s.active_buffs["focus"] = 3
        s.detail_score += s.scaled(8, reward=True)
        s.clamp()
        return "Mo trains hard and enters focus mode for 3 days."

    def engineer(self) -> str:
        s = self.state
        if s.beacon_level == 0:
            s.escape_progress += s.scaled(random.randint(1, 3), reward=True)
            s.energy -= s.scaled(8)
            return "Mo sketches a rough beacon plan. Need a Beacon Core soon."
        gain = s.scaled(
            random.randint(5, 12) + (BEACON_ENGINEERING_MULTIPLIER * s.beacon_level),
            reward=True,
        )
        s.escape_progress += gain
        s.energy -= s.scaled(random.randint(8, 13))
        s.mood += s.scaled(random.randint(1, 4), reward=True)
        s.pressure += s.scaled(random.randint(0, 3))
        s.detail_score += s.scaled(10, reward=True)
        s.clamp()
        return f"Beacon engineering session successful: +{gain}% escape progress."

    def scout_rift(self) -> str:
        s = self.state
        found_food = random.randint(0, 2) + s.drone_level
        found_scrap = random.randint(2, 7) + s.drone_level
        stress = random.randint(2, 6)
        if "null_shield" in s.active_buffs:
            stress = max(1, stress - 2)
        s.food += found_food
        s.scrap += found_scrap
        s.energy -= s.scaled(random.randint(6, 11))
        s.mood += s.scaled(random.randint(1, 5), reward=True)
        s.pressure += s.scaled(stress)
        s.detail_score += s.scaled(7, reward=True)
        s.clamp()
        return f"Rift scouting found {found_food} food and {found_scrap} scrap."

    def craft_from_scrap(self) -> str:
        s = self.state
        if s.scrap < CRAFT_SCRAP_COST:
            return f"Need at least {CRAFT_SCRAP_COST} scrap to craft field gear."
        s.scrap -= CRAFT_SCRAP_COST
        pick = random.choice(["kit", "filter", "scanner"])
        if pick == "kit":
            s.health += s.scaled(14, reward=True)
            s.energy += s.scaled(8, reward=True)
            result = "Mo crafted a med kit."
        elif pick == "filter":
            s.pressure -= s.scaled(12, reward=True)
            s.mood += s.scaled(6, reward=True)
            result = "Mo built a void filter and stabilized camp air."
        else:
            s.active_buffs["focus"] = 4
            s.escape_progress += s.scaled(6, reward=True)
            result = "Mo assembled a deep scanner. Focus extends to 4 days."
        s.detail_score += s.scaled(12, reward=True)
        s.clamp()
        return result

    # --- Events ---
    def random_event(self) -> str:
        s = self.state
        roll = random.random()
        shielded = "null_shield" in s.active_buffs

        if roll < 0.14:
            bonus = s.scaled(random.randint(15, 40), reward=True)
            s.credits += bonus
            return f"Lucky void cache discovered: +{bonus} credits."

        if roll < 0.28:
            dmg = s.scaled(random.randint(6, 13))
            pressure_hit = s.scaled(random.randint(4, 9))
            if shielded:
                pressure_hit //= 2
            s.health -= dmg
            s.pressure += pressure_hit
            s.clamp()
            return "A void storm tears through camp. Mo hangs on."

        if roll < 0.42:
            s.food += random.randint(1, 3)
            s.mood += s.scaled(5, reward=True)
            s.clamp()
            return "A friendly drifter trades supplies with Mo."

        if roll < 0.54:
            gain = s.scaled(random.randint(3, 8), reward=True)
            s.escape_progress += gain
            s.clamp()
            return f"Signal anomaly mapped. Escape route clarity +{gain}%."

        if roll < BEACON_EVENT_THRESHOLD and s.beacon_level >= BEACON_EVENT_MIN_LEVEL:
            beacon_bonus = s.scaled(random.randint(8, 14), reward=True)
            s.escape_progress += beacon_bonus
            s.mood += s.scaled(4, reward=True)
            s.clamp()
            return f"Beacon pulse synced perfectly: +{beacon_bonus}% progress."

        return "Quiet day in the void... for now."

    # --- Core game loop helpers ---
    def show_status(self) -> None:
        s = self.state
        print("\n" + "=" * 72)
        print(f"DAY {s.day} | Difficulty: {s.difficulty.title()} | Detail Score: {s.detail_score}")
        print(
            f"Credits: {s.credits:4d} | Scrap: {s.scrap:3d} | Food: {s.food:2d} | "
            f"Beacon Lv: {s.beacon_level} | Drone Lv: {s.drone_level}"
        )
        print(
            f"Health: {s.health:3d}  Energy: {s.energy:3d}  Mood: {s.mood:3d}  "
            f"Void Pressure: {s.pressure:3d}"
        )
        print(f"Escape Progress: {s.escape_progress}%")
        if s.active_buffs:
            buffs = ", ".join(f"{k}({v})" for k, v in s.active_buffs.items())
            print(f"Active Buffs: {buffs}")
        if s.daily_mission:
            m = s.daily_mission
            status = "DONE" if m.completed else f"{m.progress}/{m.goal}"
            print(f"Daily Mission: {m.text} [{status}]")
        print("=" * 72)

    def show_menu(self) -> None:
        print("\nChoose an action:")
        print("1) Salvage run (earn credits + scrap)")
        print("2) Rest (recover stats)")
        print("3) Train (boost progress + focus buff)")
        print("4) Engineer beacon")
        print("5) Scout rift (find food/scrap)")
        print("6) Craft from scrap")
        print("7) Shop")
        print("8) End run")

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
        if s.escape_progress >= 100 and s.beacon_level >= WIN_BEACON_LEVEL:
            s.running = False
            return "Rescue lock achieved! Mo escapes the void in style!"
        return None

    def perform_action(self, choice: str) -> Optional[str]:
        # Shop and end-run are stateful flows handled directly in play_turn.
        action_map = {
            "1": (self.salvage_run, "salvage"),
            "2": (self.rest, "rest"),
            "3": (self.train, "train"),
            "4": (self.engineer, "engineer"),
            "5": (self.scout_rift, "scout"),
            "6": (self.craft_from_scrap, "craft"),
        }
        if choice not in action_map:
            return None
        handler, mission_kind = action_map[choice]
        result = handler()
        mission_text = self.update_mission(mission_kind)
        if mission_text:
            result = f"{result}\n{mission_text}"
        return result

    def play_turn(self) -> None:
        s = self.state
        if not s.daily_mission or s.daily_mission.completed:
            self.roll_daily_mission()

        self.show_status()
        self.show_menu()
        choice = input("> ").strip()

        if choice in {"1", "2", "3", "4", "5", "6"}:
            print(self.perform_action(choice))
        elif choice == "7":
            self.visit_shop()
        elif choice == "8":
            s.running = False
            print("Mo ends this run and prepares for another shot.")
            return
        else:
            print("Invalid choice. Time slips away in the void...")
            s.mood -= s.scaled(2)

        event_text = self.random_event()
        print(f"Event: {event_text}")

        if "null_shield" in s.active_buffs:
            s.pressure = max(0, s.pressure - s.scaled(2, reward=True))

        s.daily_decay()

        ending = self.check_end_conditions()
        if ending:
            print("\n" + ending)
        else:
            s.day += 1

    def run(self) -> None:
        print("\n" + BANNER_ART)
        print(CAMP_ART)
        print(
            "Guide Mo through the void. Buy upgrades, manage stats, and "
            "build a rescue beacon to escape."
        )
        print(BEACON_ART)
        print(
            f"Win by reaching 100% escape progress with at least Beacon Level {WIN_BEACON_LEVEL} "
            f"(max {MAX_BEACON_LEVEL}).\n"
        )
        self.choose_difficulty()

        while self.state.running:
            self.play_turn()

        print("\nFinal stats:")
        self.show_status()
        print("Thanks for playing Mo's Void.")


def main() -> None:
    MosVoidGame().run()


if __name__ == "__main__":
    main()
