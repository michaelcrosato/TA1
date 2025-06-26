#!/usr/bin/env python3
"""
Text-Based RPG - Phase 4: Quests & Polish
A modular, extensible text-based RPG built using single-file architecture.
All game logic lives in this file for maximum LLM visibility.
"""

import json
import os
import sys
import random
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
import re

# === [CONFIGURATION] ===
class Config:
    """All game constants and configuration."""
    GAME_TITLE = "Text RPG Adventure"
    VERSION = "1.0.0 - Phase 4"
    DATA_DIR = "data"
    SAVES_DIR = "saves"
    LOGS_DIR = "logs"
    DEBUG_MODE = False
    
    # Game balance
    STARTING_INVENTORY_SIZE = 10  # Increased from 3 for Phase 3
    STARTING_HEALTH = 20
    STARTING_STRENGTH = 3
    STARTING_DEFENSE = 2
    STARTING_AGILITY = 5
    STARTING_GOLD = 25  # Increased starting gold
    STARTING_LEVEL = 1
    STARTING_XP = 0
    
    # Progression system
    XP_THRESHOLDS = [100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500, 5500]  # XP needed for each level
    LEVEL_STRENGTH_BONUS = 2  # +2 Strength per level
    LEVEL_DEFENSE_BONUS = 1   # +1 Defense per level  
    LEVEL_HEALTH_BONUS = 5    # +5 Max HP per level
    
    # Combat balance
    DEFEND_BONUS = 0.5  # 50% defense boost when defending
    FLEE_SUCCESS_BASE = 0.7  # Base chance to flee successfully
    ENCOUNTER_CHANCE = 0.3  # Chance of enemy encounter when moving
    
    # Economy
    HEALING_SERVICE_COST = 5  # Cost per HP to heal at tavern
    MERCHANT_MARKUP = 1.5     # Merchant sells at 150% of item value
    MERCHANT_BUYBACK = 0.6    # Merchant buys at 60% of item value
    
    # Quest system
    MAX_ACTIVE_QUESTS = 5     # Maximum concurrent active quests
    QUEST_XP_MULTIPLIER = 1.5 # Bonus XP multiplier for quest completion
    
    # File paths
    ROOMS_FILE = os.path.join(DATA_DIR, "rooms.json")
    ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
    ENEMIES_FILE = os.path.join(DATA_DIR, "enemies.json")
    COMBAT_TEXT_FILE = os.path.join(DATA_DIR, "combat_text.json")
    QUESTS_FILE = os.path.join(DATA_DIR, "quests.json")
    SAVE_FILE = os.path.join(SAVES_DIR, "savegame.json")
    DEBUG_LOG = os.path.join(LOGS_DIR, "debug.log")

# === [GLOBAL STATE] ===
game_state = {
    'mode': 'exploration',  # exploration, combat, dialogue
    'current_room': 'tavern',
    'player': None,
    'running': True,
    'first_play': True,
    'debug_mode': False,
    'combat': None,  # Current combat state
    'last_save_room': 'tavern'  # For respawn on death
}

# Data storage
rooms_data = {}
items_data = {}
enemies_data = {}
combat_text_data = {}
quests_data = {}

# === [LOGGING SYSTEM] ===
def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [Config.DATA_DIR, Config.SAVES_DIR, Config.LOGS_DIR]:
        os.makedirs(directory, exist_ok=True)

def log_event(event_type: str, message: str) -> None:
    """Log game events for debugging.
    
    Side effects:
        - Writes to debug.log file
        - Creates log directory if needed
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {event_type}: {message}\n"
        
        with open(Config.DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(log_message)
            
        if Config.DEBUG_MODE:
            print(f"DEBUG: {log_message.strip()}")
    except Exception as e:
        print(f"Logging error: {e}")

# === [DATA CLASSES] ===
@dataclass
class Quest:
    """Quest data structure."""
    quest_id: str
    title: str
    description: str
    objectives: List[Dict[str, Any]]
    rewards: Dict[str, Any]
    status: str = "available"  # available, active, completed, failed
    giver_npc: str = ""
    completion_text: str = ""
    
    @classmethod
    def from_template(cls, quest_id: str) -> Optional['Quest']:
        """Create quest from template data."""
        if quest_id not in quests_data:
            return None
        
        template = quests_data[quest_id]
        return cls(
            quest_id=quest_id,
            title=template["title"],
            description=template["description"],
            objectives=template["objectives"].copy(),
            rewards=template["rewards"],
            giver_npc=template.get("giver_npc", ""),
            completion_text=template.get("completion_text", "Quest completed!")
        )
    
    def is_completed(self) -> bool:
        """Check if all quest objectives are completed."""
        return all(obj.get("completed", False) for obj in self.objectives)
    
    def get_progress_text(self) -> str:
        """Get text showing quest progress."""
        lines = [f"📜 {self.title}"]
        lines.append(f"   {self.description}")
        
        for i, obj in enumerate(self.objectives, 1):
            status = "✅" if obj.get("completed", False) else "❌"
            lines.append(f"   {status} {obj['description']}")
        
        return "\n".join(lines)

@dataclass
class Player:
    """Player character data structure."""
    name: str = "Hero"
    current_room: str = "tavern"
    inventory: List[str] = field(default_factory=list)
    max_inventory: int = Config.STARTING_INVENTORY_SIZE
    
    # Combat stats
    health: int = Config.STARTING_HEALTH
    max_health: int = Config.STARTING_HEALTH
    strength: int = Config.STARTING_STRENGTH
    defense: int = Config.STARTING_DEFENSE
    agility: int = Config.STARTING_AGILITY
    gold: int = Config.STARTING_GOLD
    
    # Progression stats
    level: int = Config.STARTING_LEVEL
    experience: int = Config.STARTING_XP
    
    # Quest tracking
    active_quests: List[str] = field(default_factory=list)
    completed_quests: List[str] = field(default_factory=list)
    quest_progress: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Combat state
    defending: bool = False  # Gets defense bonus this turn
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None
    
    def can_carry_more(self) -> bool:
        """Check if player can carry more items."""
        return len(self.inventory) < self.max_inventory
    
    def add_item(self, item_id: str) -> bool:
        """Add item to inventory if there's space.
        
        Returns:
            bool: True if item was added, False if inventory full
        """
        if self.can_carry_more():
            self.inventory.append(item_id)
            log_event("INVENTORY", f"Added {item_id} to inventory")
            return True
        return False
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from inventory.
        
        Returns:
            bool: True if item was removed, False if not found
        """
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            log_event("INVENTORY", f"Removed {item_id} from inventory")
            return True
        return False
    
    def has_item(self, item_id: str) -> bool:
        """Check if player has specific item."""
        return item_id in self.inventory
    
    def get_attack_power(self) -> int:
        """Calculate total attack power including equipment."""
        base_attack = self.strength
        weapon_bonus = 0
        
        if self.equipped_weapon and self.equipped_weapon in items_data:
            weapon_stats = items_data[self.equipped_weapon].get("stats", {})
            weapon_bonus = weapon_stats.get("attack", 0)
        
        return base_attack + weapon_bonus
    
    def get_defense_power(self) -> int:
        """Calculate total defense including equipment and defending state."""
        base_defense = self.defense
        armor_bonus = 0
        defend_bonus = 0
        
        if self.equipped_armor and self.equipped_armor in items_data:
            armor_stats = items_data[self.equipped_armor].get("stats", {})
            armor_bonus = armor_stats.get("defense", 0)
        
        if self.defending:
            defend_bonus = int((base_defense + armor_bonus) * Config.DEFEND_BONUS)
        
        return base_defense + armor_bonus + defend_bonus
    
    def take_damage(self, damage: int) -> int:
        """Apply damage to player, return actual damage taken."""
        actual_damage = max(1, damage - self.get_defense_power())  # Always at least 1 damage
        self.health = max(0, self.health - actual_damage)
        log_event("COMBAT", f"Player took {actual_damage} damage (health: {self.health}/{self.max_health})")
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Heal player, return actual amount healed."""
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        actual_heal = self.health - old_health
        log_event("COMBAT", f"Player healed {actual_heal} health (health: {self.health}/{self.max_health})")
        return actual_heal
    
    def is_alive(self) -> bool:
        """Check if player is still alive."""
        return self.health > 0
    
    def is_low_health(self) -> bool:
        """Check if player is at low health."""
        return self.health <= self.max_health * 0.25  # 25% or less
    
    def get_health_bar(self) -> str:
        """Get visual health bar representation."""
        if self.max_health == 0:
            return "HP: [----------] 0/0"
        
        bar_length = 10
        filled = int((self.health / self.max_health) * bar_length)
        empty = bar_length - filled
        
        bar = "█" * filled + "-" * empty
        return f"HP: [{bar}] {self.health}/{self.max_health}"
    
    def get_xp_bar(self) -> str:
        """Get visual XP bar representation."""
        if self.level > len(Config.XP_THRESHOLDS):
            return "XP: [MAX LEVEL]"
        
        # Calculate XP for current level
        current_threshold = Config.XP_THRESHOLDS[self.level - 2] if self.level > 1 else 0
        next_threshold = Config.XP_THRESHOLDS[self.level - 1]
        
        xp_in_level = self.experience - current_threshold
        xp_needed = next_threshold - current_threshold
        
        bar_length = 10
        filled = int((xp_in_level / xp_needed) * bar_length) if xp_needed > 0 else bar_length
        empty = bar_length - filled
        
        bar = "█" * filled + "-" * empty
        return f"XP: [{bar}] {self.experience}/{next_threshold}"
    
    def gain_experience(self, amount: int) -> bool:
        """Add experience and check for level up."""
        self.experience += amount
        log_event("PROGRESSION", f"Player gained {amount} XP (total: {self.experience})")
        
        # Check for level up
        if self.level <= len(Config.XP_THRESHOLDS):
            threshold = Config.XP_THRESHOLDS[self.level - 1]
            if self.experience >= threshold:
                return self.level_up()
        
        return False
    
    def level_up(self) -> bool:
        """Level up the player and increase stats."""
        if self.level >= len(Config.XP_THRESHOLDS):
            return False  # Max level reached
        
        old_level = self.level
        self.level += 1
        
        # Increase stats
        old_max_health = self.max_health
        self.strength += Config.LEVEL_STRENGTH_BONUS
        self.defense += Config.LEVEL_DEFENSE_BONUS
        self.max_health += Config.LEVEL_HEALTH_BONUS
        
        # Heal to full when leveling up
        health_gained = self.max_health - old_max_health
        self.health = self.max_health
        
        # Display level up message
        print("\n" + "="*50)
        print("🌟 LEVEL UP! 🌟")
        print(f"You have reached level {self.level}!")
        print(f"Strength increased by {Config.LEVEL_STRENGTH_BONUS}! (now {self.strength})")
        print(f"Defense increased by {Config.LEVEL_DEFENSE_BONUS}! (now {self.defense})")
        print(f"Max Health increased by {Config.LEVEL_HEALTH_BONUS}! (now {self.max_health})")
        print("You feel refreshed and healed to full health!")
        print("="*50)
        
        log_event("PROGRESSION", f"Player leveled up from {old_level} to {self.level}")
        return True
    
    def can_afford(self, cost: int) -> bool:
        """Check if player can afford something."""
        return self.gold >= cost
    
    def spend_gold(self, amount: int) -> bool:
        """Spend gold if player has enough."""
        if self.can_afford(amount):
            self.gold -= amount
            log_event("ECONOMY", f"Player spent {amount} gold (remaining: {self.gold})")
            return True
        return False
    
    def earn_gold(self, amount: int) -> None:
        """Add gold to player's purse."""
        self.gold += amount
        log_event("ECONOMY", f"Player earned {amount} gold (total: {self.gold})")
    
    def can_accept_quest(self) -> bool:
        """Check if player can accept more quests."""
        return len(self.active_quests) < Config.MAX_ACTIVE_QUESTS
    
    def accept_quest(self, quest_id: str) -> bool:
        """Accept a new quest."""
        if not self.can_accept_quest():
            return False
        
        if quest_id in self.active_quests or quest_id in self.completed_quests:
            return False
        
        self.active_quests.append(quest_id)
        self.quest_progress[quest_id] = {}
        log_event("QUEST", f"Player accepted quest: {quest_id}")
        return True
    
    def complete_quest(self, quest_id: str) -> bool:
        """Complete a quest and move it to completed list."""
        if quest_id not in self.active_quests:
            return False
        
        self.active_quests.remove(quest_id)
        self.completed_quests.append(quest_id)
        
        # Clean up progress tracking
        if quest_id in self.quest_progress:
            del self.quest_progress[quest_id]
        
        log_event("QUEST", f"Player completed quest: {quest_id}")
        return True
    
    def update_quest_progress(self, quest_id: str, objective_key: str, value: Any) -> None:
        """Update progress on a quest objective."""
        if quest_id not in self.quest_progress:
            self.quest_progress[quest_id] = {}
        
        self.quest_progress[quest_id][objective_key] = value
        log_event("QUEST", f"Quest progress updated: {quest_id} - {objective_key}: {value}")
    
    def get_quest_progress(self, quest_id: str, objective_key: str, default: Any = 0) -> Any:
        """Get current progress on a quest objective."""
        return self.quest_progress.get(quest_id, {}).get(objective_key, default)

# === [GAME ENTITIES] ===
@dataclass
class Enemy:
    """Enemy entity with combat capabilities."""
    enemy_id: str
    name: str
    description: str
    health: int
    max_health: int
    attack: int
    defense: int
    agility: int
    ai_pattern: Dict[str, float]
    loot_table: Dict[str, Any]
    
    # Combat state
    defending: bool = False
    
    @classmethod
    def from_template(cls, enemy_id: str) -> Optional['Enemy']:
        """Create enemy from template data."""
        if enemy_id not in enemies_data:
            return None
        
        template = enemies_data[enemy_id]
        return cls(
            enemy_id=enemy_id,
            name=template["name"],
            description=template["description"],
            health=template["health"],
            max_health=template["max_health"],
            attack=template["attack"],
            defense=template["defense"],
            agility=template["agility"],
            ai_pattern=template["ai_pattern"],
            loot_table=template["loot_table"]
        )
    
    def take_damage(self, damage: int) -> int:
        """Apply damage to enemy, return actual damage taken."""
        defense_value = self.defense
        if self.defending:
            defense_value = int(defense_value * (1 + Config.DEFEND_BONUS))
        
        actual_damage = max(1, damage - defense_value)
        self.health = max(0, self.health - actual_damage)
        log_event("COMBAT", f"{self.name} took {actual_damage} damage (health: {self.health}/{self.max_health})")
        return actual_damage
    
    def is_alive(self) -> bool:
        """Check if enemy is still alive."""
        return self.health > 0
    
    def is_low_health(self) -> bool:
        """Check if enemy is at low health."""
        return self.health <= self.max_health * self.ai_pattern.get("flee_threshold", 0.3)
    
    def choose_action(self) -> str:
        """AI chooses an action based on patterns."""
        # Check if should flee when low health
        if self.is_low_health() and random.random() < self.ai_pattern.get("flee_chance", 0):
            return "flee"
        
        # Choose based on AI pattern
        rand = random.random()
        if rand < self.ai_pattern.get("attack_chance", 0.8):
            return "attack"
        elif rand < self.ai_pattern.get("attack_chance", 0.8) + self.ai_pattern.get("defend_chance", 0.2):
            return "defend"
        else:
            return "attack"  # Default fallback
    
    def get_health_bar(self) -> str:
        """Get visual health bar representation."""
        if self.max_health == 0:
            return "HP: [----------] 0/0"
        
        bar_length = 10
        filled = int((self.health / self.max_health) * bar_length)
        empty = bar_length - filled
        
        bar = "█" * filled + "-" * empty
        return f"HP: [{bar}] {self.health}/{self.max_health}"
    
    def generate_loot(self) -> Dict[str, Any]:
        """Generate loot based on loot table."""
        loot = {"gold": 0, "items": []}
        
        # Generate gold
        gold_min = self.loot_table.get("gold_min", 0)
        gold_max = self.loot_table.get("gold_max", 0)
        if gold_max > 0:
            loot["gold"] = random.randint(gold_min, gold_max)
        
        # Generate items
        for item_chance in self.loot_table.get("items", []):
            if random.random() < item_chance["chance"]:
                loot["items"].append(item_chance["item"])
        
        return loot

@dataclass
class CombatState:
    """Manages active combat state."""
    enemy: Enemy
    turn_count: int = 0
    player_initiative: bool = True
    
    def is_active(self) -> bool:
        """Check if combat is still active."""
        return self.enemy.is_alive() and game_state['player'].is_alive()

class Room:
    """Room entity with navigation and interaction."""
    
    def __init__(self, room_id: str, data: Dict[str, Any]):
        self.id = room_id
        self.name = data.get("name", "Unknown Room")
        self.description = data.get("description", "An empty room.")
        self.details = data.get("details", {})
        self.exits = data.get("exits", {})
        self.items = data.get("items", []).copy()  # Copy to avoid modifying original
        self.npcs = data.get("npcs", [])
    
    def get_full_description(self) -> str:
        """Get the complete room description with items and exits."""
        desc_parts = [self.name, self.description]
        
        # Add items if present
        if self.items:
            item_names = []
            for item_id in self.items:
                if item_id in items_data:
                    item_names.append(items_data[item_id].get("name", item_id))
                else:
                    item_names.append(item_id)
            desc_parts.append(f"You see: {', '.join(item_names)}")
        
        # Add exits
        if self.exits:
            exit_names = [direction.title() for direction in self.exits.keys()]
            desc_parts.append(f"Exits: {', '.join(exit_names)}")
        
        return "\n".join(desc_parts)
    
    def examine_object(self, object_name: str) -> Optional[str]:
        """Get detailed description of an object in the room."""
        # Normalize the object name
        object_key = object_name.lower().replace(" ", "_")
        
        # Check details dictionary
        if object_key in self.details:
            return self.details[object_key]
        
        # Check for partial matches
        for key, description in self.details.items():
            if object_key in key or key in object_key:
                return description
        
        return None
    
    def can_go(self, direction: str) -> bool:
        """Check if player can go in specified direction."""
        return direction.lower() in self.exits
    
    def get_exit(self, direction: str) -> Optional[str]:
        """Get the room ID for the specified direction."""
        return self.exits.get(direction.lower())
    
    def add_item(self, item_id: str):
        """Add item to room."""
        if item_id not in self.items:
            self.items.append(item_id)
            log_event("ROOM", f"Added {item_id} to {self.id}")
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from room."""
        if item_id in self.items:
            self.items.remove(item_id)
            log_event("ROOM", f"Removed {item_id} from {self.id}")
            return True
        return False
    
    def has_item(self, item_id: str) -> bool:
        """Check if room contains item."""
        return item_id in self.items

# === [COMMAND PARSER] ===
def normalize_input(text: str) -> str:
    """Clean and normalize user input."""
    return text.strip().lower()

def get_available_commands() -> List[str]:
    """Return commands valid in current game state."""
    if game_state['mode'] == 'exploration':
        return ['go', 'north', 'south', 'east', 'west', 'n', 's', 'e', 'w',
                'look', 'l', 'examine', 'x', 'take', 'drop', 'inventory', 'i', 'use',
                'stats', 'help', 'quit', 'save', 'debug', 'buy', 'sell', 'talk', 'heal',
                'quests', 'accept', 'complete']
    elif game_state['mode'] == 'combat':
        return ['attack', 'defend', 'use', 'flee', 'help', 'stats']
    else:
        return ['help', 'quit']

def expand_aliases(command: str) -> str:
    """Expand command aliases to full commands."""
    aliases = {
        'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
        'l': 'look', 'x': 'examine', 'i': 'inventory',
        'q': 'quit', 'h': 'help'
    }
    return aliases.get(command, command)

def parse_command(input_text: str) -> Dict[str, Any]:
    """Parse player input into action and target.
    
    Returns:
        dict: {'action': str, 'target': str, 'valid': bool, 'error': str}
    """
    if not input_text:
        return {'action': '', 'target': '', 'valid': False, 'error': 'Please enter a command.'}
    
    # Normalize and split input
    words = normalize_input(input_text).split()
    if not words:
        return {'action': '', 'target': '', 'valid': False, 'error': 'Please enter a command.'}
    
    # Expand aliases
    action = expand_aliases(words[0])
    target = ' '.join(words[1:]) if len(words) > 1 else ''
    
    # Movement commands
    if action in ['go', 'north', 'south', 'east', 'west']:
        if action == 'go':
            if not target:
                return {'action': 'go', 'target': '', 'valid': False, 'error': 'Go where?'}
            direction = expand_aliases(target.split()[0])
        else:
            direction = action
        
        if direction in ['north', 'south', 'east', 'west']:
            return {'action': 'move', 'target': direction, 'valid': True, 'error': ''}
        else:
            return {'action': 'move', 'target': direction, 'valid': False, 'error': f"I don't understand the direction '{direction}'."}
    
    # Examination commands
    elif action in ['examine', 'look']:
        if action == 'look' and not target:
            return {'action': 'look_room', 'target': '', 'valid': True, 'error': ''}
        elif action == 'examine' and not target:
            return {'action': 'examine', 'target': '', 'valid': False, 'error': 'Examine what?'}
        else:
            return {'action': 'examine', 'target': target, 'valid': True, 'error': ''}
    
    # Inventory commands
    elif action == 'take':
        if not target:
            return {'action': 'take', 'target': '', 'valid': False, 'error': 'Take what?'}
        return {'action': 'take', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'drop':
        if not target:
            return {'action': 'drop', 'target': '', 'valid': False, 'error': 'Drop what?'}
        return {'action': 'drop', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'inventory':
        return {'action': 'inventory', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'use':
        if not target:
            return {'action': 'use', 'target': '', 'valid': False, 'error': 'Use what?'}
        return {'action': 'use', 'target': target, 'valid': True, 'error': ''}
    
    # Combat commands
    elif action == 'attack':
        return {'action': 'attack', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'defend':
        return {'action': 'defend', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'flee':
        return {'action': 'flee', 'target': '', 'valid': True, 'error': ''}
    
    # System commands
    elif action == 'stats':
        return {'action': 'stats', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'help':
        return {'action': 'help', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'quit':
        return {'action': 'quit', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'save':
        return {'action': 'save', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'debug':
        return {'action': 'debug', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'buy':
        if not target:
            return {'action': 'buy', 'target': '', 'valid': False, 'error': 'Buy what?'}
        return {'action': 'buy', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'sell':
        if not target:
            return {'action': 'sell', 'target': '', 'valid': False, 'error': 'Sell what?'}
        return {'action': 'sell', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'talk':
        if not target:
            return {'action': 'talk', 'target': '', 'valid': False, 'error': 'Talk to whom?'}
        return {'action': 'talk', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'heal':
        return {'action': 'heal', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'quests':
        return {'action': 'quests', 'target': '', 'valid': True, 'error': ''}
    
    elif action == 'accept':
        if not target:
            return {'action': 'accept', 'target': '', 'valid': False, 'error': 'Accept what quest?'}
        return {'action': 'accept', 'target': target, 'valid': True, 'error': ''}
    
    elif action == 'complete':
        if not target:
            return {'action': 'complete', 'target': '', 'valid': False, 'error': 'Complete what quest?'}
        return {'action': 'complete', 'target': target, 'valid': True, 'error': ''}
    
    # Unknown command
    else:
        # Suggest similar commands
        available = get_available_commands()
        suggestions = [cmd for cmd in available if cmd.startswith(action[:2])]
        
        error_msg = f"I don't understand '{action}'."
        if suggestions:
            error_msg += f" Did you mean: {', '.join(suggestions[:3])}?"
        else:
            error_msg += " Type 'help' for available commands."
        
        return {'action': action, 'target': target, 'valid': False, 'error': error_msg}

# === [WORLD NAVIGATION] ===
def get_current_room() -> Optional[Room]:
    """Get the current room object."""
    current_room_id = game_state['current_room']
    if current_room_id in rooms_data:
        return Room(current_room_id, rooms_data[current_room_id])
    return None

def move_player(direction: str) -> None:
    """Move player to connected room.
    
    Side effects:
        - Updates game_state['current_room']
        - Updates player.current_room
        - Logs movement event
        - May trigger random encounters
    """
    current_room = get_current_room()
    if not current_room:
        print("Error: Current room not found!")
        return
    
    if current_room.can_go(direction):
        new_room_id = current_room.get_exit(direction)
        if new_room_id in rooms_data:
            game_state['current_room'] = new_room_id
            game_state['player'].current_room = new_room_id
            log_event("MOVEMENT", f"Player moved {direction} to {new_room_id}")
            
            # Show new room
            display_room()
            
            # Check for random encounters
            if check_for_encounter():
                possible_enemies = get_possible_enemies(new_room_id) if new_room_id else []
                if possible_enemies:
                    enemy_id = random.choice(possible_enemies)
                    print(f"\nAs you explore, you hear footsteps behind you...")
                    start_combat(enemy_id)
        else:
            print(f"That path leads to an unknown area.")
    else:
        print(f"You can't go {direction} from here.")

def examine_object(object_name: str) -> None:
    """Examine an object in the current room."""
    current_room = get_current_room()
    if not current_room:
        print("Error: Current room not found!")
        return
    
    # Try to examine room details
    description = current_room.examine_object(object_name)
    if description:
        print(description)
        log_event("EXAMINE", f"Player examined {object_name} in {current_room.id}")
        return
    
    # Check if it's an item in the room
    item_id = find_item_by_name(object_name, current_room.items)
    if item_id and item_id in items_data:
        item_desc = items_data[item_id].get("description", f"A {items_data[item_id].get('name', item_id)}.")
        print(item_desc)
        log_event("EXAMINE", f"Player examined item {item_id}")
        return
    
    # Check if it's an item in inventory
    player = game_state['player']
    item_id = find_item_by_name(object_name, player.inventory)
    if item_id and item_id in items_data:
        item_desc = items_data[item_id].get("description", f"A {items_data[item_id].get('name', item_id)}.")
        print(item_desc)
        log_event("EXAMINE", f"Player examined inventory item {item_id}")
        return
    
    print(f"You don't see any '{object_name}' here.")

def find_item_by_name(item_name: str, item_list: List[str]) -> Optional[str]:
    """Find item ID by name from a list of item IDs."""
    search_name = item_name.lower().replace(" ", "_")
    
    for item_id in item_list:
        if item_id in items_data:
            # Check exact match
            if item_id == search_name:
                return item_id
            
            # Check if item name matches
            item_data_name = items_data[item_id].get("name", "").lower()
            if item_data_name == item_name.lower():
                return item_id
            
            # Check if search term is in item name or ID
            if search_name in item_id or search_name in item_data_name:
                return item_id
    
    return None

# === [INVENTORY SYSTEM] ===
def take_item(item_name: str) -> None:
    """Take item from current room.
    
    Side effects:
        - Adds item to player inventory
        - Removes item from room
        - Logs inventory change
    """
    current_room = get_current_room()
    if not current_room:
        print("Error: Current room not found!")
        return
    
    player = game_state['player']
    
    # Find the item
    item_id = find_item_by_name(item_name, current_room.items)
    if not item_id:
        print(f"You don't see any '{item_name}' here.")
        return
    
    # Check inventory space
    if not player.can_carry_more():
        print(f"Your inventory is full! ({len(player.inventory)}/{player.max_inventory} items)")
        print("Drop something first with 'drop <item>'")
        return
    
    # Take the item
    if current_room.remove_item(item_id) and player.add_item(item_id):
        item_display_name = items_data.get(item_id, {}).get("name", item_id)
        print(f"You take the {item_display_name}.")
    else:
        print("Something went wrong trying to take that item.")

def drop_item(item_name: str) -> None:
    """Drop item from inventory to current room.
    
    Side effects:
        - Removes item from player inventory
        - Adds item to current room
        - Logs inventory change
    """
    current_room = get_current_room()
    if not current_room:
        print("Error: Current room not found!")
        return
    
    player = game_state['player']
    
    # Find the item in inventory
    item_id = find_item_by_name(item_name, player.inventory)
    if not item_id:
        print(f"You don't have any '{item_name}'.")
        return
    
    # Drop the item
    if player.remove_item(item_id):
        current_room.add_item(item_id)
        item_display_name = items_data.get(item_id, {}).get("name", item_id)
        print(f"You drop the {item_display_name}.")
    else:
        print("Something went wrong trying to drop that item.")

def show_inventory() -> None:
    """Display player's current inventory."""
    player = game_state['player']
    
    if not player.inventory:
        print("Your inventory is empty.")
        return
    
    print(f"Inventory ({len(player.inventory)}/{player.max_inventory}):")
    for item_id in player.inventory:
        if item_id in items_data:
            item_name = items_data[item_id].get("name", item_id)
            equipped_marker = ""
            if item_id == player.equipped_weapon:
                equipped_marker = " (equipped weapon)"
            elif item_id == player.equipped_armor:
                equipped_marker = " (equipped armor)"
            print(f"  - {item_name}{equipped_marker}")
        else:
            print(f"  - {item_id}")

def use_item(item_name: str) -> None:
    """Use/consume an item from inventory."""
    player = game_state['player']
    
    # Find the item in inventory
    item_id = find_item_by_name(item_name, player.inventory)
    if not item_id:
        print(f"You don't have any '{item_name}'.")
        return
    
    if item_id not in items_data:
        print(f"Unknown item: {item_id}")
        return
    
    item_data = items_data[item_id]
    item_type = item_data.get("type", "misc")
    
    # Handle different item types
    if item_type == "consumable":
        # Use consumable item
        effect = item_data.get("effect", {})
        
        if "heal" in effect:
            heal_amount = effect["heal"]
            actual_heal = player.heal(heal_amount)
            if actual_heal > 0:
                print(f"You use the {item_data['name']} and heal {actual_heal} health!")
                print(f"Health: {player.health}/{player.max_health}")
                player.remove_item(item_id)
                
                # Show combat text if in combat
                if game_state['mode'] == 'combat':
                    combat_message = get_combat_text("player_use_item", item=item_data['name'])
                    print(combat_message)
            else:
                print(f"You're already at full health!")
        else:
            print(f"You can't figure out how to use the {item_data['name']}.")
    
    elif item_type == "weapon":
        # Equip weapon
        if player.equipped_weapon:
            old_weapon_name = items_data.get(player.equipped_weapon, {}).get("name", player.equipped_weapon)
            print(f"You unequip the {old_weapon_name}.")
        
        player.equipped_weapon = item_id
        print(f"You equip the {item_data['name']}!")
        print(f"Attack power: {player.get_attack_power()}")
    
    elif item_type == "armor":
        # Equip armor
        if player.equipped_armor:
            old_armor_name = items_data.get(player.equipped_armor, {}).get("name", player.equipped_armor)
            print(f"You unequip the {old_armor_name}.")
        
        player.equipped_armor = item_id
        print(f"You equip the {item_data['name']}!")
        print(f"Defense power: {player.get_defense_power()}")
    
    else:
        print(f"You can't use the {item_data['name']} right now.")

# === [QUEST SYSTEM] ===
def show_quests() -> None:
    """Display player's current quests."""
    player = game_state['player']
    
    if not player.active_quests and not player.completed_quests:
        print("You have no quests. Talk to NPCs to find quest opportunities!")
        return
    
    print("\n=== QUEST LOG ===")
    
    if player.active_quests:
        print("\n📋 ACTIVE QUESTS:")
        for quest_id in player.active_quests:
            quest = Quest.from_template(quest_id)
            if quest:
                # Update quest progress before displaying
                update_quest_objectives(quest)
                print(quest.get_progress_text())
                print()
    
    if player.completed_quests:
        print("✅ COMPLETED QUESTS:")
        for quest_id in player.completed_quests:
            if quest_id in quests_data:
                quest_title = quests_data[quest_id]["title"]
                print(f"  ✅ {quest_title}")
        print()
    
    print("=" * 18)

def accept_quest_from_npc(quest_id: str) -> None:
    """Handle accepting a quest from an NPC."""
    player = game_state['player']
    
    if quest_id not in quests_data:
        print("Unknown quest.")
        return
    
    # Check if already completed or active
    if quest_id in player.completed_quests:
        print("You've already completed that quest!")
        return
    
    if quest_id in player.active_quests:
        print("You're already working on that quest!")
        return
    
    # Check if can accept more quests
    if not player.can_accept_quest():
        print(f"You can only have {Config.MAX_ACTIVE_QUESTS} active quests at once.")
        print("Complete some quests first!")
        return
    
    # Accept the quest
    if player.accept_quest(quest_id):
        quest_data = quests_data[quest_id]
        print(f"\n📜 Quest Accepted: {quest_data['title']}")
        print(f"Description: {quest_data['description']}")
        
        print("\nObjectives:")
        for i, obj in enumerate(quest_data['objectives'], 1):
            print(f"  {i}. {obj['description']}")
        
        print("\nType 'quests' to check your progress anytime.")
    else:
        print("Failed to accept quest.")

def complete_quest_with_rewards(quest_id: str) -> None:
    """Complete a quest and give rewards."""
    player = game_state['player']
    
    if quest_id not in player.active_quests:
        print("You're not currently working on that quest!")
        return
    
    quest = Quest.from_template(quest_id)
    if not quest:
        print("Quest data not found!")
        return
    
    # Update quest objectives and check completion
    update_quest_objectives(quest)
    
    if not quest.is_completed():
        print("You haven't completed all objectives yet!")
        show_quest_progress(quest_id)
        return
    
    # Complete the quest
    if player.complete_quest(quest_id):
        print(f"\n🎉 QUEST COMPLETED: {quest.title}")
        print(quest.completion_text)
        
        # Give rewards
        rewards = quest.rewards
        total_xp = 0
        
        if "xp" in rewards:
            base_xp = rewards["xp"]
            bonus_xp = int(base_xp * (Config.QUEST_XP_MULTIPLIER - 1))
            total_xp = base_xp + bonus_xp
            
            print(f"Reward: {base_xp} XP + {bonus_xp} bonus XP = {total_xp} XP!")
            leveled_up = player.gain_experience(total_xp)
            
            if not leveled_up:
                print(f"Progress: {player.get_xp_bar()}")
        
        if "gold" in rewards:
            gold_reward = rewards["gold"]
            player.earn_gold(gold_reward)
            print(f"Reward: {gold_reward} gold!")
        
        if "items" in rewards:
            for item_id in rewards["items"]:
                if item_id in items_data:
                    item_name = items_data[item_id]["name"]
                    if player.can_carry_more():
                        player.add_item(item_id)
                        print(f"Reward: {item_name}!")
                    else:
                        print(f"Inventory full! {item_name} dropped on ground.")
                        current_room = get_current_room()
                        if current_room:
                            current_room.add_item(item_id)
        
        print("\nWell done, hero!")

def show_quest_progress(quest_id: str) -> None:
    """Show detailed progress for a specific quest."""
    quest = Quest.from_template(quest_id)
    if quest:
        update_quest_objectives(quest)
        print(f"\n{quest.get_progress_text()}")

def update_quest_objectives(quest: Quest) -> None:
    """Update quest objectives based on current game state."""
    player = game_state['player']
    
    for obj in quest.objectives:
        obj_type = obj.get("type", "")
        
        if obj_type == "kill":
            # Track enemy kills
            target_enemy = obj.get("target", "")
            required_count = obj.get("count", 1)
            current_count = player.get_quest_progress(quest.quest_id, f"kill_{target_enemy}", 0)
            
            obj["completed"] = current_count >= required_count
            obj["progress"] = f"{current_count}/{required_count}"
            if not obj["completed"]:
                obj["description"] = f"Defeat {target_enemy} ({current_count}/{required_count})"
        
        elif obj_type == "collect":
            # Check if player has required items
            target_item = obj.get("target", "")
            required_count = obj.get("count", 1)
            current_count = sum(1 for item in player.inventory if item == target_item)
            
            obj["completed"] = current_count >= required_count
            obj["progress"] = f"{current_count}/{required_count}"
            if not obj["completed"]:
                item_name = items_data.get(target_item, {}).get("name", target_item)
                obj["description"] = f"Collect {item_name} ({current_count}/{required_count})"
        
        elif obj_type == "deliver":
            # Check if item was delivered
            delivered = player.get_quest_progress(quest.quest_id, "delivered", False)
            obj["completed"] = delivered
        
        elif obj_type == "visit":
            # Check if location was visited
            target_room = obj.get("target", "")
            visited = player.current_room == target_room or player.get_quest_progress(quest.quest_id, f"visit_{target_room}", False)
            obj["completed"] = visited
            
            # Auto-mark as visited if player is in the room
            if player.current_room == target_room:
                player.update_quest_progress(quest.quest_id, f"visit_{target_room}", True)

def track_enemy_kill(enemy_id: str) -> None:
    """Track enemy kill for quest purposes."""
    player = game_state['player']
    
    for quest_id in player.active_quests:
        quest = Quest.from_template(quest_id)
        if quest:
            for obj in quest.objectives:
                if obj.get("type") == "kill" and obj.get("target") == enemy_id:
                    current_count = player.get_quest_progress(quest_id, f"kill_{enemy_id}", 0)
                    player.update_quest_progress(quest_id, f"kill_{enemy_id}", current_count + 1)
                    
                    required_count = obj.get("count", 1)
                    new_count = current_count + 1
                    
                    if new_count >= required_count:
                        print(f"\n📜 Quest objective completed: Defeat {enemy_id} ({new_count}/{required_count})")
                    else:
                        print(f"\n📜 Quest progress: Defeat {enemy_id} ({new_count}/{required_count})")

# === [ECONOMY SYSTEM] ===
def get_item_price(item_id: str, is_selling: bool = False) -> int:
    """Get the price of an item for buying/selling."""
    if item_id not in items_data:
        return 0
    
    base_value = items_data[item_id].get("value", 0)
    
    if is_selling:
        # Player selling to merchant (gets less money)
        return int(base_value * Config.MERCHANT_BUYBACK)
    else:
        # Player buying from merchant (pays more)
        return int(base_value * Config.MERCHANT_MARKUP)

def show_merchant_inventory() -> None:
    """Display merchant's available items."""
    merchant_items = [
        "health_potion", "steel_sword", "chain_mail", 
        "greater_health_potion", "magic_ring", "legendary_blade"
    ]
    
    print("\n=== MERCHANT'S WARES ===")
    print("The merchant displays his finest goods:")
    
    for item_id in merchant_items:
        if item_id in items_data:
            item_data = items_data[item_id]
            price = get_item_price(item_id)
            print(f"  {item_data['name']} - {price} gold")
            
            # Show special note for legendary item
            if item_id == "legendary_blade":
                print("    ⭐ LEGENDARY ITEM ⭐")
    
    print("\nType 'buy <item>' to purchase an item")
    print("Type 'sell <item>' to sell from your inventory")
    print("=" * 25)

def buy_item(item_name: str) -> None:
    """Handle buying an item from the merchant."""
    player = game_state['player']
    
    # Find item by name in merchant inventory
    merchant_items = [
        "health_potion", "steel_sword", "chain_mail", 
        "greater_health_potion", "magic_ring", "legendary_blade"
    ]
    
    item_id = None
    for candidate_id in merchant_items:
        if candidate_id in items_data:
            item_data = items_data[candidate_id]
            if item_data['name'].lower() == item_name.lower():
                item_id = candidate_id
                break
    
    if not item_id:
        print(f"The merchant doesn't have any '{item_name}' for sale.")
        return
    
    price = get_item_price(item_id)
    item_data = items_data[item_id]
    
    # Check if player can afford it
    if not player.can_afford(price):
        print(f"You need {price} gold to buy the {item_data['name']}, but you only have {player.gold} gold.")
        return
    
    # Check inventory space
    if not player.can_carry_more():
        print("Your inventory is full! Drop something first.")
        return
    
    # Complete the purchase
    if player.spend_gold(price):
        player.add_item(item_id)
        print(f"You purchase the {item_data['name']} for {price} gold.")
        
        if item_id == "legendary_blade":
            print("The merchant's eyes widen as you count out the gold.")
            print("'That blade has quite a history,' he says with respect.")

def sell_item(item_name: str) -> None:
    """Handle selling an item to the merchant."""
    player = game_state['player']
    
    # Find the item in player's inventory
    item_id = find_item_by_name(item_name, player.inventory)
    if not item_id:
        print(f"You don't have any '{item_name}' to sell.")
        return
    
    if item_id not in items_data:
        print(f"The merchant isn't interested in that item.")
        return
    
    item_data = items_data[item_id]
    price = get_item_price(item_id, is_selling=True)
    
    if price <= 0:
        print(f"The merchant isn't interested in the {item_data['name']}.")
        return
    
    # Complete the sale
    if player.remove_item(item_id):
        player.earn_gold(price)
        print(f"You sell the {item_data['name']} for {price} gold.")

def heal_at_tavern() -> None:
    """Offer healing services at the tavern."""
    player = game_state['player']
    current_room = get_current_room()
    
    # Check if player is in tavern
    if not current_room or current_room.id != "tavern":
        print("You need to be in the tavern to use healing services.")
        return
    
    if player.health >= player.max_health:
        print("You're already at full health!")
        return
    
    missing_health = player.max_health - player.health
    total_cost = missing_health * Config.HEALING_SERVICE_COST
    
    print(f"\nThe barkeep offers to tend your wounds.")
    print(f"Healing {missing_health} HP will cost {total_cost} gold.")
    print(f"You currently have {player.gold} gold.")
    
    if not player.can_afford(total_cost):
        print("You don't have enough gold for healing services.")
        return
    
    # For now, auto-accept the healing (in a real game, we'd ask for confirmation)
    if player.spend_gold(total_cost):
        old_health = player.health
        player.health = player.max_health
        actual_heal = player.health - old_health
        print(f"\nThe barkeep tends to your wounds with practiced skill.")
        print(f"You are healed for {actual_heal} HP!")
        print(f"Health: {player.health}/{player.max_health}")
        print("You feel much better!")

def talk_to_npc(npc_name: str) -> None:
    """Handle talking to NPCs."""
    current_room = get_current_room()
    if not current_room or npc_name not in current_room.npcs:
        print(f"There's no {npc_name} here to talk to.")
        return
    
    player = game_state['player']
    
    if npc_name == "barkeep":
        print("\nThe grizzled barkeep looks up from cleaning mugs.")
        print("'Welcome to The Dusty Tankard! Can I get you anything?'")
        print()
        print("Services available:")
        print("- 'heal' - Healing services (5 gold per HP)")
        print("- 'talk barkeep' - Chat with the barkeep")
        
        # Check for available quests
        available_quests = get_available_quests_from_npc("barkeep")
        if available_quests:
            print("\nQuests available:")
            for quest_id in available_quests:
                quest_data = quests_data[quest_id]
                print(f"- 'accept {quest_id}' - {quest_data['title']}")
        
    elif npc_name == "merchant" or npc_name == "shopkeeper":
        print("\nThe merchant rubs his hands together eagerly.")
        print("'Ah, a customer! I have the finest wares in the land!'")
        show_merchant_inventory()
        
        # Check for available quests
        available_quests = get_available_quests_from_npc("merchant")
        if available_quests:
            print("\nQuests available:")
            for quest_id in available_quests:
                quest_data = quests_data[quest_id]
                print(f"- 'accept {quest_id}' - {quest_data['title']}")
    
    elif npc_name == "guard":
        print("\nThe town guard straightens up and salutes.")
        print("'Greetings, citizen! The town needs brave souls like you.'")
        
        # Check for available quests
        available_quests = get_available_quests_from_npc("guard")
        if available_quests:
            print("\nQuests available:")
            for quest_id in available_quests:
                quest_data = quests_data[quest_id]
                print(f"- 'accept {quest_id}' - {quest_data['title']}")
    
    elif npc_name == "villager":
        print("\nThe villager looks worried and approaches you.")
        print("'Oh, thank goodness! Are you an adventurer?'")
        
        # Check for available quests
        available_quests = get_available_quests_from_npc("villager")
        if available_quests:
            print("\nQuests available:")
            for quest_id in available_quests:
                quest_data = quests_data[quest_id]
                print(f"- 'accept {quest_id}' - {quest_data['title']}")
    
    else:
        print(f"The {npc_name} nods at you politely but seems busy.")

def get_available_quests_from_npc(npc_name: str) -> List[str]:
    """Get list of quests available from an NPC."""
    player = game_state['player']
    available = []
    
    for quest_id, quest_data in quests_data.items():
        # Check if this NPC offers this quest
        if quest_data.get("giver_npc") == npc_name:
            # Check if player can accept it
            if (quest_id not in player.active_quests and 
                quest_id not in player.completed_quests):
                available.append(quest_id)
    
    return available

# === [COMBAT SYSTEM] ===
def get_combat_text(text_type: str, **kwargs) -> str:
    """Get random combat text of specified type."""
    if text_type not in combat_text_data:
        return f"[{text_type}]"  # Fallback
    
    messages = combat_text_data[text_type]
    if not messages:
        return f"[{text_type}]"
    
    message = random.choice(messages)
    try:
        return message.format(**kwargs)
    except KeyError:
        return message

def check_for_encounter() -> bool:
    """Check if a random encounter should occur."""
    # No encounters in safe rooms
    safe_rooms = ['tavern', 'town_square', 'village_shop']
    if game_state['current_room'] in safe_rooms:
        return False
    
    return random.random() < Config.ENCOUNTER_CHANCE

def get_possible_enemies(room_id: str) -> List[str]:
    """Get list of enemies that can spawn in this room."""
    possible = []
    for enemy_id, enemy_data in enemies_data.items():
        spawn_locations = enemy_data.get("spawn_locations", [])
        if room_id in spawn_locations:
            possible.append(enemy_id)
    return possible

def start_combat(enemy_id: str) -> bool:
    """Initialize combat with specified enemy."""
    enemy = Enemy.from_template(enemy_id)
    if not enemy:
        log_event("ERROR", f"Failed to create enemy: {enemy_id}")
        return False
    
    # Set up combat state
    game_state['combat'] = CombatState(enemy=enemy)
    game_state['mode'] = 'combat'
    
    # Determine initiative (simple for now - could be agility-based later)
    player_agility = game_state['player'].agility
    enemy_agility = enemy.agility
    
    # Add some randomness to initiative
    player_roll = player_agility + random.randint(1, 6)
    enemy_roll = enemy_agility + random.randint(1, 6)
    
    game_state['combat'].player_initiative = player_roll >= enemy_roll
    
    # Display combat start
    print("\n" + "="*50)
    print(f"💀 COMBAT! 💀")
    print(f"A {enemy.name} appears!")
    print(enemy.description)
    print(get_combat_text("combat_start"))
    print("="*50)
    
    log_event("COMBAT", f"Combat started with {enemy.name}")
    return True

def player_attack(target: Enemy) -> None:
    """Handle player attack action."""
    player = game_state['player']
    
    # Calculate hit chance (simple system)
    hit_chance = 0.8  # 80% base hit chance
    
    if random.random() <= hit_chance:
        # Hit!
        damage = player.get_attack_power() + random.randint(1, 4)  # Add some randomness
        actual_damage = target.take_damage(damage)
        
        print(get_combat_text("player_hit", enemy=target.name, damage=actual_damage))
        
        # Check if enemy is defeated
        if not target.is_alive():
            print(get_combat_text("enemy_death", enemy=target.name))
            end_combat_victory()
    else:
        # Miss!
        print(get_combat_text("player_miss", enemy=target.name))

def player_defend() -> None:
    """Handle player defend action."""
    player = game_state['player']
    player.defending = True
    print(get_combat_text("player_defend"))

def player_flee() -> bool:
    """Handle player flee attempt."""
    player = game_state['player']
    combat = game_state['combat']
    
    # Calculate flee chance based on agility
    base_chance = Config.FLEE_SUCCESS_BASE
    agility_bonus = (player.agility - combat.enemy.agility) * 0.05  # 5% per agility point difference
    flee_chance = base_chance + agility_bonus
    
    if random.random() <= flee_chance:
        print(get_combat_text("player_flee"))
        end_combat_fled()
        return True
    else:
        print("You try to flee but the enemy blocks your escape!")
        return False

def enemy_turn(enemy: Enemy) -> None:
    """Handle enemy's turn in combat."""
    if not enemy.is_alive():
        return
    
    action = enemy.choose_action()
    player = game_state['player']
    
    if action == "attack":
        # Enemy attacks
        hit_chance = 0.75  # 75% base hit chance for enemies
        
        if random.random() <= hit_chance:
            # Hit!
            damage = enemy.attack + random.randint(1, 3)
            actual_damage = player.take_damage(damage)
            
            print(get_combat_text("enemy_hit", enemy=enemy.name, damage=actual_damage))
            
            # Check if player is defeated
            if not player.is_alive():
                print(get_combat_text("player_death"))
                handle_player_death()
        else:
            # Miss!
            print(get_combat_text("enemy_miss", enemy=enemy.name))
    
    elif action == "defend":
        enemy.defending = True
        print(get_combat_text("enemy_defend", enemy=enemy.name))
    
    elif action == "flee":
        print(get_combat_text("enemy_flee", enemy=enemy.name))
        end_combat_fled()

def process_combat_turn(player_action: str, target: str = "") -> None:
    """Process one turn of combat."""
    combat = game_state['combat']
    player = game_state['player']
    
    if not combat or not combat.is_active():
        return
    
    # Reset defending states
    player.defending = False
    combat.enemy.defending = False
    
    # Process player action
    if player_action == "attack":
        player_attack(combat.enemy)
    elif player_action == "defend":
        player_defend()
    elif player_action == "use":
        use_item(target)
    elif player_action == "flee":
        if player_flee():
            return  # Combat ended
    
    # Check if combat is still active after player action
    if not combat.is_active():
        return
    
    # Enemy turn
    enemy_turn(combat.enemy)
    
    # Check if combat is still active after enemy turn
    if not combat.is_active():
        return
    
    # Increment turn counter
    combat.turn_count += 1
    
    # Check for low health warning
    if player.is_low_health():
        print(get_combat_text("low_health_warning"))

def end_combat_victory() -> None:
    """Handle end of combat with player victory."""
    combat = game_state['combat']
    if not combat:
        return
    
    # Track enemy kill for quests
    track_enemy_kill(combat.enemy.enemy_id)
    
    # Generate and award loot
    loot = combat.enemy.generate_loot()
    player = game_state['player']
    
    print(f"\nVictory! The {combat.enemy.name} has been defeated!")
    
    # Award XP based on enemy difficulty (max health is a good indicator)
    base_xp = combat.enemy.max_health * 2  # 2 XP per HP point
    bonus_xp = random.randint(0, 5)  # Random bonus 0-5 XP
    total_xp = base_xp + bonus_xp
    
    print(f"You gain {total_xp} experience!")
    leveled_up = player.gain_experience(total_xp)
    
    # Award gold
    if loot["gold"] > 0:
        player.earn_gold(loot["gold"])
        print(f"You find {loot['gold']} gold!")
    
    # Award items
    for item_id in loot["items"]:
        if item_id in items_data:
            item_name = items_data[item_id]["name"]
            if player.can_carry_more():
                player.add_item(item_id)
                print(f"You found: {item_name}!")
            else:
                print(f"You found {item_name}, but your inventory is full!")
                # Add to room instead
                current_room = get_current_room()
                if current_room:
                    current_room.add_item(item_id)
                    print(f"The {item_name} falls to the ground.")
    
    # Show progression if no level up occurred
    if not leveled_up:
        print(f"Progress: {player.get_xp_bar()}")
    
    # Clean up combat state
    game_state['combat'] = None
    game_state['mode'] = 'exploration'
    
    log_event("COMBAT", f"Player defeated {combat.enemy.name}")

def end_combat_fled() -> None:
    """Handle end of combat with player fleeing."""
    combat = game_state['combat']
    if not combat:
        return
    
    print(f"You successfully escape from the {combat.enemy.name}!")
    
    # Clean up combat state
    game_state['combat'] = None
    game_state['mode'] = 'exploration'
    
    log_event("COMBAT", f"Player fled from {combat.enemy.name}")

def handle_player_death() -> None:
    """Handle player death and respawn."""
    player = game_state['player']
    
    print("\n" + "="*50)
    print("💀 DEFEAT 💀")
    print("You have been slain in combat!")
    
    # Apply death penalty
    gold_lost = int(player.gold * 0.1)  # Lose 10% of gold
    player.gold = max(0, player.gold - gold_lost)
    if gold_lost > 0:
        print(f"You lose {gold_lost} gold in the confusion...")
    
    # Restore health
    player.health = player.max_health
    
    # Move to last save point
    game_state['current_room'] = game_state['last_save_room']
    player.current_room = game_state['last_save_room']
    
    current_room = get_current_room()
    if current_room:
        print(f"You awaken back at the {current_room.name}.")
    else:
        print("You awaken in a safe place.")
    print("Perhaps you should be more careful next time...")
    print("="*50)
    
    # Clean up combat state
    game_state['combat'] = None
    game_state['mode'] = 'exploration'
    
    log_event("COMBAT", "Player died and respawned")

# === [UI/DISPLAY] ===
def display_title():
    """Show game title and version."""
    print("=" * 50)
    print(f"    {Config.GAME_TITLE}")
    print(f"    Version {Config.VERSION}")
    print("=" * 50)
    print()

def display_room() -> None:
    """Show current room description."""
    current_room = get_current_room()
    if current_room:
        print("\n" + "=" * 50)
        print(current_room.get_full_description())
        print("=" * 50)
    else:
        print("Error: You seem to be in an unknown location!")

def display_help(topic: str = "") -> None:
    """Display help information."""
    if not topic:
        print("\n=== HELP ===")
        print("Available commands:")
        print("  Movement: go <direction>, north/south/east/west (or n/s/e/w)")
        print("  Looking: look (room overview), examine <object> (detailed look)")
        print("  Items: take <item>, drop <item>, inventory, use <item>")
        print("  Commerce: buy <item>, sell <item>, talk <npc>")
        print("  Services: heal (at tavern)")
        print("  Quests: quests (view quest log), accept <quest>, complete <quest>")
        print("  Character: stats (view level, XP, health, etc.)")
        print("  Combat: attack, defend, use <item>, flee")
        print("  System: help, save, quit")
        print("  Debug: debug <command>")
        print("\nFor detailed help on a topic, type: help <topic>")
        print("Topics: movement, items, combat, economy, quests")
    elif topic == "movement":
        print("\n=== MOVEMENT HELP ===")
        print("You can move between rooms using:")
        print("  'go north' or just 'north' or 'n'")
        print("  Valid directions: north, south, east, west")
        print("  Use 'look' to see available exits")
    elif topic == "items":
        print("\n=== ITEMS HELP ===")
        print("Interact with items using:")
        print("  'take <item>' - Pick up an item")
        print("  'drop <item>' - Drop an item from inventory")
        print("  'inventory' - See what you're carrying")
        print("  'use <item>' - Use/equip an item")
        print("  'examine <item>' - Look at item details")
    elif topic == "combat":
        print("\n=== COMBAT HELP ===")
        print("During combat you can:")
        print("  'attack' - Strike the enemy")
        print("  'defend' - +50% defense this turn")
        print("  'use <item>' - Use a potion or consumable")
        print("  'flee' - Attempt to escape (success depends on agility)")
        print("Gain XP by defeating enemies to level up!")
    elif topic == "economy":
        print("\n=== ECONOMY HELP ===")
        print("Make money and spend it:")
        print("  'talk merchant' - See available items for sale")
        print("  'buy <item>' - Purchase an item from merchant")
        print("  'sell <item>' - Sell an item from your inventory")
        print("  'heal' - Pay for healing services at the tavern (5 gold per HP)")
        print("Legendary items cost 500+ gold - start saving!")
    elif topic == "quests":
        print("\n=== QUESTS HELP ===")
        print("Complete quests for bonus XP and rewards:")
        print("  'talk <npc>' - Talk to NPCs to discover available quests")
        print("  'accept <quest_id>' - Accept a quest from an NPC")
        print("  'quests' - View your active and completed quests")
        print("  'complete <quest_id>' - Turn in a completed quest for rewards")
        print("Quest types: kill enemies, collect items, visit locations, deliver items")
    else:
        print(f"No help available for '{topic}'. Try 'help' for main topics.")

def display_prompt() -> None:
    """Show the input prompt."""
    if game_state['first_play']:
        print("\nType 'help' for available commands, or 'look' to examine your surroundings.")
        game_state['first_play'] = False
    print("\n> ", end="")

def display_stats() -> None:
    """Display player's current stats."""
    player = game_state['player']
    
    print("\n=== CHARACTER STATS ===")
    print(f"Name: {player.name} (Level {player.level})")
    print(f"{player.get_health_bar()}")
    print(f"{player.get_xp_bar()}")
    print(f"Strength: {player.strength} (Attack: {player.get_attack_power()})")
    print(f"Defense: {player.defense} (Defense: {player.get_defense_power()})")
    print(f"Agility: {player.agility}")
    print(f"Gold: {player.gold}")
    
    # Show equipment
    if player.equipped_weapon or player.equipped_armor:
        print("\nEquipment:")
        if player.equipped_weapon:
            weapon_name = items_data.get(player.equipped_weapon, {}).get("name", player.equipped_weapon)
            print(f"  Weapon: {weapon_name}")
        if player.equipped_armor:
            armor_name = items_data.get(player.equipped_armor, {}).get("name", player.equipped_armor)
            print(f"  Armor: {armor_name}")
    
    # Show quest summary
    if player.active_quests or player.completed_quests:
        print(f"\nQuests: {len(player.active_quests)} active, {len(player.completed_quests)} completed")
        print("Type 'quests' for details")
    
    print("=" * 24)

def display_combat_status() -> None:
    """Display current combat status."""
    combat = game_state['combat']
    if not combat:
        return
    
    player = game_state['player']
    enemy = combat.enemy
    
    print("\n" + "="*50)
    print("💀 COMBAT STATUS 💀")
    print(f"Turn {combat.turn_count + 1}")
    print("-" * 50)
    
    # Player status
    print(f"🛡️  {player.name}")
    print(f"   {player.get_health_bar()}")
    if player.defending:
        print("   🛡️ DEFENDING (+50% defense)")
    if player.equipped_weapon:
        weapon_name = items_data.get(player.equipped_weapon, {}).get("name", "weapon")
        print(f"   ⚔️ {weapon_name}")
    
    print()
    
    # Enemy status
    print(f"👹 {enemy.name}")
    print(f"   {enemy.get_health_bar()}")
    if enemy.defending:
        print("   🛡️ DEFENDING (+50% defense)")
    
    print("-" * 50)
    print("Actions: attack, defend, use <item>, flee")
    print("=" * 50)

def display_debug_info() -> None:
    """Display current game state for debugging."""
    print("\n=== DEBUG INFO ===")
    print(f"Current room: {game_state['current_room']}")
    print(f"Game mode: {game_state['mode']}")
    player = game_state['player']
    print(f"Player health: {player.health}/{player.max_health}")
    print(f"Player gold: {player.gold}")
    print(f"Player inventory: {player.inventory}")
    print(f"Equipped weapon: {player.equipped_weapon}")
    print(f"Equipped armor: {player.equipped_armor}")
    current_room = get_current_room()
    if current_room:
        print(f"Room items: {current_room.items}")
    if game_state['combat']:
        print(f"Combat enemy: {game_state['combat'].enemy.name}")
    print("=" * 20)

# === [SAVE/LOAD] ===
def save_game() -> None:
    """Save current game state to JSON file."""
    try:
        # Update last save room for respawn
        game_state['last_save_room'] = game_state['current_room']
        
        # Prepare save data
        save_data = {
            "version": Config.VERSION,
            "timestamp": datetime.now().isoformat(),
            "player": asdict(game_state['player']),
            "current_room": game_state['current_room'],
            "game_mode": game_state['mode'],
            "last_save_room": game_state['last_save_room']
        }
        
        # Write to file
        with open(Config.SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
        
        print("Game saved successfully!")
        log_event("SAVE", "Game state saved")
    except Exception as e:
        print(f"Error saving game: {e}")
        log_event("ERROR", f"Save failed: {e}")

def load_game() -> bool:
    """Load game state from JSON file."""
    try:
        if not os.path.exists(Config.SAVE_FILE):
            return False
        
        with open(Config.SAVE_FILE, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        # Restore player state
        player_data = save_data.get("player", {})
        game_state['player'] = Player(**player_data)
        
        # Restore game state
        game_state['current_room'] = save_data.get("current_room", "tavern")
        game_state['mode'] = save_data.get("game_mode", "exploration")
        game_state['last_save_room'] = save_data.get("last_save_room", "tavern")
        
        print("Game loaded successfully!")
        log_event("LOAD", "Game state loaded")
        return True
    except Exception as e:
        print(f"Error loading game: {e}")
        log_event("ERROR", f"Load failed: {e}")
        return False

# === [DATA LOADING] ===
def load_game_data() -> None:
    """Load all game data from JSON files.
    
    Side effects:
        - Populates rooms_data, items_data, enemies_data, combat_text_data, quests_data dictionaries
        - Creates default data files if missing
    """
    global rooms_data, items_data, enemies_data, combat_text_data, quests_data
    
    # Load rooms
    try:
        if os.path.exists(Config.ROOMS_FILE):
            with open(Config.ROOMS_FILE, 'r', encoding='utf-8') as f:
                rooms_data = json.load(f)
        else:
            print("Warning: rooms.json not found - using empty rooms data")
            rooms_data = {}
    except Exception as e:
        log_event("ERROR", f"Failed to load rooms: {e}")
        print(f"Error loading rooms.json: {e}")
        rooms_data = {}
    
    # Load items
    try:
        if os.path.exists(Config.ITEMS_FILE):
            with open(Config.ITEMS_FILE, 'r', encoding='utf-8') as f:
                items_data = json.load(f)
        else:
            print("Warning: items.json not found - using empty items data")
            items_data = {}
    except Exception as e:
        log_event("ERROR", f"Failed to load items: {e}")
        print(f"Error loading items.json: {e}")
        items_data = {}
    
    # Load enemies
    try:
        if os.path.exists(Config.ENEMIES_FILE):
            with open(Config.ENEMIES_FILE, 'r', encoding='utf-8') as f:
                enemies_data = json.load(f)
        else:
            print("Warning: enemies.json not found - using empty enemies data")
            enemies_data = {}
    except Exception as e:
        log_event("ERROR", f"Failed to load enemies: {e}")
        print(f"Error loading enemies.json: {e}")
        enemies_data = {}
    
    # Load combat text
    try:
        if os.path.exists(Config.COMBAT_TEXT_FILE):
            with open(Config.COMBAT_TEXT_FILE, 'r', encoding='utf-8') as f:
                combat_text_data = json.load(f)
        else:
            print("Warning: combat_text.json not found - using empty combat text data")
            combat_text_data = {}
    except Exception as e:
        log_event("ERROR", f"Failed to load combat text: {e}")
        print(f"Error loading combat_text.json: {e}")
        combat_text_data = {}
    
    # Load quests
    try:
        if os.path.exists(Config.QUESTS_FILE):
            with open(Config.QUESTS_FILE, 'r', encoding='utf-8') as f:
                quests_data = json.load(f)
        else:
            print("Warning: quests.json not found - using empty quests data")
            quests_data = {}
    except Exception as e:
        log_event("ERROR", f"Failed to load quests: {e}")
        print(f"Error loading quests.json: {e}")
        quests_data = {}
    
    log_event("SYSTEM", f"Loaded {len(rooms_data)} rooms, {len(items_data)} items, {len(enemies_data)} enemies, {len(combat_text_data)} combat text categories, {len(quests_data)} quests")

# === [COMMAND PROCESSING] ===
def process_command(input_text: str) -> None:
    """Process a player command and execute the appropriate action.
    
    Side effects:
        - May modify game state
        - May display output to player
        - May log events
    """
    command_data = parse_command(input_text)
    
    if not command_data['valid']:
        print(command_data['error'])
        return
    
    action = command_data['action']
    target = command_data['target']
    
    # Execute the command
    if action == 'move':
        if game_state['mode'] == 'combat':
            print("You can't move during combat!")
        else:
            move_player(target)
    elif action == 'look_room':
        if game_state['mode'] == 'combat':
            print("You're too busy fighting to look around!")
        else:
            display_room()
    elif action == 'examine':
        if game_state['mode'] == 'combat':
            print("You're too busy fighting to examine things!")
        else:
            examine_object(target)
    elif action == 'take':
        if game_state['mode'] == 'combat':
            print("You can't pick up items during combat!")
        else:
            take_item(target)
    elif action == 'drop':
        if game_state['mode'] == 'combat':
            print("You can't drop items during combat!")
        else:
            drop_item(target)
    elif action == 'inventory':
        show_inventory()
    elif action == 'use':
        use_item(target)
    elif action == 'stats':
        display_stats()
    elif action == 'buy':
        if game_state['mode'] == 'combat':
            print("You can't shop during combat!")
        else:
            buy_item(target)
    elif action == 'sell':
        if game_state['mode'] == 'combat':
            print("You can't shop during combat!")
        else:
            sell_item(target)
    elif action == 'talk':
        if game_state['mode'] == 'combat':
            print("You're too busy fighting to chat!")
        else:
            talk_to_npc(target)
    elif action == 'heal':
        if game_state['mode'] == 'combat':
            print("You can't use healing services during combat!")
        else:
            heal_at_tavern()
    elif action == 'quests':
        show_quests()
    elif action == 'accept':
        if game_state['mode'] == 'combat':
            print("You can't accept quests during combat!")
        else:
            accept_quest_from_npc(target)
    elif action == 'complete':
        if game_state['mode'] == 'combat':
            print("You can't complete quests during combat!")
        else:
            complete_quest_with_rewards(target)
    # Combat commands
    elif action == 'attack':
        if game_state['mode'] == 'combat':
            process_combat_turn('attack')
        else:
            print("There's nothing to attack here!")
    elif action == 'defend':
        if game_state['mode'] == 'combat':
            process_combat_turn('defend')
        else:
            print("You're not in combat!")
    elif action == 'flee':
        if game_state['mode'] == 'combat':
            process_combat_turn('flee')
        else:
            print("There's nothing to flee from!")
    # System commands
    elif action == 'help':
        display_help(target)
    elif action == 'save':
        if game_state['mode'] == 'combat':
            print("You can't save during combat!")
        else:
            save_game()
    elif action == 'quit':
        confirm_quit()
    elif action == 'debug':
        if target == 'info':
            display_debug_info()
        elif target == 'toggle':
            game_state['debug_mode'] = not game_state['debug_mode']
            print(f"Debug mode {'enabled' if game_state['debug_mode'] else 'disabled'}")
        elif target.startswith('spawn '):
            enemy_id = target[6:]  # Remove 'spawn '
            if enemy_id in enemies_data:
                start_combat(enemy_id)
            else:
                print(f"Unknown enemy: {enemy_id}")
        else:
            print("Debug commands: 'debug info', 'debug toggle', 'debug spawn <enemy>'")
    else:
        print(f"Command '{action}' not implemented yet.")

def confirm_quit() -> None:
    """Confirm quit and handle saving."""
    print("Are you sure you want to quit? (y/n)")
    print("Your progress will be lost unless you save first.")
    choice = input("> ").strip().lower()
    
    if choice in ['y', 'yes']:
        print("\nThanks for playing!")
        log_event("SYSTEM", "Player quit game")
        game_state['running'] = False
    else:
        print("Continuing game...")

# === [MAIN GAME LOOP] ===
def initialize_game() -> None:
    """Initialize the game state and data.
    
    Side effects:
        - Creates directories
        - Loads game data
        - Initializes player
        - Sets up logging
    """
    setup_directories()
    load_game_data()
    
    # Try to load existing save
    if not load_game():
        # Create new player
        game_state['player'] = Player()
        log_event("SYSTEM", "New game started")
    
    # Display title
    display_title()
    
    if game_state.get('first_play', True):
        print("Welcome to the Text RPG Adventure!")
        print("You find yourself in a small village tavern...")
        print("\nType 'help' at any time for available commands.")

def main():
    """Core game loop."""
    try:
        initialize_game()
        
        # Show initial room
        display_room()
        
        # Main game loop
        while game_state['running']:
            try:
                # Show appropriate display based on game mode
                if game_state['mode'] == 'combat':
                    display_combat_status()
                
                display_prompt()
                user_input = input().strip()
                
                if user_input:
                    process_command(user_input)
                    
            except KeyboardInterrupt:
                print("\n\nGame interrupted. Type 'quit' to exit properly.")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                break
                
    except Exception as e:
        print(f"Fatal error: {e}")
        log_event("FATAL", f"Game crashed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 