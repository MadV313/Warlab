async function loadMarket() {
  const res = await fetch('../data/market_parts_rotation.json');
  const data = await res.json();
  const container = document.getElementById("market-list");
  const timer = document.getElementById("market-timer");

  const expireTime = new Date(data.expires);
  const now = new Date();
  const timeLeft = Math.max(0, expireTime - now);
  const mins = Math.floor(timeLeft / 60000);
  timer.textContent = `🕒 Market refreshes in ~${mins} minutes`;

  data.offers.forEach(item => {
    const card = document.createElement("div");
    const rarity = item.rarity.toLowerCase();
    card.className = `card ${rarity}`;
    card.innerHTML = `
      <h3>${item.name}</h3>
      <p>Rarity: <strong>${item.rarity}</strong></p>
      <p>Cost: ${getCost(item.rarity)} Prestige</p>
    `;
    container.appendChild(card);
  });
}

function getCost(rarity) {
  switch (rarity) {
    case "Common": return 15;
    case "Uncommon": return 40;
    case "Rare": return 90;
    case "Legendary": return 180;
    default: return "?";
  }
}

loadMarket();
