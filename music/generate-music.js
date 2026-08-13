const fs = require("fs");
const path = require("path");

const CONFIG_PATH = path.join(__dirname, "music-config.json");

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    throw new Error("music-config.json not found");
  }

  return JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
}

function findMp3Files(folder) {
  if (!fs.existsSync(folder)) {
    return [];
  }

  return fs
    .readdirSync(folder)
    .filter((file) => file.toLowerCase().endsWith(".mp3"));
}

function main() {
  const config = loadConfig();

  console.log("🎵 Mystery AI Music System");
  console.log("--------------------------------");

  const defaultCategory = config.defaultCategory;
  const category = config.categories[defaultCategory];

  if (!category) {
    throw new Error(`Category "${defaultCategory}" not found in music-config.json`);
  }

  const musicFolder = path.join(process.cwd(), category.folder);

  console.log(`Category: ${defaultCategory}`);
  console.log(`Folder: ${category.folder}`);
  console.log(`Volume: ${category.volume}`);

  const tracks = findMp3Files(musicFolder);

  if (tracks.length === 0) {
    console.log("⚠️ No background music tracks found yet.");
    console.log(`Add MP3 files to: ${category.folder}`);
    return;
  }

  console.log(`✅ Found ${tracks.length} music track(s):`);

  tracks.forEach((track) => {
    console.log(`   🎵 ${track}`);
  });

  console.log("--------------------------------");
  console.log("✅ Music system check completed.");
}

main();
