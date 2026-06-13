// progression.js - Shared Core Games Studio Progression Configuration

const PROGRESSION_TIERS = [
    { min: 2000, level: 6, title: 'Elite',    next: null },
    { min: 1000, level: 5, title: 'Veteran',  next: 2000 },
    { min: 500,  level: 4, title: 'Regular',  next: 1000 },
    { min: 250,  level: 3, title: 'Member',   next: 500  },
    { min: 100,  level: 2, title: 'Newcomer', next: 250  },
    { min: 0,    level: 1, title: 'Visitor',  next: 100  },
];

function getLevelInfo(xp) {
    for (let i = 0; i < PROGRESSION_TIERS.length; i++) {
        if (xp >= PROGRESSION_TIERS[i].min) return PROGRESSION_TIERS[i];
    }
    return PROGRESSION_TIERS[PROGRESSION_TIERS.length - 1];
}

// Automatically builds the HTML level table if the container exists on the page
function renderLevelTable(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Sort ascending for the display table layout
    const displayTiers = [...PROGRESSION_TIERS].reverse();
    
    let html = `
        <table class="level-table">
            <thead>
                <tr><th>Level</th><th>Title</th><th>XP Required (Total)</th></tr>
            </thead>
            <tbody>
    `;
    
    displayTiers.forEach(tier => {
        html += `<tr><td>${tier.level}</td><td>${tier.title}</td><td>${tier.min.toLocaleString()}</td></tr>`;
    });
    
    html += `</tbody></table>`;
    container.innerHTML = html;
}