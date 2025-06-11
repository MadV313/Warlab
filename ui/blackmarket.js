async function loadMarket() {
  const res = await fetch('../data/blackmarket_rotation.json');
  const data = await res.json();
  const marketList = document.getElementById("market-list");
  const countdown = document.getElementById("countdown");

  const expireTime = new Date(data.expires);
  const now = new Date();
  const timeDiff = expireTime - now;
  const minutes = Math.floor(timeDiff / 60000);
  countdown.textContent = `🕒 Next rotation in ~${minutes} minutes`;

  data.offers.forEach(item => {
    const card = document.createElement("div");
    const rarity = item.rarity.toLowerCase();
    card.classList.add("card", rarity);
    card.innerHTML = `
      <h3>${item.name}</h3>
      <p>Rarity: <strong>${item.rarity}</strong></p>
      <p>Cost: ${getCost(item.rarity)} Prestige</p>
    `;
    marketList.appendChild(card);
  });
}

function getCost(rarity) {
  switch (rarity) {
    case "Common": return 30;
    case "Uncommon": return 75;
    case "Rare": return 150;
    case "Legendary": return 300;
    default: return "?";
  }
}

loadMarket();

