async function loadInventory() {
  const userId = localStorage.getItem("userId");
  if (!userId) {
    alert("User ID not found.");
    return;
  }

  const res = await fetch(`/api/user-inventory?userId=${userId}`);
  const data = await res.json();

  const blueprintList = document.getElementById("blueprint-list");
  const inventoryList = document.getElementById("inventory-list");
  const blueprintHeader = document.getElementById("blueprint-header");

  if (data.unlocked && data.unlocked.length > 0) {
    blueprintHeader.textContent = `📜 Unlocked Blueprints (${data.unlocked.length}/12)`;
    data.unlocked.forEach(name => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>${name}</h3>`;
      blueprintList.appendChild(card);
    });
  } else {
    blueprintList.innerHTML = "<p>No blueprints unlocked yet.</p>";
  }

  if (data.inventory && data.inventory.length > 0) {
    const count = {};
    data.inventory.forEach(item => {
      count[item] = (count[item] || 0) + 1;
    });
    Object.entries(count).forEach(([item, qty]) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>${item}</h3><p>Quantity: ${qty}</p>`;
      inventoryList.appendChild(card);
    });
  } else {
    inventoryList.innerHTML = "<p>No items in inventory.</p>";
  }
}

loadInventory();
