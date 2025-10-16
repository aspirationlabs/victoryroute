import * as fs from "fs";
import * as path from "path";

const SHOWDOWN_PATH =
  process.env.SHOWDOWN_DIR ||
  path.join(process.env.HOME!, "workspace", "third_party", "pokemon-showdown");
const OUTPUT_DIR = path.join(__dirname, "..", "..", "data", "game");

require("ts-node").register({
  transpileOnly: true,
  compilerOptions: {
    module: "commonjs",
  },
});

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

console.log("Loading Showdown data from:", SHOWDOWN_PATH);

const { Natures } = require(path.join(SHOWDOWN_PATH, "data", "natures.ts"));
const { TypeChart } = require(path.join(SHOWDOWN_PATH, "data", "typechart.ts"));
const { Moves } = require(path.join(SHOWDOWN_PATH, "data", "moves.ts"));
const { Abilities } = require(path.join(SHOWDOWN_PATH, "data", "abilities.ts"));
const { Items } = require(path.join(SHOWDOWN_PATH, "data", "items.ts"));
const { Pokedex } = require(path.join(SHOWDOWN_PATH, "data", "pokedex.ts"));
const { AbilitiesText } = require(
  path.join(SHOWDOWN_PATH, "data", "text", "abilities.ts"),
);
const { ItemsText } = require(
  path.join(SHOWDOWN_PATH, "data", "text", "items.ts"),
);
const { MovesText } = require(
  path.join(SHOWDOWN_PATH, "data", "text", "moves.ts"),
);

const DAMAGE_MULTIPLIERS: Record<number, number> = {
  0: 1.0,
  1: 2.0,
  2: 0.5,
  3: 0.0,
};

const BASE_POWER_CALLBACK_TYPES: Record<string, string> = {
  eruption: "hp_based_attacker",
  waterspout: "hp_based_attacker",
  crushgrip: "hp_based_defender",
  wringout: "hp_based_defender",
  electroball: "speed_ratio",
  gyroball: "inverse_speed_ratio",
  heavyslam: "weight_ratio",
  heatcrash: "weight_ratio",
  lowkick: "target_weight",
  grassknot: "target_weight",
  storedpower: "positive_boosts",
  powertrip: "positive_boosts",
};

function extractSecondaryEffects(moveData: any): any[] | null {
  const rawSecondaries: any[] = [];

  if (moveData.secondary) {
    rawSecondaries.push(moveData.secondary);
  }
  if (Array.isArray(moveData.secondaries)) {
    for (const secondary of moveData.secondaries) {
      if (secondary) {
        rawSecondaries.push(secondary);
      }
    }
  }

  const effects: any[] = [];
  for (const effect of rawSecondaries) {
    const chance = effect.chance ?? 100;
    if (effect.status) {
      effects.push({
        chance,
        status: effect.status,
      });
    }

    if (effect.boosts) {
      effects.push({
        chance,
        boosts: effect.boosts,
      });
    }

    if (effect.volatileStatus) {
      effects.push({
        chance,
        volatile_status: effect.volatileStatus,
      });
    }
  }

  return effects.length > 0 ? effects : null;
}

function transformNatures(raw: any): any[] {
  const natures: any[] = [];
  for (const [natureId, natureData] of Object.entries<any>(raw)) {
    natures.push({
      name: natureData.name,
      plus_stat: natureData.plus || null,
      minus_stat: natureData.minus || null,
    });
  }
  return natures;
}

function transformTypeChart(raw: any): any[] {
  const typeEffectiveness: Record<string, Record<string, number>> = {};

  for (const [defendingType, typeData] of Object.entries<any>(raw)) {
    if (!typeData.damageTaken) continue;

    const damageTaken = typeData.damageTaken;

    for (const [attackingType, damageCode] of Object.entries<any>(
      damageTaken,
    )) {
      if (["prankster", "par"].includes(attackingType)) continue;
      if (typeof damageCode !== "number") continue;

      const attackingTypeLower = attackingType.toLowerCase();
      const defendingTypeLower = defendingType.toLowerCase();

      if (!(attackingTypeLower in typeEffectiveness)) {
        typeEffectiveness[attackingTypeLower] = {};
      }

      const multiplier = DAMAGE_MULTIPLIERS[damageCode] ?? 1.0;
      typeEffectiveness[attackingTypeLower][defendingTypeLower] = multiplier;
    }
  }

  return [{ effectiveness: typeEffectiveness }];
}

function transformMoves(raw: any, textData: any): any[] {
  const moves: any[] = [];
  for (const [moveId, moveData] of Object.entries<any>(raw)) {
    let accuracy = moveData.accuracy;
    if (accuracy === true) {
      accuracy = null;
    }

    const basePower = moveData.basePower ?? 0;

    const textEntry = textData[moveId];
    const description = textEntry?.desc || textEntry?.shortDesc || "";

    const secondaryEffects = extractSecondaryEffects(moveData);
    const hasSecondaryEffect = Boolean(secondaryEffects);

    const moveEntry: any = {
      name: moveData.name,
      num: moveData.num,
      type: moveData.type,
      base_power: basePower,
      accuracy: accuracy,
      pp: moveData.pp,
      priority: moveData.priority,
      category: moveData.category,
      description: description,
      base_power_callback_type:
        BASE_POWER_CALLBACK_TYPES[moveId as string] || null,
      recoil: moveData.recoil ?? null,
      drain: moveData.drain ?? null,
      secondary_effects: secondaryEffects,
      has_secondary_effect: hasSecondaryEffect,
      flags: moveData.flags ? Object.keys(moveData.flags) : [],
    };

    if (moveData.multihit) {
      moveEntry.multihit = moveData.multihit;
    }

    moves.push(moveEntry);
  }
  return moves;
}

function transformAbilities(raw: any, textData: any): any[] {
  const abilities: any[] = [];
  for (const [abilityId, abilityData] of Object.entries<any>(raw)) {
    const textEntry = textData[abilityId];
    const description = textEntry?.shortDesc || textEntry?.desc || "";

    abilities.push({
      name: abilityData.name,
      num: abilityData.num,
      rating: abilityData.rating ?? 0.0,
      description: description,
    });
  }
  return abilities;
}

function transformItems(raw: any, textData: any): any[] {
  const items: any[] = [];
  for (const [itemId, itemData] of Object.entries<any>(raw)) {
    const itemText = textData[itemId];
    let description = null;

    if (itemText) {
      // Prefer 'description' if available, otherwise use 'shortDesc'
      // Ignore generation-specific descriptions (gen7, gen6, etc.)
      description = itemText.description || itemText.shortDesc || null;
    }

    items.push({
      name: itemData.name,
      num: itemData.num,
      gen: itemData.gen ?? 0,
      description: description,
    });
  }
  return items;
}

function transformPokemon(raw: any): any[] {
  const pokemonList: any[] = [];
  for (const [speciesId, speciesData] of Object.entries<any>(raw)) {
    if (!("num" in speciesData)) continue;

    pokemonList.push({
      name: speciesData.name,
      num: speciesData.num,
      types: speciesData.types,
      base_stats: speciesData.baseStats,
      abilities: speciesData.abilities,
      weight_kg: speciesData.weightkg ?? null,
    });
  }
  return pokemonList;
}

console.log("Transforming and writing natures...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "natures.json"),
  JSON.stringify(transformNatures(Natures), null, 2),
);

console.log("Transforming and writing typechart...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "type_chart.json"),
  JSON.stringify(transformTypeChart(TypeChart), null, 2),
);

console.log("Transforming and writing moves...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "moves.json"),
  JSON.stringify(transformMoves(Moves, MovesText), null, 2),
);

console.log("Transforming and writing abilities...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "abilities.json"),
  JSON.stringify(transformAbilities(Abilities, AbilitiesText), null, 2),
);

console.log("Transforming and writing items...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "items.json"),
  JSON.stringify(transformItems(Items, ItemsText), null, 2),
);

console.log("Transforming and writing pokedex...");
fs.writeFileSync(
  path.join(OUTPUT_DIR, "pokemon.json"),
  JSON.stringify(transformPokemon(Pokedex), null, 2),
);

console.log("Done! All data synced to:", OUTPUT_DIR);
