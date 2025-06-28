# Text RPG Adventure - Phase 4: Quests & Polish

A comprehensive text-based RPG built with Python, featuring a complete quest system, combat mechanics, character progression, economic gameplay, and advanced social systems.

## 🌟 Version 1.0.0 - Phase 4 Features

### 📜 Quest System
- **Dynamic Quest Tracking**: Accept up to 5 concurrent quests
- **Multiple Quest Types**: Kill, collect, visit, and delivery quests
- **NPC Quest Givers**: Barkeep, merchant, guard, and villager offer unique quests
- **Quest Rewards**: Bonus XP (50% multiplier), gold, and rare items
- **Progress Tracking**: Real-time objective completion monitoring

### ⚔️ Combat System
- **Turn-based Combat**: Strategic attack, defend, use item, and flee options
- **3 Enemy Types**: Goblins, wolves, and bandits with unique AI patterns
- **Equipment System**: Weapons and armor affect combat performance
- **Visual Health Bars**: See health status at a glance
- **Quest Integration**: Enemy kills automatically tracked for quest objectives

### 📈 Character Progression
- **10-Level System**: Gain XP to level up with increasing requirements
- **Stat Growth**: +2 Strength, +1 Defense, +5 Max HP per level
- **XP Sources**: Combat victories and quest completion with bonus multipliers
- **Visual Progress**: XP bar shows progress to next level

### 💰 Economy System
- **Merchant Trading**: Buy premium items at 150% value, sell at 60%
- **Healing Services**: Tavern healing at 1 gold per HP
- **Legendary Items**: High-end equipment for dedicated players
- **Quest Rewards**: Additional income through quest completion

### 🤝 Social Systems
- **Faction Reputation**: Build relationships with different factions (-100 to +100)
- **NPC Relationships**: Individual relationship tracking with NPCs
- **World Impact Tracking**: Your actions affect the game world
- **Dynamic Interactions**: NPC responses change based on your reputation

### 🗺️ Game World
- **9 Interconnected Rooms**: Tavern, town square, shops, forests, caves, and ancient ruins
- **Interactive Objects**: Examine marked objects **[like this]** for detailed descriptions
- **Item Placement**: Strategic item locations encourage exploration
- **Environmental Storytelling**: Rich descriptions create immersive atmosphere
- **Recall System**: Fast travel back to town when needed

### 🎮 Gameplay Features
- **Smart Command Parser**: Natural language commands with aliases (n/s/e/w, l=look, x=examine)
- **Unlimited Inventory**: Carry as many items as you find
- **Equipment System**: Separate weapon and armor slots
- **Save/Load System**: Persistent game state with JSON serialization
- **Debug Tools**: Development commands for testing and balancing

## 🎯 Available Quests

### 1. **Pest Control**
- **Giver**: Barkeep
- **Objective**: Defeat 3 goblins
- **Rewards**: 50 XP + 25 bonus XP, 25 gold

### 2. **Gathering Pelts**
- **Giver**: Merchant
- **Objective**: Collect 2 wolf pelts
- **Rewards**: 75 XP + 37 bonus XP, 50 gold, health potion

### 3. **Security Patrol**
- **Giver**: Guard
- **Objective**: Defeat 2 bandits
- **Rewards**: 100 XP + 50 bonus XP, 75 gold, iron sword

### 4. **Lost Treasure**
- **Giver**: Villager
- **Objectives**: Visit ancient ruins + collect rusty dagger
- **Rewards**: 125 XP + 62 bonus XP, 100 gold

### 5. **Apprentice Trial**
- **Giver**: Barkeep
- **Objectives**: Defeat 1 goblin + visit forest path + obtain health potion
- **Rewards**: 150 XP + 75 bonus XP, 60 gold, leather armor

## 🎮 How to Play

### Starting Out
1. **Talk to NPCs**: Use `talk barkeep` to discover available quests
2. **Accept Quests**: Use `accept pest_control` to begin your first quest
3. **Check Progress**: Use `quests` to view your quest log anytime
4. **Explore Safely**: Start in the tavern and town square (safe zones)

### Combat Tips
- **Defend Strategically**: Defending gives +50% defense for that turn
- **Use Items**: Health potions can turn the tide of battle
- **Flee When Necessary**: Low health? Better to flee and heal up
- **Equipment Matters**: Better weapons and armor make combat easier

### Progression Strategy
- **Complete Quests**: Quest XP has a 50% bonus multiplier
- **Level Up Efficiently**: Each level significantly improves your stats
- **Manage Economy**: Save gold for premium equipment and healing
- **Explore Thoroughly**: Hidden items and areas await discovery

## 📋 Command Reference

### Movement
- `go north` or `north` or `n` - Move in that direction
- `look` or `l` - Examine current room
- `examine <object>` or `x <object>` - Look at something closely

### Inventory & Items
- `take <item>` - Pick up an item
- `drop <item>` - Drop an item from inventory
- `inventory` or `i` - View your items
- `use <item>` - Use/equip an item

### Combat
- `attack` - Strike the enemy
- `defend` - Boost defense by 50% this turn
- `use <item>` - Use a consumable item
- `flee` - Attempt to escape combat

### Quests
- `talk <npc>` - Speak with NPCs to discover quests
- `accept <quest_id>` - Accept a quest from an NPC
- `quests` - View your quest log
- `complete <quest_id>` - Turn in a completed quest

### Economy
- `buy <item>` - Purchase from merchant
- `sell <item>` - Sell to merchant
- `heal` - Use healing services at tavern (1 gold per HP)

### Character
- `stats` - View character information and progression
- `reputation` - View faction standings and NPC relationships
- `recall` - Fast travel back to town
- `save` - Save your game progress
- `help [topic]` - Get help on commands or specific topics

## 🏗️ Technical Implementation

### Architecture
- **Single-file Design**: All game logic in main.py for maximum clarity and LLM visibility
- **Data-driven Content**: JSON files for rooms, items, enemies, combat text, and quests
- **Modular Systems**: Separate systems for combat, quests, economy, progression, and social interactions

### Data Files
- `rooms.json` - 9 rooms with rich descriptions and interactive objects (2151 lines)
- `items.json` - Comprehensive item database with weapons, armor, consumables, and quest items (1097 lines)
- `enemies.json` - 3 enemy types with unique AI patterns and loot tables (822 lines)
- `combat_text.json` - 88+ varied combat messages for immersion (88 lines)
- `quests.json` - 5 quests with multiple objective types and rewards (655 lines)

### Advanced Features
- **Faction System**: Track reputation with different groups
- **Relationship Tracking**: Individual NPC relationship management
- **World State Management**: Global flags and action tracking
- **Dynamic Content**: Game world responds to player actions

### Save System
- **JSON Serialization**: Complete game state preservation
- **Player Data**: Stats, inventory, equipment, quest progress, and social standings
- **Respawn System**: Death penalty with safe respawn location

## 🚀 Development Phases

### ✅ Phase 1: Foundation
- Room navigation and descriptions
- Inventory management and interaction
- Command parser with natural language support
- Save/load functionality

### ✅ Phase 2: Combat System
- Turn-based combat mechanics
- Enemy AI with different patterns
- Equipment and damage calculations
- Combat text variety

### ✅ Phase 3: Progression Loop
- Experience points and leveling
- Stat growth and character advancement
- Economy with merchant trading
- Equipment upgrade path

### ✅ Phase 4: Quests & Polish
- Complete quest system with multiple types
- NPC interactions and quest givers
- Quest tracking and reward system
- Final polish and balance improvements

## 🎯 Future Enhancements

While Phase 4 represents a complete game, potential expansions could include:
- **Magic System**: Spells and magical abilities
- **Crafting**: Create items from gathered materials
- **Multiple Areas**: Expand beyond the village
- **Character Classes**: Different playstyles and abilities
- **Multiplayer**: Shared adventures with friends

---

**Enjoy your adventure!** This RPG offers hours of gameplay with its quest system, character progression, and rich world to explore. 