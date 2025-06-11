// public/renderBlueprints.js

async function loadBlueprints() {
  const userId = "user_123"; // Placeholder until Discord integration

  const [userRes, masterRes] = await Promise.all([
    fetch('../data/user_profiles.json'),
    fetch('../data/blackmarket_items_master.json')
  ]);

  const userData = await userRes.json();
  const masterData = await masterRes.json();

  const user = userData[userId] || { blueprints: [], inventory: {} };

  const blueprintList = document.getElementById("blueprints");
  const inventoryList = document.getElementById("inventory");
  const ownedBlueprints = user.blueprints || [];
  const allBlueprintNames = Object.keys(masterData);

  // === BLUEPRINT PROGRESS ===
  document.getElementById("progress").textContent = `Blueprints Unlocked: ${ownedBlueprints.length} / ${allBlueprintNames.length}`;

  // === BLUEPRINT CARDS ===
  allBlueprintNames.forEach(name => {
    const data = masterData[name];
    const owned = ownedBlueprints.includes(name);

    const card = document.createElement("div");
    card.className = `card ${owned ? 'owned' : 'missing'}`;
    card.innerHTML = `
      <h3>${name}</h3>
      <p>Type: ${data.type}</p>
      <p>Rarity: ${data.rarity}</p>
      <p>Tags: ${data.tags.join(", ")}</p>
    `;
    blueprintList.appendChild(card);
  });

  // === INVENTORY CARDS ===
  const invEntries = Object.entries(user.inventory || {});
  invEntries.sort((a, b) => a[0].localeCompare(b[0]));
  invEntries.forEach(([item, count]) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h4>${item}</h4><p>Qty: ${count}</p>`;
    inventoryList.appendChild(card);
  });
}

loadBlueprints();
